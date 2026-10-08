#!/usr/bin/env python3
"""Full-shape protected flight gate and private wrong-output negative control."""
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
FILES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','rtl/hbm_accel/collective_flight_20261007/ot_hbm_collective_protected_flight.sv','rtl/hbm_accel/collective_flight_20261007/tb_protected_flight.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
 hashes={f:sha(ROOT/f) for f in FILES};runs={}
 for name in ['positive','negative']:
  d=out/name;d.mkdir();sources=[ROOT/f for f in FILES]
  if name=='negative':
   src=sources[2].read_text();old='assign out_d=corrected_output[W-1:0];';new="assign out_d=corrected_output[W-1:0] ^ {{(W-1){1'b0}},1'b1};"
   assert src.count(old)==1;mut=d/'mutant.sv';mut.write_text(src.replace(old,new));sources[2]=mut
   (d/'mutation.json').write_text(json.dumps({'original_sha256':hashes[FILES[2]],'mutant_sha256':sha(mut),'old':old,'new':new},indent=2)+'\n')
  cmd=['iverilog','-g2012','-s','tb_protected_flight','-o',str(d/'test.vvp'),*[str(x) for x in sources]]
  b=subprocess.run(cmd,capture_output=True,text=True);(d/'build.log').write_text(b.stdout+b.stderr)
  if b.returncode:runs[name]={'build_returncode':b.returncode,'pass':False};continue
  r=subprocess.run(['vvp',str(d/'test.vvp')],capture_output=True,text=True);log=r.stdout+r.stderr;(d/'simulation.log').write_text(log)
  passed=(r.returncode==0 and 'PASS flight' in log) if name=='positive' else (r.returncode!=0 and 'DATA mismatch' in log)
  runs[name]={'returncode':r.returncode,'pass':passed,'command':cmd}
 verdict={'pass':all(x['pass'] for x in runs.values()),'runs':runs,'source_sha256':hashes,'physical_qualified':False}
 (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n');print(json.dumps(verdict));return 0 if verdict['pass'] else 1
if __name__=='__main__':sys.exit(main())
