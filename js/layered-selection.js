/* Stock Picking PEA — architecture de sélection en 3 couches.
 * Couche 1: présélection large (150 max) sur indicateurs simples.
 * Couche 2: classement approfondi (25 max) via les moteurs stratégiques.
 * Couche 3: score global et seuils de décision, avec couverture explicite.
 * Aucune donnée manquante n'est imputée.
 */
(function(){
  'use strict';
  const n=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
  const rank=(values,value,lowerIsBetter=false)=>{
    const a=values.filter(v=>v!==null).sort((x,y)=>x-y);
    if(value===null||!a.length)return null;
    if(a.length===1)return 50;
    let below=0,equal=0;
    for(const x of a){if(x<value)below++;else if(x===value)equal++;}
    const p=100*(below+(equal-1)/2)/(a.length-1);
    return lowerIsBetter?100-p:p;
  };
  const specs={
    growth:{label:'Growth',screen:[['revenue_cagr_3y_pct',false],['eps_growth_next_year_pct',false],['forward_pe',true]],final:[['peg',true,35],['revenue_cagr_3y_pct',false,20],['operating_margin_pct',false,15],['return_12_1m_pct',false,15],['max_drawdown_3y_pct',false,15]]},
    quality:{label:'Growth Quality',screen:[['revenue_cagr_3y_pct',false],['operating_margin_pct',false],['roic_pct',false]],final:[['layer2_score',false,35],['forward_pe',true,10],['fcf_margin_pct',false,15],['roic_pct',false,15],['net_debt_ebitda',true,10],['max_drawdown_3y_pct',false,15]]},
    momentum:{label:'Growth Momentum',screen:[['return_12_1m_pct',false],['return_6m_pct',false],['price_vs_sma200_pct',false]],final:[['layer2_score',false,35],['forward_pe',true,10],['eps_growth_next_year_pct',false,10],['sharpe_3y',false,15],['max_drawdown_1y_pct',false,15],['volatility_1y_pct',true,15]]}
  };
  const screen=(universe,key)=>{
    const cfg=specs[key];
    const raw=universe.map(item=>{
      const values=cfg.screen.map(([field])=>n(item[field]));
      const available=values.filter(v=>v!==null).length;
      const components=values.map((v,i)=>v===null?null:rank(universe.map(x=>n(x[cfg.screen[i][0]])),v,cfg.screen[i][1]));
      const valid=components.filter(v=>v!==null);
      return {item,score:valid.length>=2?valid.reduce((a,b)=>a+b,0)/valid.length:null,coverage:available,coverageMax:cfg.screen.length};
    });
    const ranked=raw.filter(x=>x.score!==null).sort((a,b)=>b.score-a.score||b.coverage-a.coverage);
    ranked.forEach((x,i)=>x.rank=i+1);
    return {ranked,candidates:ranked.slice(0,150),eligible:universe.length,screened:ranked.length};
  };
  const finalScore=(finalists,key)=>{
    const factors=specs[key].final;
    const raw=finalists.map(row=>{
      const item=row.item;
      const values=factors.map(([field])=>field==='peg'?n(row.peg):field==='layer2_score'?n(row.layer2_score):n(item[field]));
      const present=values.reduce((s,v,i)=>s+(v===null?0:factors[i][2]),0);
      const count=values.filter(v=>v!==null).length;
      return {item,values,present,count,totalWeight:factors.reduce((s,f)=>s+f[2],0)};
    });
    const scored=raw.map(r=>{
      if(r.count<4||r.present<75)return {...r,score:null,coveragePct:r.present/r.totalWeight*100,decision:'N/D'};
      const components=r.values.map((v,i)=>v===null?null:rank(raw.map(x=>x.values[i]),v,factors[i][1]));
      const weighted=components.reduce((s,v,i)=>s+(v===null?0:v*factors[i][2]),0);
      const score=weighted/r.present;
      return {...r,score,coveragePct:r.present/r.totalWeight*100,components,decision:score>=75?'ACHAT':score<40?'VENTE / ÉVITER':'CONSERVER'};
    });
    const valid=scored.filter(x=>x.score!==null).sort((a,b)=>b.score-a.score);
    valid.forEach((x,i)=>x.finalRank=i+1);
    return {rows:valid.concat(scored.filter(x=>x.score===null)),valid:valid.length};
  };
  const fmt=v=>v===null||v===undefined?'—':Number(v).toFixed(1);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function render(universe){
    const root=document.getElementById('layeredSelection');
    if(!root)return;
    const engines=window.StockPickingEngines;
    if(!engines){root.innerHTML='<div class="empty">Moteurs de sélection indisponibles.</div>';return;}
    const output=Object.keys(specs).map(key=>{
      const first=screen(universe,key);
      const engine=key==='growth'?engines.growth(first.candidates):key==='quality'?engines.quality(first.candidates):engines.momentum(first.candidates);
      const finalists=engine.ranked.slice(0,25).map(r=>({item:r.item,peg:r.peg??null,layer2_score:r.score??null,layer2_rank:r.rank??null}));
      const third=finalScore(finalists,key);
      return {key,label:specs[key].label,first,engine,finalists,third};
    });
    root.innerHTML='<div class="notice"><strong>Entonnoir en 3 couches :</strong> couche 1 = 150 candidats maximum par stratégie ; couche 2 = 25 dossiers maximum ; couche 3 = score global sur 100. Seuls les titres PEA vérifiés entrent dans le calcul. Les seuils 75/40 sont provisoires et non backtestés. Les facteurs absents ne sont pas imputés ; le score final exige au moins 4 facteurs et 75 % du poids disponible.</div>'+
      output.map(o=>{
        const firstRows=o.first.candidates.slice(0,10).map(r=>'<tr><td>'+r.rank+'</td><td>'+esc(r.item.name)+'</td><td>'+fmt(r.score)+'</td><td>'+r.coverage+'/'+r.coverageMax+'</td></tr>').join('');
        const secondRows=o.finalists.map((r,i)=>'<tr><td>'+(i+1)+'</td><td>'+esc(r.item.name)+'</td><td>'+(o.key==='growth'?fmt(r.peg):fmt(r.layer2_score))+'</td></tr>').join('');
        const thirdRows=o.third.rows.slice(0,25).map(r=>'<tr><td>'+(r.finalRank??'—')+'</td><td>'+esc(r.item.name)+'</td><td>'+(r.score===null?'N/D':fmt(r.score))+'</td><td>'+fmt(r.coveragePct)+' %</td><td>'+r.decision+'</td></tr>').join('');
        const topTable=(head,body,empty)=>'<div class="table-wrap"><table class="table"><thead><tr>'+head+'</tr></thead><tbody>'+(body||'<tr><td colspan="5">'+empty+'</td></tr>')+'</tbody></table></div>';
        return '<div class="card wide" style="margin-top:14px"><div class="row"><h3>'+o.label+'</h3><span class="pill">'+o.first.candidates.length+' candidats · '+o.finalists.length+' finalistes</span></div>'+
          '<div class="grid"><div><div class="small muted">Couche 1 · screening</div><div class="metric">'+o.first.candidates.length+' / 150</div><div class="metric-sub">Candidats classables sur '+o.first.eligible+' titres PEA vérifiés</div></div><div><div class="small muted">Couche 2 · analyse approfondie</div><div class="metric">'+o.finalists.length+' / 25</div><div class="metric-sub">'+o.engine.available+' titres avec données stratégiques complètes</div></div><div><div class="small muted">Couche 3 · score final</div><div class="metric">'+o.third.valid+' / '+o.finalists.length+'</div><div class="metric-sub">Scores finaux suffisamment documentés</div></div></div>'+
          '<div class="section-head"><h3>Couche 1 · premiers candidats</h3><span>10 premiers affichés · 150 maximum retenus</span></div>'+
          topTable('<th>Rang</th><th>Société</th><th>Score écran</th><th>Couverture</th>',firstRows,'Pas assez de données pour classer les candidats.')+
          '<div class="section-head"><h3>Couche 2 · Top 25 approfondi</h3><span>Classement stratégique</span></div>'+
          topTable('<th>Rang</th><th>Société</th><th>'+(o.key==='growth'?'PEG':'Score stratégique')+'</th>',secondRows,'Aucun titre ne dispose des indicateurs requis.')+
          '<div class="section-head"><h3>Couche 3 · décision d’investissement</h3><span>Achat ≥ 75 · Vente / éviter &lt; 40</span></div>'+
          topTable('<th>Rang</th><th>Société</th><th>Score /100</th><th>Poids couvert</th><th>Signal</th>',thirdRows,'Scores finaux non calculables avec les données actuelles.')+
          '<p class="small muted">Entre 40 et 75 : conserver / surveiller. Les signaux restent indicatifs et ne déclenchent aucun ordre. Le score est relatif aux titres analysés dans ce panel, pas une probabilité de rendement.</p></div>';
      }).join('');
  }
  window.StockPickingLayeredSelection={render};
})();
