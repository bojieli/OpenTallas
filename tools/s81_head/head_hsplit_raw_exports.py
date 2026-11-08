#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: re-source the die START stages that read hd_host raw reset relays (l48uo: 5 stages, host
rst_start_raw_0..3) from the actual raw relays of hd_host_w / hd_host_e (head_start_reset_exports.plan_exports rule:
nearest registered raw relay, role raw/boot/bootstrap_transport, hop <= 405), and declare the type exports
(head_start_reset_aliases.declare). Only host stages and host types change."""
import json, sys, copy, gzip
sys.path[:0] = ['tools/die_plan', 'tools/s81_head']
import schema as S, reset_tree as R
from head_start_reset_aliases import declare
from pathlib import Path
plan_path, stages_gz, out_dir = sys.argv[1:4]
P = S.Plan(S.load(plan_path), Path(plan_path)); W = R.wf_plan(P)
st = json.load(gzip.open(stages_gz))
cands = []
for pn in ('host_w', 'host_e'):
    tn = P.parts[pn]['type']; T = R.for_type(P, tn)
    raw = R.start_relays(T) if T.get('start') else T['relays']
    for r in raw:
        if T.get('start') and r['role'] not in ('raw', 'boot', 'bootstrap_transport'): continue
        xy = P.to_die(pn, r['xy'])
        rel = W['parts'][pn]['release'] - R.release_clocks(T) + R.entry_stages(T) + r['depth']
        cands.append(dict(part=pn, type=tn, instance=r['name'], net=r['q'], xy_um=list(xy), local_xy_um=list(r['xy']), raw_release=rel))
dist = lambda a, b: sum(abs(x - y) for x, y in zip(a, b))
rows = []; uses = {}
for s in st['stages']:
    src = s.get('reset_source', {})
    if src.get('part') != 'host': continue
    c = min(cands, key=lambda q: (dist(s['clock_pin_xy_um'], q['xy_um']), q['part'], q['net']))
    d = dist(s['clock_pin_xy_um'], c['xy_um'])
    uses[(c['type'], c['instance'], c['net'])] = c
    rows.append(dict(stage=s['id'], xy=s['clock_pin_xy_um'], old=dict(port=src['port'], instance=src['instance'], raw_release=src['raw_release'], hop=s['reset_hop_um']), new=c, hop=round(d, 3)))
types = {}; alias = {}
for tn in ('hd_host_w', 'hd_host_e'):
    for n, key in enumerate(sorted(k for k in uses if k[0] == tn)):
        c = uses[key]; port = f'rst_start_raw_{n}'; alias[key] = port
        types.setdefault(tn, []).append(dict(port=port, instance=c['instance'], net=c['net'], xy_um=[round(v, 4) for v in c['local_xy_um']]))
for r in rows:
    c = r['new']; r['new'] = dict(c, port=alias[(c['type'], c['instance'], c['net'])])
raw_plan = json.load(open(plan_path))
newp = declare(raw_plan, dict(types=types))
Path(out_dir).mkdir(parents=True, exist_ok=True)
json.dump(newp, open(out_dir + '/source_plan.json', 'w'), indent=1)
json.dump(dict(types=types, stages=rows), open(out_dir + '/raw_exports.json', 'w'), indent=1)
for r in rows: print(r['stage'], r['xy'], 'old', r['old']['port'], r['old']['instance'], 'rel', r['old']['raw_release'], 'hop', r['old']['hop'], '-> new', r['new']['part'], r['new']['port'], r['new']['instance'], r['new']['net'], 'rel', r['new']['raw_release'], 'hop', r['hop'])
print(json.dumps(types))
