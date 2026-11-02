"""Actual native DB+guide class coverage, unchanged original clock guide geometry."""
import csv,json,hashlib
from pathlib import Path
r=Path.cwd();rows=list(csv.DictReader((r/'combined_clock_census.tsv').open(),delimiter='\t'))
def read(p):
 out={};name=None;rects=None
 for line in p.open():
  s=line.strip()
  if not s:continue
  if s=='(':
   assert name is not None and rects is None;rects=[]
  elif s==')':
   assert name is not None and rects is not None and rects
   out[name.lstrip('\\')]=sorted(rects);name=None;rects=None
  elif rects is None:name=s
  else:
   f=s.split();assert len(f)==5 and all(x.lstrip('-').isdigit()for x in f[:4]),s
   rects.append(s)
 assert name is None and rects is None,'unterminated guide block'
 return out
new=read(next((r/'run/results').rglob('route.guide')));old=read(r/'snapshot/route.guide')
counts={'CLOCK':0,'SIGNAL':0};clockchanged=[]
for x in rows:
 c=x['class'];n=x['net']
 if c not in counts or int(x['degree'])<=1:continue
 counts[c]+=1
 assert int(x['special'])==0 and int(x['special_wires'])==0 and int(x['guides'])>0,(c,n,'DBcoverage')
 assert n in new,(c,n,'native guide missing')
 if c=='CLOCK' and old.get(n)!=new[n]:clockchanged.append(n)
assert all(counts.values())
assert not clockchanged,('clock guide geometry changed',clockchanged)
(r/'candidate_guide_coverage.json').write_text(json.dumps({'connected':counts,'native_all_classes_covered':True,'clock_guide_geometry_unchanged':True,'guide_sha256':hashlib.sha256(next((r/'run/results').rglob('route.guide')).read_bytes()).hexdigest(),'scope':'retained-GRT three-DATA-edit candidate only; not full GRT50/DRT/EQ/source qualification'},indent=2)+'\n')
