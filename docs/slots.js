'use strict';
// Harpstar Free Slots: just-for-fun reels with fun coins that have no value.
// Built like a real machine (about 86% payback) so players can watch the
// house edge work over many spins.
(function slots() {
  const SYMBOLS = [
    {s: '🍒', w: 5, pays: 10}, {s: '🍋', w: 7, pays: 8}, {s: '🔔', w: 6, pays: 16}, {s: '⭐', w: 4, pays: 25},
    {s: '💎', w: 2, pays: 50}, {s: '7️⃣', w: 1, pays: 120}, {s: '💰', w: 1, pays: 250},
  ];
  const TOTAL_W = SYMBOLS.reduce((a, x) => a + x.w, 0);
  const START_COINS = 100, KEY = 'fun-slots';
  const el = id => document.getElementById(id);
  const panel = el('slots');
  if (!panel) return;
  const reels = [...panel.querySelectorAll('.reel-strip')];

  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; } };
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* private mode */ } };
  const state = Object.assign({coins: START_COINS, bet: 1, spins: 0, in: 0, out: 0, best: 0}, load() || {});
  let spinning = false;

  function pick() {
    let r = Math.random() * TOTAL_W;
    for (const x of SYMBOLS) { if ((r -= x.w) < 0) return x; }
    return SYMBOLS[0];
  }
  /** Coins won per 1-coin bet for a finished spin. */
  function payout(line) {
    if (line[0].s === line[1].s && line[1].s === line[2].s) return line[0].pays;
    const cherries = line.filter(x => x.s === '🍒').length;
    if (cherries === 2) return 2;
    if (cherries === 1 && line[0].s === '🍒') return 1;
    return 0;
  }
  // Exact long-run payback from the weights, shown so the house edge is no secret.
  const PAYBACK = (() => {
    let ev = 0;
    for (const a of SYMBOLS) for (const b of SYMBOLS) for (const c of SYMBOLS) ev += (a.w * b.w * c.w) / TOTAL_W ** 3 * payout([a, b, c]);
    return ev;
  })();

  function render(msg, cls = '') {
    el('slot-coins').textContent = state.coins.toLocaleString();
    el('slot-bet').textContent = state.bet;
    el('slot-spins').textContent = state.spins.toLocaleString();
    el('slot-payback').textContent = state.in ? `${Math.round(state.out / state.in * 100)}%` : '—';
    el('slot-best').textContent = state.best.toLocaleString();
    el('slot-spin').disabled = spinning || state.coins < state.bet;
    el('slot-refill').hidden = state.coins >= 1;
    if (msg != null) { const m = el('slot-msg'); m.textContent = msg; m.className = `slot-msg ${cls}`; }
    panel.querySelectorAll('[data-bet]').forEach(b => b.classList.toggle('on', Number(b.dataset.bet) === state.bet));
  }

  function fill(strip, symbols) { strip.innerHTML = symbols.map(x => `<div class="sym">${x.s}</div>`).join(''); }

  function spin() {
    if (spinning || state.coins < state.bet) return;
    spinning = true;
    state.coins -= state.bet; state.in += state.bet; state.spins++;
    render('Spinning…');
    const line = [pick(), pick(), pick()];
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const done = reels.map((strip, i) => new Promise(resolve => {
      const filler = Array.from({length: 18 + i * 6}, pick);
      fill(strip, [...filler, line[i]]);
      strip.style.transition = 'none';
      strip.style.transform = 'translateY(0)';
      strip.getBoundingClientRect(); // restart the transition
      const target = `translateY(calc(-100% + var(--sym-h)))`;
      if (reduce) { strip.style.transform = target; return setTimeout(resolve, 150 + i * 100); }
      const secs = 1.1 + i * 0.45;
      strip.style.transition = `transform ${secs}s cubic-bezier(.12,.75,.2,1)`;
      strip.style.transform = target;
      strip.addEventListener('transitionend', resolve, {once: true});
      setTimeout(resolve, secs * 1000 + 400); // in case transitionend never fires
    }));
    Promise.all(done).then(() => {
      spinning = false;
      const won = payout(line) * state.bet;
      state.coins += won; state.out += won; state.best = Math.max(state.best, won);
      save();
      panel.classList.remove('win', 'jackpot');
      if (won) {
        panel.getBoundingClientRect();
        const isBig = payout(line) >= 50;
        panel.classList.add(isBig ? 'jackpot' : 'win');
        const msg = isBig ? `💰 BIG WIN! +${won} coins!` : `✨ Winner! +${won} coins`;
        render(msg, 'good');
        if (isBig) launchConfetti();
      } else render(state.coins < 1 ? '🪙 Refill for 100 free coins — tap the button!' : 'Keep spinning…');
    });
  }

  function launchConfetti() {
    const symbols = ['💰', '⭐', '💎', '🎉', '✨'];
    for (let i = 0; i < 20; i++) {
      setTimeout(() => {
        const c = document.createElement('div');
        c.className = 'confetti';
        c.textContent = symbols[Math.floor(Math.random() * symbols.length)];
        c.style.left = Math.random() * 100 + '%';
        c.style.top = -20 + 'px';
        c.style.animation = `confetti-fall ${1.5 + Math.random() * 1}s ease-out forwards`;
        c.style.setProperty('--delay', Math.random() * 0.2 + 's');
        document.body.appendChild(c);
        setTimeout(() => c.remove(), 3500);
      }, i * 30);
    }
  }

  panel.addEventListener('click', e => {
    const bet = e.target.closest('[data-bet]');
    if (bet && !spinning) { state.bet = Number(bet.dataset.bet); save(); render(); }
  });
  el('slot-spin').addEventListener('click', spin);
  el('slot-refill').addEventListener('click', () => { state.coins = START_COINS; save(); render('Refilled 100 free fun coins.'); });
  el('slot-reset').addEventListener('click', () => {
    Object.assign(state, {coins: START_COINS, spins: 0, in: 0, out: 0, best: 0}); save(); render('Stats reset.');
  });
  const open = v => { panel.classList.toggle('open', v); el('slots-fab').setAttribute('aria-expanded', String(v)); };
  el('slots-fab').addEventListener('click', () => open(!panel.classList.contains('open')));
  el('slots-close').addEventListener('click', () => open(false));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') open(false); });

  el('slot-rtp').textContent = `${Math.round(PAYBACK * 100)}%`;
  el('slot-paytable').innerHTML = [...SYMBOLS].reverse().map(x => `<li><span>${x.s}${x.s}${x.s}</span><b>wins ${x.pays}×</b></li>`).join('') +
    '<li><span>🍒🍒 any</span><b>wins 2×</b></li><li><span>🍒 first</span><b>wins 1×</b></li>';
  reels.forEach(strip => fill(strip, [pick()]));
  render('Free play. Coins never cost real money.');
})();
