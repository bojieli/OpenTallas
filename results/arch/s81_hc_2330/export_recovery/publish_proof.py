"""Validate source-pinned replay artifacts before attaching additive historical proof."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
from export_provenance import check_invariants,sha,write_json
import child_lint

def main(artifacts):
 summary=[]
 for r in json.loads((Path(__file__).parent/'inputs.json').read_text()):
  d=Path(artifacts)/r['job'];result=json.loads((d/'replay.json').read_text());assert result['passed']
  v=ROOT/r['view'];raw=d/'raw.lef';final=v/(r['cell']+'.lef')
  assert sha(raw)==r['raw_lef_expected'] and sha(d/'final.lef')==sha(final)==r['published_hashes'][final.name]
  assert sha(d/'helper.py')==r['helper_sha256']
  assert all(sha(v/f)==h for f,h in r['published_hashes'].items())
  inv=check_invariants(raw.read_text(),final.read_text(),child_lint.parse_lef)
  current=child_lint.lint(str(final),str(v));assert current['verdict']=='PASS',current
  p=v/'provenance';assert not p.exists();(p/'raw').mkdir(parents=True);(p/'helper').mkdir();(p/'reconstruction').mkdir()
  (p/'view_export.abstract.json').write_bytes((v/'abstract.json').read_bytes())
  shutil.copyfile(raw,p/'raw'/final.name);shutil.copyfile(d/'helper.py',p/'helper/abstract_pin_stub.py')
  for filename in ('raw.tcl','raw_export.log','processor.log','replay.json'):
   shutil.copyfile(d/filename,p/'reconstruction'/filename)
  write_json(p/'reconstruction/child_lint_current.json',current)
  receipt=dict(schema=1,kind='abstract_pin_stub',status='PASS',input={'path':'provenance/raw/'+final.name,'sha256':sha(raw)},
   output={'path':final.name,'sha256':sha(final)},helper={'path':'tools/hier_contract/abstract_pin_stub.py','sha256':r['helper_sha256'],
   'source_commit':r['source_commit'],'retained_copy':'provenance/helper/abstract_pin_stub.py'},environment=result['environment'],
   command=result['helper_command'],returncode=result['helper_returncode'],stdout=result['helper_stdout'],stderr=result['helper_stderr'],
   invariants=inv,child_lint=json.loads((v/'child_lint.json').read_text()),replay={'record_commit':r['record_commit'],
   'source_commit':r['source_commit'],'immutable_final_odb':r['immutable_final_odb'],'odb_sha256':result['odb_sha256'],
   'raw_expected_hash_matches':True,'published_final_hash_matches':True,'environment_basis':result['environment_basis'],
   'published_files_verified':result['published_files_verified'],'evidence':'provenance/reconstruction/replay.json'})
  write_json(p/'abstract_pin_stub.json',receipt)
  manifest=json.loads((v/'abstract.json').read_text());manifest['files'][final.name]=sha(final)
  manifest['export_provenance']=dict(schema=1,raw_manifest='provenance/view_export.abstract.json',raw_manifest_sha256=sha(p/'view_export.abstract.json'),
   transformation='provenance/abstract_pin_stub.json',transformation_sha256=sha(p/'abstract_pin_stub.json'))
  write_json(v/'abstract.json',manifest)
  assert all(sha(v/f)==h for f,h in r['published_hashes'].items() if f!='abstract.json')
  assert all(sha(v/f)==h for f,h in manifest['files'].items())
  summary.append({'job':r['job'],'record_commit':r['record_commit'],'source_commit':r['source_commit'],'view':r['view'],'status':'PASS',
   'raw_sha256':sha(raw),'final_sha256':sha(final),'invariants':inv,'current_child_lint':'PASS','preserved_all_original_files_except_manifest':True})
 write_json(Path(__file__).parent/'summary.json',{'status':'PASS','count':len(summary),'scope':'Historical export lineage only; parent adoption requires separate review.','bundles':summary})
if __name__=='__main__':main(sys.argv[1])
