from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Proposal:
    strategy: str
    side: str  # long | short | hold
    entry_price: float
    stop_loss: float
    take_profit: float
    rationale: str


def compute_features(df: pd.DataFrame) -> dict[str, float | list[float]]:
    out = df.copy()
    out['ema_fast'] = out['close'].ewm(span=12, adjust=False).mean()
    out['ema_slow'] = out['close'].ewm(span=26, adjust=False).mean()
    delta = out['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    out['rsi'] = 100 - (100 / (1 + rs))
    high_low = out['high'] - out['low']
    high_close = (out['high'] - out['close'].shift()).abs()
    low_close = (out['low'] - out['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    out['atr'] = tr.rolling(14).mean()
    out['returns'] = out['close'].pct_change()
    recent = out.tail(60)
    close = float(out['close'].iloc[-1])
    atr = float(out['atr'].iloc[-1]) if pd.notna(out['atr'].iloc[-1]) else max(close * 0.01, 1.0)
    ema_fast = float(out['ema_fast'].iloc[-1])
    ema_slow = float(out['ema_slow'].iloc[-1])
    trend_strength = (ema_fast - ema_slow) / close if close else 0.0
    range_width_pct = ((float(recent['high'].max()) - float(recent['low'].min())) / close) if close else 0.0
    return {
        'close': close,
        'ema_fast': ema_fast,
        'ema_slow': ema_slow,
        'trend_strength': trend_strength,
        'rsi': float(out['rsi'].fillna(50).iloc[-1]),
        'atr': atr,
        'atr_pct': atr / close if close else 0.0,
        'recent_high': float(recent['high'].max()),
        'recent_low': float(recent['low'].min()),
        'range_width_pct': range_width_pct,
        'recent_closes': [float(x) for x in recent['close'].tolist()[-20:]],
    }


def ema_trend(features: dict[str, float]) -> Proposal:
    price = float(features['close'])
    atr = float(features['atr'])
    if features['ema_fast'] > features['ema_slow']:
        return Proposal('ema_trend', 'long', price, price - 1.6 * atr, price + 3.2 * atr, 'Fast EMA is above slow EMA.')
    if features['ema_fast'] < features['ema_slow']:
        return Proposal('ema_trend', 'short', price, price + 1.6 * atr, price - 3.2 * atr, 'Fast EMA is below slow EMA.')
    return Proposal('ema_trend', 'hold', price, price, price, 'EMAs are flat.')


def rsi_mean_reversion(features: dict[str, float]) -> Proposal:
    price = float(features['close'])
    atr = float(features['atr'])
    rsi = float(features['rsi'])
    if rsi <= 28:
        return Proposal('rsi_mean_reversion', 'long', price, price - 1.1 * atr, price + 1.9 * atr, 'RSI is deeply oversold.')
    if rsi >= 72:
        return Proposal('rsi_mean_reversion', 'short', price, price + 1.1 * atr, price - 1.9 * atr, 'RSI is deeply overbought.')
    return Proposal('rsi_mean_reversion', 'hold', price, price, price, 'RSI is neutral.')


def breakout(features: dict[str, float]) -> Proposal:
    price = float(features['close'])
    atr = float(features['atr'])
    recent_high = float(features['recent_high'])
    recent_low = float(features['recent_low'])
    if price >= recent_high * 0.9995:
        return Proposal('breakout', 'long', price, price - 1.25 * atr, price + 2.7 * atr, 'Price is testing the recent high.')
    if price <= recent_low * 1.0005:
        return Proposal('breakout', 'short', price, price + 1.25 * atr, price - 2.7 * atr, 'Price is testing the recent low.')
    return Proposal('breakout', 'hold', price, price, price, 'No breakout trigger.')


def choose_proposal(regime: str, features: dict[str, float]) -> Proposal:
    if regime == 'trend':
        return ema_trend(features)
    if regime == 'range':
        return rsi_mean_reversion(features)
    if regime == 'breakout':
        return breakout(features)
    return Proposal('none', 'hold', float(features['close']), float(features['close']), float(features['close']), 'Risk-off regime.')
