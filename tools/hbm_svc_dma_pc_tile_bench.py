"""Minimum native-PC CAM exactness and finite-admission gate."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=['rtl/ot_hbm_svc_dma_pc_tile.sv','rtl/test/hbm_accel/tb_hbm_svc_dma_pc_tile.sv','tools/hbm_svc_dma_pc_tile_bench.py']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 if a.out.exists():raise SystemExit('fresh immutable record required')
 a.work.mkdir(parents=True,exist_ok=True);hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in SRC};cases=[]
 for name,mut in [('baseline',0),('unknown_tag',1),('out_of_bounds_beat',2),('duplicate_beat',3),('retired_tag',4)]:
  exe=a.work/(name+'.vvp');c=subprocess.run(['iverilog','-g2012','-s','tb_hbm_svc_dma_pc_tile','-Ptb_hbm_svc_dma_pc_tile.MUT='+str(mut),'-o',str(exe),*[str(ROOT/s)for s in SRC[:2]]],capture_output=True,text=True)
  if c.returncode:cases.append(dict(case=name,verdict='COMPILE_FAIL',output=c.stdout+c.stderr));break
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(case=name,verdict='PASS'if r.returncode==0 else'FAIL',returncode=r.returncode,output=r.stdout+r.stderr))
 stable=all(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()==v for s,v in hashes.items());ok=stable and len(cases)==5 and cases[0]['verdict']=='PASS'and all(x['verdict']=='FAIL'for x in cases[1:])
 d=dict(schema='opentallas.hbm_svc.dma_pc_tile.v1',verdict='PASS'if ok else'FAIL',sources_unchanged=stable,cases=cases,input_sha256=hashes,scope='One actual RTL native-PC16leaseCAM; permuted lease completion, reversed beat ordering, finite request admission, CPU exact slot/index scoreboard. Physical closure and service ownership integration remain separate.')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
