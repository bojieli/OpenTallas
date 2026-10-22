import pathlib,json,hashlib,subprocess,concurrent.futures
A=pathlib.Path(__file__).resolve().parent;B=A.parent
CELLS=json.loads((B/'reuse_a.json').read_text())['reuse']
META={c:json.loads((B/'synmeta_a'/c/'meta.json').read_text()) for c in CELLS}
code=r"""
import pathlib,json,hashlib
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={}
for c,m in META.items():
 O=pathlib.Path(m['remote']); rec={'output':str(O),'source_snapshot':m.get('declared_source_snapshot'),'native_qualified':False,'PG_binding':'OPEN_HOLD_UNAUDITED','macro_area':'UNKNOWN_NOT_ZERO','checks':{}};result[c]=rec
 for n,expected in m.get('consumed_file_sha256',{}).items():
  p=O/n;actual=h(p) if p.exists() else None;rec['checks'][str(p)]={'expected':expected,'actual':actual,'match':actual==expected}
 # Source path follows the frozen run root, never current main.
 S=O.parent.parent/('src_'+m.get('declared_source_snapshot',''))
 for n,expected in m.get('source_file_sha256',{}).items():
  p=S/n;actual=h(p) if p.exists() else None;rec['checks'][str(p)]={'expected':expected,'actual':actual,'match':actual==expected}
 rec['metadata_hashes_match']=all(v['match'] for v in rec['checks'].values()) and bool(rec['checks'])
 rec['status']='FROZEN_HASH_IDENTITY_ONLY' if rec['metadata_hashes_match'] else 'INCOMPLETE_HASH_OR_SOURCE_MISSING'
print(json.dumps(result))
"""
def run(host):
 mm={c:m for c,m in META.items() if m['host']==host}
 try:
  p=subprocess.run(['ssh','-o','ConnectTimeout=8',host,'python3 -'],input='META='+repr(mm)+'\n'+code,text=True,capture_output=True,timeout=110)
  return host,json.loads(p.stdout) if p.returncode==0 else {'collection_error':p.stderr}
 except Exception as e:return host,{'collection_error':str(e)}
result=dict(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(run,sorted(set(m['host'] for m in META.values()))))
(A/'reuse_verified_receipts.json').write_text(json.dumps(result,indent=2)+'\n')
print({h:{c:r.get('status') if isinstance(r,dict) else r for c,r in rows.items()} for h,rows in result.items()})
(A/'reuse_metadata.json').write_text(json.dumps(META,indent=2)+'\n')
