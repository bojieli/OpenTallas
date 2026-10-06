#!/usr/bin/env python3
"""Exact original20case fullshape gather gate on the protected production parent."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_reindex_candidates as gate
P='rtl/dsrom_sys/reindex_parent/'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--gold',type=Path,required=True);p.add_argument('--split-counters',action='store_true');p.add_argument('--io-margin',action='store_true',help='register-to-register boundary twin (default off)');a=p.parse_args()
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise SystemExit('pinned clean source required')
 gate.KG_SRC=['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv']+[P+n for n in ['ot_dsrom_reindex_gather_parent.sv','ot_dsrom_reindex_parent_control.sv','ot_dsrom_reindex_kgctl_parent.sv','ot_dsrom_reindex_kgdata_parent.sv','ot_dsrom_reindex_drain_queue.sv','ot_dsrom_reindex_list_macro.sv','ot_dsrom_reindex_request_cut.sv','ot_dsrom_reindex_io_margin.sv','tb_dsrom_reindex_gather_parent.sv']]+['physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v','rtl/test/hdc_v41x_idx_kgather.cpp']
 a.out.mkdir(parents=True,exist_ok=False)
 pins=gate.KG_SRC+['tools/dsrom_reindex_production_gate.py','tools/dsrom_reindex_candidates.py','tools/dsrom_reindex_parent_model.py','tools/uarch_model.py','tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py']
 (a.out/'source.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins}),indent=2)+'\n')
 def build(obj,params,defines=()):
  params=dict(params, SPLIT_COUNTERS=int(a.split_counters), IO_MARGIN=int(a.io_margin))
  obj.mkdir(parents=True,exist_ok=True)
  cmd=[gate.verilator(),'--cc','--exe','--build','-j','4','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT','--top-module','tb_hdc_v41x_idx_kgather',*[f'+define+{d}' for d in defines],*[f'-G{k}={v}' for k,v in params.items()],'--Mdir',str(obj),*[str(ROOT/f) for f in gate.KG_SRC]]
  with (obj/'build.log').open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  return obj/'Vtb_hdc_v41x_idx_kgather'
 gate.kg_build=build
 original_run=gate.kg_run
 def run(binary,out,lists):
  result=original_run(binary,out,lists)
  Path(str(out)+'.case.json').write_text(json.dumps(result,indent=2)+'\n')
  if not result.get('pass_'):raise RuntimeError('exact gate failed: '+str(out))
  return result
 gate.kg_run=run
 try:gate.cmd_gather(a)
 except Exception as error:
  (a.out/'FAIL.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),error=repr(error)),indent=2)+'\n')
  raise
 # Exercise the actual four-entry queue under repeated multi-cycle stalls.
 binary=a.out/'obj_kg_p2/Vtb_hdc_v41x_idx_kgather'
 stalled_prefix=a.out/'real_rank0_p2' # same already checked exact golden inputs
 stalled=subprocess.run([str(binary),f'+PFX={stalled_prefix}','+STALL'],capture_output=True,text=True)
 (a.out/'backpressure.log').write_text(stalled.stdout+stalled.stderr)
 stall_pass=stalled.returncode==0 and gate.KGP.search(stalled.stdout) is not None
 if not stall_pass:raise RuntimeError('production finite drain backpressure gate failed')
 negative=None
 if a.io_margin:
  # Negative control: a skid buffer that keeps stale data must fail the same stalled exact oracle.
  mut=build(a.out/'obj_kg_p2_mutant',dict(gate.PLACEMENTS['p2'],CLK_PS=gate.CLK_PS),defines=('OT_REINDEX_MARGIN_SKID_MUTANT',))
  m=subprocess.run([str(mut),f'+PFX={stalled_prefix}','+STALL'],capture_output=True,text=True)
  (a.out/'mutant_backpressure.log').write_text(m.stdout+m.stderr)
  negative=dict(mutant='OT_REINDEX_MARGIN_SKID_MUTANT',expected='FAIL',failed=(m.returncode!=0 or gate.KGP.search(m.stdout) is None))
  if not negative['failed']:raise RuntimeError('margin skid mutant was not detected')
 record=json.loads((a.out/'gather.json').read_text());record['io_margin']=a.io_margin;record['negative_control']=negative;record['backpressure']=dict(pass_=stall_pass,pattern='9 held edges /17; same real_rank0_p2 fullshape exact output oracle');record['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 record['source_sha256']['tools/dsrom_reindex_production_gate.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 record['split_counters']=a.split_counters;record['added_cycles']=None if a.io_margin else 0
 record['scope']='protected actual16macro LSW3 list; KC8-derived full128slot32PC production control, sealed request cuts, real drain reservations; golden/original20cases unchanged'
 (a.out/'gather.json').write_text(json.dumps(record,indent=2)+'\n')
 if record['status']!='pass':raise SystemExit(1)
if __name__=='__main__':main()
