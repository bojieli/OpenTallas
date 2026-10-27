from pathlib import Path
import sys,json,subprocess
b=Path(__file__).resolve().parent;r=b/'src';sys.path[:0]=[str(r/'tools/die_plan')]
import core_family_slice as F
core='dsdv_gunit_l4';fam=next(f for f in json.load(open(b/'families.json'))['families'] if core in f['members']);fam=dict(fam,balance_leaf_counts=True)
rec=F.plan(b/'input/geo.txt',fam,str(b/'lib/invbuf_tt.lib'),str(b/'lib/invbuf_ff.lib'),core+'_r21_balanced')
(b/'plan.json').write_text(json.dumps([rec]));print('BALANCED',rec['balanced_leaf_counts'],flush=True)
cmd=[sys.executable,str(r/'results/core_lat_r9_1026/l0r_r9_d1.py'),str(b/'plan.json'),str(b/'input/geo.txt'),str(b/'lib'),str(r/'results/model_refit3_1026/uf_phys3_v1.json'),str(b/'plan_d1.json'),'--steps','60']
p=subprocess.run(cmd,text=True,capture_output=True);(b/'d1.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
rec=F.refresh_after_d1(rec,json.load(open(b/'plan_d1.json'))[0]);(b/'plan_d1.json').write_text(json.dumps([rec]))
cmd=[sys.executable,str(r/'tools/die_plan/core_plan_to_infra.py'),str(b/'plan_d1.json'),'--sites',str(b/'input/sites.txt'),'--module',core,'--clock-port',(b/'input/clkport.txt').read_text().strip(),'--band','info','--ndr','none','--out',str(b/'slice.json')]
p=subprocess.run(cmd,text=True,capture_output=True);(b/'convert.log').write_text(p.stdout+p.stderr);sl=json.load(open(b/'slice.json')) if p.returncode==0 else None
ck=F.checks(rec,sl,b/'input/geo.txt')
if p.returncode:ck['verdict']='FAIL';ck['fails'].append('converter rc'+str(p.returncode))
(b/'checks.json').write_text(json.dumps(ck,indent=1));F.render(b/'input/geo.txt',rec,sl,b/'plan.png');print(json.dumps(ck),flush=True)
