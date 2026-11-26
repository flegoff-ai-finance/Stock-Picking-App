/* Stock Picking PEA — moteurs de scoring v1
 * Scores calculés uniquement sur les titres de window.stockPickingPeaUniverse.
 * Donnée manquante = score N/D ; aucune imputation ni donnée fictive.
 */
(function(){
  'use strict';
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const num=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
  const pctRank=(values,value,ascending=false)=>{
    const valid=values.filter(v=>v!==null).sort((a,b)=>a-b);
    if(value===null||!valid.length)return null;
    if(valid.length===1)return 50;
    let below=0,equal=0;for(const x of valid){if(x<value)below++;else if(x===value)equal++;}
    const p=100*(below+(equal-1)/2)/(valid.length-1);
    return ascending?100-p:p;
  };
  const average=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
  const complete=(obj,keys)=>keys.every(k=>num(obj[k])!==null);
  const scoreCohort=(items,extract,keys,directions,weights)=>{
    const raw=items.map(x=>({x,values:keys.map(k=>num(extract(x)[k]))}));
    const columns=keys.map((_,i)=>raw.map(r=>r.values[i]));
    return raw.map(r=>{
      if(r.values.some(v=>v===null))return {item:r.x,score:null,coverage:r.values.filter(v=>v!==null).length,components:[]};
      const components=r.values.map((v,i)=>pctRank(columns[i],v,directions[i]));
      const totalWeight=weights.reduce((a,b)=>a+b,0);\n      const score=components.reduce((sum,v,i)=>sum+v*weights[i],0)/totalWeight;\n      return {item:r.x,score,coverage:keys.length,components};
    });
  };
  function growth(items){
    const rows=items.map(x=>{const pe=num(x.forward_pe),growth=num(x.eps_growth_cagr_pct);const peg=pe!==null&&growth!==null&&pe>0&&growth>0?pe/growth:null;return {item:x,peg,score:peg!==null?peg:null,reason:peg===null?'PER prévisionnel ou croissance BPA manquant, nul ou non positif':null};});
    const valid=rows.filter(r=>r.peg!==null).sort((a,b)=>a.peg-b.peg);
    valid.forEach((r,i)=>r.rank=i+1);
    return {name:'Growth — PEG',rows:valid.concat(rows.filter(r=>r.peg===null)),ranked:valid,available:valid.length,required:items.length,top25:valid.slice(0,25)};
  }
  function quality(items){
    const keys=['revenue_cagr_3y_pct','operating_income_cagr_3y_pct','operating_margin_pct','fcf_margin_pct','roic_pct','net_debt_ebitda','sharpe_3y','max_drawdown_3y_pct'];
    const directions=[false,false,false,false,false,true,false,false];
    const scored=scoreCohort(items,x=>x,keys,directions,[15,15,15,15,15,10,10,5]).map(r=>({item:r.item,score:r.score,coverage:r.coverage,components:r.components,reason:r.score===null?'Au moins un indicateur fondamental ou de risque manque':null}));
    const ranked=scored.filter(r=>r.score!==null).sort((a,b)=>b.score-a.score);
    ranked.forEach((r,i)=>r.rank=i+1);
    return {name:'Growth Quality',rows:ranked.concat(scored.filter(r=>r.score===null)),ranked,available:ranked.length,required:items.length,top25:ranked.slice(0,25),indicators:keys};
  }
  function momentum(items){
    const keys=['return_12_1m_pct','return_6m_pct','price_vs_sma200_pct','sma50_vs_sma200_pct','sharpe_3y','max_drawdown_1y_pct','volatility_1y_pct','relative_return_6m_pct'];
    const directions=[false,false,false,false,false,false,true,false];
    const scored=scoreCohort(items,x=>x,keys,directions,[25,15,15,10,10,10,5,10]).map(r=>({item:r.item,score:r.score,coverage:r.coverage,components:r.components,reason:r.score===null?'Historique de cours, moyennes mobiles, benchmark ou risque incomplet':null}));
    const ranked=scored.filter(r=>r.score!==null).sort((a,b)=>b.score-a.score);
    ranked.forEach((r,i)=>r.rank=i+1);
    return {name:'Growth Momentum',rows:ranked.concat(scored.filter(r=>r.score===null)),ranked,available:ranked.length,required:items.length,top25:ranked.slice(0,25),indicators:keys};
  }
  function run(universe){
    const eligible=Array.isArray(universe)?universe.filter(x=>x&&x.pea_status==='eligible'&&x.isin&&x.pea_checked_at):[];
    return {universeCount:eligible.length,growth:growth(eligible),quality:quality(eligible),momentum:momentum(eligible)};
  }
  window.StockPickingEngines={run,growth,quality,momentum};
})();