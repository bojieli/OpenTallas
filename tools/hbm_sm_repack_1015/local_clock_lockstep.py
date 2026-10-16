#!/usr/bin/env python3
"""Clock-only SM body equivalence using the established production-shape vectors.
This is component arithmetic/clock proof. The legacy PQ test driver does not
qualify the fixed-cycle production compiler, attention path or full native die.
"""
import argparse,inspect,json,pathlib,re,sys
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--workdir',required=True);p.add_argument('--mut-clockdrop',action='store_true');p.add_argument('--jobs',type=int,default=8);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(r/'tools'));import dshbm_sm_pq_seq as M
out=pathlib.Path(a.workdir).resolve();out.mkdir(parents=True,exist_ok=True)
base=r/'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv';s=base.read_text()
for name in ['ot_hbm_accel_smh_tile_eg','ot_hbm_accel_smh_tile_wg']:
 m=re.search(r'^module '+name+r'\b.*?^endmodule',s,re.M|re.S)
 if not m:raise RuntimeError(name)
 body=m[0];header=body[:body.index(');')+2]
 body=header+'\n ot_hbm_smh_rp4_gated #(.MUT_CLKDROP('+str(int(a.mut_clockdrop))+')) u(.*);\nendmodule'
 s=s[:m.start()]+body+s[m.end():]
shadow=out/'smh_rp4_shadow.sv';shadow.write_text(s)
M.SMH_SRC=[str(shadow) if x=='rtl/hbm_accel/sm/ot_hbm_accel_smh.sv' else x for x in M.SMH_SRC]
M.SMH_SRC+=['rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_clocks.sv']
# Change optimization only; preserve the existing parser/vector/checker/compiler.
f=inspect.getsource(M.compile_bench).replace('"-O2"','"-O1", "-CFLAGS", "-O1"')
exec(compile(f,'<production compile_bench with O1>', 'exec'),M.__dict__)
spec=json.loads((r/'physical/ref_tile/smh_tile_rp3/spec.json').read_text())
args=['run','--seq','stress','--nc','8','--active','8','--rmax','4096','--req-credit','--smh','--cg','--cg-gap','300','--build-jobs',str(a.jobs),'--workdir',str(out),'--out',a.out]
for d in spec['defines']:args+=['--define',d]
raise SystemExit(M.main(args))
