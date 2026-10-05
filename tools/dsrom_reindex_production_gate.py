#!/usr/bin/env python3
"""Exact original20case fullshape gather gate on the protected production parent."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_reindex_candidates as gate
P='rtl/dsrom_sys/reindex_parent/'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--gold',type=Path,required=True);a=p.parse_args()
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise SystemExit('pinned clean source required')
 gate.KG_SRC=['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv']+[P+n for n in ['ot_dsrom_reindex_gather_parent.sv','ot_dsrom_reindex_kgctl_parent.sv','ot_dsrom_reindex_kgdata_parent.sv','ot_dsrom_reindex_list_macro.sv','ot_dsrom_reindex_request_cut.sv','tb_dsrom_reindex_gather_parent.sv']]+['physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v','rtl/test/hdc_v41x_idx_kgather.cpp']
 def build(obj,params):
  obj.mkdir(parents=True,exist_ok=True)
  cmd=[gate.verilator(),'--cc','--exe','--build','-j','4','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT','--top-module','tb_hdc_v41x_idx_kgather',*[f'-G{k}={v}' for k,v in params.items()],'--Mdir',str(obj),*[str(ROOT/f) for f in gate.KG_SRC]]
  with (obj/'build.log').open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  return obj/'Vtb_hdc_v41x_idx_kgather'
 gate.kg_build=build
 original_run=gate.kg_run
 def run(binary,out,lists):
  result=original_run(binary,out,lists)
  Path(str(out)+'.case.json').write_text(json.dumps(result,indent=2)+'\n')
  return result
 gate.kg_run=run
 try:gate.cmd_gather(a)
 except Exception as error:
  (a.out/'FAIL.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),error=repr(error)),indent=2)+'\n')
  raise
 record=json.loads((a.out/'gather.json').read_text());record['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 record['source_sha256']['tools/dsrom_reindex_production_gate.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 record['scope']='protected actual16macro LSW3 list; KC8-derived full128slot32PC production control, sealed request cuts, real drain reservations; golden/original20cases unchanged'
 (a.out/'gather.json').write_text(json.dumps(record,indent=2)+'\n')
 if record['status']!='pass':raise SystemExit(1)
if __name__=='__main__':main()
