from pathlib import Path
import json,math
out=Path(__file__).parent
BIG={'ot_v41_rom_elem_q_qxpq_w10','ot_v41_bf_col','dsfd_bf_front_roots'}
def snap(x,l):return round(math.ceil((x-1e-7)/l)*l,3)
def clear(a,b):return a['x']+a['w']+20 <= b['x']+1e-7 or b['x']+b['w']+20 <= a['x']+1e-7 or a['y']+a['h']+20 <= b['y']+1e-7 or b['y']+b['h']+20 <= a['y']+1e-7
for h in (9,10):
 base=json.loads((out/f'h{h}.json').read_text());src=json.loads(Path(base['source']).read_text());bs=src['blocks'];ys=sorted(set(r['y'] for r in bs if r['master'] in BIG));mp={y:216+302.4*i for i,y in enumerate(ys)};H=snap(mp[ys[-1]]+198.72+22.16,43.2);W=base['width'];placed=[];rest=[]
 def target(y):
  if y<=ys[0]:return y
  for a,b in zip(ys,ys[1:]):
   if a<=y<=b:return mp[a]+(y-a)*(mp[b]-mp[a])/(b-a)
  return mp[ys[-1]]+y-ys[-1]
 for r in bs:
  r=dict(r);r['old_x']=r['x'];r['old_y']=r['y']
  if r['master'] in BIG:r['y']=mp[r['y']];placed.append(r)
  elif r['y']<172.8:placed.append(r)
  else:rest.append(r)
 failed=[]
 for r in sorted(rest,key=lambda r:-(r['w']+20)*(r['h']+20)):
  raw=r['master']=='ot_rom_4096x72_m8';lx=.432 if raw else 43.2;ly=2.16 if raw else 43.2
  tx=r['old_x'];ty=target(r['old_y']);xs={snap(22.16,lx),snap(tx,lx)};yv={snap(22.16,ly),snap(ty,ly)}
  for q in placed:xs.add(snap(q['x']+q['w']+20,lx));yv.add(snap(q['y']+q['h']+20,ly))
  choices=sorted(((abs(x-tx)+abs(y-ty),x,y) for x in xs if x+r['w']<=W-22.16+1e-7 for y in yv if y+r['h']<=H-22.16+1e-7))
  for cost,x,y in choices:
   a=dict(r,x=x,y=y)
   if all(clear(a,q) for q in placed):placed.append(a);break
  else:failed.append(r['inst'])
 rec=dict(status='MODEL_ONLY_UNROUTED' if not failed else 'MODEL_REFUSED_PACKING',width=W,height=H,pitch=302.4,blocks=placed,failed=failed,required=len(bs),placed=len(placed),hard_ABI_unchanged=True,limitations='Pure rectangle placement, not routing/reach/clock/reset/soft utilization qualification. Hard+ROM20um channels and43.2/2.16 lattice construction; old large-row order retained, small blocks reordered.')
 (out/f'repack_h{h}.json').write_text(json.dumps(rec,indent=2)+'\n');print(h,'H',H,'placed',len(placed),'failed',failed)
