import gzip,json,pathlib
p=pathlib.Path(__file__).parent/'input';P=json.load(gzip.open(p/'hm_r26.json.gz','rt'));mod='ot_qwen_tp8_pv_join_t'
def box(h,w=None,he=None,tall=False):
 ow,oh=h['outline_um'];w=w or ow;he=he or oh;dx,dy=h.get('track_offset_um',[0,0]);x,y=h['origin_um'];x+=(ow-w)/2;y=531.36 if tall else y+(oh-he)/2
 return [x+dx,y+dy,x+dx+w,y+dy+he]
def inside(q,b):return b[0]<q[0]<b[2] and b[1]<q[1]<b[3]
for width,height,tall in [(259.2,172.8,False),(190.08,267.84,True)]:
 added=[];old=[];closest=[];unsited=0;affected=[]
 for tn,t in P['partition_types'].items():
  hs=[h for h in t.get('hard_cores',[]) if h['module']==mod]
  if not hs:continue
  points=[]
  for k in ('ft_slots','internal_stations'):
   for j,r in enumerate(t.get(k,[])):
    if k=='ft_slots' and not r.get('regs_um') and not r.get('bit_sites_um'):unsited+=1
    for qi,q in enumerate(r.get('regs_um',[])):
     if isinstance(q,list) and len(q)==2:points.append((k,j,qi,q))
  for h in hs:
   a=box(h);b=box(h,width,height,tall)
   for k,j,qi,q in points:
    if inside(q,a):old.append((tn,h['inst'],k,j,qi,q))
    elif inside(q,b):added.append((tn,h['inst'],k,j,qi,q))
   for o in t['hard_cores']:
    if o is h:continue
    c=box(o)
    if b[0]<c[2] and c[0]<b[2]:closest.append(max(c[1]-b[3],b[1]-c[3]))
   affected.append((tn,h['inst'],b))
 print(width,height,'new_station_overlaps',len(added),'base_overlaps',len(old),'min_vertical_gap',min(closest),'unsited_ft_slots',unsited)
 print('examples',added[:12])
