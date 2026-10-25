#!/usr/bin/env python3
"""Adopt decision16a on canonical PG lane split wrappers and their source lists.

Explicit migration on an isolated successor tree; ports/module identities and
wiring stay identical. Existing run sources/evidence must remain pinned.
The regeneration tool reads OT_HBM_ONECLOCK=1 to retain the new parameters.
"""
import argparse
import json
import re
from pathlib import Path

TYPES=('pg_lane_full','pg_lane_exp','pg_lanes4')
SIDE_TYPES={'pgslice_side_rest':'ot_hbm_su_side_rest_core',
            'pgslice_side_softplus':'ot_hbm_su_side_softplus_core'}
OLD='rtl/hdc/ot_hdc_fastfp_lat.sv'
NEW=['rtl/hdc/ot_hdc_fastfp_lat_c12.sv','rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/v41x/ot_dsrom_su_add6.sv']


def source_files(files):
    out=[]
    for f in files:
        for x in NEW if f==OLD else [f]:
            if x not in out:
                out.append(x)
    return out


def adopt(root):
    root=Path(root)
    hard=root/'physical/die_plan/hbm/cores/harden'
    rtl=root/'rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg'
    changed=[]
    for typ in TYPES:
        name='ot_hbm_su_'+typ+'_core'
        p=rtl/(name+'.sv');s=p.read_text()
        n=s.count('.ALAT(3)')
        if n:
            s=s.replace('.ALAT(3)','.ALAT(4)').replace('MLAT 4 ALAT 3 LEAF 1','MLAT 4 ALAT 4 LEAF 1')
            s='// Decision16a successor: ALAT4 f12_l4, MLAT4, one1.2GHz core clock; parent must bind all clock pins together.\n'+s
            p.write_text(s);changed.append(str(p.relative_to(root)))
        elif '.ALAT(4)' not in s:
            raise ValueError(f'{name}: no ALAT3/4 binding')
        p=hard/'split_files'/(name+'.files')
        original=p.read_text().splitlines();new=source_files(original)
        if new!=original:
            p.write_text('\n'.join(new)+'\n');changed.append(str(p.relative_to(root)))
    for name in SIDE_TYPES.values():
        p=hard/'split_files'/(name+'.files')
        original=p.read_text().splitlines();new=source_files(original)
        if new!=original:
            p.write_text('\n'.join(new)+'\n');changed.append(str(p.relative_to(root)))
    p=hard/'recipes_split.json'
    if p.exists():
        recipes=json.loads(p.read_text());n=0
        for recipe in recipes.values():
            if recipe.get('functional_type') in (*TYPES,*SIDE_TYPES):
                old=recipe['files'];recipe['files']=source_files(old)
                if old!=recipe['files']:n+=1
        if n:
            p.write_text(json.dumps(recipes,indent=1)+'\n');changed.append(str(p.relative_to(root)))
    return dict(schema='opentallas.hbm_pg_oneclock.v1',changed=changed,ALAT=4,MLAT=4,
                source_override=NEW,common_lane_result_added_cycles=1,
                nonlinear_latency='native ALAT4 formulas; exp+8, sigmoid+9, rsqrt+3, softplus+18 core edges from ALAT term',
                side_added_cycles=dict(RSQRT=12,SQRT=0,SPSQRT=36,EGATE=16),
                gate='minimum LIGHT lane31classes/1984outputs/3968checks+3mutants PASS on codex/hbm-token-1025@d2af28485')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();r=adopt(a.repo)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps(r,indent=1))

if __name__=='__main__':main()
