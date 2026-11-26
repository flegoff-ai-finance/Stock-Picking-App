const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const root = process.cwd();
const document = { instruments: JSON.parse(fs.readFileSync(root + '/data/technical_screener.json', 'utf8')).instruments };
const rendered = { innerHTML: '' };
const context = { window: {}, document: { getElementById: () => rendered }, console };
vm.createContext(context);
vm.runInContext(fs.readFileSync(root + '/js/scoring-engines.js', 'utf8'), context);
vm.runInContext(fs.readFileSync(root + '/js/layered-selection.js', 'utf8'), context);

const pilot = context.window.StockPickingLayeredSelection.run(document.instruments);
assert.equal(pilot.length, 3);
assert.equal(Array.from(pilot, x => x.key).join(','), 'growth,quality,momentum');
for (const strategy of pilot) {
  assert.equal(strategy.screened, 7, strategy.key + ' should screen the seven verified pilot securities internally');
  if (strategy.key === 'growth') {
    assert.equal(strategy.finalists.length, 0, 'Growth PEG must remain N/D without 3-5 year EPS growth');
    assert.equal(strategy.third.valid, 0, 'Growth final scores must remain N/D without PEG');
  } else {
    assert.equal(strategy.finalists.length, 7, strategy.key + ' should rank the pilot using at least 75% documented weight');
    assert.equal(strategy.third.valid, 7, strategy.key + ' should calculate final scores at the 75% coverage threshold');
  }
}
assert.equal(pilot[0].engine.available, 0, 'PEG needs positive 3-5 year EPS growth estimates');
assert.equal(pilot[1].engine.available, 7, 'Quality should use its 75% documented weight without imputing ROIC or Sharpe');
assert.equal(pilot[2].engine.available, 7, 'Momentum should use its 80% documented weight without imputing Sharpe or relative return');
assert.equal(Array.from(pilot[1].finalists, x => x.item.name).slice(0,3).join(','), 'GTT,Exosens,Planisware');
assert.equal(Array.from(pilot[2].finalists, x => x.item.name).slice(0,3).join(','), 'Euronext,Planisware,VIEL & Cie');
assert.equal(Array.from(pilot[1].third.rows, x => x.item.name).slice(0,3).join(','), 'GTT,Exosens,Euronext');
assert.equal(Array.from(pilot[2].third.rows, x => x.item.name).slice(0,3).join(','), 'Euronext,VIEL & Cie,Rexel');

context.window.StockPickingLayeredSelection.render(document.instruments);
assert.ok(rendered.innerHTML.includes('Couche 2'));
assert.ok(!rendered.innerHTML.includes('premiers candidats'));
assert.ok(!rendered.innerHTML.includes('Score écran'));
assert.ok(!rendered.innerHTML.includes('Couche 1 · premiers candidats'));

const sample = [0,1,2,3].map(i => ({
  name: 'TEST' + i, isin: 'FR000000000' + i, pea_status: 'eligible', pea_checked_at: '2026-11-26',
  forward_pe: 12 + i, eps_growth_cagr_pct: 8 + i * 2,
  revenue_cagr_3y_pct: 5 + i * 3, operating_income_cagr_3y_pct: 6 + i * 3,
  operating_margin_pct: 10 + i, fcf_margin_pct: 7 + i, roic_pct: 8 + i,
  net_debt_ebitda: 2 - i * .2, sharpe_3y: .4 + i * .1,
  max_drawdown_3y_pct: -30 + i * 3, return_12_1m_pct: 5 + i * 4,
  return_6m_pct: 4 + i * 3, price_vs_sma200_pct: 2 + i * 2,
  sma50_vs_sma200_pct: 1 + i, max_drawdown_1y_pct: -20 + i * 2,
  volatility_1y_pct: 30 - i * 2, relative_return_6m_pct: 1 + i
}));
const engines = context.window.StockPickingEngines;
assert.equal(engines.growth(sample).available, 4);
assert.equal(engines.quality(sample).available, 4);
assert.equal(engines.momentum(sample).available, 4);
console.log('Selection engine tests passed: pilot data stays N/D; complete fixtures rank in all three strategies; layer 1 remains hidden.');
