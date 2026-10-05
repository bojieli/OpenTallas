"""Read-only cold parse of captured GRT inputs; never launches OpenROAD."""
import gzip,hashlib,json,pathlib,sys,tempfile
p=pathlib.Path(__file__).resolve().parent
root=p.parents[3];sys.path.insert(0,str(root/'tools'))
import qwen_rom_fulldie as F
m=json.loads((p/'manifest.json').read_text())
for n,v in m.items():
 b=(p/n).read_bytes();assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],n
s=json.loads((p/'summary.json').read_text())
with tempfile.TemporaryDirectory() as d:
 w=pathlib.Path(d)
 for n,v in s['raw_inputs'].items():
  if n=='manifest.json':b=(p/'source_case_manifest.json').read_bytes()
  elif (p/(n+'.gz')).exists():b=gzip.decompress((p/(n+'.gz')).read_bytes())
  else:b=(p/n).read_bytes()
  assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],n
  (w/n).write_bytes(b)
 r=F.record_b(w,F.build(tree_mode='banded'))
 assert r==json.loads((p/'record.json').read_text())
 assert r['exit']==0 and r['grt']['total']['overflow_total']==36383
 assert r['grt']['layers']['M9']['overflow_total']==35131
print('PASS: raw hashes and original case manifest verified, cold record byte-equivalent; congestion FAIL retained')
