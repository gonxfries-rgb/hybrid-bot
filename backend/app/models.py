from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str
    side: str  # long | short
    quantity: float
    entry_price: float
    mark_price: float
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    status: str = 'open'
    opened_at: datetime = Field(default_factory=utc_now)
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    strategy_name: str = ''
    regime: str = 'unknown'
    rationale: str = ''


class Trade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str
    side: str  # buy | sell
    quantity: float
    price: float
    notional: float
    fees: float = 0.0
    mode: str = 'paper'
    position_id: Optional[int] = None
    reason: str = ''
    created_at: datetime = Field(default_factory=utc_now)


class LogEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    level: str = 'INFO'
    message: str
    created_at: datetime = Field(default_factory=utc_now)


class BotState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mode: str = 'paper'
    running: bool = False
    symbol: str = 'BTC'
    interval: str = '1h'
    base_strategy: str = 'hybrid'
    ai_enabled: bool = True
    kill_switch: bool = False
    last_price: float = 0.0
    cash: float = 10_000.0
    equity: float = 10_000.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    daily_pnl: float = 0.0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    trades_today: int = 0
    cooldown_until: Optional[datetime] = None
    last_signal: str = 'hold'
    last_regime: str = 'unknown'
    last_ai_confidence: float = 0.0
    last_regime_confidence: float = 0.0
    last_ai_summary: str = ''
    last_decision_reason: str = ''
    updated_at: datetime = Field(default_factory=utc_now)
    daily_reset_at: datetime = Field(default_factory=utc_now)
