"""Compose same-model schedule deltas relative to the existing price receipt."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sweeps = json.loads((HERE/'sweeps.json').read_text())
old = json.loads((HERE.parent/'hbm_price_qdq54_hc17_1021/result.json').read_text())
out = {'schema':'opentallas.hbm_price_p40_r18.v1',
       'status':'conditional_source_adoption_not_full_l12_geometry',
       'mtp':'deferred; no AR-to-MTP extrapolation', 'rows':[]}
for key, prevkey in [('release','h9b'),('next','r7xl')]:
    assert set(sweeps[key]) == {'previous','p40_r18','rl75_sensitivity'}
    for pair in sweeps[key].values():
        assert pair['ds']['classes']['HC.HC_MIX']['n'] == 80
        assert pair['ds']['classes']['FUSED.QDQ_FP8']['n'] == 40
        assert pair['qwen']['classes'] == {}
        assert pair['qwen']['schedule_total'] == sweeps[key]['previous']['qwen']['schedule_total']
    before = sweeps[key]['previous']['ds']['classes']
    after = sweeps[key]['p40_r18']['ds']['classes']
    assert after['HC.HC_MIX']['used_sum']-before['HC.HC_MIX']['used_sum'] == 80*17
    assert after['FUSED.QDQ_FP8']['used_sum']-before['FUSED.QDQ_FP8']['used_sum'] == 40*73
    rec = next(r for r in old['rows'] if r['base']==prevkey)
    # Preserve unrounded token cycle inputs used by the previous composition.
    ds0 = {'release':1207635.2,'next':901166.7}[key] + rec['ds_sched_delta']/.9887
    qw0 = {'release':2232996.1,'next':1198142.9}[key] + rec['qwen_sched_delta']/.9993
    for variant, pair in sweeps[key].items():
        row = {'base':key,'variant':variant,'ds_users':1,'qwen_users':1}
        for design, cyc0, factor in [('ds',ds0,.9887),('qwen',qw0,.9993)]:
            delta = pair[design]['schedule_total'] - sweeps[key]['previous'][design]['schedule_total']
            row[design+'_schedule_delta_vs_previous'] = round(delta,1)
            row[design+'_token_cycles_delta_vs_previous'] = round(delta/factor,3)
            row[design+'_tok_s'] = round(1.2e9/(cyc0+delta/factor),1)
        out['rows'].append(row)
(HERE/'result.json').write_text(json.dumps(out,indent=2)+'\n')
for row in out['rows']:
    print(row)
