"""rtlx.py W PLAN SIDECAR OUTDIR [types]: HEAD kit export replay (head_wave_kit_rtl prepare+export RTL steps, no wave):
prepare_plan on ALL types, then per export type gen.py phys --trial + alias_patch + private_patch on the wrapper."""
import json,sys,subprocess,tempfile,shutil
from pathlib import Path
W,PL,SC,OUT=[str(Path(a).resolve()) for a in sys.argv[1:5]];sys.path[:0]=[W+'/tools/die_plan',W+'/tools/s81_head']
from head_count_strap_sites import apply as count_sites
from head_start_raw_private import prepare_plan, patch_rtl as private_patch
from head_start_reset_aliases import patch_rtl as alias_patch
plan=json.load(open(PL));allt=sorted(plan['partition_types'])
res={}
try:
    p2,_=prepare_plan(plan,set(allt));res['_prepare_all']='OK %d types'%len(allt)
except Exception as e:
    res['_prepare_all']='FAIL '+str(e);print(json.dumps(res,indent=1));sys.exit(1)
types=sys.argv[5].split(',') if len(sys.argv)>5 else [t for t in allt if plan['partition_types'][t].get('reset_start_raw_exports')]
p3,_=prepare_plan(plan,set(types))  # count sites already placed in the plan
out=Path(OUT);out.mkdir(parents=True,exist_ok=True);pp=Path(PL).parent/('_rtlx_'+out.name+'.json');pp.write_text(json.dumps(p3,indent=1)+'\n')  # beside core_pins/ (relative side files)
def one(t):
    k=Path(tempfile.mkdtemp(dir=OUT))
    try:
        r=subprocess.run([sys.executable,'-I',W+'/tools/die_plan/gen.py','phys',str(pp),'--clock-landing',SC,'--types',t,'--out',str(k/'b'),'--rtl-root',W,'--trial'],capture_output=True,text=True,cwd=W)
        (out/(t+'.log')).write_text(r.stdout+r.stderr)
        if r.returncode:return 'GEN FAIL rc=%d'%r.returncode
        tt=p3['partition_types'][t];wr=k/'b'/'_rtl'/(tt['module']+'.sv')
        text=alias_patch(wr.read_text(),tt.get('reset_start_raw_exports',[]))
        text,info=private_patch(text,tt)
        return 'OK private=%s'%info.get('private_ports',[])
    except Exception as e:return 'FAIL '+str(e)
    finally:shutil.rmtree(k,ignore_errors=True)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(6) as ex:
    for t,v in zip(types,ex.map(one,types)):res[t]=v
print(json.dumps(res,indent=1));sys.exit(int(any(v.startswith(('FAIL','GEN')) for v in res.values())))
