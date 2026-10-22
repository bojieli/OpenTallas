"""Independent geometric graph: net labels group candidates but never create edges."""
from collections import defaultdict

def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def connected(boxes,vias,ports=()):
 bynet=defaultdict(list)
 for b in boxes:
  if b['layer'].startswith('M'):bynet[b['net']].append(b)
 for p in ports:bynet[p['net']].append(p)
 result={}
 for net,bs in bynet.items():
  par=list(range(len(bs)))
  def root(i):
   while par[i]!=i:par[i]=par[par[i]];i=par[i]
   return i
  def join(i,j):par[root(i)]=root(j)
  layers=defaultdict(list)
  for i,b in enumerate(bs):layers[b['layer']].append(i)
  for inds in layers.values():
   for pos,i in enumerate(inds):
    for j in inds[pos+1:]:
     if overlap(bs[i]['rect_nm'],bs[j]['rect_nm']):join(i,j)
  for v in vias:
   if v['net']!=net:continue
   boxesv=v.get('boxes_nm',{'M4':v.get('m4_rect_nm'),'M5':v.get('m5_rect_nm'),'V4':v.get('cut_rect_nm')})
   metal=[(l,r) for l,r in boxesv.items() if l.startswith('M')]
   assert len(metal)==2
   # Only an actual complete via bridges layers; coincident XY alone cannot.
   ia=[i for i in layers[metal[0][0]] if overlap(bs[i]['rect_nm'],metal[0][1])]
   ib=[i for i in layers[metal[1][0]] if overlap(bs[i]['rect_nm'],metal[1][1])]
   assert ia and ib,(net,v)
   for i in ia:
    for j in ib:join(i,j)
  groups=defaultdict(list)
  for i,b in enumerate(bs):groups[root(i)].append(b.get('identity',str(i)))
  result[net]={'components':len(groups),'metal_or_interface_objects':len(bs),'groups':list(groups.values())}
 return result
