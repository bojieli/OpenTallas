"""Prebuild native clock homes on actual rows; keep topology fixed and price later."""
from pathlib import Path
import sys,json,math,collections
sys.path.insert(0,str(Path('tools/die_plan').resolve()))
import die_trial as D
import schema as S
from clock_reach import actual_reach,freeze_sites
DB=1000;W,H=1.62,.27;CLEAR=.12
class RectIndex:
 def __init__(self,rects,B=32.):
  self.r=rects;self.B=B;self.idx=collections.defaultdict(list)
  for k,r in enumerate(rects):
   for i in range(math.floor(r[0]/B),math.floor(r[2]/B)+1):
    for j in range(math.floor(r[1]/B),math.floor(r[3]/B)+1):self.idx[i,j].append(k)
 def near(self,r):
  ids=set()
  for i in range(math.floor(r[0]/self.B),math.floor(r[2]/self.B)+1):
   for j in range(math.floor(r[1]/self.B),math.floor(r[3]/self.B)+1):ids.update(self.idx.get((i,j),()))
  return [self.r[k] for k in ids if self.r[k][0]<r[2] and self.r[k][2]>r[0] and self.r[k][1]<r[3] and self.r[k][3]>r[1]]
 def clear(self,r):return not self.near(r)
class NativeSite:
 def __init__(self,base,rows,pg,limit,strict):
  self.base=base;self.rows=rows;self.pg=pg;self.limit=limit;self.strict=strict;self.W=base.W;self.H=base.H;self.cache={}
 def legal(self,q):
  x,y=q;ix,iy=round(x*DB),round(y*DB);row=self.rows.get(iy)
  if row is None or abs(ix-x*DB)>1e-5 or abs(iy-y*DB)>1e-5:return False
  if (ix-row['origin'][0])%row['spacing'] or ix<row['bbox'][0] or ix+1620>row['bbox'][2]:return False
  if not self.base.legal(q):return False
  rect=(x-CLEAR,y-CLEAR,x+W+CLEAR,y+H+CLEAR)
  return self.pg['M8'].clear(rect) and (not self.strict or self.pg['M9'].clear(rect))
 def nearest(self,q,axis=None):
  key=tuple(q)
  if key in self.cache:return self.cache[key]
  x,y=q;R=self.limit
  xs={round(round(x/.054)*.054,6)};ys={round(round(y/.54)*.54,6)}
  box=(x-R-W,y-R-H,x+R+W,y+R+H)
  for layer in ['M8']+(['M9'] if self.strict else []):
   for a,b,c,d in self.pg[layer].near(box):
    xs.update([round(math.floor((a-W-CLEAR)/.054)*.054,6),round(math.ceil((c+CLEAR)/.054)*.054,6)])
    ys.update([round(math.floor((b-H-CLEAR)/.54)*.54,6),round(math.ceil((d+CLEAR)/.54)*.54,6)])
  for r in self.base.hits(q):
   xs.update([round(math.floor(r[0]/.054)*.054,6),round(math.ceil(r[2]/.054)*.054,6)])
   ys.update([round(math.floor(r[1]/.54)*.54,6),round(math.ceil(r[3]/.54)*.54,6)])
  try:
   a,b=self.base.nearest(q,axis);xs.add(round(round(a/.054)*.054,6));ys.add(round(round(b/.54)*.54,6))
  except (ValueError,RuntimeError):pass
  cand=sorted(((a,b) for a in xs for b in ys if abs(a-x)+abs(b-y)<=R+1e-6),key=lambda p:(abs(p[0]-x)+abs(p[1]-y),p))
  for p in cand:
   if self.legal(p):self.cache[key]=p;return p
  raise ValueError(f'no native PG-aware clock home within {R} um of {q}; strict_M9={self.strict}')
def main():
 out=Path('body_pack02');out.mkdir(exist_ok=True)
 c=json.load(open('/srv/opentallas-scratch2/claude/codex-provider-import-1029/constraints_kv6/constraints.json'))
 assert c['dbu']==DB and not c['actual_lower_PG']
 assert all((r[4]-r[2],r[5]-r[3])==(1620,270) for r in c['existing_cells'])
 rows={r['origin'][1]:r for r in c['rows'] if r['orient']=='R0'}
 assert all(r['origin'][0]==0 and r['spacing']==54 and y%540==0 for y,r in rows.items())
 p=Path('/srv/opentallas-scratch2/claude/codex-kv-25-1029/inputs/event/plan_sites_astk.json');P=S.Plan(S.load(p),p)
 D.DME_ACTUAL_MAX_UM=405.;base=D.clock_site(P)
 tf=Path('/srv/opentallas-scratch2/claude/die-kv-21-1028/kit_c/clock/tree.json');t=json.loads(tf.read_text())
 assert set(t['sites'])=={r[0] for r in c['existing_cells']}
 assert all(abs(t['sites'][r[0]][0]*DB-r[2])<1e-5 and abs(t['sites'][r[0]][1]*DB-r[3])<1e-5 for r in c['existing_cells'])
 pg=json.load(open('pg_model_rects.json'));indexes={l:RectIndex([tuple(r[2:]) for r in pg if r[1]==l]) for l in ['M8','M9']}
 original=[(n,*q) for n,q in t['sites'].items()];attempts=[];packed=None
 for strict,limit in [(True,8.64),(True,17.28)]:
  site=NativeSite(base,rows,indexes,limit,strict)
  try:packed=D.physical_pack(site,original,max_displacement=limit)
  except ValueError as e:
   a={'strict_M9_body_gap':strict,'max_move_um':limit,'verdict':'FAIL','cause':str(e)};attempts.append(a);(out/f'attempt_{len(attempts)}.json').write_text(json.dumps(a,indent=1));print(a,flush=True)
  else:
   attempts.append({'strict_M9_body_gap':strict,'max_move_um':limit,'verdict':'PASS'});break
 if packed is None:raise RuntimeError('native clock body geometry remains blocked; see attempts')
 old=t['sites'];new={n:[x,y] for n,x,y in packed};t['sites']=new
 for i,n in t['nodes'].items():n['x'],n['y']=new[t['node_buf'][i]]
 t['meta']['physical_dme']=freeze_sites(t,405.)
 t['meta']['physical_dme'].update(scope='native PREBUILD body/row plus planned upper PG access; actual RC unmeasured',actual_pg_checked=False)
 reach=actual_reach(t,405.);assert reach['verdict']=='PASS',reach
 moves=[{'cell':n,'old':old[n],'new':q,'manhattan_um':sum(abs(a-b) for a,b in zip(old[n],q))} for n,q in new.items() if old[n]!=q]
 t['meta']['body_pack']={'attempts':attempts,'max_move_um':max(x['manhattan_um'] for x in moves),'moved':len(moves),'cells':len(new)}
 (out/'tree_native.json').write_text(json.dumps(t))
 (out/'moves.json').write_text(json.dumps(moves,indent=1))
 (out/'report.json').write_text(json.dumps({'attempts':attempts,'cells':len(new),'moved':len(moves),'max_move_um':max(x['manhattan_um'] for x in moves),'actual_reach':reach,'body_overlap':0,'native_row_site':True,'model_M8_PG_clear':True,'model_M9_body_gap':strict,'actual_PG_checked':False,'topology_cycles_delta':0},indent=1))
 print('NATIVE_CLOCK_BODY_PACK_DONE',len(moves),flush=True)
if __name__=='__main__':main()
