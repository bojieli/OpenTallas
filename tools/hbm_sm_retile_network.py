#!/usr/bin/env python3
"""Generate unqualified full-shape retile connectivity for physical path checks."""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_accel_die_fp as H


def generate():
    m=H.build(H.R24SM3,network_probe=True)
    check=H.legality(m)
    if check['overlaps'] or check['outside']:
        raise ValueError(check)
    return dict(status='network-probe-unqualified',selected=False,
      generator_sha256=hashlib.sha256(Path(H.__file__).read_bytes()).hexdigest(),
      insts=[dict(name=i.name,master=i.master,x=i.x,y=i.y,w=i.w,h=i.h,
        orient=i.orient,kind=i.kind,box_um=i.box()) for i in m['insts']],
      buses=m['buses'],paths=m['paths'],geo=m['geo'],legality=check,
      prior_split_placement_failure=['no room for the B half: w33_xmSW1',
        'no room for the B half: w186_xmNW1'],
      internal_tu_contract='W2/HA2 h_v/h_d/h_r stay inside hb_coll; no external sender bus or macro',
      remaining_gates=['measure full collective inventory including finite W2/HA2 queues in actual internal hierarchy',
        'bind actual planned SM pins and routed gather pins',
        'joint obstacle-aware bus routing and track capacity',
        'split multicast A/B path balance after moving B macro to free ninth site',
        'all extra relay registers, credit flights and token latency composition',
        'actual clock tree/domain coverage and SS/FF >=15ps DRC0',
        'actual physical views for every generated tree/relay macro'])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True)
    a=ap.parse_args();p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    r=generate();p.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(instances=len(r['insts']),buses=len(r['buses']),legality=r['legality'])))
