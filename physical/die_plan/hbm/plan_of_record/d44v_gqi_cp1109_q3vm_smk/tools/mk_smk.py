#!/usr/bin/env python3
"""mk_smk.py BASE_PLAN_JSON P11_DIR OUT_DIR

DIE-HBM-97/COUNT 2026-11-09 (rebased onto the merged opsb overlay): counter plan d44v_gqi_cp1109_q3vm_smk =
d44v_gqi_cp1109_q3vm_opsb (BASE; its 2 opsb_output pins_file leaves are kept) with the four q_sm partition
types (q_sm0..q_sm3) taken from the HBM wave plan p11 (2bd45422, = restjrev 6cc23d96 for these types): the SM-ASBUILT
q_sm kids (smh_xs/bdc/tcl_gu/tct/pt_w/pt_e, sm_* and static_front) replace the hnx_rp3h_* hard cores.
Only partition_types.q_sm0..3 and the top-level note change; the 17 pin tables those types name are copied (gzip -n)
into OUT_DIR/cores.  Fails closed if the q_sm partitions, type outlines or any non-q_sm leaf differ.
"""
import gzip, hashlib, json, pathlib, re, sys

base_p, p11_d, out_d = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
QS = ('q_sm0', 'q_sm1', 'q_sm2', 'q_sm3')
raw = base_p.read_text()
B = json.loads(raw)
assert json.dumps(B) == raw, 'base plan is not compact json.dumps output'
P = json.loads((p11_d / 'die_plan.json').read_text())
TB, TP = B['partition_types'], P['partition_types']
# guards: same q_sm partitions, same type frame (only as-built keys may differ)
assert [x for x in B['partitions'] if x.get('type') in QS] == [x for x in P['partitions'] if x.get('type') in QS]
AS_BUILT = {'cells', 'clock', 'contents', 'hard', 'hard_cores', 'note', 'reset'}
for tk in QS:
    diff = {k for k in set(TB[tk]) | set(TP[tk]) if TB[tk].get(k) != TP[tk].get(k)}
    assert diff <= AS_BUILT, (tk, diff - AS_BUILT)
old_mods = sorted({h['module'] for tk in QS for h in TB[tk]['hard_cores']})
new_mods = sorted({h['module'] for tk in QS for h in TP[tk]['hard_cores']})
N = json.loads(raw)
for tk in QS:
    N['partition_types'][tk] = json.loads(json.dumps(TP[tk]))
N['note'] = ('DIE-HBM-97/COUNT smk_1109 (counter overlay: q_sm0..3 partition types = HBM wave plan p11 2bd45422 '
             '(SM-ASBUILT q_sm kids replace hnx_rp3h_*); nothing else) <- ' + (B.get('note') or ''))
# leaf check: nothing outside partition_types.q_sm0..3 and /note changed
def leaves(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from leaves(v, p + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from leaves(v, '%s[%d]' % (p, i))
    else: yield p, o
lb, ln = dict(leaves(B)), dict(leaves(N))
changed = sorted(k for k in set(lb) | set(ln) if lb.get(k, '<absent>') != ln.get(k, '<absent>'))
outside = [k for k in changed if not (k == '/note' or any(k.startswith('/partition_types/%s/' % q) for q in QS))]
assert not outside, outside[:10]
# the opsb overlay's leaves are kept
for tk in ('q_b113', 'q_b113__physical_v1'):
    assert [h['pins_file'] for h in N['partition_types'][tk]['hard_cores'] if h['module'] == 'ot_hgi_sfu_opsb_output'] == \
        ['cores/ot_hgi_sfu_opsb_output__760.32x280.8__ev74_tall__lwa375.json'], tk
# pin tables
refs = sorted({h['pins_file'] for tk in QS for h in TP[tk]['hard_cores'] if h.get('pins_file')})
(out_d / 'cores').mkdir(parents=True, exist_ok=True)
tables = []
for r in refs:
    b = (p11_d / r).read_bytes()
    (out_d / (r + '.gz')).write_bytes(gzip.compress(b, mtime=0))
    tables.append(dict(table=r, sha256=hashlib.sha256(b).hexdigest(), pins=len(json.loads(b))))
data = json.dumps(N).encode()
(out_d / 'die_plan.json.gz').write_bytes(gzip.compress(data, mtime=0))
ev = dict(schema='opentallas.hbm_plan_event.v1', event='smk_1109', plan='d44v_gqi_cp1109_q3vm_smk',
          base='d44v_gqi_cp1109_q3vm_opsb die_plan.json (sha256 %s)' % hashlib.sha256(raw.encode()).hexdigest(),
          source='HBM wave plan p11 die_plan.json (sha256 %s), q_sm0..3 = restjrev_1109 6cc23d96 for these types'
                 % hashlib.sha256((p11_d / 'die_plan.json').read_bytes()).hexdigest(),
          lane='DIE-HBM-97/COUNT', date='2026-11-09',
          types=list(QS), type_keys_replaced=sorted(AS_BUILT),
          hard_cores_old=sum(len(TB[t]['hard_cores']) for t in QS), hard_cores_new=sum(len(TP[t]['hard_cores']) for t in QS),
          modules_removed=[m for m in old_mods if m not in new_mods], modules_added=[m for m in new_mods if m not in old_mods],
          leaves_changed=len(changed), leaves_outside_q_sm=0, tables=tables,
          plan_sha256=hashlib.sha256(data).hexdigest(),
          not_changed='partitions, ports, lanes, every other type, clock_entries/core_conns/core_macros sidecars')
(out_d / 'smk_1109_event.json').write_text(json.dumps(ev, indent=1) + '\n')
print(json.dumps({k: ev[k] for k in ('hard_cores_old', 'hard_cores_new', 'modules_removed', 'modules_added', 'leaves_changed', 'plan_sha256')}, indent=1))
