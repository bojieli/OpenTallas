import sys,json,math,time
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).parent/'tools/die_plan'))
import schema as S,gen_phys,check,g2,ft_bit_sites

def scan(P,tn):
 t=P.types[tn];slots=t.get('ft_slots',[])
 if not slots:return dict(slots=0,over_reach_bits=0,st_in_core=0,max_hop_um=0,failures=[])
 by=defaultdict(dict)
 for bus,bit,layer,x,y,f in gen_phys.type_pins(P,tn):by[bus][bit]=(x,y,f)
 boxes=S.placed_macro_boxes(t)
 # Preserve legacy conservative logical-leaf blockages, with authoritative
 # physical contents/core boxes (including track offsets) taking precedence.
 for c in g2.probe_blockages(t):
  if c['inst'] not in boxes:
   x,y=c['origin_um'];w,h=c['outline_um'];boxes[c['inst']]=(x,y,x+w,y+h)
 rect=[(x0+1,y0+1,x1-1,y1-1) for x0,y0,x1,y1 in boxes.values()]
 def inset(p):
  x,y,f=p;return {'E':(x-1,y),'W':(x+1,y),'N':(x,y-1),'S':(x,y+1)}[f]
 out=[];worst=0;allover=0;allinside=0
 for slot in slots:
  sn=slot['name'];k=int(slot.get('stations',1));ft_bit_sites.validate_slot(slot)
  pi,po=by[sn+'_i'],by[sn+'_o'];inside=0;over=0;top=0;worstbit=None;worstseg=None
  for bit in sorted(set(pi)|set(po)):
   ap=pi.get(bit) or po[bit];bp=po.get(bit) or pi[bit];a,b=inset(ap),inset(bp);seg=check.zroute(a,b,ap[2],bp[2]);L=check.plen(seg);chain=[]
   for j in range(k):
    if slot.get('bit_sites_um') and j>0:
     x,y=slot['bit_sites_um'][j-1][bit];w,h=slot['bit_site_cell_um'];xy=(x+w/2,y+h/2)
    elif slot.get('bit_sites_um'):xy=a
    elif slot.get('regs_um'):xy=tuple(slot['regs_um'][j])
    else:xy=check.point_at(seg,L*j/k)
    chain.append(xy)
    if any(x0<xy[0]<x1 and y0<xy[1]<y1 for x0,y0,x1,y1 in rect):inside+=1
   pts=([ap[:2]] if bit in pi else [])+chain+([bp[:2]] if bit in po else [])
   lengths=[abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(pts,pts[1:])];m=max(lengths,default=0)
   if m>top:top=m;worstbit=bit;idx=lengths.index(m);worstseg=pts[idx:idx+2]
   over+=m>405+1e-6
  worst=max(worst,top);allover+=over;allinside+=inside
  if over or inside:out.append(dict(slot=sn,max_hop_um=round(top,4),over_reach_bits=over,st_in_core=inside,stations=k,worst_bit=worstbit,worst_segment=worstseg))
 return dict(slots=len(slots),max_hop_um=round(worst,4),over_reach_bits=allover,st_in_core=allinside,failures=out)

if __name__ == '__main__':
 root=Path(__file__).parent;ref=(root/'source.ref').read_text().strip()
 for name in sys.argv[1:] or ['qc','kv','s81','head','hbm']:
  t0=time.time();P=S.Plan(S.load(root/f'{name}.json'));out={}
  for tn in sorted(P.types):
   if P.types[tn].get('hard'):continue
   out[tn]=scan(P,tn)
  data=dict(source_ref=ref,die=name,types=out,elapsed_s=round(time.time()-t0,1));(root/f'{name}_geometry.json').write_text(json.dumps(data,indent=1)+'\n')
  print(name,'types',len(out),'fail',sum(bool(x['failures']) for x in out.values()),'maxhop',max(x['max_hop_um'] for x in out.values()),'inside',sum(x['st_in_core'] for x in out.values()),'seconds',data['elapsed_s'],flush=True)
