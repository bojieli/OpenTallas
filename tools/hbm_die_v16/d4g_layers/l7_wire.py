#!/usr/bin/env python3
"""HBM-WIRE 10-18: contract post-layer L7 (after l6_collq) -- functional wiring of the d4g die.

    l7_wire.py IN_contract.json[.gz] OUT_contract.json --report R.json

TOKEN-PASS-HBMDS graded every DS layer BLOCKED on G-CIL-INJ/DEL/RC, G-SMVM-XCMD, G-HC-ENG, G-SFU-OPERAND-JOIN-*, G-DMA-WB.
The functional check (tools/hbm_die_v16/d4g_functional_bind.py: every compiled command/data consumer pin driven by its
compiled producer, bit for bit, plus the schedule-slot parameter rules) shows on the GEN2 pre-relay contract:
  * all 1,152 producer -> consumer paths of those classes ARE bound bit-exactly (cxport leaves, cij x4, xcal + x-load
    issuer, HC root + quarter hubs + bank rings, sfustore vi_q, DMA write-back partner): the contract's gap list was
    never pruned when the layers bound them (stale since v16 / GEN1 l2-l5b);
  * ONE real functional gap: l5b_cij4 put cij_<q> (INJLAT 12) between cxij_<q> and hb_coll_<q> in SE / NW / NE but left
    those cxij leaves at their pre-join parameters INJ_RET 11 / B39_NOOP 0.  The join samples the SU word at
    P+INJLAT-2 and needs the SU inj_d register at P+INJLAT-3 = P+9 (ot_hgi_coll_inj_idx_join.sv header; cij_SW binding
    note "SU reg at P+9"), so every SU-sourced inject word in SE/NW/NE reaches COLL two edges stale, and an IDX-staging
    request (addr_lo[39]=1) is read (and checked) as an SU address.  cxij_SW (INJ_RET 9, B39_NOOP 1) is the reference.
This layer:
  1. re-parametrises cxij_SE/NW/NE: INJ_RET 11 -> 9, B39_NOOP 0 -> 1 (= cxij_SW; same master
     ot_hbm_su_static_cxport_ij, same ports/edges; the leaf is SYNTH -> 3 new synthesis cells, no route change);
  2. syncs the gap list: every gap whose functional paths ALL pass after (1) gets status 'closed' + closed_by
     (entries are kept, never deleted), so layer_coverage.py stops grading closed paths BLOCKED.
"""
import argparse, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H)); sys.path.insert(0, str(H.parent))
import l3_vm_hc_coll as L3M  # noqa: E402
import d4g_functional_bind as FB  # noqa: E402

REGION = 'd4g_gen2_l7_wire'
FIX = {'INJ_RET': 9, 'B39_NOOP': 1}


def run(c, rep):
    I = c['instances']
    fixed = []
    for q in ('SE', 'NW', 'NE'):
        n = f'cxij_{q}'
        assert n in I and I[n]['master'] == 'ot_hbm_su_static_cxport_ij', n
        assert f'cij_{q}' in I and int(I[f'cij_{q}']['params']['INJLAT']) - 3 == FIX['INJ_RET'], q
        old = {k: I[n]['params'].get(k) for k in FIX}
        if old != FIX:
            I[n]['params'].update(FIX)
            I[n]['region'] = REGION
            I[n]['note'] = (I[n].get('note') or '') + (f' | {REGION}: {old} -> {FIX} (cij_{q} join INJLAT 12 samples the SU word '
                                                        f'at P+INJLAT-2: SU inj_d register at P+9, as cxij_SW; bit 39 = IDX staging)')
            fixed.append(dict(inst=n, old=old, new=dict(FIX)))
    res = FB.check(c, FB.spec())
    pres = FB.check_params(c, FB.param_rules())
    st = {}
    for r in res + pres:
        st.setdefault(r['gap'], []).append(r['status'])
    closed = []
    for g in c.get('gaps', []):
        s = st.get(g['id'])
        if s and all(x == 'PASS' for x in s) and g.get('status') != 'closed':
            g['status'] = 'closed'
            g['closed_by'] = (f'{REGION}: tools/hbm_die_v16/d4g_functional_bind.py -- all {len(s)} compiled producer->consumer '
                              f'paths/slot rules of this gap bound bit-exactly in this contract; slice bench '
                              f'tools/hbm_die_v16/d4g_wire_bench_*.py (lanes/HBM-WIRE.md)')
            closed.append(g['id'])
    c.setdefault('notes', [])
    note = (f'{REGION}: cxij SE/NW/NE INJ_RET 9 / B39_NOOP 1 (inject slot behind cij); gaps closed by the functional check: '
            f'{", ".join(closed)}')
    if isinstance(c['notes'], list):
        c['notes'].append(dict(region=REGION, note=note))
    else:
        c['notes'][REGION] = note
    fails = [r for r in res + pres if r['status'] != 'PASS']
    rep.update(fixed=fixed, closed_gaps=closed, functional_fail=len(fails),
               open_gaps=sorted({r['gap'] for r in fails}), paths=len(res), slot_rules=len(pres))
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = L3M.ld(a.inp)
    rep = dict(schema='opentallas.hbm.d4g.gen2_l7_wire.v1', region=REGION, inp=str(a.inp))
    fails = run(c, rep)
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L7', json.dumps(dict(fixed=len(rep['fixed']), closed=rep['closed_gaps'], functional_fail=rep['functional_fail'])))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
