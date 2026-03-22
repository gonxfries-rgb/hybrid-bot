from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import settings


REGIME_SCHEMA = {
    'name': 'regime_selection',
    'schema': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'regime': {'type': 'string', 'enum': ['trend', 'range', 'breakout', 'risk_off']},
            'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
            'summary': {'type': 'string'},
        },
        'required': ['regime', 'confidence', 'summary'],
    },
    'strict': True,
}

FILTER_SCHEMA = {
    'name': 'trade_filter',
    'schema': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'allow_trade': {'type': 'boolean'},
            'bias': {'type': 'string', 'enum': ['bullish', 'bearish', 'neutral']},
            'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
            'summary': {'type': 'string'},
        },
        'required': ['allow_trade', 'bias', 'confidence', 'summary'],
    },
    'strict': True,
}


class AIAdvisor:
    def __init__(self) -> None:
        self.enabled = bool(settings.ai_enabled and settings.openai_api_key)
        self.client: OpenAI | None = None
        if self.enabled:
            kwargs: dict[str, Any] = {'api_key': settings.openai_api_key}
            if settings.openai_base_url:
                kwargs['base_url'] = settings.openai_base_url
            self.client = OpenAI(**kwargs)

    def classify_regime(self, prompt_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled or not self.client:
            return self._heuristic_regime(prompt_payload)
        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.1,
                response_format={'type': 'json_schema', 'json_schema': REGIME_SCHEMA},
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a crypto market regime classifier. Use only the supplied data. '
                            'Be conservative and prefer risk_off when data quality is poor.'
                        ),
                    },
                    {'role': 'user', 'content': json.dumps(prompt_payload, default=str)},
                ],
            )
            data = json.loads(response.choices[0].message.content)
            return self._sanitize_regime(data)
        except Exception:
            return self._heuristic_regime(prompt_payload)

    def filter_trade(self, prompt_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled or not self.client:
            return self._heuristic_filter(prompt_payload)
        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.1,
                response_format={'type': 'json_schema', 'json_schema': FILTER_SCHEMA},
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a crypto trade filter. Do not freestyle. Decide whether the proposed trade should '
                            'be allowed based only on the given market data, proposed strategy, and risk context.'
                        ),
                    },
                    {'role': 'user', 'content': json.dumps(prompt_payload, default=str)},
                ],
            )
            data = json.loads(response.choices[0].message.content)
            return self._sanitize_filter(data)
        except Exception:
            return self._heuristic_filter(prompt_payload)

    def _sanitize_regime(self, data: dict[str, Any]) -> dict[str, Any]:
        regime = data.get('regime', 'risk_off')
        if regime not in {'trend', 'range', 'breakout', 'risk_off'}:
            regime = 'risk_off'
        confidence = float(data.get('confidence', 0.0))
        confidence = min(max(confidence, 0.0), 1.0)
        summary = str(data.get('summary', 'No summary provided.'))[:500]
        return {'regime': regime, 'confidence': confidence, 'summary': summary}

    def _sanitize_filter(self, data: dict[str, Any]) -> dict[str, Any]:
        bias = data.get('bias', 'neutral')
        if bias not in {'bullish', 'bearish', 'neutral'}:
            bias = 'neutral'
        confidence = float(data.get('confidence', 0.0))
        confidence = min(max(confidence, 0.0), 1.0)
        allow_trade = bool(data.get('allow_trade', False))
        summary = str(data.get('summary', 'No summary provided.'))[:500]
        return {'allow_trade': allow_trade, 'bias': bias, 'confidence': confidence, 'summary': summary}

    def _heuristic_regime(self, payload: dict[str, Any]) -> dict[str, Any]:
        closes = payload['features']['recent_closes']
        ema_fast = payload['features']['ema_fast']
        ema_slow = payload['features']['ema_slow']
        atr_pct = payload['features']['atr_pct']
        trend_strength = payload['features']['trend_strength']
        momentum = (closes[-1] / closes[max(0, len(closes) - 10)] - 1) if len(closes) >= 10 else 0.0
        if atr_pct > 0.04 and abs(momentum) > 0.015:
            regime = 'breakout'
            summary = 'Volatility expansion plus momentum favors breakout behavior.'
            confidence = 0.72
        elif trend_strength > 0.006 and abs(momentum) > 0.01 and abs(ema_fast - ema_slow) / max(abs(ema_slow), 1e-9) > 0.004:
            regime = 'trend'
            summary = 'EMA separation and trend slope indicate a directional market.'
            confidence = 0.74
        elif atr_pct < 0.022:
            regime = 'range'
            summary = 'Contained volatility supports a ranging market interpretation.'
            confidence = 0.65
        else:
            regime = 'risk_off'
            summary = 'Conditions are mixed, so the safest stance is risk_off.'
            confidence = 0.60
        return {'regime': regime, 'confidence': confidence, 'summary': summary}

    def _heuristic_filter(self, payload: dict[str, Any]) -> dict[str, Any]:
        proposed = payload['proposal']
        regime = payload['regime']['regime']
        rsi = payload['features']['rsi']
        side = proposed['side']
        if side == 'hold' or regime == 'risk_off':
            return {'allow_trade': False, 'bias': 'neutral', 'confidence': 0.84, 'summary': 'Hold in risk-off or no-signal conditions.'}
        if side == 'long' and rsi > 70:
            return {'allow_trade': False, 'bias': 'bullish', 'confidence': 0.71, 'summary': 'Long rejected because RSI is too stretched.'}
        if side == 'short' and rsi < 30:
            return {'allow_trade': False, 'bias': 'bearish', 'confidence': 0.71, 'summary': 'Short rejected because RSI is too oversold.'}
        if regime == 'trend' and side == 'short' and payload['features']['trend_strength'] > 0:
            return {'allow_trade': False, 'bias': 'bullish', 'confidence': 0.69, 'summary': 'Short rejected because the underlying trend is still up.'}
        if regime == 'trend' and side == 'long' and payload['features']['trend_strength'] < 0:
            return {'allow_trade': False, 'bias': 'bearish', 'confidence': 0.69, 'summary': 'Long rejected because the underlying trend is still down.'}
        bias = 'bullish' if side == 'long' else 'bearish'
        return {'allow_trade': True, 'bias': bias, 'confidence': 0.72, 'summary': 'Heuristic filter agrees with the proposed trade.'}
