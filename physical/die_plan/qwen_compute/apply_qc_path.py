#!/usr/bin/env python3
"""Compose the approved QC path metadata after floorplan generation.

B1 bootstrap roles, B2 line bumps, registered-pin PHY option B, native59
16-enable SRAM views/re-site, and the production coll_ftm clock correction.
Data lane routing, station counts and latency remain the floorplan's contract.
"""
import argparse
import json
from pathlib import Path
import apply_start_broadcast
import apply_registered_phy
import native59_memory_views
import coll_ftm_clock
import apply_st_a_ctl_width

PHY_BUMPS = [dict(pin=p,dir=d,width=w) for p,d,w in (
    ('link_v','output',1),('link_flit','output',583),('far_v','input',1),('far_flit','input',583))]


def apply(raw):
    if raw.get('die',{}).get('name') != 'qwen_compute':
        raise ValueError('QC path batch is scoped to qwen_compute')
    apply_st_a_ctl_width.apply(raw)
    apply_start_broadcast.apply(raw)
    phy=raw['partition_types']['phy_ucie_kv']
    cores=[c for c in phy['contents'] if c.get('module')=='ot_qkvd_ucie_x64_phy']
    if len(cores)!=1:raise ValueError('expected one actual UCIe hard PHY core')
    cores[0]['bump_ports']=[dict(x) for x in PHY_BUMPS]
    if any(not c.get('registered_pins') for tn in ('phy_ucie_kv','phy_serdes','phy_serdes_b')
           for c in raw['partition_types'][tn]['contents'] if c.get('inst') != 'u_pstn'):
        apply_registered_phy.apply(raw)
    native59_memory_views.attach(raw)
    coll_ftm_clock.apply(raw)
    return raw


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path)
    a=ap.parse_args()
    raw=json.loads(a.plan.read_text());apply(raw)
    tmp=a.plan.with_suffix(a.plan.suffix+'.qc-path.tmp')
    tmp.write_text(json.dumps(raw,indent=1)+'\n');tmp.replace(a.plan)


if __name__=='__main__':main()
