#!/usr/bin/env python3
"""mk_opsb_counter.py BASE_PLAN_JSON NEW_TABLE_JSON OUT_DIR

DIE-HBM-97/COUNT 2026-11-09: counter plan d44v_gqi_cp1109_q3vm_opsb = d44v_gqi_cp1109_q3vm with the two
ot_hgi_sfu_opsb_output pins_file fields pointed at the __lwa375 table (event opsbpins_1109: 9 unread lwa[375..383]
input pins dropped).  Fails closed unless exactly those 2 fields and the top-level note change.
"""
import gzip, hashlib, json, pathlib, sys
base_p, table_p, out_d = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
OLD = 'cores/ot_hgi_sfu_opsb_output__760.32x280.8__ev74_tall.json'
NEW = 'cores/ot_hgi_sfu_opsb_output__760.32x280.8__ev74_tall__lwa375.json'
raw = base_p.read_text(); B = json.loads(raw)
assert json.dumps(B) == raw
N = json.loads(raw)
n = 0
for tk in ('q_b113', 'q_b113__physical_v1'):
    for h in N['partition_types'][tk]['hard_cores']:
        if h.get('module') == 'ot_hgi_sfu_opsb_output':
            assert h['pins_file'] == OLD, h['pins_file']; h['pins_file'] = NEW; n += 1
assert n == 2
N['note'] = ('DIE-HBM-97/COUNT opsbpins_1109 (counter overlay: ot_hgi_sfu_opsb_output pins_file -> __lwa375 table, '
             '9 unread lwa[375..383] input pins dropped; q_b113 + q_b113__physical_v1) <- ' + (B.get('note') or ''))
def leaves(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from leaves(v, p + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from leaves(v, '%s[%d]' % (p, i))
    else: yield p, o
lb, ln = dict(leaves(B)), dict(leaves(N))
changed = sorted(k for k in set(lb) | set(ln) if lb.get(k) != ln.get(k))
assert len(changed) == 3 and all(k == '/note' or k.endswith('/pins_file') for k in changed), changed
t = table_p.read_bytes()
assert hashlib.sha256(t).hexdigest() == '68eaa7f152b1f25d83bb2ea0437c448bab399a02122e75c9f692fd35c04ef33a'
(out_d / 'cores').mkdir(parents=True, exist_ok=True)
(out_d / (NEW + '.gz')).write_bytes(gzip.compress(t, mtime=0))
data = json.dumps(N).encode()
(out_d / 'die_plan.json.gz').write_bytes(gzip.compress(data, mtime=0))
print('changed', changed); print('plan sha256', hashlib.sha256(data).hexdigest())
