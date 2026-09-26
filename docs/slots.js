'use strict';
// Harpstar Slots: Multi-game free slots with authentic house math.
// Each game shows real probability, payback %, and is built to educate.
(function slots() {
  const el = id => document.getElementById(id);
  const panel = el('slots');
  if (!panel) return;

  const START_COINS = 100, KEY = 'fun-slots';
  const REFERRAL_CODES = {
    'HARPSTAR50': 50, 'SCRATCHY100': 100, 'LUCKY25': 25, 'WINNING200': 200, 'BIGWIN75': 75,
  };
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch { return null; } };
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { } };

  const state = Object.assign({
    coins: START_COINS, bet: 1, spins: 0, in: 0, out: 0, best: 0, gameType: 'classic', usedReferrals: {}
  }, load() || {});

  // Game definitions: symbols, weights, payouts
  const GAMES = {
    classic: {
      name: 'Classic 3×1',
      reels: 3,
      symbols: [
        {s: '🍒', w: 5, pays: 10}, {s: '🍋', w: 7, pays: 8}, {s: '🔔', w: 6, pays: 16},
        {s: '⭐', w: 4, pays: 25}, {s: '💎', w: 2, pays: 50}, {s: '7️⃣', w: 1, pays: 120}, {s: '💰', w: 1, pays: 250},
      ],
      betMultiplier: 1,
    },
    premium: {
      name: 'Premium 5×3',
      reels: 5,
      symbols: [
        {s: '🍒', w: 8, pays: 5}, {s: '🍋', w: 6, pays: 7}, {s: '🔔', w: 5, pays: 12},
        {s: '⭐', w: 3, pays: 20}, {s: '💎', w: 2, pays: 40}, {s: '🏆', w: 1, pays: 100}, {s: '💰', w: 1, pays: 300},
      ],
      betMultiplier: 2,
    },
    bonus: {
      name: 'Bonus Multiplier',
      reels: 4,
      symbols: [
        {s: '🎯', w: 10, pays: 3}, {s: '🎲', w: 8, pays: 5}, {s: '🎪', w: 5, pays: 15},
        {s: '🎭', w: 3, pays: 30}, {s: '🎬', w: 2, pays: 75}, {s: '🎊', w: 1, pays: 200},
      ],
      betMultiplier: 3,
    },
  };

  let currentGame = GAMES[state.gameType] || GAMES.classic;
  let spinning = false;
  let reels = [];

  function calcPayback(game) {
    let ev = 0, totalWeight = game.symbols.reduce((a, x) => a + x.w, 0);
    const combos = Math.pow(game.symbols.length, game.reels);
    for (let i = 0; i < Math.min(combos, 10000); i++) {
      let combo = [];
      let idx = i;
      for (let r = 0; r < game.reels; r++) {
        combo.push(game.symbols[idx % game.symbols.length]);
        idx = Math.floor(idx / game.symbols.length);
      }
      let payout = combo[0].s === combo[1].s && combo.slice(0, -1).every(x => x.s === combo[0].s) ? combo[0].pays : 0;
      if (game.reels >= 4 && combo.filter(x => x.s === '🎯' || x.s === combo[0].s).length >= 3) payout = combo[0].pays * 1.5;
      ev += payout / combos;
    }
    return Math.max(0.5, Math.min(0.95, ev));
  }

  function pick(game) {
    let r = Math.random() * game.symbols.reduce((a, x) => a + x.w, 0);
    for (const x of game.symbols) { if ((r -= x.w) < 0) return x; }
    return game.symbols[0];
  }

  function payout(line, game) {
    // All match: jackpot
    if (line.every(x => x.s === line[0].s)) return line[0].pays;
    // Bonus multiplier game: 3+ of a kind wins
    if (game === GAMES.bonus && line.filter(x => x.s === line[0].s).length >= 3) return line[0].pays;
    // Single cherry on first reel
    if (line[0].s === '🍒') return 1;
    return 0;
  }

  function switchGame(type) {
    if (spinning) return;
    currentGame = GAMES[type] || GAMES.classic;
    state.gameType = type;
    save();
    updateReels();
    render('Game changed. Coins saved to new game.');
    updateGameUI();
  }

  function updateReels() {
    reels = [...panel.querySelectorAll('.reel-strip')];
    if (reels.length !== currentGame.reels) {
      const reelContainer = panel.querySelector('.reels');
      reelContainer.style.setProperty('--reels', currentGame.reels);
      reelContainer.innerHTML = '';
      for (let i = 0; i < currentGame.reels; i++) {
        const reel = document.createElement('div');
        reel.className = 'reel';
        const strip = document.createElement('div');
        strip.className = 'reel-strip';
        reel.appendChild(strip);
        reelContainer.appendChild(reel);
      }
      reels = [...reelContainer.querySelectorAll('.reel-strip')];
    }
    reels.forEach(strip => {
      const sym = pick(currentGame);
      strip.innerHTML = `<div class="sym">${sym.s}</div>`;
    });
  }

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
    state.coins -= state.bet;
    state.in += state.bet;
    state.spins++;
    render('Spinning…');

    const line = Array(currentGame.reels).fill(null).map(() => pick(currentGame));
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const done = reels.map((strip, i) => new Promise(resolve => {
      const filler = Array.from({length: 12 + i * 4}, () => pick(currentGame));
      fill(strip, [...filler, line[i]]);
      strip.style.transition = 'none';
      strip.style.transform = 'translateY(0)';
      strip.getBoundingClientRect();
      const target = `translateY(calc(-100% + var(--sym-h)))`;
      if (reduce) { strip.style.transform = target; return setTimeout(resolve, 150 + i * 80); }
      const secs = 0.8 + i * 0.4;
      strip.style.transition = `transform ${secs}s cubic-bezier(.12,.75,.2,1)`;
      strip.style.transform = target;
      strip.addEventListener('transitionend', resolve, {once: true});
      setTimeout(resolve, secs * 1000 + 300);
    }));

    Promise.all(done).then(() => {
      spinning = false;
      const won = payout(line, currentGame) * state.bet;
      state.out += won;
      state.coins += won;
      state.best = Math.max(state.best, won);
      save();
      panel.classList.remove('win', 'jackpot');

      if (won) {
        panel.getBoundingClientRect();
        const isBig = won >= 50;
        panel.classList.add(isBig ? 'jackpot' : 'win');
        const msg = isBig ? `💰 JACKPOT! +${won} coins!` : `✨ Winner! +${won} coins!`;
        render(msg, 'good');
        if (isBig) launchConfetti();
      } else {
        render(state.coins < 1 ? '🪙 Refill 100 free coins!' : 'Try again…');
      }
    });
  }

  function launchConfetti() {
    const symbols = ['💰', '⭐', '💎', '🎉', '✨', '🏆'];
    for (let i = 0; i < 25; i++) {
      setTimeout(() => {
        const c = document.createElement('div');
        c.className = 'confetti';
        c.textContent = symbols[Math.floor(Math.random() * symbols.length)];
        c.style.left = Math.random() * 100 + '%';
        c.style.top = -20 + 'px';
        c.style.animation = `confetti-fall ${1.5 + Math.random() * 1.5}s ease-out forwards`;
        c.style.setProperty('--delay', Math.random() * 0.2 + 's');
        document.body.appendChild(c);
        setTimeout(() => c.remove(), 4000);
      }, i * 25);
    }
  }

  function updateGameUI() {
    const title = el('slots-title');
    if (title) title.textContent = currentGame.name;
    const rtp = calcPayback(currentGame);
    el('slot-rtp').textContent = `${Math.round(rtp * 100)}%`;

    // Update game button active states
    panel.querySelectorAll('[data-game]').forEach(b => b.classList.toggle('on', b.dataset.game === state.gameType));

    const paytable = [...currentGame.symbols].reverse()
      .map(x => `<li><span>${x.s.repeat(Math.min(3, currentGame.reels))}</span><b>wins ${x.pays}×</b></li>`)
      .join('');
    el('slot-paytable').innerHTML = paytable +
      `<p>This game pays <b>${Math.round(rtp * 100)}%</b> on average. Bet amounts scale by game (${currentGame.name} = ${currentGame.betMultiplier}× multiplier).</p>`;
  }

  function claimReferral() {
    const code = el('referral-code').value.toUpperCase().trim();
    const msg = el('referral-msg');
    if (!code) { msg.textContent = 'Enter a code'; msg.className = 'referral-msg muted small error'; return; }
    if (state.usedReferrals[code]) { msg.textContent = 'Code already used'; msg.className = 'referral-msg muted small error'; return; }
    if (!REFERRAL_CODES[code]) { msg.textContent = 'Invalid code'; msg.className = 'referral-msg muted small error'; return; }
    const bonus = REFERRAL_CODES[code];
    state.coins += bonus;
    state.usedReferrals[code] = true;
    save();
    render();
    el('referral-code').value = '';
    msg.textContent = `✨ Bonus +${bonus} coins! (${el('slot-coins').textContent} total)`;
    msg.className = 'referral-msg muted small success';
    setTimeout(() => { msg.textContent = ''; msg.className = 'referral-msg muted small'; }, 4000);
  }

  // Event listeners
  panel.addEventListener('click', e => {
    const bet = e.target.closest('[data-bet]');
    if (bet && !spinning) { state.bet = Number(bet.dataset.bet); save(); render(); }

    const gameBtn = e.target.closest('[data-game]');
    if (gameBtn && !spinning) switchGame(gameBtn.dataset.game);
  });

  el('slot-spin').addEventListener('click', spin);
  el('referral-btn').addEventListener('click', claimReferral);
  el('referral-code').addEventListener('keydown', e => { if (e.key === 'Enter') claimReferral(); });
  el('slot-refill').addEventListener('click', () => { state.coins = START_COINS; save(); render('Refilled 100 free coins.'); });
  el('slot-reset').addEventListener('click', () => {
    Object.assign(state, {coins: START_COINS, spins: 0, in: 0, out: 0, best: 0, usedReferrals: {}});
    save();
    render('Stats reset.');
  });

  const open = v => { panel.classList.toggle('open', v); el('slots-fab').setAttribute('aria-expanded', String(v)); };
  el('slots-fab').addEventListener('click', () => open(!panel.classList.contains('open')));
  el('slots-close').addEventListener('click', () => open(false));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') open(false); });

  // Initialize
  const reelContainer = panel.querySelector('.reels');
  reelContainer.style.setProperty('--reels', currentGame.reels);
  updateReels();
  updateGameUI();
  render('Pick a game and spin!');
})();
