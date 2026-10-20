import json,hashlib,sys
from pathlib import Path
inventory=json.loads(Path(sys.argv[1]).read_text());src=Path(sys.argv[2]);actual={};rows=[]
for row in inventory['views']:
 if 'meta' not in row:continue
 bad=[]
 for rel,want in row['meta']['source_file_sha256'].items():
  if rel not in actual:
   p=src/rel;actual[rel]=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
  if actual[rel]!=want:bad.append({'path':rel,'expected':want,'actual':actual[rel]})
 rows.append({'cell':row['cell'],'mismatches':bad,'files':len(row['meta']['source_file_sha256'])})
out={'source_root':str(src),'unique_files':len(actual),'cells':len(rows),'mismatch_cells':sum(bool(r['mismatches']) for r in rows),'rows':rows,'actual_sha256':actual}
Path(sys.argv[3]).write_text(json.dumps(out,indent=2)+'\n');print('S6_CURRENT_SOURCE',out['cells'],out['unique_files'],'mismatch_cells',out['mismatch_cells'])
