#!/usr/bin/env python3
"""Full native flat glue with explicit retained minimum-delay datapaths."""
import argparse
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args()
    cmd=[sys.executable,str(ROOT/'tools/run_abi3_physical.py'),
         '--view','asap7','--top','ot_dsrom_head_bundle_glue',
         '--source','rtl/s81/ot_dsrom_head_bundle_glue.sv',
         '--source','rtl/s81/ot_s81_head_min_delay.sv',
         '--source','rtl/hdc/ot_hdc_delay.sv','--param','USE_MIN_DELAY_CELLS=1',
         '--clock-period-ns','.833','--clock-uncertainty-ns','.060',
         '--clock-uncertainty-hold-ns','.025','--orfs-corner','WC',
         '--hold-corners','WC,BC','--stages','pnr','--io-delay-fraction','.2',
         '--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited',
         '--core-utilization','55','--place-density','.60',
         '--routing-layers','M2','M6','--orfs-var','ADDER_MAP_FILE=',
         '--max-transition-ns','.25','--orfs-var','NUM_CORES=16',
         '--orfs-var','PLACE_DENSITY_LB_ADDON=',
         '--keep-workdir',str(a.work.resolve()),'--output',str(a.output.resolve()),
         '--nickname-tag','native_flat_min_delay','--keep-heavy-artifacts']
    for hook in ['POST_PDN','POST_CTS','POST_GLOBAL_ROUTE']:
        cmd+=['--step-tcl',hook+'=physical/s81_die_views/hbglue/flat_min_delay_keep.tcl']
    return subprocess.call(cmd,cwd=ROOT)
if __name__=='__main__':raise SystemExit(main())
