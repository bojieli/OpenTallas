#!/usr/bin/env python3
"""Resume only three frozen capture attempts after proven OpenDB API correction.

Existing synthesis and floorplan targets are explicitly old (-o), never rebuilt.
Original terminal verdicts, configuration and source stay immutable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
SOURCE_COMMIT='14940752483dad5b24a76bb640c9b5c7f47f7945'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--height',type=int,choices=(456,570,685),required=True)
    a=ap.parse_args();root=a.root.resolve();src=root/'src'
    assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==SOURCE_COMMIT
    name=f'qss_fanout_capture_{a.height}_l7';case=root/name;work=case/'work/orfs'
    base=work/'results/asap7'/f'opentallas_ot_qwen_slab_port_group_capture_asap7_{name}'/'base'
    retained=[base/n for n in ['1_2_yosys.v','1_2_yosys.sdc','1_synth.odb','1_synth.sdc','2_1_floorplan.odb','2_1_floorplan.sdc']]
    retained += [work/'config.mk',work/'constraint.sdc',work/'1_2_yosys.raw.v',
        src/'physical/qwen_slab_fanout/finite_boundary.sdc',src/'rtl/physical/ot_qwen_slab_port_group_capture.sv']
    before={str(p):sha(p) for p in retained}
    repair=root/'capture_api_repair_r1';hook=repair/f'capture_api_r2_{a.height}.tcl'
    assert (repair/f'validate_{a.height}.exit').read_text().strip()=='0'
    assert 'CAPTURE_API_MEMBERSHIP_PASS 4 EXCLUSIVE_GROUPS 512 UNIQUE_FF' in (repair/f'validate_{a.height}.log').read_text()
    assert (repair/f'regions_groups_{a.height}.def').read_text().count('+ TYPE FENCE')==4
    assert (case/'driver.exit').read_text().strip()=='1'
    out=work/'resume_r2';out.mkdir(exist_ok=False)
    config=(work/'config.mk').read_text()
    old=f'export MACRO_PLACEMENT_TCL = /src/physical/qwen_slab_fanout/capture_{a.height}.tcl'
    new=f'export MACRO_PLACEMENT_TCL = /repair/capture_api_r2_{a.height}.tcl'
    assert config.count(old)==1
    (out/'config.mk').write_text(config.replace(old,new))
    assert (out/'config.mk').read_text().replace(new,old)==config
    (out/'side_effects.mk').write_text('$(RESULTS_DIR)/%.sdc: $(RESULTS_DIR)/%.odb\n\t@test -f $@\n')
    basepath='/work/'+str(base.relative_to(work))+'/'
    make=['make','-f','Makefile','-f','/work/resume_r2/side_effects.mk',
        'DESIGN_CONFIG=/work/resume_r2/config.mk','WORK_HOME=/work','FLOW_VARIANT=base','NUM_CORES=16','-j16']
    for file in ['1_2_yosys.v','1_2_yosys.sdc','1_synth.odb','1_synth.sdc','2_1_floorplan.odb','2_1_floorplan.sdc']:
        make += ['-o',basepath+file]
    # All entries are fixed machine-generated paths; shell quoting retains literal make parameters.
    import shlex
    command='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '+shlex.join(make+[basepath+'2_2_floorplan_macro.odb'])+' && '+shlex.join(make+['finish','metadata-generate'])
    argv=['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(work)+':/work',
        '-v',str(repair)+':/repair:ro','-w','/OpenROAD-flow-scripts/flow',IMAGE,'bash','-lc',command]
    record=dict(schema='qwen.slab.capture.api_resume.r2',name=name,pid=os.getpid(),source_commit=SOURCE_COMMIT,
        hook_sha256=sha(hook),helper_sha256=sha(Path(__file__)),image=IMAGE,argv=argv,
        started_epoch=time.time(),status='RUNNING',retained_sha256=before,
        clock_geometry_RTL_unchanged=True,synthesis_repeated=False,floorplan_repeated=False,
        model_added_area_um2=0,model_added_cycles=0,flow_timeout_seconds=None)
    def save():(out/'receipt.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    save();env=os.environ.copy();env.update(OT_SYNTH_TIMEOUT_SECONDS='unlimited',OT_FLOW_TIMEOUT_SECONDS='unlimited',OT_ORFS_NUM_CORES='16',NUM_CORES='16')
    with (out/'route.log').open('w') as log:
        result=subprocess.run(argv,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=None)
    (out/'route.exit').write_text(str(result.returncode)+'\n')
    after={str(p):sha(p) for p in retained}
    record.update(status='TERMINAL',exit_code=result.returncode,ended_epoch=time.time(),retained_objects_byteidentical=(after==before),retained_after_sha256=after)
    save()
    if after!=before:raise RuntimeError('retained mapped/floorplan/source/constraint object changed')
    if (base/'6_final.odb').exists():
        with (out/'corner.log').open('w') as log:
            corner=subprocess.run([sys.executable,str(src/'tools/w18/corner_sta.py'),'--orfs-dir',str(work),
                '--macro','physical/asap7_memory_macros/ot_rom_4096x266_m8','--output',str(out/'corner_sta.json')],
                cwd=src,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=None)
        (out/'corner.exit').write_text(str(corner.returncode)+'\n')
    return result.returncode
if __name__=='__main__':sys.exit(main())
