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
    ap.add_argument('--mapped-cfg',action='store_true',help='Reuse actual cfg-parent mapped Verilog and repair only the consumed-bit SDC assertion')
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
            if a.mapped_cfg and p=='physical/dsrom_qx10_parent_context/cfg_boundary.sdc': continue
            if digest(ROOT/p)!=h:raise SystemExit('retained RTL/macro/clock cut differs: '+p)
            identical.append(p)
    if (baseline/'smoke.rc').read_text().strip()!='0':
        raise SystemExit('baseline has no retained functional PASS')
    model_name='hard_cfg_model.json' if a.mapped_cfg else ('boundary_hold_model.json' if a.boundary_hold else 'model.json')
    model=json.loads((ROOT/'results/uarch/dsrom_qx10_parent_context_20261005'/model_name).read_text())
    if not model['full_context_build_ready']:
        raise SystemExit('unified model rejects resumed context')
    if a.region_only and a.boundary_hold:
        raise SystemExit('region-only correction preserves the retained PDN and all memberships; no concurrent hold variant')
    if a.mapped_cfg and (a.region_only or a.boundary_hold): raise SystemExit('mapped-cfg assertion-only continuation')
    checkpoint='1_2_yosys.v' if a.mapped_cfg else ('2_4_floorplan_pdn.odb' if a.region_only else '2_3_floorplan_tapcell.odb')
    work=out/'work/orfs'
    result=next(work.glob('results/asap7/*/base'))
    old_result=next((baseline/'work/orfs').glob('results/asap7/*/base'))
    reused={}
    for n in (('1_2_yosys.v',) if a.mapped_cfg else dict.fromkeys(('1_2_yosys.v','1_synth.odb','2_3_floorplan_tapcell.odb',checkpoint))):
        if digest(result/n)!=digest(old_result/n):raise SystemExit('checkpoint identity changed: '+n)
        reused[n]=digest(result/n)
    hooks=[] if a.mapped_cfg else [('region_only.tcl','region_only.tcl')] if a.region_only else [('pdn_count_fix.tcl','post_pdn_regions.tcl')]
    if a.boundary_hold:
        if model['boundary_hold']['buffers']!=3:raise SystemExit('missing three-buffer model')
        hooks=[('regions.tcl','post_pdn_regions.tcl'),('hold_boundary.tcl','post_detail_place_hold_boundary.tcl')]
    for source,target in hooks:
        shutil.copy2(BASE/source,work/'hooks'/target)
    if a.mapped_cfg:
        old_sdc=(baseline/'src/physical/dsrom_qx10_parent_context/cfg_boundary.sdc').read_text()
        new_sdc=(BASE/'cfg_boundary.sdc').read_text()
        prefix=old_sdc[:old_sdc.index('set cfg_captures')]
        if not new_sdc.startswith(prefix): raise SystemExit('mapped-cfg must preserve original numeric/clock constraints')
        # ABI3 emits executable SDC lines, omitting comments and blanks.
        def rendered(sdc):
            return '\n'.join(line for line in sdc.splitlines() if line.strip() and not line.lstrip().startswith('#'))+'\n'
        old_append=rendered(old_sdc);new_append=rendered(new_sdc)
        for target in (work/'constraint.sdc', result/'1_2_yosys.sdc'):
            text=target.read_text()
            if text.count(old_append)!=1: raise SystemExit('retained cfg SDC append not unique')
            target.write_text(text.replace(old_append,new_append))
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
                 checkpoint=checkpoint,region_only=a.region_only,mapped_cfg=a.mapped_cfg,place_density=0.6,
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
