'use strict';
const $ = s => document.querySelector(s);
const DATA_URL = 'data/latest.json';
const POLL_MS = 5 * 60 * 1000;
const PUBLISH_DELAY_MS = 4 * 60 * 1000; // scheduled job + Pages deploy take a few minutes
const SIM_RUNS = 3000, SIM_MAX_TICKETS = 2000;
// Where "Did you win?" emails go. Leave empty to hide the email button.
const WIN_EMAIL = 'harpstarunlimited@gmail.com';
const VERDICT = {best: 'Best bet', good: 'Good value', fair: 'Fair', skip: 'Skip'};

const store = {
  get(key, fallback) { try { const v = localStorage.getItem(key); return v == null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } },
};

let data = null, priceFilter = 'all', nextCheckAt = null;
const simCache = new Map();

// ---------- formatting ----------
const money = x => x == null ? '—' : new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: x >= 100 ? 0 : 2}).format(x);
const whole = x => x == null ? '—' : new Intl.NumberFormat('en-US', {maximumFractionDigits: 0}).format(x);
const pct = x => x == null ? '—' : x > 0 && x < 0.0001 ? '<0.01%' : `${(x * 100).toFixed(x < 0.01 && x > 0 ? 2 : 0)}%`;
const cents = r => `${Math.round(r * 100)}¢`;
const safe = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
function ago(date) {
  const s = Math.max(0, (Date.now() - date) / 1000);
  if (s < 90) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400 * 2) return `${Math.round(s / 3600)} hr ago`;
  return `${Math.round(s / 86400)} days ago`;
}
function sourceLabel(text) { // "9/25/2026 12:35:05 AM" (Pacific time) -> "9/25 12:35 AM PT"
  const m = /^(\d+)\/(\d+)\/\d+ (\d+:\d+):\d+ ([AP]M)$/.exec(String(text).trim());
  return m ? `${m[1]}/${m[2]} ${m[3]} ${m[4]} PT` : String(text);
}

// ---------- simulation ----------
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

/** Monte Carlo sessions: buy n tickets of game g, return outcome stats. */
function simulate(g, n) {
  const key = `${g.id}:${n}:${data.generated_at}`;
  if (simCache.has(key)) return simCache.get(key);
  const tiers = g.tiers.filter(t => t.p > 0), cum = [], vals = [];
  let acc = 0;
  for (const t of tiers) { acc += t.p; cum.push(acc); vals.push(t.value || 0); }
  const spent = n * g.cost, rand = rng(g.id * 7919 + n), totals = new Float64Array(SIM_RUNS);
  let ahead = 0, even = 0, sum = 0, nothing = 0, some = 0, big = 0;
  for (let r = 0; r < SIM_RUNS; r++) {
    let won = 0;
    for (let i = 0; i < n; i++) {
      const u = rand();
      if (u >= acc) continue;
      let k = 0; while (u >= cum[k]) k++;
      won += vals[k];
    }
    totals[r] = won; sum += won;
    if (won > spent) ahead++;
    if (won >= spent) even++;
    if (won === 0) nothing++;
    else if (won < spent) some++;
    if (won >= spent * 5) big++;
  }
  totals.sort();
  const res = {n, spent, ahead: ahead / SIM_RUNS, even: even / SIM_RUNS, mean: sum / SIM_RUNS,
    nothing: nothing / SIM_RUNS, some: some / SIM_RUNS, back: (even - ahead) / SIM_RUNS, big: big / SIM_RUNS,
    median: totals[Math.floor(SIM_RUNS / 2)], p10: totals[Math.floor(SIM_RUNS * 0.1)], p90: totals[Math.floor(SIM_RUNS * 0.9)]};
  simCache.set(key, res);
  return res;
}
const ticketsFor = (budget, g) => Math.min(SIM_MAX_TICKETS, Math.floor(budget / g.cost));

// ---------- plain-English wins ----------
const OUTCOMES = [
  {key: 'nothing', label: 'Win nothing', cls: 'o-nothing', icon: '✖'},
  {key: 'some', label: 'Win some back, still down', cls: 'o-some', icon: '↘'},
  {key: 'back', label: 'Get exactly your money back', cls: 'o-back', icon: '＝'},
  {key: 'ahead', label: 'Come out ahead', cls: 'o-ahead', icon: '$'},
];
/** Round shares so the ten people always add up to 10. */
function outOfTen(sim) {
  const raw = OUTCOMES.map(o => sim[o.key] * 10), base = raw.map(Math.floor);
  let left = 10 - base.reduce((a, b) => a + b, 0);
  raw.map((r, i) => [r - base[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => { if (left > 0) { base[i]++; left--; } });
  return base;
}
function outcomeBlock(sim) {
  const ten = outOfTen(sim);
  const people = OUTCOMES.flatMap((o, i) => Array(ten[i]).fill(`<span class="person ${o.cls}" title="${o.label}">${o.icon}</span>`)).join('');
  const lines = OUTCOMES.map((o, i) => `<li><i class="${o.cls}"></i><span>${o.label}</span><b>${pct(sim[o.key])}</b><small>${ten[i]} of 10</small></li>`).join('');
  return `
    <div class="outcomes">
      <p class="outcome-head">If 10 people each spend <b>${money(sim.spent)}</b> this way:</p>
      <div class="people" aria-hidden="true">${people}</div>
      <ul class="outcome-list">${lines}</ul>
      <p class="fineprint">Big wins (5× your money or more) happen in about ${sim.big ? `1 in ${whole(Math.max(1, 1 / sim.big))}` : 'fewer than 1 in 3,000'} tries. Typical cash back: ${money(sim.median)}. Average cost of playing: <b class="neg">${money(sim.spent - sim.mean)}</b>.</p>
    </div>`;
}
function tierKind(t, g) {
  if (t === g.tiers[0]) return ['Top prize', 'k-top'];
  if (t.value == null) return ['Non-cash', 'k-profit'];
  if (t.value < g.cost) return ['Less than ticket', 'k-less'];
  if (t.value === g.cost) return ['Money back', 'k-back'];
  if (t.value >= g.cost * 20) return ['Big win', 'k-big'];
  return ['Profit', 'k-profit'];
}
function winTruth(g) {
  const all = g.tiers.reduce((a, t) => a + t.p, 0) || 1;
  const small = g.tiers.filter(t => t.value != null && t.value <= g.cost).reduce((a, t) => a + t.p, 0);
  const profit = g.tiers.filter(t => t.value == null || t.value > g.cost).reduce((a, t) => a + t.p, 0);
  return `About <b>1 in ${g.odds.toFixed(1)}</b> tickets is a “winner” — but <b>${pct(small / all)}</b> of those wins only give back your ticket price or less. A win that actually beats the ticket price comes about <b>1 in ${whole(profit ? 1 / profit : null)}</b> tickets.`;
}

// ---------- rendering ----------
function scoreBadge(g) { return `<span class="score v-${g.verdict}" title="Smart Score"><b>${g.score}</b><small>${VERDICT[g.verdict]}</small></span>`; }
function thumb(g) { return `<img class="thumb" src="${safe(g.img)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`; }

// The scheduled robot (GitHub Action) only commits when WA's numbers change,
// so "last checked" comes from its public run history instead of the data file.
const ROBOT_RUNS = 'https://api.github.com/repos/hermz580/wa-scratch-lens/actions/workflows/update-data.yml/runs?per_page=1';
let robot = null, robotFetchedAt = 0;
async function loadRobot() {
  if (Date.now() - robotFetchedAt < 4 * 60 * 1000) return;
  robotFetchedAt = Date.now();
  try {
    const r = await fetch(ROBOT_RUNS, {headers: {Accept: 'application/vnd.github+json'}});
    const run = r.ok ? (await r.json()).workflow_runs?.[0] : null;
    if (run) robot = {at: new Date(run.updated_at || run.created_at), status: run.status, ok: run.conclusion === 'success'};
  } catch { /* offline or rate-limited: keep the last known value */ }
  if (data) renderStatus();
}

function renderStatus() {
  $('#source-line').innerHTML = `WA Lottery published: <b>${safe(sourceLabel(data.source_updated))}</b> · ${data.game_count} games`;
  let robotText = 'Robot status loading…';
  if (robot) {
    const late = Date.now() - robot.at > 75 * 60 * 1000;
    robotText = robot.status !== 'completed' ? '🔄 Robot is checking right now…'
      : !robot.ok ? `⚠️ Robot's last check ${ago(robot.at)} failed — will retry`
      : late ? `⏳ Robot last checked ${ago(robot.at)} (GitHub is running late)`
      : `✅ Robot checked ${ago(robot.at)}`;
  }
  $('#changed-line').textContent = `${robotText} · numbers last changed ${ago(new Date(data.generated_at))}`;
}

function nextCheck(minutes) {
  const now = new Date(), d = new Date(now);
  d.setSeconds(0, 0);
  for (let i = 0; i < 120; i++) { d.setMinutes(d.getMinutes() + 1); if (minutes.includes(d.getUTCMinutes())) return d; }
  return new Date(now.getTime() + 30 * 60000);
}

function tick() {
  if (!data) return;
  if (!nextCheckAt || Date.now() > nextCheckAt.getTime() + PUBLISH_DELAY_MS) {
    if (nextCheckAt) load(true);
    nextCheckAt = nextCheck(data.check_minutes || [7, 37]);
    robotFetchedAt = 0; loadRobot();
  }
  const left = nextCheckAt - Date.now();
  const span = 60000 * 60 / (data.check_minutes || [7, 37]).length;
  if (left > 0) {
    const m = Math.floor(left / 60000), s = Math.floor(left / 1000) % 60;
    $('#countdown').textContent = `${m}:${String(s).padStart(2, '0')}`;
  } else {
    $('#countdown').textContent = 'checking…';
  }
  const frac = Math.max(0, Math.min(1, left / span));
  $('#ring-fg').style.strokeDashoffset = String(97.4 * (1 - frac));
  if (Date.now() % 30000 < 1000) renderStatus();
}

function budget() { const b = Number($('#budget').value); return Number.isFinite(b) && b > 0 ? b : 0; }

function renderPick() {
  const b = budget();
  store.set('budget', b);
  const affordable = data.games.filter(g => g.cost <= b && g.verdict !== 'skip');
  const pool = affordable.length ? affordable : data.games.filter(g => g.cost <= b);
  if (!pool.length) { $('#pick-body').innerHTML = `<p class="muted">The cheapest ticket is ${money(Math.min(...data.games.map(g => g.cost)))}. Raise your budget to see a pick.</p>`; return; }
  const best = [...pool].sort((a, b2) => b2.score - a.score || b2.rtp - a.rtp)[0];
  const n = ticketsFor(b, best), sim = simulate(best, n);
  const alts = pool.filter(g => g.id !== best.id).slice(0, 3);
  $('#pick-body').innerHTML = `
    <p class="eyebrow">Smart pick for ${money(b)}</p>
    <button class="pick" data-id="${best.id}">
      ${thumb(best)}
      <div class="pick-main"><h3>${safe(best.name)}</h3><p>${money(best.cost)} ticket · buy <b>${n}</b></p></div>
      ${scoreBadge(best)}
    </button>
    <ul class="reasons">${best.reasons.map(r => `<li>${safe(r)}</li>`).join('')}</ul>
    ${outcomeBlock(sim)}
    <p class="win-truth">${winTruth(best)}</p>
    <p class="fineprint">Based on ${whole(SIM_RUNS)} simulated sessions of ${n} tickets using the prizes still left. A lucky 1 in 10 got back ${money(sim.p90)} or more.</p>
    ${alts.length ? `<p class="eyebrow">Also good at this budget</p><div class="alts">${alts.map(g => `<button class="alt" data-id="${g.id}">${thumb(g)}<span>${safe(g.name)}<small>${money(g.cost)} · ${cents(g.rtp)} per $1</small></span>${scoreBadge(g)}</button>`).join('')}</div>` : ''}`;
}

function renderNew() {
  const seen = new Set(store.get('seen-ids', []));
  const fresh = data.games.filter(g => g.is_new).sort((a, b) => (b.first_seen || '').localeCompare(a.first_seen || '') || a.sold_pct - b.sold_pct);
  $('#new-list').innerHTML = fresh.length ? fresh.map(g => `
    <button class="new-card" data-id="${g.id}">
      ${!seen.has(g.id) && seen.size ? '<span class="dot-new">NEW TO YOU</span>' : ''}
      <img src="${safe(g.img)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
      <b>${safe(g.name)}</b>
      <small>${money(g.cost)} · top ${safe(g.top_label)} · ${g.top_rem}/${g.top_total} left</small>
      <small>${g.first_seen ? `Added ${ago(new Date(g.first_seen))}` : `${pct(1 - g.sold_pct)} of prizes still out`}</small>
      ${scoreBadge(g)}
    </button>`).join('') : '<p class="muted">No brand-new games right now. You\'ll see them here the day they show up.</p>';
}

function renderFeed() {
  const icon = {new_game: '🆕', top_claimed: '💰', top_gone: '⛔', retired: '📦'};
  const ev = data.events.slice(0, 12);
  $('#feed-list').innerHTML = ev.length ? ev.map(e => `<div class="event"><span>${icon[e.kind] || '•'}</span><div><b>${safe(e.name)}</b><p>${safe(e.message)}</p></div><time>${ago(new Date(e.t))}</time></div>`).join('')
    : '<p class="muted">Tracking started. New games, claimed top prizes and retired games will show up here.</p>';
}

function renderList() {
  const prices = [...new Set(data.games.map(g => g.cost))].sort((a, b) => a - b);
  $('#price-chips').innerHTML = ['all', ...prices].map(p => `<button type="button" data-p="${p}" class="${String(p) === String(priceFilter) ? 'on' : ''}">${p === 'all' ? 'All' : money(p)}</button>`).join('');
  const sort = $('#sort').value, hide = $('#hide-gone').checked;
  let list = data.games.filter(g => (priceFilter === 'all' || g.cost === Number(priceFilter)) && (!hide || g.top_rem > 0));
  const by = {score: (a, b) => b.score - a.score, rtp: (a, b) => b.rtp - a.rtp, top: (a, b) => (a.top_one_in ?? Infinity) - (b.top_one_in ?? Infinity), cost: (a, b) => a.cost - b.cost || b.score - a.score};
  list = list.sort(by[sort]);
  $('#game-count').textContent = `${list.length} shown`;
  $('#game-list').innerHTML = list.map((g, i) => `
    <button class="row" data-id="${g.id}">
      <span class="rank">${i + 1}</span>${thumb(g)}
      <span class="row-main"><b>${safe(g.name)}${g.is_new ? ' <em class="tag-new">NEW</em>' : ''}</b>
        <small>${money(g.cost)} · ${g.rtp_is_floor ? '≥' : ''}${cents(g.rtp)} per $1 · top ${safe(g.top_label)} ${g.top_rem}/${g.top_total} left</small>
        <span class="bar"><i style="width:${Math.round((1 - g.sold_pct) * 100)}%"></i></span></span>
      ${scoreBadge(g)}
    </button>`).join('') || '<p class="muted">No games match.</p>';
}

function openDetail(id) {
  const g = data.games.find(x => String(x.id) === String(id));
  if (!g) return;
  const b = Math.max(budget(), g.cost), n = ticketsFor(b, g), sim = simulate(g, n);
  const drift = g.drift * 100;
  $('#detail-body').innerHTML = `
    <div class="detail-head"><img src="${safe(g.img)}" alt="" onerror="this.style.visibility='hidden'"><div><h3>${safe(g.name)}</h3><p>${money(g.cost)} · Game #${g.id} · Rank ${g.rank} of ${data.game_count}</p>${scoreBadge(g)}</div></div>
    <ul class="reasons">${g.reasons.map(r => `<li>${safe(r)}</li>`).join('')}</ul>
    <div class="stats four">
      <div><small>Payback now</small><b>${g.rtp_is_floor ? '≥' : ''}${cents(g.rtp)}</b></div>
      <div><small>At launch</small><b>${cents(g.launch_rtp)}</b></div>
      <div><small>Drift</small><b class="${drift >= 0 ? 'pos' : 'neg'}">${drift >= 0 ? '+' : ''}${drift.toFixed(1)}</b></div>
      <div><small>Sold (est.)</small><b>${pct(g.sold_pct)}</b></div>
      <div><small>Any prize</small><b>1 in ${g.odds}</b></div>
      <div><small>Top prize</small><b>${g.top_one_in ? `1 in ${whole(g.top_one_in)}` : 'gone'}</b></div>
      <div><small>Tickets left</small><b>${whole(g.est_remaining)}</b></div>
      <div><small>Sells out in</small><b>${g.days_left ? `~${whole(g.days_left)} days` : '—'}</b></div>
    </div>
    <p class="eyebrow">With ${money(n * g.cost)} (${n} ticket${n === 1 ? '' : 's'})</p>
    ${outcomeBlock(sim)}
    <p class="win-truth">${winTruth(g)}</p>
    <p class="eyebrow">Every prize, in plain words</p>
    <div class="table-wrap"><table class="prize-table"><thead><tr><th>Prize</th><th>Odds</th><th>Your chance</th></tr></thead><tbody>
      ${g.tiers.map(t => { const [kind, cls] = tierKind(t, g); return `<tr class="${t.rem ? '' : 'gone'}"><td><b>${safe(t.label)}</b> <span class="kind ${cls}">${kind}</span><small class="left">${whole(t.rem)} of ${whole(t.total)} left</small></td><td>${t.p ? `1 in ${whole(1 / t.p)}` : 'gone'}</td><td>${t.p ? pct(1 - Math.pow(1 - t.p, n)) : '0%'}</td></tr>`; }).join('')}
    </tbody></table></div>
    <p class="fineprint">“Left” = not yet claimed. WA data updated ${safe(sourceLabel(g.source_updated))}.</p>`;
  $('#detail').showModal();
}

// ---------- tracker ----------
function renderTracker() {
  const log = store.get('results-log', []);
  $('#log-game').innerHTML = '<option value="">Game…</option>' + [...data.games].sort((a, b) => a.name.localeCompare(b.name)).map(g => `<option value="${g.id}">${safe(g.name)} (${money(g.cost)})</option>`).join('');
  const spent = log.reduce((s, r) => s + r.spent, 0), won = log.reduce((s, r) => s + r.won, 0), net = won - spent;
  $('#log-summary').innerHTML = log.length ? `<div class="stats"><div><small>Spent</small><b>${money(spent)}</b></div><div><small>Won</small><b>${money(won)}</b></div><div><small>Net</small><b class="${net >= 0 ? 'pos' : 'neg'}">${money(net)}</b></div></div>` : '<p class="muted">Log what you buy and win to see your real net over time.</p>';
  $('#log-list').innerHTML = log.slice(-8).reverse().map((r, i) => `<div class="log-row"><span>${safe(r.date)}</span><b>${safe(r.name)}</b><span class="${r.won - r.spent >= 0 ? 'pos' : 'neg'}">${money(r.won - r.spent)}</span><button class="ghost small" data-del="${log.length - 1 - i}" aria-label="Delete">✕</button></div>`).join('');
}

// ---------- did you win? ----------
function renderWinBox() {
  const current = $('#win-game').value;
  $('#win-game').innerHTML = '<option value="">Which game?</option>' + [...data.games].sort((a, b) => a.name.localeCompare(b.name)).map(g => `<option value="${g.id}">${safe(g.name)} (${money(g.cost)})</option>`).join('');
  $('#win-game').value = current;
  $('#win-email').hidden = !WIN_EMAIL;
}
$('#win-form').addEventListener('submit', e => {
  e.preventDefault();
  if (!WIN_EMAIL) return;
  const g = data?.games.find(x => String(x.id) === $('#win-game').value);
  const amount = Number($('#win-amount').value) || 0;
  const name = $('#win-name').value.trim();
  if (amount >= 100) window.playJackpot();
  const subject = `I won${amount ? ` ${money(amount)}` : ''}${g ? ` on ${g.name}` : ''}! 🎉`;
  const body = [`Game: ${g ? `${g.name} (${money(g.cost)})` : 'not picked'}`, `Won: ${amount ? money(amount) : 'not given'}`,
    name ? `From: ${name}` : '', '', $('#win-comment').value.trim(), '', '— sent from Scratchtastic by Harpstar'].filter((l, i) => l || i > 2).join('\n');
  location.href = `mailto:${WIN_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
});

// ---------- new-ticket alerts ----------
function checkNewForUser() {
  const seen = store.get('seen-ids', null), ids = data.games.map(g => g.id);
  if (seen) {
    const fresh = data.games.filter(g => !seen.includes(g.id));
    if (fresh.length) {
      const names = fresh.map(g => g.name).join(', ');
      showBanner(`🆕 ${fresh.length} new ticket${fresh.length > 1 ? 's' : ''} since your last visit: ${names}`);
      if ('Notification' in window && Notification.permission === 'granted' && document.visibilityState !== 'visible') {
        navigator.serviceWorker?.ready.then(r => r.showNotification('New WA scratch tickets', {body: names, icon: 'icons/icon-192.png', tag: 'new-tickets'}))
          .catch(() => new Notification('New WA scratch tickets', {body: names}));
      }
    }
  }
  renderNew();
  store.set('seen-ids', [...new Set([...(seen || []), ...ids])]);
}

function showBanner(text) { const b = $('#banner'); b.textContent = text; b.hidden = false; }

// ---------- data ----------
async function load(quiet = false) {
  loadRobot();
  document.body.classList.add('loading');
  try {
    const r = await fetch(`${DATA_URL}?t=${Math.floor(Date.now() / 60000)}`, {cache: 'no-store'});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const next = await r.json();
    const changed = !data || next.generated_at !== data.generated_at;
    if (changed) {
      if (data && quiet) showBanner('✨ Fresh lottery data just loaded.');
      data = next; simCache.clear();
      renderStatus(); renderPick(); renderFeed(); renderList(); renderTracker(); renderWinBox(); checkNewForUser();
    } else renderStatus();
  } catch (e) {
    if (!data) $('#pick-body').innerHTML = `<p class="muted">Couldn't load game data (${safe(e.message)}). Check your connection and tap ↻.</p>`;
    else showBanner('Offline — showing the last data you loaded.');
  } finally { document.body.classList.remove('loading'); }
}

// ---------- events ----------
$('#budget').value = store.get('budget', 20) || 20;
$('#budget-form').addEventListener('submit', e => { e.preventDefault(); if (data) renderPick(); });
let budgetTimer;
$('#budget').addEventListener('input', () => { clearTimeout(budgetTimer); budgetTimer = setTimeout(() => data && renderPick(), 250); });
$('#budget-chips').addEventListener('click', e => { const b = e.target.closest('[data-b]'); if (b && data) { $('#budget').value = b.dataset.b; renderPick(); } });
$('#price-chips').addEventListener('click', e => { const b = e.target.closest('[data-p]'); if (b) { priceFilter = b.dataset.p; renderList(); } });
$('#sort').addEventListener('change', renderList);
$('#hide-gone').addEventListener('change', renderList);
document.addEventListener('click', e => { const el = e.target.closest('[data-id]'); if (el && data) openDetail(el.dataset.id); });
$('#detail-close').addEventListener('click', () => $('#detail').close());
$('#detail').addEventListener('click', e => { if (e.target.id === 'detail') $('#detail').close(); });
$('#refresh').addEventListener('click', () => load());
$('#banner').addEventListener('click', () => { $('#banner').hidden = true; });
$('#log-form').addEventListener('submit', e => {
  e.preventDefault();
  const g = data?.games.find(x => String(x.id) === $('#log-game').value);
  const spent = Number($('#log-spent').value) || (g ? g.cost : 0), won = Number($('#log-won').value) || 0;
  if (!g) return;
  const log = store.get('results-log', []);
  log.push({date: new Date().toLocaleDateString(), id: g.id, name: g.name, spent, won});
  store.set('results-log', log);
  e.target.reset(); renderTracker();
});
$('#log-list').addEventListener('click', e => {
  const b = e.target.closest('[data-del]'); if (!b) return;
  const log = store.get('results-log', []); log.splice(Number(b.dataset.del), 1); store.set('results-log', log); renderTracker();
});
$('#notify-btn').addEventListener('click', async () => {
  if (!('Notification' in window)) return showBanner('This browser can\'t show alerts. New tickets will still appear at the top when you open the app.');
  const p = await Notification.requestPermission();
  showBanner(p === 'granted' ? '🔔 You\'ll get an alert when new tickets show up while the app is open or in the background.' : 'Alerts are off. New tickets will still show up here.');
});
$('#share-btn').addEventListener('click', async () => {
  const url = location.href.split('#')[0];
  try { if (navigator.share) await navigator.share({title: 'Scratchtastic by Harpstar', text: 'Smart picks for WA scratch tickets', url}); else { await navigator.clipboard.writeText(url); showBanner('Link copied — paste it to anyone.'); } } catch { /* cancelled */ }
});
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') load(true); });

// Harpstar hero: dollar signs shooting out of the title
(function burst() {
  const box = $('#burst'); if (!box) return;
  const colors = ['#ffd766', '#f2b631', '#fff1b8', '#e6e9ee', '#c9ced6'];
  const count = 28;
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2 + Math.random() * 0.25, dist = 120 + Math.random() * 120;
    const el = document.createElement('i');
    el.textContent = '$';
    el.style.cssText = `--x:${Math.cos(a) * dist * 1.5}px;--y:${Math.sin(a) * dist * 0.75}px;--r:${Math.round(Math.random() * 120 - 60)}deg;` +
      `--s:${18 + Math.round(Math.random() * 22)}px;--d:${(2.2 + Math.random() * 1.6).toFixed(2)}s;--delay:${(-Math.random() * 3).toFixed(2)}s;--c:${colors[i % colors.length]}`;
    box.appendChild(el);
  }
})();

// Scratchtastic theme song: click title or "by Harpstar" to play
['#theme-trigger', '#harpstar-trigger'].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.addEventListener('click', () => {
    const audio = $('#theme-audio');
    if (!audio) return;
    audio.currentTime = 0;
    const playPromise = audio.play();
    if (playPromise && playPromise.catch) playPromise.catch(() => console.log('Audio blocked'));
  });
});

// Jackpot sound: play when big win logged
window.playJackpot = () => {
  const audio = $('#jackpot-audio');
  if (!audio) return;
  audio.currentTime = 0;
  const playPromise = audio.play();
  if (playPromise && playPromise.catch) playPromise.catch(() => console.log('Audio blocked'));
};

if ('serviceWorker' in navigator && location.protocol !== 'file:') navigator.serviceWorker.register('sw.js').catch(() => {});
load();
setInterval(tick, 1000);
setInterval(() => load(true), POLL_MS);
