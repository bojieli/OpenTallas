#!/usr/bin/env python3
"""New native query packing gate; archived expected words are comparison only."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=['rtl/hbm_accel/index/ot_hbm_accel_index_query.sv','rtl/hdc/v41/ot_hdc_actquant.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/test/hbm_accel/tb_hbm_index_query.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--expected',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);a.input=a.input.resolve();a.expected=a.expected.resolve()
 record={'scope':'NEW parent native FP4 packing/hold/phase gate ONLY. Archived RoPE quant vectors are not evidence of an actual SU producer. No full index or clock claim.','source_pins':{n:sha(ROOT/n) for n in RTL},'input_sha256':sha(a.input),'comparison_sha256':sha(a.expected),'complete_index_qualified':False,'SS_FF_closed':False}
 (a.out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
 vl=os.environ.get('VERILATOR','verilator');obj=a.out.resolve()/'obj'
 with (a.out/'build.log').open('w') as f:
  rc=subprocess.call([vl,'--binary','--timing','-j','8','-O2','-Wno-fatal','--top-module','tb_hbm_index_query','-Mdir',str(obj),*[str(ROOT/n) for n in RTL]],stdout=f,stderr=subprocess.STDOUT)
 (a.out/'build.exit').write_text(str(rc)+'\n')
 if rc:return rc
 with (a.out/'runtime.log').open('w') as f:rc=subprocess.call([str(obj/'Vtb_hbm_index_query'),f'+INPUT={a.input}',f'+EXPECTED={a.expected}'],stdout=f,stderr=subprocess.STDOUT)
 (a.out/'runtime.exit').write_text(str(rc)+'\n')
 return rc
if __name__=='__main__':raise SystemExit(main())
