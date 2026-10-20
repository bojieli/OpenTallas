"""Read-only historical-library provenance check, not native electrical admission."""
import glob,hashlib,json,re
from pathlib import Path
p=json.load(open('/work/historical_used_masters.json'));rows=[]
for old in p['fake_lib_sources']:
 fs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/'+Path(old['path']).name)
 if len(fs)!=1:raise ValueError('expected exact library file '+old['path'])
 f=Path(fs[0]);raw=f.read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha==old['sha256'],f
 cells=sorted(set(re.findall(r'\bcell\s*\(\s*"?([^"\s)]+)',raw.decode())))
 rows.append(dict(path=str(f),sha256=sha,cell_names=cells,actual_used_intersection=sorted(set(cells)&set(p['actual_used_master_names']))))
d=dict(status='READ_ONLY_PROVENANCE_CHECK',historical_odb_sha256=p['historical_odb_sha256'],fake_libraries=rows,actual_masters=len(p['actual_used_master_names']),native_admission=False,note='Only exact library-byte hashes and used-master intersections checked; no standard PDK alias or fake clock authority granted.')
Path('/work/library_mapping_result.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
