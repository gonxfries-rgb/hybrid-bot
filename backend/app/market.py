from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

from .config import settings


@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    candles: list[dict[str, Any]]
    headline_summary: str


class HyperliquidMarketClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.hyperliquid_base_url

    def _post(self, body: dict[str, Any]) -> Any:
        response = requests.post(
            f'{self.base_url}/info',
            json=body,
            headers={'Content-Type': 'application/json'},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def get_mid(self, symbol: str) -> float:
        data = self._post({'type': 'allMids'})
        if symbol not in data:
            raise KeyError(f'{symbol} not found in allMids response')
        return float(data[symbol])

    def get_candles(self, symbol: str, interval: str = '1h', lookback: int = 200) -> pd.DataFrame:
        body = {
            'type': 'candleSnapshot',
            'req': {
                'coin': symbol,
                'interval': interval,
                'startTime': 0,
                'endTime': 2**63 - 1,
            },
        }
        data = self._post(body)
        if not isinstance(data, list) or not data:
            raise ValueError('No candle data returned from Hyperliquid')
        trimmed = data[-lookback:]
        df = pd.DataFrame(trimmed)
        # Hyperliquid fields are strings; map defensively.
        rename_map = {'T': 'time', 't': 'time', 'c': 'close', 'o': 'open', 'h': 'high', 'l': 'low', 'v': 'volume'}
        df = df.rename(columns=rename_map)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], unit='ms', utc=True)
        return df

    def get_snapshot(self, symbol: str, interval: str = '1h', lookback: int = 200) -> MarketSnapshot:
        price = self.get_mid(symbol)
        candles_df = self.get_candles(symbol, interval=interval, lookback=lookback)
        headline_summary = (
            'No external news feed configured yet. AI will reason over recent market structure only until '
            'you connect a news source.'
        )
        return MarketSnapshot(
            symbol=symbol,
            price=price,
            candles=candles_df.to_dict(orient='records'),
            headline_summary=headline_summary,
        )
