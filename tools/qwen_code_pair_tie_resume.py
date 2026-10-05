#!/usr/bin/env python3
"""Insert actual standard ties, legalize, and route a copied retained CTS context.

Invoke through admit.sh 64. This performs no synthesis, floorplan or CTS replay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--retained-work',type=Path,required=True)
    ap.add_argument('--source-dir',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args()
    old,src,work=[p.resolve() for p in (a.retained_work,a.source_dir,a.work)]
    base=next((old/'results/asap7').glob('*/base'))
    assert (base/'4_cts.odb').is_file() and (base/'4_cts.sdc').is_file()
    work.mkdir(parents=True,exist_ok=False)
    for name in ('config.mk','constraint.sdc','mapped.v','mapped.json','capture_bindings.json','side_effects.mk','regions.tcl','local_capture_regions.tcl','route_manifest.json'):
        if (old/name).exists():shutil.copy2(old/name,work/name)
    shutil.copytree(old/'slot',work/'slot')
    target=work/base.relative_to(old);target.mkdir(parents=True)
    for name in ('4_cts.odb','4_cts.sdc'):
        shutil.copy2(base/name,target/name)
    hook=Path(__file__).with_name('qwen_code_pair_ties.tcl')
    shutil.copy2(hook,work/'ties.tcl')
    config=(work/'config.mk').read_text()
    assert 'PRE_GLOBAL_ROUTE_TCL' not in config
    (work/'config.mk').write_text(config+'\nexport PRE_GLOBAL_ROUTE_TCL = /work/ties.tcl\n')
    (work/'tmp').mkdir()
    manifest=dict(retained_work=str(old),source_dir=str(src),image=IMAGE,
        helper_sha256=sha(Path(__file__)),hook_sha256=sha(hook),
        retained_cts_sha256={n:sha(base/n) for n in ('4_cts.odb','4_cts.sdc')},
        sdc_sha256=sha(work/'constraint.sdc'),cores=16,synthesis_repeated=False,
        floorplan_repeated=False,cts_repeated=False,rtl_changed=False,
        added_cycles=0,added_state_bits=0,
        prebuild_cost='Actual load census and LEF area in tie_cost.tsv before mutation; one real tie per input or padding output; 0 clock sinks, two actual PG pins per tie. Wire/loading cost remains measured by routed SS/FF.')
    (work/'tie_successor.json').write_text(json.dumps(manifest,indent=2)+'\n')
    make='make -f Makefile -f /work/side_effects.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 -j16 '
    stages=('do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report')
    # Actual pinned ORFS spelling is fillcell (not a new placement recipe).
    commands='; '.join(f'echo PAULI_STAGE {s}; {make}{s} || exit $?' for s in stages)
    cmd=['docker','run','--rm','-e','TMPDIR=/work/tmp','-v',f'{src}:/src:ro','-v',f'{work}:/work','-w','/OpenROAD-flow-scripts/flow',IMAGE,'bash','-lc','source /OpenROAD-flow-scripts/env.sh; '+commands]
    with (work/'route.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
    (work/'route.exit').write_text(str(rc)+'\n')
    raise SystemExit(rc)

if __name__=='__main__':main()
