#!/usr/bin/env python3
"""Explicit source closure for actual NS16/NK4 native HBM index parent.

Elaboration checks implementation connectivity only. It proves neither numeric
full context, installed SRAM/provider/clock, nor full-token qualification.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=[
 'rtl/hbm_accel/index/ot_hbm_accel_index_path.sv',
 'rtl/hbm_accel/index/ot_hbm_accel_index_query_source.sv',
 'rtl/hbm_accel/index/ot_hbm_accel_index_query.sv',
 'rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_sel.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv',
 'rtl/hdc/v41/ot_hdc_actquant.sv',
 'rtl/hdc/ot_hdc_delay.sv',
 'rtl/hdc/ot_hdc_fastfp.sv',
 'rtl/hdc/ot_hdc_fp32_add_lat.sv',
 'rtl/hdc/ot_hdc_prefix.sv',
 'rtl/hdc/ot_hdc_fpu.sv',
 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
 'rtl/proto/ot_fp32_add_rne_pipe.sv',
]
def main():
 p=argparse.ArgumentParser();p.add_argument('--elaborate',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
 pins={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in RTL}
 if not a.elaborate:print(json.dumps({'sources':RTL,'source_pins':pins},indent=2));return 0
 if a.out is None:p.error('--out required for unique elaboration logs')
 a.out.mkdir(parents=True,exist_ok=False)
 argv=[os.environ.get('VERILATOR','verilator'),'--lint-only','--timing','-Wno-fatal','--top-module','ot_hbm_accel_index_path','-GENABLE=1','-GSOURCE_VM_ENABLE=1',*[str(ROOT/n) for n in RTL]]
 (a.out/'source.json').write_text(json.dumps({'source_pins':pins,'argv':argv,'NS':16,'NK':4,'Q':4,'W':16,'FPL':7,'FML':5,'QL':5,'full_context_numerical_qualified':False,'SS_FF_closed':False},indent=2)+'\n')
 with (a.out/'elaborate.log').open('w') as f:rc=subprocess.call(argv,stdout=f,stderr=subprocess.STDOUT)
 (a.out/'exit').write_text(str(rc)+'\n');return rc
if __name__=='__main__':raise SystemExit(main())
