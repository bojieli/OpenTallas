#!/usr/bin/env python3
"""Price the instanced die relay chains (tools/hbm_die_relays.py relays.json) against the budget relay/stage plan on a die GRT wire record:
relay ends added/removed vs relay_ends.json and wire stages beyond the box-to-box budget count become relay_count adders per bus, priced
with the same per-token path model as tools/hbm_die_views_recompose.py.  Usage: hbm_die_relay_price.py <relays.json> <grt work dir>"""
import json, sys, math, copy
sys.path.insert(0, 'tools')
import hbm_die_views as V
import hbm_die_views_recompose as RC
import hbm_accel_die_fp as F
from pathlib import Path
from collections import defaultdict
rel = json.load(open(sys.argv[1]))
m = V.model()[0]
grt = Path(sys.argv[2])
rends = {(r[0], r[1]) for r in m.get('relay_ends', [])}
base = RC.priced(m, grt, 5)
d_rel, d_ws = defaultdict(int), defaultdict(int)
for ch in rel['chains']:
    b = ch['bus']
    old_rel = sum((b, e) in rends for e in (ch.get('src'), ch.get('dst')))
    v_ = ch.get("relays", 0) - old_rel; d_rel[b] = v_ if b not in d_rel else max(d_rel[b], v_)
    d_ws[b] = max(d_ws[b], ch.get('wire_stages', 0) - ch.get('planned_wire_stages', ch.get('wire_stages', 0)))
m2 = dict(m)
rc = dict(m.get('relay_count', {}))
for b in set(d_rel) | set(d_ws):
    rc[b] = rc.get(b, 0) + d_rel[b] + d_ws[b]
m2['relay_count'] = rc
new = RC.priced(m2, grt, 5)
out = {}
for key in base:
    g0, g1 = base[key]['compositions']['ds_matched'], new[key]['compositions']['ds_matched']
    ar0 = g0['rows']['gate']['AR_priced_us']; ar1 = g1['rows']['gate']['AR_priced_us']
    out[key] = dict(AR_us_before=ar0, AR_us_after=ar1, delta_us=round(ar1 - ar0, 3), delta_pct=round(100 * (ar1 - ar0) / ar0, 3))
tot = dict(relay_delta=sum(d_rel.values()), relay_added=sum(v for v in d_rel.values() if v > 0), relay_removed=-sum(v for v in d_rel.values() if v < 0),
           ws_extra=sum(d_ws.values()))
print(json.dumps(dict(totals=tot, priced=out), indent=1))
