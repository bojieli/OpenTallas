#!/usr/bin/env python3
"""Resolve the frame body from the actual already-selected functional closure."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--kit',type=Path,required=True)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();inv=json.loads(a.inventory.read_text());kit=json.loads((a.kit/'kit.json').read_text())
    assert not kit['problems']
    hits=[]
    for f in kit['files']:
        path=a.kit/'src'/f['path'];assert sha(path)==f['sha256']
        if re.search(r'\bmodule\s+col_h9_l4_lp\b',path.read_text()):hits.append(f)
    assert len(hits)==1,hits
    selected=hits[0];model=json.loads(a.schedule.read_text())
    assert model['selected_frame_path']==selected['path']
    assert model['selected_frame_sha256']==selected['sha256']
    assert model['functional_kit_sha256']==sha(a.kit/'kit.json')
    old='rtl/dsrom_sys/s81_dv/frame_lp/col_h9_l4_lp.sv'
    rejected=inv['sources'].pop(old)
    inv['canonical_frame_inventory_rejected']=dict(path=old,**rejected,
        reason='actual original port_bind rtl_extra preference selects different emitted body')
    inv['sources'][selected['path']]=dict(sha256=selected['sha256'],source_root_kind='functional_kit_src',
        origin=selected['origin'],binding='actual functional kit selected module col_h9_l4_lp',
        manifest_sha256=None,matches_manifest=False,binding_lines=[])
    inv['source_selection_correction']=dict(previous_inventory_sha256=sha(a.inventory),
        functional_kit_sha256=sha(a.kit/'kit.json'),emitted_frame_schedule_sha256=sha(a.schedule),
        variant_choices=kit['variant_choices'],changed_master_bodies=False,source_guard_waived=False)
    inv['status']='SELECTED_FUNCTIONAL_SOURCE_MODEL_ONLY_NOT_EXECUTED'
    a.out.write_text(json.dumps(inv,indent=1)+'\n')


if __name__=='__main__':main()
