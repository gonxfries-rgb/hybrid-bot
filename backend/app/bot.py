from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlmodel import Session, select

from .ai import AIAdvisor
from .config import settings
from .execution import HyperliquidLiveExecutor, PaperExecutor
from .market import HyperliquidMarketClient
from .models import BotState, LogEvent, Position, Trade
from .strategy import choose_proposal, compute_features


class BotEngine:
    def __init__(self) -> None:
        self.market = HyperliquidMarketClient()
        self.ai = AIAdvisor()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def ensure_state(self, session: Session) -> BotState:
        state = session.exec(select(BotState).where(BotState.id == 1)).first()
        if state:
            return state
        state = BotState(
            id=1,
            mode=settings.mode,
            running=False,
            symbol=settings.default_symbol,
            interval=settings.default_interval,
            cash=settings.starting_cash,
            equity=settings.starting_cash,
            ai_enabled=settings.ai_enabled,
        )
        session.add(state)
        session.commit()
        session.refresh(state)
        return state

    def log(self, session: Session, message: str, level: str = 'INFO') -> None:
        session.add(LogEvent(message=message, level=level))
        session.commit()

    def start(self, session_factory) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(session_factory,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run_loop(self, session_factory) -> None:
        while not self._stop.is_set():
            with session_factory() as session:
                state = self.ensure_state(session)
                if state.running:
                    try:
                        self.tick(session)
                    except Exception as exc:  # noqa: BLE001
                        self.log(session, f'Tick failed: {exc}', level='ERROR')
                session.commit()
            self._stop.wait(settings.loop_seconds)

    def _daily_loss_hit(self, state: BotState) -> bool:
        return state.daily_pnl <= -abs(settings.max_daily_loss_pct * settings.starting_cash)

    def _reset_daily_counters(self, state: BotState) -> None:
        now = datetime.now(timezone.utc)
        if state.daily_reset_at.date() != now.date():
            state.daily_pnl = 0.0
            state.trades_today = 0
            state.daily_reset_at = now
            state.kill_switch = False

    def _cooldown_active(self, state: BotState) -> bool:
        return bool(state.cooldown_until and state.cooldown_until > datetime.now(timezone.utc))

    def _open_position(self, session: Session, state: BotState) -> Position | None:
        return session.exec(select(Position).where(Position.status == 'open', Position.symbol == state.symbol)).first()

    def _mark_position(self, position: Position, price: float) -> None:
        position.mark_price = price
        if position.side == 'long':
            position.unrealized_pnl = (price - position.entry_price) * position.quantity
        else:
            position.unrealized_pnl = (position.entry_price - price) * position.quantity

    def _update_trailing_stop(self, position: Position, price: float, atr: float) -> None:
        trail_distance = max(atr * settings.trailing_stop_atr_multiple, 0.0)
        if trail_distance <= 0:
            return
        if position.side == 'long':
            candidate = price - trail_distance
            position.trailing_stop = max(position.trailing_stop or position.stop_loss, candidate)
            position.stop_loss = max(position.stop_loss, position.trailing_stop)
        else:
            candidate = price + trail_distance
            position.trailing_stop = min(position.trailing_stop or position.stop_loss, candidate)
            position.stop_loss = min(position.stop_loss, position.trailing_stop)

    def _revalue(self, session: Session, state: BotState, price: float, atr: float) -> None:
        open_positions = session.exec(select(Position).where(Position.status == 'open')).all()
        unrealized = 0.0
        for pos in open_positions:
            if pos.symbol == state.symbol:
                self._mark_position(pos, price)
                self._update_trailing_stop(pos, price, atr)
            unrealized += pos.unrealized_pnl
            session.add(pos)
        state.unrealized_pnl = unrealized
        state.equity = state.cash + unrealized
        state.last_price = price
        state.updated_at = datetime.now(timezone.utc)
        session.add(state)

    def _estimate_fees(self, quantity: float, price: float) -> float:
        return quantity * price * (settings.fee_bps / 10_000)

    def _close_position(self, session: Session, state: BotState, position: Position, price: float, reason: str) -> None:
        self._mark_position(position, price)
        fees = self._estimate_fees(position.quantity, price)
        position.status = 'closed'
        position.closed_at = datetime.now(timezone.utc)
        position.exit_price = price
        position.realized_pnl = position.unrealized_pnl - fees
        state.cash += position.realized_pnl
        state.realized_pnl += position.realized_pnl
        state.daily_pnl += position.realized_pnl
        if position.realized_pnl >= 0:
            state.wins += 1
            state.consecutive_losses = 0
        else:
            state.losses += 1
            state.consecutive_losses += 1
            if state.consecutive_losses >= settings.max_consecutive_losses:
                state.kill_switch = True
                state.last_decision_reason = 'Kill switch armed after too many consecutive losses.'
        state.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=settings.cooldown_minutes)
        trade_side = 'sell' if position.side == 'long' else 'buy'
        session.add(
            Trade(
                symbol=position.symbol,
                side=trade_side,
                quantity=position.quantity,
                price=price,
                notional=position.quantity * price,
                fees=fees,
                mode=state.mode,
                position_id=position.id,
                reason=reason,
            )
        )
        session.add(position)
        self.log(session, f'Closed {position.side} {position.symbol}: {reason}. PnL={position.realized_pnl:.2f}')

    def _guard_reason(self, state: BotState, regime: dict, filter_result: dict, proposal) -> str | None:
        if state.kill_switch:
            return 'Kill switch is active.'
        if self._daily_loss_hit(state):
            state.kill_switch = True
            return 'Daily loss limit hit.'
        if state.trades_today >= settings.max_trades_per_day:
            return 'Max trades for the day reached.'
        if self._cooldown_active(state):
            return 'Cooldown active after the last close.'
        if regime['confidence'] < settings.ai_regime_min_confidence:
            return f"Regime confidence {regime['confidence']:.2f} is below threshold."
        if filter_result['confidence'] < settings.ai_min_confidence:
            return f"Filter confidence {filter_result['confidence']:.2f} is below threshold."
        if not filter_result['allow_trade']:
            return 'AI trade filter vetoed the trade.'
        if settings.require_ai_agreement:
            if proposal.side == 'long' and filter_result['bias'] != 'bullish':
                return 'AI bias does not confirm the long trade.'
            if proposal.side == 'short' and filter_result['bias'] != 'bearish':
                return 'AI bias does not confirm the short trade.'
        return None

    def tick(self, session: Session) -> dict:
        state = self.ensure_state(session)
        self._reset_daily_counters(state)
        snapshot = self.market.get_snapshot(state.symbol, state.interval)
        candles_df = pd.DataFrame(snapshot.candles)
        features = compute_features(candles_df)
        regime = self.ai.classify_regime(
            {
                'symbol': state.symbol,
                'interval': state.interval,
                'headline_summary': snapshot.headline_summary,
                'features': features,
            }
        )
        proposal = choose_proposal(regime['regime'], features)
        filter_result = self.ai.filter_trade(
            {
                'symbol': state.symbol,
                'interval': state.interval,
                'headline_summary': snapshot.headline_summary,
                'regime': regime,
                'proposal': proposal.__dict__,
                'features': features,
                'risk_context': {
                    'mode': state.mode,
                    'equity': state.equity,
                    'cash': state.cash,
                    'max_notional_pct': settings.max_notional_pct,
                    'daily_pnl': state.daily_pnl,
                    'trades_today': state.trades_today,
                },
            }
        )
        state.last_regime = regime['regime']
        state.last_regime_confidence = float(regime['confidence'])
        state.last_ai_confidence = float(filter_result['confidence'])
        state.last_ai_summary = f"{regime['summary']} | {filter_result['summary']}"
        state.last_signal = proposal.side

        price = snapshot.price
        current = self._open_position(session, state)
        self._revalue(session, state, price, float(features['atr']))

        if current:
            if current.side == 'long' and (price <= current.stop_loss or price >= current.take_profit):
                self._close_position(session, state, current, price, 'stop/take triggered')
            elif current.side == 'short' and (price >= current.stop_loss or price <= current.take_profit):
                self._close_position(session, state, current, price, 'stop/take triggered')
            elif proposal.side != 'hold' and proposal.side != current.side and filter_result['allow_trade']:
                self._close_position(session, state, current, price, 'signal reversal')

        current = self._open_position(session, state)
        guard_reason = self._guard_reason(state, regime, filter_result, proposal) if proposal.side in {'long', 'short'} else 'No actionable trade proposal.'
        state.last_decision_reason = guard_reason or f'Allowed: {proposal.strategy} {proposal.side}.'

        if current is None and proposal.side in {'long', 'short'} and guard_reason is None:
            risk_capital = max(state.equity * settings.risk_per_trade, 1.0)
            stop_distance = abs(proposal.entry_price - proposal.stop_loss)
            quantity = risk_capital / max(stop_distance, 1e-6)
            max_notional = state.equity * settings.max_notional_pct
            quantity = min(quantity, max_notional / proposal.entry_price)
            if quantity > 0:
                executor = PaperExecutor() if state.mode == 'paper' else HyperliquidLiveExecutor()
                side = 'buy' if proposal.side == 'long' else 'sell'
                result = executor.place_market_order(state.symbol, side, quantity, price)
                if result.accepted:
                    fees = self._estimate_fees(quantity, price)
                    state.trades_today += 1
                    state.cash -= fees
                    position = Position(
                        symbol=state.symbol,
                        side=proposal.side,
                        quantity=quantity,
                        entry_price=price,
                        mark_price=price,
                        stop_loss=proposal.stop_loss,
                        take_profit=proposal.take_profit,
                        trailing_stop=proposal.stop_loss,
                        strategy_name=proposal.strategy,
                        regime=regime['regime'],
                        rationale=f"{proposal.rationale} {filter_result['summary']}",
                    )
                    session.add(position)
                    session.commit()
                    session.refresh(position)
                    session.add(
                        Trade(
                            symbol=state.symbol,
                            side=side,
                            quantity=quantity,
                            price=price,
                            notional=quantity * price,
                            fees=fees,
                            mode=state.mode,
                            position_id=position.id,
                            reason=position.rationale,
                        )
                    )
                    self.log(session, f'Opened {proposal.side} {state.symbol} using {proposal.strategy}.')
                else:
                    state.last_decision_reason = result.message
                    self.log(session, result.message, level='WARNING')

        session.add(state)
        session.commit()
        return {
            'symbol': state.symbol,
            'price': price,
            'regime': regime,
            'proposal': proposal.__dict__,
            'filter': filter_result,
            'decision_reason': state.last_decision_reason,
        }
