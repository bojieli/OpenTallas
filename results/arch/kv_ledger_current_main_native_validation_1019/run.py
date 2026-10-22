import os,sys,json,hashlib,subprocess,unittest
from pathlib import Path
root=Path.cwd(); pattern=sys.argv[1]; out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
sys.path[:0]=[str(root/'tools/qwen_kv_die'),str(root/'tools')]
class Result(unittest.TextTestResult):
 def __init__(self,*a,**k): super().__init__(*a,**k); self.passed=[]
 def addSuccess(self,test): super().addSuccess(test); self.passed.append(test.id())
suite=unittest.TestLoader().discover(str(root/'tools/qwen_kv_die'),pattern=pattern)
r=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
mods={str(Path(m.__file__).resolve()):sha(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file() and str(root) in str(Path(m.__file__).resolve())}
yosys=Path(subprocess.check_output(['which','yosys'],text=True).strip()).resolve()
report=dict(pattern=pattern,tests=r.testsRun,passed=r.passed,failures=[(t.id(),x) for t,x in r.failures],errors=[(t.id(),x) for t,x in r.errors],skipped=[(t.id(),x) for t,x in r.skipped],successful=r.wasSuccessful(),loaded_modules=mods,yosys=dict(path=str(yosys),sha256=sha(yosys),version=subprocess.check_output([str(yosys),'-V'],text=True)),actual_root=os.environ['KV_PARAMETER_ACTUAL_ROOT'])
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
sys.exit(0 if r.wasSuccessful() else 1)
