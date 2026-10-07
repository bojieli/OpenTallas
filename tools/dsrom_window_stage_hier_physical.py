#!/usr/bin/env python3
"""Route the full NPC32/128-row WINDOW stage with all 68 real hardened columns."""
import argparse
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--clock-period-ns',default='0.8333333333333333',
                   help='route SDC period; margin-first routes use 0.770 and sign off separately at 0.833333')
    p.add_argument('--margin',type=int,default=0,choices=(0,1),help='stage MARGIN parameter (default off)')
    p.add_argument('--split-columns',type=int,default=1,choices=(1,2))
    p.add_argument('--column-views',default='physical/dsrom_window_columns',
                   help='directory of adopted M2-M6 macro views; no view substitution is implicit')
    a=p.parse_args(); out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'work/orfs/tmp').mkdir(parents=True)
    cmd=['python3','tools/run_abi3_physical.py','--view','asap7',
         '--top','ot_dsrom_window_stage_pipeline','--param',f'SPLIT_COLUMNS={a.split_columns}',
         *(['--param','MARGIN=1'] if a.margin else []),
         '--source','rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_stage_pipeline.sv',
         '--clock-period-ns',a.clock_period_ns,'--clock-uncertainty-ns','0.060',
         '--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC',
         '--io-delay-fraction','0.2','--stages','pnr',
         '--die-area','0','0','1900','1900','--core-area','5','5','1895','1895',
         '--place-density','0.55','--orfs-var','PLACE_DENSITY_LB_ADDON=',
         '--max-fanout','32','--max-transition-ns','0.15',
         '--hold-margin-ns','0.008','--orfs-var','ADDER_MAP_FILE=',
         '--orfs-var','TMPDIR=/work/tmp',
         '--orfs-var','PDN_TCL=/src/physical/dsrom_window_columns/parent_pdn.tcl',
         '--orfs-var','IO_PLACER_H=M4 M6 M8','--orfs-var','IO_PLACER_V=M5 M7 M9',
         '--routing-layers','M2','M9','--macro-place-halo','4','4',
         '--step-tcl','POST_MACRO_PLACE=physical/dsrom_window_columns/place_stage.tcl',
         '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
         '--purpose','characterization','--nickname-tag','window_stage_hier'+('_margin' if a.margin else ''),
         '--keep-workdir',str(out/'work'),'--output',str(out/'physical.json')]
    for width in ((128,) if a.split_columns==2 else (128,256)):
        name=f'ot_dsrom_window_column_{width}'
        cmd+=['--macro-view',f'{name}={a.column_views}/{name}']
    (out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    rc=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,OT_ORFS_NUM_CORES='16')).returncode
    (out/'terminal.exit').write_text(str(rc)+'\n')
    raise SystemExit(rc)
if __name__=='__main__':main()
