import collections,hashlib,json
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-final-guides-1131')
i=Path('/srv/opentallas-scratch2/claude/codex-qc-nl-clock50-1504')
def guides(path):
 out=collections.defaultdict(collections.Counter); name=None
 for line in path.read_text().splitlines():
  line=line.strip()
  if not line or line=='(': continue
  if line==')': name=None;continue
  if name is None: name=line
  else:
   x0,y0,x1,y1,layer=line.split();out[name][(layer,int(x0),int(y0),int(x1),int(y1))]+=1
 return dict(out)
db=collections.defaultdict(collections.Counter)
for line in (r/'db_guides.tsv').read_text().splitlines():
 n,layer,*box=line.split('\t');db[n][(layer,*map(int,box))]+=1
new=guides(r/'final.route.guide');old=guides(i/'native_route.guide')
missing_old=sorted(set(db)-set(old));missing_new=sorted(set(db)-set(new));extra_new=sorted(set(new)-set(db))
boxes_differ=[n for n in db if n in new and db[n]!=new[n]]
census={}
for line in (i/'class_census.tsv').read_text().splitlines()[1:]:
 ty,n,deg,special,sw,wire,ng=line.split('\t')
 if n in db: census[ty]=census.get(ty,0)+1
pg={}
for line in (i/'class_census.tsv').read_text().splitlines()[1:]:
 ty,n,deg,special,sw,wire,ng=line.split('\t')
 if ty in ('POWER','GROUND'): pg[n]=(ty,special,sw)
pg_after={}
for line in (r/'pg.tsv').read_text().splitlines():
 ty,n,special,sw=line.split('\t');pg_after[n]=(ty,special,sw)
report=dict(db_nets=len(db),class_counts=census,old_missing_count=len(missing_old),old_missing_first=missing_old[:10],new_missing=missing_new,new_extra=extra_new,new_boxes_differ=boxes_differ,guide_rectangles=sum(sum(c.values()) for c in db.values()),pg_unchanged=pg==pg_after,pg=pg_after,input_sha256=hashlib.sha256((i/'input.odb').read_bytes()).hexdigest(),drt_consumer='Pinned detail_route.tcl load_design reads 5_1_grt.odb; no route.guide read. Export/coverage defect, no demonstrated DRT defect.')
(r/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
assert census=={'SIGNAL':67826,'CLOCK':1184},census
assert len(missing_old)==937,len(missing_old)
assert not missing_new and not extra_new and not boxes_differ,report
assert pg==pg_after
print(json.dumps(report,indent=2))
