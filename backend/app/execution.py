from __future__ import annotations

from dataclasses import dataclass

from .config import settings


@dataclass
class ExecutionResult:
    accepted: bool
    message: str
    fill_price: float | None = None


class PaperExecutor:
    def place_market_order(self, symbol: str, side: str, quantity: float, price: float) -> ExecutionResult:
        return ExecutionResult(True, f'Paper {side} {quantity:.6f} {symbol} at {price:.2f}', price)


class HyperliquidLiveExecutor:
    def place_market_order(self, symbol: str, side: str, quantity: float, price: float) -> ExecutionResult:
        if not settings.enable_live_trading:
            return ExecutionResult(False, 'Live trading is disabled. Set ENABLE_LIVE_TRADING=true only after you finish paper testing.')
        if not settings.hyperliquid_wallet_address or not settings.hyperliquid_api_wallet_private_key:
            return ExecutionResult(False, 'Live mode requires Hyperliquid wallet settings in .env.')
        return ExecutionResult(
            False,
            'Live execution remains behind a guardrail in this starter. Wire in the official Hyperliquid SDK and test tiny size first.',
        )
