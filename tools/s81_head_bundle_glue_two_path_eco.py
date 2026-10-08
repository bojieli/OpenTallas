#!/usr/bin/env python3
"""Reproduce the two-endpoint physical ECO from the pinned native final ORFS tree.

The base must be the b25c67c retained-delay route (SS +44.695ps, FF -.816541ps).
No synthesis or CTS is rerun. Full GRT, DRT, extraction, final STA and GDS follow.
Actual utilization remains approximately 62.1%; this is a conditional native view.
Run remotely only after immediate host admission, with an empty --output-dir.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-orfs',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--image',default='openroad/orfs:asap7lock')
    a=ap.parse_args();base=a.base_orfs.resolve();out=a.output_dir.resolve()
    if out.exists():raise SystemExit('Refuse to overwrite any prior ECO run')
    out.mkdir(parents=True)
    work=out/'orfs';shutil.copytree(base,work)
    rb=list(work.glob('results/asap7/*/base'))
    if len(rb)!=1:raise SystemExit('Expected exactly one native result directory')
    rb=rb[0]
    record={'base_orfs':str(base),'inputs':{f:sha(rb/f) for f in ['6_final.odb','6_final.sdc','6_final.spef']},
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'scope':'native standalone; 166.6ps IO conditional; no die closure',
            'uncertainty_ps':{'setup':60,'hold':25},'added_cycles':0}
    (out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    shutil.copy2(rb/'6_final.odb',rb/'4_cts.odb')
    shutil.copy2(rb/'6_final.sdc',rb/'4_cts.sdc')
    shutil.copy2(ROOT/'physical/s81_die_views/hbglue/flat_two_path_eco.tcl',work/'two_path_eco.tcl')
    with (work/'config.mk').open('a') as f:
        f.write('\n# Retained final placement/clock tree: only two failing data paths change.\n')
        f.write('export PRE_GLOBAL_ROUTE_TCL = /work/two_path_eco.tcl\n')
        f.write('export SKIP_INCREMENTAL_REPAIR = 1\n')
    # Explicit do-route forces fresh global/detailed routes; finish consumes them.
    cmd=['docker','run','--rm','--cpus','16','-v',f'{ROOT}:/src:ro','-v',f'{work}:/work',
         '-w','/OpenROAD-flow-scripts/flow','--entrypoint','make',a.image,
         'DESIGN_CONFIG=/work/config.mk','WORK_HOME=/work','NUM_CORES=16','do-route','finish']
    with (out/'route.log').open('w') as f:r=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
    (out/'exit_code.txt').write_text(str(r)+'\n')
    return r
if __name__=='__main__':raise SystemExit(main())
