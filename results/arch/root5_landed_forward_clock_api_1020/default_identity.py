import sys,pathlib,json,subprocess,hashlib,tempfile
root=pathlib.Path(__file__).resolve().parent
worker='''import sys,json,pathlib
sys.path[:0]=[str(pathlib.Path(sys.argv[1])/"tools/ref_tile"),str(pathlib.Path(sys.argv[1])/"tools/ref_tile/tests")]
import clock_entry_constraints as CE
import test_landed_cluster_kit as K
r=pathlib.Path(sys.argv[2]);r.mkdir(exist_ok=True)
if not (r/"hard").exists(): K.view(r)
s=K.spec(r)
if sys.argv[3]=="empty": s["forwarded_clock_ports"]=[]
print(json.dumps(dict(entries=CE.generate(s,r),clocks=CE.clocks(s,833.333),landed_sdc=CE.landed_sdc(s,r),landed_body=CE.LANDED_BODY)))
'''
results=[]
with tempfile.TemporaryDirectory() as temp:
 for mode in ['absent','empty']:
  a=json.loads(subprocess.check_output([sys.executable,'-c',worker,str(root/'baseline'),temp,mode]))
  b=json.loads(subprocess.check_output([sys.executable,'-c',worker,str(root/'candidate'),temp,mode]))
  for k in a:
   results.append(dict(mode=mode,artifact=k,identical=a[k]==b[k],sha256=hashlib.sha256(a[k].encode()).hexdigest()))
(root/'DEFAULT_IDENTITY.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
assert all(r['identical'] for r in results)
