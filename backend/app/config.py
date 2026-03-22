from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Hybrid Crypto Bot'
    database_url: str = 'sqlite:///./data/hybrid_bot.db'
    default_symbol: str = 'BTC'
    default_interval: str = '1h'
    loop_seconds: int = 300
    starting_cash: float = 10_000.0
    risk_per_trade: float = 0.0075
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    max_notional_pct: float = 0.20
    max_daily_loss_pct: float = 0.03
    max_trades_per_day: int = 6
    max_consecutive_losses: int = 3
    cooldown_minutes: int = 30
    ai_min_confidence: float = 0.67
    ai_regime_min_confidence: float = 0.60
    require_ai_agreement: bool = True
    enable_live_trading: bool = False
    fee_bps: float = 5.0
    trailing_stop_atr_multiple: float = 1.0
    mode: str = 'paper'  # paper | live

    openai_api_key: str | None = None
    openai_model: str = 'gpt-5-mini'
    openai_base_url: str | None = None
    ai_enabled: bool = True

    hyperliquid_base_url: str = 'https://api.hyperliquid.xyz'
    hyperliquid_testnet: bool = False
    hyperliquid_wallet_address: str | None = None
    hyperliquid_api_wallet_private_key: str | None = Field(default=None, repr=False)


settings = Settings()
