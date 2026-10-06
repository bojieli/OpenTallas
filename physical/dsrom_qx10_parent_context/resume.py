#!/usr/bin/env python3
"""Resume the failed native parent from its immutable pre-PDN checkpoint.

Invoke only through the unchanged host guard in a clean, pinned own snapshot.
The source/objects of the baseline are never modified. No synthesis or smoke
replay: RTL identity is checked before accepting the retained checkpoint.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'physical/dsrom_qx10_parent_context'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--boundary-hold',action='store_true')
    ap.add_argument('--region-only',action='store_true',help='Resume PDN with canonical initial-place empty-core removal; omit broken automatic-density prequery')
    a=ap.parse_args();out=a.out.resolve();baseline=a.baseline.resolve()
    if out==baseline or (out/'resume.terminal.json').exists():
        raise SystemExit('fresh own variant required; preserve every terminal')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():
        raise SystemExit('resume requires clean pinned own source')
    pins=json.loads((ROOT/'results/uarch/dsrom_qx10_parent_context_20261005/source_inventory.json').read_text())
    for p,h in pins['files'].items():
        if digest(ROOT/p)!=h:raise SystemExit('source pin changed: '+p)
    original=json.loads((baseline/'src/results/uarch/dsrom_qx10_parent_context_20261005/source_inventory.json').read_text())
    identical=[]
    for p,h in original['files'].items():
        if p.endswith(('.sv','.v','.lib','.lef','.sdc')):
            if digest(ROOT/p)!=h:raise SystemExit('retained RTL/macro/clock cut differs: '+p)
            identical.append(p)
    if (baseline/'smoke.rc').read_text().strip()!='0':
        raise SystemExit('baseline has no retained functional PASS')
    model_name='boundary_hold_model.json' if a.boundary_hold else 'model.json'
    model=json.loads((ROOT/'results/uarch/dsrom_qx10_parent_context_20261005'/model_name).read_text())
    if not model['full_context_build_ready']:
        raise SystemExit('unified model rejects resumed context')
    if a.region_only and a.boundary_hold:
        raise SystemExit('region-only correction preserves the retained PDN and all memberships; no concurrent hold variant')
    checkpoint='2_4_floorplan_pdn.odb' if a.region_only else '2_3_floorplan_tapcell.odb'
    work=out/'work/orfs'
    result=next(work.glob('results/asap7/*/base'))
    old_result=next((baseline/'work/orfs').glob('results/asap7/*/base'))
    reused={}
    for n in dict.fromkeys(('1_2_yosys.v','1_synth.odb','2_3_floorplan_tapcell.odb',checkpoint)):
        if digest(result/n)!=digest(old_result/n):raise SystemExit('checkpoint identity changed: '+n)
        reused[n]=digest(result/n)
    hooks=[('region_only.tcl','region_only.tcl')] if a.region_only else [('pdn_count_fix.tcl','post_pdn_regions.tcl')]
    if a.boundary_hold:
        if model['boundary_hold']['buffers']!=3:raise SystemExit('missing three-buffer model')
        hooks=[('regions.tcl','post_pdn_regions.tcl'),('hold_boundary.tcl','post_detail_place_hold_boundary.tcl')]
    for source,target in hooks:
        shutil.copy2(BASE/source,work/'hooks'/target)
    image=subprocess.check_output(['docker','image','inspect','openroad/orfs:latest',
                                   '--format','{{.Id}}'],text=True).strip()
    if a.region_only:
        baseline_receipt=json.loads((baseline/'resume.receipt.json').read_text())
        if image!=baseline_receipt['image_id']:
            raise SystemExit('region-only continuation requires the exact retained canonical image')
        if 'export PLACE_DENSITY = 0.6\n' not in (work/'config.mk').read_text():
            raise SystemExit('region-only continuation requires unchanged modeled density0.6')
    receipt=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 image_id=image,baseline=str(baseline),reused_checkpoint_sha256=reused,
                 checkpoint=checkpoint,region_only=a.region_only,place_density=0.6,
                 automatic_density_prequery_disabled=a.region_only,tool_binary_changed=False,
                 identical_RTL_macro_and_clock_sources=identical,smoke_replayed=False,
                 added_pipeline_cycles=0,mandatory_boundary_buffers=3 if a.boundary_hold else 0,started_ns=time.time_ns(),
                 setup_uncertainty_ps=60,hold_uncertainty_ps=25,missing_input_clocks=True)
    (out/'resume.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    relative=result.relative_to(work)
    # -o marks only the source-identical completed checkpoint as already built.
    # Subsequent PDN/placement/CTS/route stages execute for this physical variant.
    shell=('source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
           'python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && '
           'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=4 '
           +('POST_DETAIL_PLACE_TCL=/work/hooks/post_detail_place_hold_boundary.tcl ' if a.boundary_hold else '')+
           ('PLACE_DENSITY_LB_ADDON= PRE_GLOBAL_PLACE_SKIP_IO_TCL=/work/hooks/region_only.tcl '
            'POST_GLOBAL_PLACE_SKIP_IO_TCL=/work/hooks/region_only.tcl ' if a.region_only else '')+
           f'-o /work/{relative}/{checkpoint} finish metadata-generate')
    command=['docker','run','--rm','-v',str(ROOT)+':/src:ro','-v',str(work)+':/work',
             '-w','/OpenROAD-flow-scripts/flow',image,'bash','-lc',shell]
    (out/'resume.command.json').write_text(json.dumps(command,indent=2)+'\n')
    with (out/'resume.log').open('x') as log:
        rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
    (out/'resume.terminal.json').write_text(json.dumps(dict(returncode=rc,ended_ns=time.time_ns(),
        all_sources_logs_objects_preserved=True,physical_qualified=False,missing_input_clocks=True),indent=2)+'\n')
    raise SystemExit(rc)
