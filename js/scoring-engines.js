/* Stock Picking PEA — moteurs stratégiques v2.
 * Scores partiels autorisés uniquement avec >=4 facteurs et >=75 % du poids.
 * Les poids manquants sont renormalisés ; aucune donnée n'est imputée.
 */
(function(){
  'use strict';
  const num=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
  const pctRank=(values,value,lowerIsBetter=false)=>{
    const valid=values.filter(v=>v!==null).sort((a,b)=>a-b);
    if(value===null||!valid.length)return null;
    if(valid.length===1)return 50;
    let below=0,equal=0;for(const x of valid){if(x<value)below++;else if(x===value)equal++;}
    const p=100*(below+(equal-1)/2)/(valid.length-1);
    return lowerIsBetter?100-p:p;
  };
  const scoreCohort=(items,keys,directions,weights)=>{
    const raw=items.map(x=>({x,values:keys.map(k=>num(x[k]))}));
    const columns=keys.map((_,i)=>raw.map(r=>r.values[i]));
    const totalWeight=weights.reduce((a,b)=>a+b,0);
    return raw.map(r=>{
      const availableWeight=r.values.reduce((sum,v,i)=>sum+(v===null?0:weights[i]),0);
      const coverage=r.values.filter(v=>v!==null).length;
      if(coverage<4||availableWeight<totalWeight*.75){
        return {item:r.x,score:null,coverage,coverageWeightPct:availableWeight/totalWeight*100,components:[],reason:'Moins de 4 facteurs ou moins de 75 % du poids documenté'};
      }
      const components=r.values.map((v,i)=>v===null?null:pctRank(columns[i],v,directions[i]));
      const score=components.reduce((sum,v,i)=>sum+(v===null?0:v*weights[i]),0)/availableWeight;
      return {item:r.x,score,coverage,coverageWeightPct:availableWeight/totalWeight*100,components,reason:null};
    });
  };
  function growth(items){
    const rows=items.map(x=>{const pe=num(x.forward_pe),growth=num(x.eps_growth_cagr_pct);const peg=pe!==null&&growth!==null&&pe>0&&growth>0?pe/growth:null;return {item:x,peg,score:peg!==null?peg:null,reason:peg===null?'PER prévisionnel ou croissance BPA 3–5 ans manquant, nul ou non positif':null};});
    const valid=rows.filter(r=>r.peg!==null).sort((a,b)=>a.peg-b.peg);
    valid.forEach((r,i)=>r.rank=i+1);
    return {name:'Growth — PEG',rows:valid.concat(rows.filter(r=>r.peg===null)),ranked:valid,available:valid.length,required:items.length,top25:valid.slice(0,25)};
  }
  function quality(items){
    const keys=['revenue_cagr_3y_pct','operating_margin_pct','roic_pct','fcf_margin_pct','net_debt_ebitda'];
    const directions=[false,false,false,false,true];
    const weights=[25,20,20,20,15];
    const scored=items.map(item=>{
      const values=keys.map(key=>num(item[key]));
      const coverage=values.filter(value=>value!==null).length;
      const mandatory=num(item.revenue_cagr_3y_pct)!==null;
      const profitability=num(item.roic_pct)!==null||num(item.fcf_margin_pct)!==null;
      if(coverage<4||!mandatory||!profitability) return {item,score:null,coverage,coverageWeightPct:values.reduce((sum,value,i)=>sum+(value===null?0:weights[i]),0),reason:'Growth Quality : 4 indicateurs sur 5 requis, croissance du CA obligatoire et ROIC ou marge FCF obligatoire'};
      const columns=keys.map((_,i)=>items.map(row=>num(row[keys[i]])));
      const components=values.map((value,i)=>value===null?null:pctRank(columns[i],value,directions[i]));
      const availableWeight=values.reduce((sum,value,i)=>sum+(value===null?0:weights[i]),0);
      const score=components.reduce((sum,value,i)=>sum+(value===null?0:value*weights[i]),0)/availableWeight;
      return {item,score,coverage,coverageWeightPct:availableWeight,components,reason:null};
    });
    const ranked=scored.filter(r=>r.score!==null).sort((a,b)=>b.score-a.score);
    ranked.forEach((r,i)=>r.rank=i+1);
    return {name:'Growth Quality',rows:ranked.concat(scored.filter(r=>r.score===null)),ranked,available:ranked.length,required:items.length,top25:ranked.slice(0,25),indicators:keys};
  }
  function momentum(items){
    const keys=['return_12_1m_pct','return_6m_pct','price_vs_sma200_pct','volatility_1y_pct','max_drawdown_1y_pct'];
    const directions=[false,false,false,true,false];
    const weights=[25,20,20,15,20];
    const scored=items.map(item=>{
      const values=keys.map(key=>num(item[key]));
      const coverage=values.filter(value=>value!==null).length;
      if(coverage<4||num(item.return_12_1m_pct)===null||num(item.return_6m_pct)===null) return {item,score:null,coverage,coverageWeightPct:values.reduce((sum,value,i)=>sum+(value===null?0:weights[i]),0),reason:'Momentum : 4 indicateurs sur 5 requis, dont performances 12-1 mois et 6 mois obligatoires'};
      const columns=keys.map((_,i)=>items.map(row=>num(row[keys[i]])));
      const components=values.map((value,i)=>value===null?null:pctRank(columns[i],value,directions[i]));
      const availableWeight=values.reduce((sum,value,i)=>sum+(value===null?0:weights[i]),0);
      const score=components.reduce((sum,value,i)=>sum+(value===null?0:value*weights[i]),0)/availableWeight;
      return {item,score,coverage,coverageWeightPct:availableWeight,components,reason:null};
    });
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