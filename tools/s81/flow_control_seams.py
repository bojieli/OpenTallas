#!/usr/bin/env python3
"""S81 die flow-control seam audit (owner rule 10-14 18:59 + HANDOFF 0az refinement 10-15).

On-die execution is static-slot: no credit / ready / room / grant / stall seam between on-chip blocks.  The ONLY
elastic boundary is the HBM stack / PHY (HBM-backed KV cache and any other HBM/PHY): the PHY's DFI ready lines into the
HBM service controller (svc_*/ctrl_*) and that controller's ingress elastic buffer; everything after its
'buffer block ready' is fixed-slot.  This tool lists every die-level port whose name is a flow-control signal and
classifies it: HBM_PHY_BOUNDARY (allowed), GLUE_TIED (glue r_rdy constant / overflow-fault only, allowed), or
ON_DIE_FLOW_CONTROL (violation; must become a static slot).

  flow_control_seams.py DIE.v [--glue DIE_glue.sv] --out OUT.json
"""
import argparse
import collections
import json
import re
import sys

FC = re.compile(r'(^|_)(rdy|ready|credit|cred|room|stall|grant|gnt|tcs|full|bp|backpressure|yr)($|_|\d)', re.I)
INST = re.compile(r'^\s*([A-Za-z_][\w$]*)\s+(?:#\(.*?\)\s*)?([A-Za-z_][\w$\[\]]*)\s*\((.*)\);\s*$')
PORT = re.compile(r'\.([A-Za-z_]\w*)\s*\(')
HBM_MASTER = re.compile(r'^(ot_hbm|dsfd_ctrl|dsfd_svc)', re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('die')
    ap.add_argument('--glue')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rows = []
    with open(a.die) as f:
        for line in f:
            mm = INST.match(line)
            if not mm or mm[1] in ('module', 'input', 'output', 'wire', 'assign'):
                continue
            master, inst, body = mm[1], mm[2], mm[3]
            for p in PORT.findall(body):
                if FC.search(p):
                    cls = 'HBM_PHY_BOUNDARY' if HBM_MASTER.match(master) else 'ON_DIE_FLOW_CONTROL'
                    rows.append(dict(inst=inst, master=master, port=p, cls=cls))
    glue = collections.Counter()
    if a.glue:
        txt = open(a.glue).read()
        for mod in re.findall(r'module\s+(\w+).*?endmodule', txt, re.S):
            pass
        glue['r_rdy_tied_1'] = len(re.findall(r'\.r_rdy\s*\(\s*1\'b1\s*\)', txt))
        glue['w_rdy_ports_unverified_use'] = len(re.findall(r'\.w_rdy\s*\(', txt))
    by = collections.Counter((r['cls'], r['master'], r['port']) for r in rows)
    out = dict(schema='opentallas.s81.flow_control_seams.v1', die=a.die,
               rule='static-slot on die; elastic only at the HBM stack/PHY boundary (DFI ready into dsfd_svc/ctrl '
                    'ingress buffer, one ready per buffer block); everything after it fixed-slot',
               summary={k: v for k, v in collections.Counter(r['cls'] for r in rows).items()},
               glue=dict(glue), by_master_port=[dict(cls=c, master=m, port=p, instances=n) for (c, m, p), n in sorted(by.items())],
               verdict='PASS' if not any(r['cls'] == 'ON_DIE_FLOW_CONTROL' for r in rows) else 'FAIL')
    open(a.out, 'w').write(json.dumps(out, indent=1) + '\n')
    print('FLOW_CONTROL_SEAMS', out['verdict'], out['summary'])
    for r in out['by_master_port']:
        if r['cls'] != 'HBM_PHY_BOUNDARY':
            print(' ', r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
