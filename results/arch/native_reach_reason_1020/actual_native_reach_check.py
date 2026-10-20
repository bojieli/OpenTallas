import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path('cand3/tools/closure_loop').resolve()))
import closed_stands as C
p=json.loads(Path('actual_native_reach_packet.json').read_text());files=p['files']
def show(ref,path):return files.get(ref,{}).get(path)
def blob(ref,path):
 if ref not in files:return None
 if path=='':return 'tree-'+ref
 text=show(ref,path)
 return hashlib.sha1(text.encode()).hexdigest() if text is not None else None
out=C.check(p['spec'],p['spec']['name'],[p['job']],show,blob)
print(json.dumps(out,indent=2))
assert out['verdict']=='PASS',out
