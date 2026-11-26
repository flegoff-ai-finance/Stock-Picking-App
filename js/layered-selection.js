/* Stock Picking PEA — pipeline en 3 couches.
 * La couche 1 est strictement interne : aucun nom, rang ou score écran n'est affiché.
 * Les données absentes ne sont jamais imputées.
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
  function screen(universe,key){
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
  }
  function finalScore(finalists,key){
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
  }
  function isPeaVerified(item,today=new Date()){
    if(!item||item.pea_status!=='eligible'||!/^([A-Z]{2}[A-Z0-9]{10})$/.test(String(item.isin||''))||!String(item.ticker||'').trim())return false;
    const checked=Date.parse(String(item.pea_checked_at||item.verified_at||'')+'T00:00:00Z');
    const age=(today.getTime()-checked)/86400000;
    return Number.isFinite(checked)&&age>=0&&age<=90;
  }
  function build(universe,peaRegistry){
    const engines=window.StockPickingEngines;
    if(!engines)return [];
    const registry=Array.isArray(peaRegistry)?peaRegistry:universe;
    const verifiedByIsin=new Map(registry.filter(item=>isPeaVerified(item)).map(item=>[String(item.isin).toUpperCase(),item]));
    return Object.keys(specs).map(key=>{
      const first=screen(universe,key);
      // Layer 1 ranks the full discovery pool. PEA evidence is applied only afterwards.
      // Continue down the ranked list until 150 verified instruments are found, so
      // unverified candidates are replaced by the next ranked candidate.
      const candidates=first.ranked
        .map(row=>({discovery:row.item,verified:verifiedByIsin.get(String(row.item.isin||'').toUpperCase())}))
        .filter(row=>row.verified)
        .slice(0,150)
        .map(row=>({...row.discovery,...row.verified}));
      const engine=key==='growth'?engines.growth(candidates):key==='quality'?engines.quality(candidates):engines.momentum(candidates);
      const finalists=engine.ranked.slice(0,25).map(r=>({item:r.item,peg:r.peg??null,layer2_score:r.score??null,layer2_rank:r.rank??null,layer2_coverage:r.coverage??null,layer2_coverage_weight_pct:r.coverageWeightPct??null}));
      const third=finalScore(finalists,key);
      const blockers={};
      (engine.rows||[]).filter(r=>r.reason).forEach(r=>{blockers[r.reason]=(blockers[r.reason]||0)+1;});
      return {key,label:specs[key].label,screened:first.candidates.length,peaVerified:candidates.length,peaRejected:first.ranked.length-candidates.length,engine,finalists,third,blockers};
    });
  }
  const fmt=v=>v===null||v===undefined?'—':Number(v).toFixed(1);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const indicatorSpecs={
    growth:[['PEG','peg','ratio'],['PER prévisionnel','forward_pe','ratio'],['Croissance BPA estimée 5 ans','eps_growth_cagr_pct','pct'],['Croissance CA 3 ans','revenue_cagr_3y_pct','pct'],['Marge opérationnelle','operating_margin_pct','pct'],['Momentum 12-1 mois','return_12_1m_pct','pct'],['Drawdown maximal 3 ans','max_drawdown_3y_pct','pct']],
    quality:[['Croissance CA 3 ans','revenue_cagr_3y_pct','pct'],['Croissance EBIT 3 ans','operating_income_cagr_3y_pct','pct'],['Marge opérationnelle','operating_margin_pct','pct'],['Marge FCF','fcf_margin_pct','pct'],['ROIC','roic_pct','pct'],['Dette nette / EBITDA','net_debt_ebitda','ratio'],['Sharpe 3 ans','sharpe_3y','number'],['Drawdown maximal 3 ans','max_drawdown_3y_pct','pct']],
    momentum:[['Performance 12-1 mois','return_12_1m_pct','pct'],['Performance 6 mois','return_6m_pct','pct'],['Cours vs MM200','price_vs_sma200_pct','pct'],['MM50 vs MM200','sma50_vs_sma200_pct','pct'],['Sharpe 3 ans','sharpe_3y','number'],['Drawdown maximal 1 an','max_drawdown_1y_pct','pct'],['Volatilité 1 an','volatility_1y_pct','pct'],['Performance relative 6 mois','relative_return_6m_pct','pct']]
  };
  function indicatorDetails(item,key,peg){
    const rows=indicatorSpecs[key].map(([label,field,type])=>{
      const value=field==='peg'?peg:item[field];
      const shown=value===null||value===undefined?'N/D':type==='pct'?fmt(value)+' %':type==='ratio'?fmt(value)+'x':fmt(value);
      return '<tr><td>'+esc(label)+'</td><td>'+shown+'</td></tr>';
    }).join('');
    return '<details><summary>Voir les indicateurs</summary><div class="table-wrap"><table class="table"><tbody>'+rows+'</tbody></table></div></details>';
  }
  function render(universe,peaRegistry){
    const root=document.getElementById('layeredSelection');
    if(!root)return;
    const output=build(universe,peaRegistry);
    if(!output.length){root.innerHTML='<div class="empty">Moteurs de sélection indisponibles.</div>';return;}
    root.innerHTML='<div class="notice"><strong>Pipeline interne :</strong> le premier filtre réduit l’univers à 150 candidats maximum par stratégie ; ses résultats détaillés restent masqués. Seuls les 25 dossiers les mieux classés et suffisamment documentés peuvent atteindre la couche finale. Les seuils 75/40 sont provisoires et non backtestés. Aucune donnée manquante n’est imputée.</div>'+
      output.map(o=>{
        const secondRows=o.finalists.map((r,i)=>'<tr><td>'+(i+1)+'</td><td>'+esc(r.item.name)+'</td><td>'+(o.key==='growth'?fmt(r.peg):fmt(r.layer2_score))+'</td><td>'+(r.layer2_coverage===null?'PEG':r.layer2_coverage+'/8 · '+fmt(r.layer2_coverage_weight_pct)+' %')+'</td><td>'+indicatorDetails(r.item,o.key,r.peg)+'</td></tr>').join('');
        const thirdRows=o.third.rows.slice(0,25).map(r=>'<tr><td>'+(r.finalRank??'—')+'</td><td>'+esc(r.item.name)+'</td><td>'+(r.score===null?'N/D':fmt(r.score))+'</td><td>'+fmt(r.coveragePct)+' %</td><td>'+r.decision+'</td></tr>').join('');
        const topTable=(head,body,empty)=>'<div class="table-wrap"><table class="table"><thead><tr>'+head+'</tr></thead><tbody>'+(body||'<tr><td colspan="5">'+empty+'</td></tr>')+'</tbody></table></div>';
        const blockerText=Object.entries(o.blockers).map(([reason,count])=>'<li>'+count+' titre(s) : '+esc(reason)+'</li>').join('');
        const layer2Empty=o.engine.available===0
          ?'<div class="empty"><b>Aucun titre ne satisfait encore les exigences de données de '+esc(o.label)+'.</b><br>'+o.screened+' candidat(s) transmis par le filtre interne ; indicateurs stratégiques incomplets. Aucun classement artificiel.</div>'
          :'<div class="empty">Aucun finaliste disponible.</div>';
        return '<div class="card wide" style="margin-top:14px"><div class="row"><h3>'+o.label+'</h3><span class="pill">'+o.finalists.length+' / 25 finalistes</span></div>'+
          '<div class="grid"><div><div class="small muted">Titres vérifiés PEA après couche 2</div><div class="metric">'+(o.engine.required??o.screened)+'</div><div class="metric-sub">Titres transmis au moteur après vérification PEA</div></div><div><div class="small muted">Couche 2 · analyse stratégique</div><div class="metric">'+o.engine.available+' / '+o.screened+'</div><div class="metric-sub">Dossiers classables avec les indicateurs requis</div></div><div><div class="small muted">Couche 3 · score final</div><div class="metric">'+o.third.valid+' / '+o.finalists.length+'</div><div class="metric-sub">Scores suffisamment documentés</div></div></div>'+
          '<div class="section-head"><h3>Couche 2 · sélection stratégique</h3><span>Top 25 maximum</span></div>'+
          (secondRows?topTable('<th>Rang</th><th>Société</th><th>'+(o.key==='growth'?'PEG':'Score stratégique /100')+'</th><th>Couverture</th><th>Indicateurs</th>',secondRows,'Aucun titre classable.'):layer2Empty)+
          (blockerText?'<div class="notice"><strong>Indicateurs bloquants :</strong><ul>'+blockerText+'</ul></div>':'')+
          '<div class="section-head"><h3>Couche 3 · score global et décision</h3><span>Achat ≥ 75 · Vente / éviter &lt; 40</span></div>'+
          topTable('<th>Rang</th><th>Société</th><th>Score /100</th><th>Poids couvert</th><th>Signal</th>',thirdRows,'Scores finaux non calculables avec les données actuelles.')+
          '<p class="small muted">Les scores de couche 2 et 3 sont calculés si au moins 4 facteurs et 75 % du poids sont documentés ; les poids manquants sont renormalisés, sans imputation. Entre 40 et 75 : conserver / surveiller. Les signaux restent indicatifs et ne déclenchent aucun ordre. Le score est relatif aux titres analysés dans ce panel, pas une probabilité de rendement.</p></div>';
      }).join('');
  }
  window.StockPickingLayeredSelection={render,run:build};
})();