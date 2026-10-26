#!/usr/bin/env python3
"""HBM-BIND-CMP (COORD ruling 4, 2026-10-26): bind the SM request check on the native B2 die.

    python3 tools/hbm_b2/native_reqcheck_items.py IN_DELTA.json --die die_r18h5.v.gz --out OUT_DELTA.json

Every SM service group svg_<Q><k> that drives sm_<Q><k>.command is remastered to ot_hbm_svc_sm_group_rel_id_rc
(rtl/hbm_accel/loader/service_native/ot_hbm_sm_req_check.sv): the S1 consumer copy's data views (expected_request, lt0,
lt1, lb0, lb1, fm -- unread on the die) become internal, the SM's request is wired back (sm_request <- sm_<Q><k>.request)
and compared with the scheduled expected_request after the plan round trip RQD (tools/hbm_b2/b2_delays.py rule RQD,
carried in the delta's remaster params by make_wiring).  The sticky mismatch is ORed into svg.fault, which the host reads
per SM (cp_svg tgt_fault -> hleaf t_fault; sfault svg_fault).  Fails closed: a group without an RQD param, or whose
sm_packet / sm_command do not feed exactly the paired SM, stops the generator.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_top as T  # noqa: E402

NEW = 'ot_hbm_svc_sm_group_rel_id_rc'
DROP = ['expected_request', 'lt0', 'lt1', 'lb0', 'lb1', 'fm']


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('delta')
    ap.add_argument('--die', required=True)
    ap.add_argument('--asbuilt', help='asbuilt.json (transport rules) to trace the svg -> sm pairing through stations')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    d = json.loads(Path(a.delta).read_text())
    tr = json.loads(Path(a.asbuilt).read_text())['transport'] if a.asbuilt else []
    die = T.Die(a.die, tr)
    rm, dp, ad, rb = (d.setdefault(k, {}) for k in ('remaster', 'drop_ports', 'add_ports', 'rebuild'))
    keepq = set(d['keep']['quadrants'])
    done = []
    for n, i in sorted(die.insts.items()):
        if i['master'] != 'ot_hbm_svc_sm_group_rel_id' or not n.startswith('svg_'):
            continue
        q = T.QTAG.search(n)
        if q and q.group(1) not in keepq or n in d['keep'].get('drop_instances', []):
            continue
        sm = 'sm_' + n[4:]
        assert sm in die.insts, f'{n}: no paired {sm}'
        for port, sp in (('packet', 'sm_packet'), ('command', 'sm_command')):
            srcs = {T.src_inst(die, s[1]) for s, _ in die.resolve(T.parse_expr(die.insts[sm]['conns'][port], die.widths))
                    if s[0] == 'n'}
            assert n in srcs, f'{sm}.{port} is not fed by {n} (sources {sorted(x for x in srcs if x)})'
        r = rm.get(n, dict(master=i['master'], params=i['params']))
        assert r['master'] in ('ot_hbm_svc_sm_group_rel_id', NEW), (n, r['master'])
        assert re.search(r'\.RQD\(\d+\)', r['params']), f'{n}: no RQD param (run b2_delays.py + make_wiring --delays)'
        rm[n] = dict(master=NEW, params=r['params'])
        dp[n] = sorted(set(dp.get(n, [])) | set(DROP))
        ad.setdefault(n, {})['sm_request'] = 'in'
        rb.setdefault(n, {})['sm_request'] = [[sm, 'request', 0, 42]]
        done.append(n)
    assert done, 'no SM service group found'
    d.setdefault('items', []).append(dict(
        id='R-SM-REQ-CHECK', kind='rtl+wiring',
        status=f'implemented on {len(done)} groups ({", ".join(done)}); bench rtl/test/hbm_bind_cmp/run_sm_req_check.sh',
        what='sm.request vs svg expected_request sticky mismatch (RQD from b2_delays) ORed into svg.fault; the S1 copy '
             'views expected_request/lt0/lt1/lb0/lb1/fm are internal to ot_hbm_svc_sm_group_rel_id_rc'))
    Path(a.out).write_text(json.dumps(d, indent=1))
    print(f'REQCHECK groups={len(done)}')


if __name__ == '__main__':
    main()
