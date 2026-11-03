from pathlib import Path
import re,json,hashlib
p=Path('/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/repair')
def cells(f):
 d={}; active=False; rec=''
 for line in open(f):
  if line.startswith('COMPONENTS '):active=True;continue
  if line.startswith('END COMPONENTS'):break
  if not active:continue
  rec+=line
  if ';' in line:
   m=re.search(r'^\s*-\s+(\S+)\s+(\S+)',rec); q=re.search(r'\+\s+(FIXED|PLACED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)',rec)
   if m:d[m[1]]={'master':m[2],'pose':list(q.groups()) if q else None}
   rec=''
 return d
old=p/'ORIGINAL_COMPONENTS.json'; a=json.load(open(old));b=cells(p/'repair_checkpoint.def')
new={n:b[n] for n in b.keys()-a.keys()}; removed={n:a[n] for n in a.keys()-b.keys()}; changed={n:{'before':a[n],'after':b[n]} for n in a.keys()&b.keys() if a[n]!=b[n]}
files={}
for n in ['repair_checkpoint.odb','repair_checkpoint.raw.odb','repair_checkpoint.def','repair_checkpoint.v','repair_checkpoint.active_mode.sdc','repair_phase.log']:
 f=p/n;files[n]={'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
removed_filler={n:v for n,v in removed.items() if v['master'].startswith(('FILLER','DECAP'))}; removed={n:v for n,v in removed.items() if n not in removed_filler}
j={'removed_filler_count':len(removed_filler),'status':'PROTECTED_REPAIR_CHECKPOINT_ONLY','source':str(old),'before_cells':len(a),'after_cells':len(b),'new':new,'removed':removed,'changed':changed,'files':files}
(p/'CHECKPOINT_CENSUS.json').write_text(json.dumps(j,indent=2)+'\n');print(len(a),len(b),len(new),len(removed),len(changed)); print('unplaced',sum(not v['pose'] for v in b.values()))
