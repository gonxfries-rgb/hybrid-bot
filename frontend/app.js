async function api(path, options={}) {
  const res = await fetch(path, {headers: {'Content-Type':'application/json'}, ...options});
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function money(v){
  const n = Number(v || 0);
  return `${n < 0 ? '-' : ''}$${Math.abs(n).toFixed(2)}`;
}

function setText(id, value, cls=''){
  const el = document.getElementById(id);
  el.textContent = value;
  el.className = cls;
}

function renderRows(id, rows, mapper, emptyCols=6){
  const body = document.getElementById(id);
  body.innerHTML = rows.length ? rows.map(mapper).join('') : `<tr><td colspan="${emptyCols}">None</td></tr>`;
}

async function refresh(){
  const data = await api('/api/state');
  const state = data.state;
  setText('cash', money(state.cash));
  setText('equity', money(state.equity));
  setText('realized', money(state.realized_pnl), state.realized_pnl >= 0 ? 'positive' : 'negative');
  setText('unrealized', money(state.unrealized_pnl), state.unrealized_pnl >= 0 ? 'positive' : 'negative');
  setText('lastPrice', money(state.last_price));
  setText('lastSignal', state.last_signal);
  setText('lastRegime', state.last_regime);
  setText('lastConfidence', `${(Number(state.last_ai_confidence || 0) * 100).toFixed(0)}%`);
  setText('regimeConfidence', `${(Number(state.last_regime_confidence || 0) * 100).toFixed(0)}%`);
  setText('tradesToday', String(state.trades_today || 0));
  setText('consecutiveLosses', String(state.consecutive_losses || 0), state.consecutive_losses > 0 ? 'negative' : '');
  setText('killSwitch', state.kill_switch ? 'ACTIVE' : 'OFF', state.kill_switch ? 'negative' : 'positive');

  document.getElementById('aiSummary').textContent = state.last_ai_summary || 'No AI summary yet.';
  document.getElementById('decisionReason').textContent = state.last_decision_reason || 'No decisions yet.';
  document.getElementById('modeSelect').value = state.mode;
  document.getElementById('symbolInput').value = state.symbol;
  document.getElementById('intervalSelect').value = state.interval;
  document.getElementById('aiCheckbox').checked = !!state.ai_enabled;
  document.getElementById('killSwitchCheckbox').checked = !!state.kill_switch;

  renderRows('positionsBody', data.positions, (p) => `
    <tr><td>${p.symbol}</td><td>${p.side}</td><td>${Number(p.quantity).toFixed(5)}</td><td>${Number(p.entry_price).toFixed(2)}</td><td>${Number(p.mark_price).toFixed(2)}</td><td>${Number(p.stop_loss).toFixed(2)}</td><td class="${p.unrealized_pnl >= 0 ? 'positive':'negative'}">${money(p.unrealized_pnl)}</td></tr>`, 7);

  renderRows('tradesBody', data.trades, (t) => `
    <tr><td>${new Date(t.created_at).toLocaleString()}</td><td>${t.side}</td><td>${Number(t.quantity).toFixed(5)}</td><td>${Number(t.price).toFixed(2)}</td><td>${money(t.fees)}</td><td>${t.reason}</td></tr>`, 6);

  const limits = data.limits;
  document.getElementById('riskLimits').textContent = [
    `AI filter minimum confidence: ${(limits.ai_min_confidence * 100).toFixed(0)}%`,
    `Regime minimum confidence: ${(limits.ai_regime_min_confidence * 100).toFixed(0)}%`,
    `Max daily loss: ${(limits.max_daily_loss_pct * 100).toFixed(1)}% of starting cash`,
    `Max trades per day: ${limits.max_trades_per_day}`,
    `Max consecutive losses: ${limits.max_consecutive_losses}`,
    `Cooldown: ${limits.cooldown_minutes} minutes after a close`,
    `Live trading hard switch: ${limits.enable_live_trading ? 'enabled' : 'disabled'}`,
  ].join('\n');

  const logs = document.getElementById('logs');
  logs.innerHTML = data.logs.length ? data.logs.map((l) => `<div class="logline">[${l.level}] ${new Date(l.created_at).toLocaleString()} — ${l.message}</div>`).join('') : 'No logs yet.';
}

document.getElementById('startBtn').onclick = async () => { await api('/api/start', {method:'POST'}); refresh(); };
document.getElementById('stopBtn').onclick = async () => { await api('/api/stop', {method:'POST'}); refresh(); };
document.getElementById('tickBtn').onclick = async () => { await api('/api/tick', {method:'POST'}); refresh(); };
document.getElementById('saveBtn').onclick = async () => {
  await api('/api/settings', {
    method:'POST',
    body: JSON.stringify({
      mode: document.getElementById('modeSelect').value,
      symbol: document.getElementById('symbolInput').value.trim(),
      interval: document.getElementById('intervalSelect').value,
      ai_enabled: document.getElementById('aiCheckbox').checked,
      kill_switch: document.getElementById('killSwitchCheckbox').checked,
    })
  });
  refresh();
};

refresh();
setInterval(refresh, 10000);
