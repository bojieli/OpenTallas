import gzip,json,collections,hashlib
from pathlib import Path
base=Path(__file__).resolve().parent
m=base/'inputs/matrix_map.jsonl.gz'
rows=[]
with gzip.open(m,'rt') as f:
 for line in f:
  x=json.loads(line)
  rows.append({k:x.get(k) for k in ('layer','alias','original_alias','stage','row_offset','rows','K','rank_slices','format','segments')})
out=base/'field_fragments.json'
out.write_text(json.dumps(rows,separators=(',',':'))+'\n')
print('canonical_fragments',len(rows),'summary_bytes',out.stat().st_size,'canonical_sha256',hashlib.sha256(m.read_bytes()).hexdigest())
