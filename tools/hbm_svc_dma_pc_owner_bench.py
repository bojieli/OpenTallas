"""Minimum one-PC ownership gate; overlapping normal/DMA tag namespace."""
import argparse, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=['rtl/ot_hbm_svc_dma_pc_owner.sv','rtl/test/hbm_accel/tb_hbm_svc_dma_pc_owner.sv','tools/hbm_svc_dma_pc_owner_bench.py']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 if a.out.exists():raise SystemExit('fresh immutable record required')
 a.work.mkdir(parents=True,exist_ok=True)
 hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC};cases=[]
 for name,mut in [('baseline',0),('bypass_drain_mutant',1),('prefix_route_mutant',2),('early_release_mutant',3)]:
  exe=a.work/(name+'.vvp')
  c=subprocess.run(['iverilog','-g2012','-s','tb_hbm_svc_dma_pc_owner','-Ptb_hbm_svc_dma_pc_owner.MUT='+str(mut),'-o',str(exe),*[str(ROOT/s) for s in SRC[:2]]],capture_output=True,text=True)
  if c.returncode:cases.append(dict(case=name,verdict='COMPILE_FAIL',output=c.stdout+c.stderr));break
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
  cases.append(dict(case=name,verdict='PASS' if r.returncode==0 else 'FAIL',returncode=r.returncode,output=r.stdout+r.stderr))
 stable=all(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()==v for s,v in hashes.items())
 ok=stable and len(cases)==4 and cases[0]['verdict']=='PASS' and all(c['verdict']=='FAIL' for c in cases[1:])
 d=dict(schema='opentallas.hbm_svc.dma_pc_owner.v1',verdict='PASS' if ok else 'FAIL',sources_unchanged=stable,cases=cases,input_sha256=hashes,scope='One actual RTL PC owner with CPU native request/response scoreboard; normal_quiescent driven as full read/write/relay debt contract. Does not prove integration computes that contract or physical closure.')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
