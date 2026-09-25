# WA Scratch Lens

Local, dependency-free dashboard that retrieves Washington Lottery scratch-game data and compares games for a user-set entertainment budget.

## Run

Double-click `Start WA Scratch Lens.bat`, or:

```bash
python server.py
```

Open <http://127.0.0.1:8879>.

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
node --check static/app.js
curl http://127.0.0.1:8879/api/health
```
