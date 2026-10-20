import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'paired3/cand/tools/ref_tile/tests'))
import test_ot_rst_copies as T
result={'source':json.loads(Path('and2_source_manifest.json').read_text()),'helper_sha256':hashlib.sha256(Path('paired3/cand/physical/common_flow/ot_rst_copies.py').read_bytes()).hexdigest(),'leaves':{}}
for name in result['source']:
 actual=json.loads(Path(name+'.json').read_text())['modules'][name]
 assert T.RS.comb_module_test({'modules':{name:actual}})(name)
 nl=T.T().leaf_nl(leaf_type=name);nl['modules'][name]=actual
 _,rr=T.RS.analyse(nl,100,T.RS.DEFAULT_RE)
 rec=next(r for r in rr if r['family']=='u_m.hgo_qv')
 assert rec['status']=='OK' and rec['leaf_equiv'] and rec['moves']==300,rec
 result['leaves'][name]={'module_structural_proof':True,'status':rec['status'],'moves':rec['moves'],'groups':rec['groups'],'leaf_equiv':rec['leaf_equiv'],'coarse_json_sha256':hashlib.sha256(Path(name+'.json').read_bytes()).hexdigest()}
Path('and2_coupon.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
