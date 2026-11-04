import sys,time,json,resource
from pathlib import Path
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--sidecar',type=Path,required=True);ap.add_argument('--rtl-filelist',type=Path,required=True);ap.add_argument('--rtl-root',type=Path,required=True);args=ap.parse_args()
r=args.work;r.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import gen,gen_rtl
s=args.rtl_root
results={};original=gen_rtl.write_rtl
for mode in ['optimized','retained']:
 if mode=='retained':
  def retained(*a,**kw):
   kw['emit_die_top']=True
   return original(*a,**kw)
  gen_rtl.write_rtl=retained
 out=r/('actual_'+mode)
 start=time.monotonic()
 rc=gen.main(['phys',str(args.plan),'--out',str(out),'--types','slice_station__t41','--rtl-root',str(s),'--kit-rtl','slice_station__t41='+str(args.rtl_filelist),'--hold-ff-margin','10','--max-wire-um','100','--cland-pinslot','all','--clock-landing',str(args.sidecar)])
 assert rc==0,(mode,rc)
 results[mode]={'wall_s':time.monotonic()-start,'maxrss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 (r/'actual_progress.json').write_text(json.dumps(results,indent=1))
a=r/'actual_retained';b=r/'actual_optimized'
def manifest(d):
 return {str(p.relative_to(d/'slice_station__t41')):p.read_bytes().replace(str(d).encode(),b'<OUT>') for p in (d/'slice_station__t41').rglob('*') if p.is_file()}
x,y=manifest(a),manifest(b)
assert x==y,dict(only_retained=sorted(x.keys()-y.keys()),only_optimized=sorted(y.keys()-x.keys()),changed=[k for k in x.keys()&y.keys() if x[k]!=y[k]])
assert (a/'run_kit.sh').read_bytes()==(b/'run_kit.sh').read_bytes()
assert list((a/'_rtl').glob('*_top.sv')) and not list((b/'_rtl').glob('*_top.sv'))
assert 'land_slots.json' in y
results.update(kit_files=len(y),byte_equal=True,land_slots_json=True,run_kit_equal=True)
(r/'actual_comparison.json').write_text(json.dumps(results,indent=1))
print(json.dumps(results))
