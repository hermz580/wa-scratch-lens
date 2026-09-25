const form=document.querySelector('#budget-form'), input=document.querySelector('#budget');
const alertToggle=document.querySelector('#alerts-toggle');
const prizeGame=document.querySelector('#prize-game');
let latestGames=[];
function renderPrizeBoard(){const g=latestGames.find(x=>String(x.id)===prizeGame.value)||latestGames[0];if(!g)return;document.querySelector('#prize-summary').innerHTML=`<b>${safe(g.name)}</b> · ${money(g.cost)} ticket · ${g.tickets_affordable} ticket${g.tickets_affordable===1?'':'s'} in budget · ${g.prize_tiers.length} prize tiers`;
 document.querySelector('#prize-tier-rows').innerHTML=g.prize_tiers.map(t=>`<tr><td><b>${safe(t.label)}</b></td><td>${whole(t.total)}</td><td>${whole(t.paid)}</td><td><b>${whole(t.remaining)}</b></td><td>${pct(t.percent_remaining)}</td><td>${t.estimated_one_in?`1 in ${whole(t.estimated_one_in)}`:'None reported'}</td><td>${pct(t.chance_with_budget)}</td><td>${t.expected_value_contribution==null?'Unknown':money(t.expected_value_contribution)}</td></tr>`).join('')}
prizeGame.addEventListener('change',renderPrizeBoard);
alertToggle.checked=localStorage.getItem('alerts-enabled')!=='false';
alertToggle.addEventListener('change',()=>localStorage.setItem('alerts-enabled',String(alertToggle.checked)));
const pct=x=>`${(x*100).toFixed(x<.001?4:1)}%`;
const money=x=>x==null?'Unavailable':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(x);
const whole=x=>x==null?'Unavailable':new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(x);
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function statusClass(value, values){const sorted=[...values].sort((a,b)=>a-b), low=sorted[Math.floor(sorted.length/3)], high=sorted[Math.floor(sorted.length*2/3)];return value>=high?'rank-good':value>=low?'rank-mid':'rank-low'}
function card(selector,g,metric,label){document.querySelector(`${selector} .card-content`).innerHTML=`<img src="${safe(g.grid_image_url)}" alt="" loading="lazy"><div><h3>${safe(g.name)}</h3><div class="big">${label}</div><p>$${g.cost} each · ${g.tickets_affordable} ticket${g.tickets_affordable===1?'':'s'} within budget</p><p class="tiny">Top prizes remaining: ${g.top_prizes_remaining}/${g.top_prizes_total}</p></div>`}
function render(data){
 const games=data.games.filter(g=>g.tickets_affordable>0); latestGames=data.games; const selected=prizeGame.value; prizeGame.innerHTML=data.games.map(g=>`<option value="${g.id}">${safe(g.name)} — ${money(g.cost)}</option>`).join(''); if(data.games.some(g=>String(g.id)===selected))prizeGame.value=selected; renderPrizeBoard(); document.querySelector('#source-status').innerHTML=`Verified WA Lottery run<br><b>${new Date(data.checked_at).toLocaleString()}</b><br><small>${safe(data.run_id)}</small>`;
 const ops=data.operations||{agents:[],events:[]};
 document.querySelector('#run-verdict').textContent=data.quality?.verdict==='publish'?'QUALITY GATE: PUBLISHED':'QUALITY GATE: PUBLISHED WITH WARNINGS';
 document.querySelector('#run-verdict').className=`pill ${data.quality?.verdict==='publish'?'open':'warn'}`;
 document.querySelector('#operations-grid').innerHTML=ops.agents.map(a=>`<article class="op-card ${safe(a.status)}"><div class="op-head"><b>${safe(a.name)}</b><span class="status-chip">${safe(a.status)}</span></div><p>${safe(a.responsibility)}</p><div class="op-count"><b>${a.records_out}</b><small> output · ${a.records_failed} rejected</small></div><small>${a.duration_ms} ms · ${safe(a.run_id)}</small><div class="handoff">→ ${a.handoffs.length?safe(a.handoffs.join(', ')):'final output'}</div>${a.latest_error?`<p class="error">${safe(a.latest_error)}</p>`:''}</article>`).join('');
 document.querySelector('#audit-trail').innerHTML=ops.events.map(e=>`<div class="event"><time>${new Date(e.timestamp).toLocaleTimeString()}</time><b>${safe(e.agent_id)}</b><span>${safe(e.message)}</span><small>${e.duration_ms} ms</small></div>`).join('');
 if(!games.length){document.querySelector('#message').textContent='Your budget is below the price of every available ticket.';document.querySelector('#game-rows').innerHTML='';return}
 document.querySelector('#message').textContent=`Compared ${games.length} games within your $${data.budget.toFixed(2)} budget.`;
 const any=[...games].sort((a,b)=>b.chance_any_win-a.chance_any_win)[0];
 const evGames=games.filter(g=>g.ev_complete), ev=[...evGames].sort((a,b)=>b.return_rate-a.return_rate)[0];
 const top=[...games].filter(g=>g.top_prizes_remaining>0).sort((a,b)=>b.chance_top_prize-a.chance_top_prize)[0];
 card('#best-any',any,'chance_any_win',pct(any.chance_any_win));
 if(ev) card('#best-ev',ev,'return_rate',`${pct(ev.return_rate)} est. return`); else document.querySelector('#best-ev .card-content').textContent='No complete cash-value estimates available.';
 if(top) card('#best-top',top,'chance_top_prize',pct(top.chance_top_prize)); else document.querySelector('#best-top .card-content').textContent='No top prizes reported remaining.';
 document.querySelector('#jackpot-rows').innerHTML=data.jackpot_watchlist.map(g=>`<tr><td><div class="game"><img src="${safe(g.grid_image_url)}" alt=""><div><b>${safe(g.name)}</b><small>${safe(g.top_prize_label)} possible top payout</small></div></div></td><td><b>${money(g.cost)}</b><small>minimum entry spend</small></td><td><b>${g.top_prizes_remaining}/${g.top_prizes_total}</b></td><td><b>1 in ${whole(g.top_prize_one_in)}</b><small>estimated per ticket</small></td><td><b>${money(g.top_prize_expected_spend)}</b><small>long-run probability cost, not a guarantee</small></td><td><b>${money(g.spend_for_1pct_top_prize)}</b></td><td><b>${money(g.spend_for_5pct_top_prize)}</b></td><td><b>${money(g.spend_for_50pct_top_prize)}</b></td></tr>`).join('');
 document.querySelector('#deep-stats').innerHTML=`
  <div class="stat"><span>No prize</span><b>${pct(any.chance_no_prize)}</b><small>all ${any.tickets_affordable} tickets lose</small></div>
  <div class="stat"><span>Exactly one prize</span><b>${pct(any.chance_exactly_one_prize)}</b><small>one listed winning ticket</small></div>
  <div class="stat"><span>Two or more prizes</span><b>${pct(any.chance_two_or_more_prizes)}</b><small>multiple listed winning tickets</small></div>
  <div class="stat"><span>Expected winning tickets</span><b>${any.expected_winning_tickets.toFixed(2)}</b><small>long-run average, not a promise</small></div>
  <div class="stat"><span>Expected payout</span><b>${money(any.estimated_budget_return)}</b><small>from ${money(any.cost*any.tickets_affordable)} actually spent</small></div>
  <div class="stat"><span>Payout volatility</span><b>${money(any.payout_standard_deviation)}</b><small>estimated standard deviation; high means wide swings</small></div>`;
 const planNames={any_win:'Maximize any-prize chance',expected_value:'Maximize expected payout',top_prize:'Maximize top-prize chance'};
 document.querySelector('#plan-grid').innerHTML=Object.entries(data.plans).map(([key,plan])=>`<article class="plan"><span class="tag">${safe(planNames[key])}</span><h3>${plan.items.map(i=>`${i.count}× ${safe(i.name)}`).join(' + ')||'No affordable tickets'}</h3><p><b>${money(plan.spent)}</b> spent · ${money(plan.unspent)} unspent</p><small>Optimized only for the named metric. Buying a mix does not guarantee a better outcome.</small></article>`).join('');
 const anyVals=games.map(g=>g.chance_any_win), retVals=evGames.map(g=>g.return_rate), topVals=games.map(g=>g.chance_top_prize);
 document.querySelector('#game-rows').innerHTML=[...games].sort((a,b)=>b.chance_any_win-a.chance_any_win).map(g=>`<tr><td><div class="game"><img src="${safe(g.grid_image_url)}" alt="" loading="lazy"><div><b>${safe(g.name)}</b><small>Game #${g.id}</small></div></div></td><td><b>$${g.cost}</b><small>${g.tickets_affordable} affordable</small></td><td class="${statusClass(g.chance_any_win,anyVals)}"><b>${pct(g.chance_any_win)}</b><small>≥1 listed prize</small></td><td><b>${pct(g.chance_profit)}</b><small>prize above cost</small></td><td class="${g.return_rate==null?'':statusClass(g.return_rate,retVals)}"><b>${g.return_rate==null?'Incomplete':pct(g.return_rate)}</b><small>${g.return_rate==null?'non-cash value unknown':`${money(g.estimated_gross_ev)} gross / ticket`}</small></td><td class="${statusClass(g.chance_top_prize,topVals)}"><b>${pct(g.chance_top_prize)}</b><small>${g.top_prizes_remaining}/${g.top_prizes_total} remaining · ${safe(g.top_prize_label)}</small></td><td><span class="pill ${g.top_prizes_remaining?'open':'closed'}">${g.top_prizes_remaining?'Top prize open':'Top prize gone'}</span></td></tr>`).join('');
 document.querySelector('#alert-list').innerHTML=data.alerts.length?data.alerts.map(a=>`<div class="alert"><b>${safe(a.game)}</b><span>${safe(a.message)}</span><time>${new Date(a.detected_at).toLocaleString()}</time></div>`).join(''):'<p class="muted">No changes detected since the previous check.</p>';
}
async function load(){const budget=Number(input.value);if(!Number.isFinite(budget)||budget<0){document.querySelector('#message').textContent='Enter a budget of $0 or more.';return}document.body.classList.add('loading');try{const r=await fetch(`/api/games?budget=${encodeURIComponent(budget)}`), data=await r.json();if(!r.ok)throw new Error(data.error||'Unable to load data');render(data)}catch(e){document.querySelector('#message').textContent=e.message}finally{document.body.classList.remove('loading')}}
form.addEventListener('submit',e=>{e.preventDefault();load()});
setInterval(()=>{if(alertToggle.checked)load()},15*60*1000);
load();
