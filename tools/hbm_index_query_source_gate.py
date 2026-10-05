#!/usr/bin/env python3
"""New native VM-read/query join; retained native outputs never oracle operands."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=['rtl/hbm_accel/index/ot_hbm_accel_index_query_source.sv','rtl/hbm_accel/index/ot_hbm_accel_index_query.sv','rtl/hdc/v41/ot_hdc_actquant.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/test/hbm_accel/tb_hbm_index_query_source.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--expected',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 record={'scope':'Actual retained native SU landing bytes -> matched VM response -> NEW query packing/hold. Native source was N64/BCAST4/RET5/M4/A3; no current BCAST7/RET8/performance or complete-index claim. Comparator never provides operands.','source_pins':{n:sha(ROOT/n) for n in RTL},'input_pins':{k:{'path':str(getattr(a,k).resolve()),'sha256':sha(getattr(a,k))} for k in ['original','native','expected']},'complete_index_qualified':False,'SS_FF_closed':False}
 (a.out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
 obj=a.out.resolve()/'obj';vl=os.environ.get('VERILATOR','verilator')
 with (a.out/'build.log').open('w') as f:rc=subprocess.call([vl,'--binary','--timing','-j','8','-O2','-Wno-fatal','--top-module','tb_hbm_index_query_source','-Mdir',str(obj),*[str(ROOT/n) for n in RTL]],stdout=f,stderr=subprocess.STDOUT)
 (a.out/'build.exit').write_text(str(rc)+'\n')
 if rc:return rc
 with (a.out/'runtime.log').open('w') as f:rc=subprocess.call([str(obj/'Vtb_hbm_index_query_source'),f'+ORIGINAL={a.original.resolve()}',f'+NATIVE={a.native.resolve()}',f'+EXPECTED={a.expected.resolve()}'],stdout=f,stderr=subprocess.STDOUT)
 (a.out/'runtime.exit').write_text(str(rc)+'\n')
 return rc
if __name__=='__main__':raise SystemExit(main())
