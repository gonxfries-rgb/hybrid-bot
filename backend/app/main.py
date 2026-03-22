from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from .bot import BotEngine
from .config import settings
from .db import engine, get_session, init_db
from .models import BotState, LogEvent, Position, Trade


bot_engine = BotEngine()
BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / 'frontend'


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        bot_engine.ensure_state(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
if FRONTEND_DIR.exists():
    app.mount('/static', StaticFiles(directory=str(FRONTEND_DIR)), name='static')


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    html_path = FRONTEND_DIR / 'index.html'
    return html_path.read_text(encoding='utf-8')


@app.get('/api/state')
def get_state(session: Session = Depends(get_session)):
    state = session.exec(select(BotState).where(BotState.id == 1)).first()
    if not state:
        raise HTTPException(status_code=404, detail='Bot state not initialized')
    positions = session.exec(select(Position).where(Position.status == 'open')).all()
    trades = session.exec(select(Trade).order_by(Trade.created_at.desc())).all()[:20]
    logs = session.exec(select(LogEvent).order_by(LogEvent.created_at.desc())).all()[:50]
    return {
        'state': state.model_dump(mode='json'),
        'positions': [p.model_dump(mode='json') for p in positions],
        'trades': [t.model_dump(mode='json') for t in trades],
        'logs': [l.model_dump(mode='json') for l in logs],
        'limits': {
            'ai_min_confidence': settings.ai_min_confidence,
            'ai_regime_min_confidence': settings.ai_regime_min_confidence,
            'max_daily_loss_pct': settings.max_daily_loss_pct,
            'max_trades_per_day': settings.max_trades_per_day,
            'max_consecutive_losses': settings.max_consecutive_losses,
            'cooldown_minutes': settings.cooldown_minutes,
            'enable_live_trading': settings.enable_live_trading,
        },
    }


@app.post('/api/tick')
def run_tick(session: Session = Depends(get_session)):
    return bot_engine.tick(session)


@app.post('/api/start')
def start_bot(session: Session = Depends(get_session)):
    state = bot_engine.ensure_state(session)
    state.running = True
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.commit()
    bot_engine.start(lambda: Session(engine))
    return {'ok': True, 'running': True}


@app.post('/api/stop')
def stop_bot(session: Session = Depends(get_session)):
    state = bot_engine.ensure_state(session)
    state.running = False
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.commit()
    bot_engine.stop()
    return {'ok': True, 'running': False}


@app.post('/api/settings')
def update_settings(payload: dict, session: Session = Depends(get_session)):
    state = bot_engine.ensure_state(session)
    allowed = {'mode', 'symbol', 'interval', 'ai_enabled', 'kill_switch'}
    for key, value in payload.items():
        if key in allowed and hasattr(state, key):
            setattr(state, key, value)
    state.updated_at = datetime.now(timezone.utc)
    session.add(state)
    session.commit()
    return {'ok': True, 'state': state.model_dump(mode='json')}
