"""Full candidate reference comparison; the original jobs remain untouched."""
import copy,importlib.util,json,pathlib,runpy,sys,time
root=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tools'))
import hub_repack as HR,hbm_r11_delta as R11
spec=importlib.util.spec_from_file_location('hub_repack_reference',root/'hub_repack_reference.py')
ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
fast=HR.pack_hub;oldcache={};rows=[];hits=0

def compare(*args,**kw):
 global hits
 key=json.dumps([args,kw],sort_keys=True)
 t=time.perf_counter();got=fast(*args,**kw);ft=time.perf_counter()-t
 if key in oldcache:
  want=oldcache[key];rt=0;hits+=1
 else:
  t=time.perf_counter();want=ref.pack_hub(*args,**kw);rt=time.perf_counter()-t
  oldcache[key]=copy.deepcopy(want)
 assert got==want, 'FULL SHAPE PACK OUTPUT MISMATCH'
 rows.append(dict(cores=len(args[2]),W=args[0],H=args[1],fast_s=ft,reference_s=rt,exact=True,reference_cache_hits=hits))
 (root/'comparisons.json').write_text(json.dumps(rows,indent=1)+'\n')
 print('PACK_EXACT',json.dumps(rows[-1]),flush=True)
 return got
HR.pack_hub=compare
run=R11.run_hub

def capture(*args,**kw):
 result=run(*args,**kw)
 (root/'candidate.json').write_text(json.dumps(dict(cores=result[0],stations=result[1],report=result[2]),indent=1)+'\n')
 return result
R11.run_hub=capture
height,hub=sys.argv[1:3]
sys.argv=[str(root/'mu_r13_probe.py'),str(root),height,hub]
runpy.run_path(str(root/'mu_r13_probe.py'),run_name='__main__')
print('FULL_CANDIDATE_EXACT_PASS',flush=True)
