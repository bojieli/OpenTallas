from pathlib import Path
import json,re,sys,collections,importlib.util
base=Path(__file__).parent
sys.path.insert(0,str(base))
import face_guard as fg
import geom_rules as g
Dold=g.Design(str(base/'old_geom.tsv'));old={c[6].replace('\\[','[').replace('\\]',']'):c for c in Dold.cells.values() if c[0]=='S'}
masters={c[1]:(c[4]-c[2],c[5]-c[3]) for c in Dold.cells.values() if c[0]=='S'}
meta=json.load(open(base/'anchors.json'));anchors={a['name'].replace('\\[','[').replace('\\]',']'):a['box_um'] for a in meta['anchors']}
extra={a['name'].replace('\\[','[').replace('\\]',']'):a['box_um'] for a in meta.get('new_source_extra_anchors',[])}
mods=fg.parse((base/'mapped.v').read_text());F=fg.Flat(mods,'qkd_kvs_pc');top=mods['qkd_kvs_pc']
D=object.__new__(g.Design);D.memory_reach=False;D.memory_models={};D.extra={};D.cells={};D.pins=[];D.pin_by_k={};D.nets=[];D.drives=collections.defaultdict(list);D.cell_in=collections.defaultdict(list);D.pin_net={};D.die=Dold.die
coords={p['name']:p for p in Dold.pins};net={};unmatched=[];new=0;matched=0
for cid,(typ,name,pins) in enumerate(F.cells,1):
 kind='S' if fg.is_ff(typ) else 'B' if fg.is_buf(typ) else 'K' if typ.startswith(('ICG','CKINV','CKBUF','CLKBUF')) else 'L'
 w,h=masters.get(typ,(1.08,.27))
 if kind=='S':
  if name in extra:
   x,y=extra[name][:2]
  elif name in old:
   o=old[name];r=anchors.get(name,o[2:6]);x,y=r[:2];matched+=1
  elif name.startswith('pcin_'):
   m=re.fullmatch(r'pcin_(\w+)(?:\[(\d+)\])?\$_DFF_P_',name)
   if not m:raise ValueError('new FF name '+name)
   pin=m[1]+'['+(m[2] or '0')+']';p=coords[pin];x,y=p['x']-w/2,p['y']-h/2
   if pin=='rst_n[0]':x,y=203.04,181.44
   elif p['x']<4.32:x=4.32;y=max(4.32,min(358.56-h,y))
   elif p['x']>393.12:x=393.12-w;y=max(4.32,min(358.56-h,y))
   elif p['y']<4.32:y=4.32;x=max(4.32,min(393.12-w,x))
   elif p['y']>358.56:y=358.56-h;x=max(4.32,min(393.12-w,x))
   new+=1
  else:raise ValueError('Unlocated new source FF '+name)
 else:x,y=0.,0.
 D.cells[cid]=(kind,typ,x,y,x+w,y+h,name)
 for pin,(direction,bits) in pins.items():
  for b in bits:
   z=net.setdefault(F.find(b),[None,[]]);ref=('i',cid,kind=='S' and pin in ('CLK','CK','C'))
   if direction=='out':
    if z[0] is not None:raise ValueError('multiple drivers')
    z[0]=ref
   else:z[1].append(ref)
for name in top.ports:
 for bit in fg._bits_of(top,name):
  if bit not in coords:continue
  p=dict(coords[bit]);k=len(D.pins)+1;p['k']=k;D.pins.append(p);D.pin_by_k[k]=p
  z=net.setdefault(F.find(bit),[None,[]]);ref=('p',k,False)
  if top.dirs[name]=='input':z[0]=ref
  else:z[1].append(ref)
for dr,ss in net.values():
 n=len(D.nets);D.nets.append(('SIGNAL',dr,ss))
 if dr:
  if dr[0]=='i':D.drives[dr[1]].append(n)
  else:D.pin_net[dr[1]]=n
 for s in ss:
  if s[0]=='i':D.cell_in[s[1]].append((n,s[2]))
  else:D.pin_net[s[1]]=n
r=dict(scope='Actual new mapped netlist + prebuild source constraints; new collar FF locations ideal face sites, NOT a placed gate',old_seq_matched=matched,new_collar=new,new_explicit_constraints=list(extra),unmatched=unmatched,r2r=g.r2r_metrics(D))
(base/'new_graph_model.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
