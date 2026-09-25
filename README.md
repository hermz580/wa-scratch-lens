# WA Scratch Lens

A phone app that ranks every Washington Lottery scratch ticket by how good its *remaining* prize pool looks. It updates itself, flags new tickets, and can be shared with anyone as a link.

## Use it on a phone

Once GitHub Pages is on (one-time setup below), the app lives at:

**https://hermz580.github.io/wa-scratch-lens/**

Send that link to anyone. To install it like an app:

- **iPhone:** open in Safari → Share → *Add to Home Screen*
- **Android:** open in Chrome → ⋮ → *Install app*

It works offline with the last data it loaded.

### One-time setup (repo owner)

1. Merge this branch into `main`.
2. GitHub repo → **Settings → Pages** → Source: *Deploy from a branch* → Branch `main`, folder `/docs` → Save.
3. **Actions** tab → *Update lottery data* → *Run workflow* once to confirm it works.

After that, a scheduled GitHub Action checks walottery.com every 15 minutes (at :07, :22, :37 and :52). It commits new data only when the lottery numbers actually changed. WA usually publishes once a day, overnight.

## What the app shows

- **Smart pick for your budget:** the best-scoring game you can afford, how many tickets to buy, and your simulated chance to end ahead.
- **Smart Score (0–100)** for every game:
  - *Payback (45%)* — estimated cents back per $1 on the unsold tickets.
  - *Drift (30%)* — payback now vs. at launch. Positive means big prizes are outlasting small ones.
  - *Big-prize share (25%)* — share of the top 3 prize tiers left vs. share of all winners left.
  - Games with every top prize gone get a 45% cut and are marked **Skip**.
- **New tickets:** games added in the last 30 days or barely sold. A "NEW TO YOU" tag marks games added since your last visit. Optional alerts fire while the app is open.
- **What changed:** new games, top prizes claimed, games retired.
- **Countdown timer** to the next automatic check. The app reloads fresh data by itself.
- **Game details:** prize table, odds now, sell-out estimate, and outcome simulation.
- **My results:** log what you spend and win (stored only on your phone) to see your real net.

## Honest limits

Every WA scratch game pays back less than $1 per $1 on average. The Smart Score finds the *better-value* games; it cannot predict a winning ticket or make play profitable.

## Run locally (optional)

Double-click `Start WA Scratch Lens.bat`, or:

```bash
python server.py
```

Open <http://127.0.0.1:8879>. The local server serves the same app from `docs/` and refreshes `docs/data/` every 30 minutes.

To rebuild data by hand: `python site_builder.py` (add `--force` to rewrite even if unchanged).

## Worker pipeline

- **Source Scout:** retrieves the official `explorer.aspx` embedded game dataset.
- **Game Analyst:** calculates affordable ticket count, prize-tier counts, probabilities, estimated return, and payout volatility.
- **Portfolio Planner:** allocates a budget for any-prize chance, expected payout, or top-prize chance.
- **Jackpot Sentinel:** ranks every game that still reports an available top prize.
- **Change Monitor:** compares each refresh with the prior local snapshot and produces alerts.
- **Quality Gate:** checks worker contracts and invariants before results are published.

## Important limitations

The site does not expose actual unsold retailer inventory. The app estimates remaining tickets as:

`published overall-odds denominator × reported remaining winning prizes`

This assumes winning and losing tickets deplete proportionally and that claims track sales. “Any prize” can include break-even prizes. Non-cash prizes without an official supported dollar value are marked incomplete and excluded from expected-value rankings. No result guarantees a win or profit.

## Verify

```bash
python -m unittest discover -s tests -v
node --check docs/app.js
curl http://127.0.0.1:8879/api/health
```
