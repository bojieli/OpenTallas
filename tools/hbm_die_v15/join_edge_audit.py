#!/usr/bin/env python3
"""Recover all incident edges of v6 new masters and quantify placement lower bounds.

No peer/source pin coordinates are invented: source-bound join pins are supplied
separately by join_face_assignment.py. Slot gaps here are necessary lower bounds.
"""
import argparse
import collections
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_globalfp as F


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    ap.add_argument('--netlist-ref', default='af261fbcb')
    ap.add_argument('--su-spec', default='/home/ubuntu/wt/hnl-0030/tools/hbm_die_v15/v16_specs/su_collport_0253.json')
    a = ap.parse_args()
    d = Path(a.plan)
    p = json.loads((d / 'corrected.P.json').read_text())
    r = json.loads((d / 'recovery.json').read_text())
    net = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                             f'{a.netlist_ref}:results/arch/hbm_die_v16/contract.json']))
    raw = Path(a.su_spec).read_bytes()
    spec = json.loads(raw)
    names = set(r['source_pins'])
    edges = [dict(source=e['source'], sink=e['sink'], bits=e['bits'], clock=e['clock'], basis=e.get('basis'))
             for e in net['edges'] if e['source'][0] in names or e['sink'][0] in names]
    edges += [dict(source=e['src'], sink=e['dst'], bits=e['bits'], clock=e['clock'], basis=e.get('basis'))
              for e in spec['edges']]

    def block(n):
        if n in p:
            return n, 'explicit window'
        if n.startswith('hb_') and n[3:] in p:
            return n[3:], 'named parent window'
        slot = net['instances'].get(n, {}).get('slot')
        if slot in p:
            return slot, 'netlist slot'
        if n.startswith('cp_svg_'):
            return n.replace('cp_svg_', 'pc_'), 'service collar parent; individual home OPEN'
        if n.startswith('hb_vms_'):
            return n.replace('hb_vms_', 'vmh_'), 'aggregate VM parent; leaf pin OPEN'
        if n == 'hb_idx':
            return 'idx_link', 'IDX transmit leaf estimate; source placement OPEN'
        return None, 'MISSING_PHYSICAL_HOME'

    missing = collections.Counter()
    data = []
    for e in edges:
        src, st = block(e['source'][0])
        dst, dt = block(e['sink'][0])
        row = dict(e, source_block=src, sink_block=dst, source_scope=st, sink_scope=dt)
        if src and dst:
            gap = F.gap(p[src], p[dst])[0]
            row['gap_lower_bound_um'] = round(gap, 3)
            row['stages_lower_bound_480'] = max(0, math.ceil(gap / 480) - 1)
        else:
            for ep, b in [(e['source'], src), (e['sink'], dst)]:
                if not b:
                    missing[ep[0]] += 1
        data.append(row)
    xc = []
    for n in sorted(names):
        if not n.startswith('xc_'):
            continue
        sm = n.replace('xc_', 'sm_')
        gap = F.gap(p[n], p[sm])[0]
        xc.append(dict(calendar=n, consumer=sm, band_gap_lower_bound_um=round(gap, 3),
                       band_stages_lower_bound_480=max(0, math.ceil(gap / 480) - 1),
                       alternative='explicit child inside its own SM frame, adjacent command capture',
                       child_stages_lower_bound=0, child_status='REQUIRES_H_SM_PARENT_SLOT_AND_VIEW'))
    out = dict(schema='opentallas.hbm.join_edges.v1', qualification='FAIL_CLOSED_PARTIAL_PHYSICAL_BINDING',
               netlist_source_ref=a.netlist_ref, su_spec_path=a.su_spec,
               su_spec_sha256=hashlib.sha256(raw).hexdigest(), su_spec=json.loads(raw),
               incident_edges=len(data), missing_physical_homes=dict(missing),
               source_masters_with_no_edges=[n for n in names if not any(e['source'][0] == n or e['sink'][0] == n for e in data)],
               xc_critical_adjacency=xc, edges=data,
               caveats=['Gap-derived stages are necessary lower bounds only; no pin route or cut proof.',
                        'Compiler fixed cycles must include actual relay stages, not these lower bounds.',
                        'New complete graph cannot be claimed while physical homes or peer pins are absent.'])
    (d / 'join_edges.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ['incident_edges', 'missing_physical_homes', 'source_masters_with_no_edges']}))
    print('XC band gap range um:', min(x['band_gap_lower_bound_um'] for x in xc), max(x['band_gap_lower_bound_um'] for x in xc))
    print('XC band relay lower-bound stages:', sorted(set(x['band_stages_lower_bound_480'] for x in xc)))


if __name__ == '__main__':
    main()
