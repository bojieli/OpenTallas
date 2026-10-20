import re,json,hashlib,collections,math
from pathlib import Path
B=Path(__file__).resolve().parent
phy=B.parent/'mu5k_grt/phy_source.lef'; old=B.parent/'mu5k_grt/controller7_standin.lef'; new=B/'n32s_pins.tcl'
def lef(p):
 s=p.read_text();r={}
 for m in re.finditer(r'\n  PIN (\S+)(.*?)(?=\n  END \S+)',s,re.S):
  name,body=m.groups();q=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body)
  if q:
   x0,y0,x1,y1=map(float,q.groups());r[name]=((x0+x1)/2,(y0+y1)/2)
 return r
pp=lef(phy);oo=lef(old);nn={}
for m in re.finditer(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}',new.read_text()):
 n,l,x,y=m.groups();nn[n]=(float(x),float(y),l)
widths=collections.Counter(re.sub(r'\[.*','',n) for n in pp)
rows=[];missing=[]
for pair in range(16):
 for n,(nx,ny,nl) in nn.items():
  z=re.fullmatch(r'(k_\w+|kr_\w+)\[(\d+)\]',n)
  if not z:continue
  bus,j=z.groups(); j=int(j); step=widths[bus]//16; src=f'{bus}[{pair*step+j}]'
  if src not in pp or n not in oo:missing.append([pair,n,src]);continue
  px,py=pp[src];ox,oy=oo[n];xpair=11734.256+pair*531.25
  ps=(11734.256+px,20+py); oldp=(xpair+ox,1200+oy);newp=(xpair+(531.25-388.8)/2+nx,1200+ny)
  d=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
  rows.append(dict(pair=pair,pin=n,phy_pin=src,phy_xy=ps,old_xy=oldp,n32s_xy=newp,n32s_layer=nl,old_l1_um=d(ps,oldp),n32s_l1_um=d(ps,newp)))
def stats(k):
 a=sorted(rows,key=lambda z:-z[k]);return dict(bits=len(a),over405=sum(z[k]>405 for z in a),over100=sum(z[k]>100 for z in a),max_um=a[0][k],worst=a[:5])
def cut_demand(target):
 events=[]
 for z in rows:
  if z['pair']!=0:continue
  a,b=sorted((z['phy_xy'][0],z[target][0]))
  if b>a:events.extend([(a,1),(b,-1)])
 peak=now=0;wx=0
 for x,d in sorted(events,key=lambda q:(q[0],q[1])):
  now+=d
  if now>peak:peak=now;wx=x
 return dict(pair=0,peak_crossing_wires=peak,cut_x=wx,M6_pitch_um=0.064,target_use=0.55,required_escape_height_um=peak*0.064/0.55)
r=dict(schema='opentallas.s81.actual_pin_seam_model.v1',status='MODEL_ONLY',source_hashes={str(f.relative_to(B.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [phy,old,new,B/'n32s_floorplan.json']},missing=missing,old=stats('old_l1_um'),n32s=stats('n32s_l1_um'),routing_budget=dict(old=cut_demand('old_xy'),n32s=cut_demand('n32s_xy'),assumption='one horizontal M6 layer,55percent target availability; actualPG/OBS/above-body native tracks must be audited'),body_fit=dict(old_slot_wh=[531.25,250],n32s_wh=[388.8,324],center_dx=71.225,body_height_growth=74,reader_y_idx3=1490,ctrl_top_n32s=1524,reader_overlap34=True),limitations=['prospective gate pinplan, no closed n32s view yet','endpoint Manhattan lowerbound only; routed wires and insertedbuffers not proven','n32s body exceeds old250um reservation by74um and overlaps idx3 reader by34um','pin-to-pin100um target and routing-density budget still explicit obligations'])
(B/'model.json').write_text(json.dumps(r,indent=2)+'\n')
(B/'all_bits.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
assert not missing
print('SEAM_BITS',len(rows),'OLD',r['old']['max_um'],r['old']['over405'],'N32S',r['n32s']['max_um'],r['n32s']['over405'],'BODY_OVERLAP',34)
