from pathlib import Path
import re,json,hashlib
p=Path('/srv/opentallas-scratch2/claude/s81ck12/k13/peco_caprt_B1440__LWA/out/6_final.def');vias={};pg=[];unknown=[];blockages=[];mode=None;buf='';net=None;counts={'M4':0,'M5':0};via_names=set();block_section_seen=False
for line in p.open():
 s=line.strip()
 if s.startswith('VIAS '):mode='vias';continue
 if s=='END VIAS':mode=None;continue
 if s.startswith('SPECIALNETS '):mode='pg';continue
 if s=='END SPECIALNETS':mode=None;continue
 if s.startswith('BLOCKAGES '):mode='block';block_section_seen=True;continue
 if s=='END BLOCKAGES':mode=None;continue
 if mode=='vias':
  buf+=s+' '
  if ';' not in s:continue
  m=re.match(r'-\s+(\S+)',buf);name=m.group(1);rects=[]
  for r in re.finditer(r'\+ RECT (M[45]) \(\s*(-?\d+)\s+(-?\d+)\s*\) \(\s*(-?\d+)\s+(-?\d+)\s*\)',buf):rects.append((r.group(1),list(map(int,r.group(2,3,4,5)))))
  vias[name]=rects;buf='';continue
 if mode=='block':blockages.append(s);continue
 if mode!='pg':continue
 if s.startswith('- '):net=s.split()[1]
 m=re.search(r'(?:\+ ROUTED|NEW) (\S+) (\d+)(.*)',s)
 if not m:continue
 layer,width,tail=m.group(1),int(m.group(2)),m.group(3);points=[];last=None
 for q in re.finditer(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)',tail):
  a,b=q.groups()
  if '*' in (a,b) and last is None:unknown.append(s);break
  xy=[last[0] if a=='*' else int(a),last[1] if b=='*' else int(b)];points.append(xy);last=xy
 if not points:continue
 rects=[]
 for a,b in zip(points,points[1:]):
  if a[0]!=b[0] and a[1]!=b[1]:unknown.append(s);continue
  if layer in counts and width:
   z=width/2;rects.append((layer,[min(a[0],b[0])-z,min(a[1],b[1])-z,max(a[0],b[0])+z,max(a[1],b[1])+z],'stripe'))
 # Special-wire vias here are explicit DEF-generated RECT geometries, not guessed nominal via dimensions.
 end=tail[tail.rfind(')')+1:].strip().split()
 for token in end:
  if token in vias:
   via_names.add(token)
   for ly,r in vias[token]:rects.append((ly,[r[0]+last[0],r[1]+last[1],r[2]+last[0],r[3]+last[1]],'via:'+token))
  elif token not in [';','N','NEW']:unknown.append('UNPARSED_VIA_TOKEN '+s)
 for ly,r,kind in rects:
  counts[ly]+=1;r=[v/1000 for v in r]
  if r[0]<120 and r[2]>88 and r[1]<96 and r[3]>76:pg.append(dict(net=net,layer=ly,rect_um=r,kind=kind))
result=dict(schema='opentallas.actual_DEF_power_inventory.v1',source=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),basis='Actual OpenROAD-written DEF SPECIALNETS straight stripes plus exact DEF VIAS RECT enclosures; no CAD run or nominal PG substitute',counts=counts,region_um=[88,76,120,96],region_pg_shapes=pg,unknown_patterns=unknown[:30],unknown_count=len(unknown),placement_blockage_section_present=block_section_seen,blockage_records=blockages,via_shapes=vias,via_names_used=sorted(via_names));print(json.dumps(result,separators=(',',':')))
