#!/usr/bin/env python3
"""Fleet-only model of square216 PVJOIN in the existing PV trunk architecture.
Loads exact candidate pin manifest; never installs its generated RTL/plan as release input.
Other station abstractions remain the original planning models, not routed reach proof.
"""
import argparse,collections,hashlib,json,re,sys,types,traceback
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--join-pins',required=True);ap.add_argument('--out',required=True);ap.add_argument('--ct',type=float,default=345.6);ap.add_argument('--ns',type=int,default=3);ap.add_argument('--landed',action='store_true');ap.add_argument('--epoch-v3',action='store_true');ap.add_argument('--epoch-v4',action='store_true');ap.add_argument('--wide-local',action='store_true');ap.add_argument('--constrained',action='store_true');ap.add_argument('--small-relays',action='store_true');a=ap.parse_args()
if a.epoch_v4:a.epoch_v3=True
assert not a.epoch_v3 or a.landed
b=Path(a.root).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);base=b/'tools/qwen_kv_die/pv_trunk_gen.py';text=base.read_text();target="self.by(r) + PV_JOIN[1], TILE, TILE, 'R0')";assert text.count(target)==1;text=text.replace(target,"self.by(r) + PV_JOIN[1], 216.0, 216.0, 'R0')")
if a.landed:
 # Insert local real register stations before placement; these are additional hardware edges.
 text=text.replace("            placed = []\n            tx, ty = d['target']","            placed = []\n            if d.get('placement_between'):\n                aa,bb=d['placement_between'];ratio=d.get('placement_ratio',.5);ra=self.st[aa]['reps'];rb=self.st[bb]['reps'];assert ra and rb\n                d['target']=(sum(x+STD[k][0] for k,(x,y) in ra)/len(ra)*(1-ratio)+sum(x for k,(x,y) in rb)/len(rb)*ratio,sum(y+STD[k][1]/2 for k,(x,y) in ra)/len(ra)*(1-ratio)+sum(y+STD[k][1]/2 for k,(x,y) in rb)/len(rb)*ratio)\n            tx, ty = d['target']")
 text=text.replace('        self.place_all()','        self.add_local_landings()\n        self.place_all()',1)
 text=text.replace('inj[s] = j + s if c == 0 else d8 + j + s - 8','inj[s] = (j + s if c == 0 else d8 + j + s - 8) + 1')
 text=text.replace('ready[s] = Dcol[s] - Dcol[0]','ready[s] = Dcol[s] - Dcol[0] + 1')
 text=text.replace('rs_d = 1 + hd_d + J0','rs_d = 2 + hd_d + J0').replace('t_hd = 1 + J0','t_hd = 2 + J0')
 lo=text.index('    def rs_emit(');hi=text.index('    # ---- timing',lo);chunk=text[lo:hi]
 chunk=chunk.replace("L = [' wire[31:0] rs_sel;']", "L = [' wire[31:0] rs_sel;', ' wire[31:0] yv_land;'] + [f' assign yv_land[{s}]=w_Y{s}Q0[256];' for s in range(32)]")
 chunk=chunk.replace("f'out_leaf[{512 * s + RS_DQ * q + RS_DQ - 1}:{512 * s + RS_DQ * q}]'", "f'w_Y{s}Q{q}[255:0]'").replace('yv_w[','yv_land[')
 text=text[:lo]+chunk+text[hi:]
text=text.replace('range(0, 512, 37)','range(512)')
if a.wide_local:text=text.replace('h * B for h in range(17)','h * BLOCK_H for h in range(17)').replace(' + B / 2      # pin in', ' + BLOCK_H / 2      # pin in')
if a.epoch_v4:
 text=text.replace("f' wire[4095:0] ts_{s}; wire[7:0] sf_{s};'", "f' wire[4095:0] ts_{s},ts_landed_{s}; wire[7:0] sf_{s},sf_landed_{s};'")
 for k in range(4):text=text.replace(f'.ts{k}(ts_{{s}}[',f'.ts{k}(ts_landed_{{s}}[')
 text=text.replace("sfj = f'sf_{s}'","sfj = f'sf_landed_{s}'")
 text=text.replace('        L += body',"        L += body\n        for s in range(32):\n            for l in range(8):\n                L.append(f' assign ts_landed_{s}[{512*l+511}:{512*l}]=w_TS{s}B{l}[511:0]; assign sf_landed_{s}[{l}]=w_TS{s}B{l}[512];')")
if a.constrained:
 text=text.replace("            for j, s in enumerate(d['sizes']):", "            for j, s in enumerate(d['sizes']):\n                self.free.constraints = self.geometric_bounds(name,j,s)")
 text=text.replace("        d = np.abs(ox + w / 2 - tx) + np.abs(oy + h / 2 - ty)", "        bounds=getattr(self,'constraints',None)\n        if bounds is not None:\n            ulo,uhi,vlo,vhi=bounds;ok=(ox+oy>=ulo)&(ox+oy<=uhi)&(ox-oy>=vlo)&(ox-oy<=vhi);ox,oy=ox[ok],oy[ok]\n            if not len(ox):return None\n        d = np.abs(ox + w / 2 - tx) + np.abs(oy + h / 2 - ty)")
(out/'generator_model.py').write_text(text)
m=types.ModuleType('pv_trunk_model');m.__file__=str(base);exec(compile(text,str(base),'exec'),m.__dict__)
m.B=604.8;m.PV_BANK={0:(0.,0.,'R0'),1:(216.,0.,'R0'),2:(0.,216.,'MX'),3:(0.,432.,'MX'),4:(216.,432.,'MX'),5:(432.,432.,'MX'),6:(432.,0.,'R0'),7:(432.,216.,'R0')};m.PV_JOIN=(194.4,194.4,'R0')
if a.landed:
 m.B=691.2;m.PV_BANK={0:(0.,0.,'R0'),1:(259.2,0.,'R0'),2:(0.,259.2,'MX'),3:(0.,518.4,'MX'),4:(259.2,518.4,'MX'),5:(518.4,518.4,'MX'),6:(518.4,0.,'R0'),7:(518.4,259.2,'R0')};m.PV_JOIN=(237.6,237.6,'R0')
 def add_local(self):
  if a.epoch_v3:
   for node,d in list(self.st.items()):
    if not re.fullmatch(r'V[WE]\d+c\dt',node):continue
    parent=next(iter(d['par'].values()));pd=self.st[parent];target=((pd['target'][0]+d['target'][0])/2,pd['target'][1]);bridge=self.station('GB'+node,d['keys'],parent,target,d['ck'],pd['region'],prio=2)
    d['par']={k:bridge for k in d['keys']}
  for (s,t),prior in list(self.s1_of.items()):
   if t=='j':continue
   tk=[k for k in self.st[prior]['keys'] if k not in [('R',),('C',31)]];parents={k:prior for k in tk}
   cell=f'u_s{s}_b{t}';pp=[self.tpin(cell,f'{pn}[{i}]') for pn,n in [('pv2',256),('pe2',32),('bc',23)] for i in [0,n-1]]
   tx=sum(p[0] for p in pp)/len(pp);ty=sum(p[1] for p in pp)/len(pp);r=self.row_of[s];c=(s//8)%2
   if a.epoch_v3:
    pd=self.st[prior];pd['target']=(tx,pd['target'][1]);groups=collections.defaultdict(list)
    for k,pn in pd['par'].items():groups[pn].append(k)
    for idx,(pn,kk) in enumerate(groups.items()):
     xx=(self.st[pn]['target'][0]+tx)/2;yy=pd['target'][1];bridge=self.station(f'G{s}b{t}p{idx}',kk,pn,(xx,yy),pd['ck'],(self.bx(c),self.by(r)-self.a.ch,self.bx(c)+m.B,self.by(r)+m.B+self.a.ch),prio=3)
     self.st[bridge]['placement_between']=(pn,prior)
     if a.epoch_v4:
      self.st[bridge]['placement_ratio']=1/3;self.st[bridge]['sink_nodes']=[(prior,800)];other=self.station(f'G2_{s}b{t}p{idx}',kk,bridge,(xx,yy),pd['ck'],(self.bx(c),self.by(r)-self.a.ch,self.bx(c)+m.B,self.by(r)+m.B+self.a.ch),prio=4);self.st[other]['placement_between']=(pn,prior);self.st[other]['placement_ratio']=2/3;self.st[other]['sink_nodes']=[(prior,400)];bridge=other
     for k in kk:pd['par'][k]=bridge
    pd['depth']+=(2 if a.epoch_v4 else 1)
   region=(self.bx(c),self.by(r)-self.a.ch,self.bx(c)+m.B,self.by(r)+m.B+self.a.ch)
   nm=self.station(f'L{s}b{t}',tk,parents,(tx,ty),f'col_clk[{s}]',region,prio=-2,depth_check=False)
   self.st[prior]['align']=nm;self.st[prior]['sink_nodes']=[(nm,400)]
   dest={}
   for pn,kk in zip(['pv2','pe2','bc'],self.tile_srcs(s//8,s%8,t)):
    for ii,key in enumerate(kk):dest[key]=self.tpin(cell,f'{pn}[{ii}]')
   self.st[nm]['destinations']=dest
   if a.epoch_v4:self.st[prior].pop('row',None);self.st[prior]['same_row']=False
   self.s1_of[(s,t)]=nm
   rp=self.rst_of[(s,t)];rr=self.station(f'LR{s}b{t}',[('R',)],rp,self.st[rp]['target'],f'col_clk[{s}]',region,prio=4)
   if a.epoch_v3:
    raw_r=rp;middle_r=rr;rp_pin=self.tpin(cell,'rst_n');rr=self.station(f'LR2_{s}b{t}',[('R',)],middle_r,(rp_pin[0]-10.8,rp_pin[1]),f'col_clk[{s}]',region,prio=-2);self.st[middle_r]['placement_between']=(raw_r,rr)
   if a.epoch_v4:
    last_r=rr;mid_r=self.station(f'LR3_{s}b{t}',[('R',)],middle_r,self.st[middle_r]['target'],f'col_clk[{s}]',region,prio=5);self.st[mid_r]['placement_between']=(middle_r,last_r);self.st[last_r]['par'][('R',)]=mid_r;self.st[last_r]['depth']+=1;self.st[last_r]['destinations']={('R',):rp_pin};self.st[mid_r]['sink_nodes']=[(last_r,400)];self.st[middle_r]['sink_nodes']=[(last_r,800)]
   self.rst_of[(s,t)]=rr
   if t==4:
    join=f'u_s{s}_j';jp=[self.tpin(join,k) for k in ['join_go','rst_n']];jx=sum(x for x,y in jp)/2;jy=sum(y for x,y in jp)/2
    jkeys=[('C',31),('R',)];jparents={k:self.st[prior]['par'][k] for k in jkeys};mid=self.station(f'JG{s}',jkeys,jparents,(jx,jy),f'col_clk[{s}]',region,prio=4,depth_check=False);last=self.station(f'JC{s}',jkeys,mid,(jx-25.92,jy),f'col_clk[{s}]',region,prio=-2);self.st[mid]['placement_between']=(jparents[('C',31)],last)
    if a.epoch_v4:last=self.station(f'JC2_{s}',jkeys,last,(jx-25.92,jy),f'col_clk[{s}]',region,prio=-4)
    self.st[last]['destinations']={('C',31):jp[0],('R',):jp[1]};self.st[mid]['sink_nodes']=[(next(iter(self.st[last]['par'].values())),400)]
    previous=next(iter(self.st[last]['par'].values()))
    if previous!=mid:self.st[previous]['sink_nodes']=[(last,400)]
    self.s1_of[(s,'j')]=last
  if a.epoch_v4:
   # The original flag landing stayed in the outer channel after the join moved inward.
   # Re-admit its SAME registered stage beside the actual join pins, then span to the existing pads.
   for node,d in list(self.st.items()):
    fm=re.fullmatch(r'F(\d+)a',node)
    if not fm:continue
    ss=int(fm[1]);rr=self.row_of[ss];cc=(ss//8)%2;pts=[self.rootpin[k] for k in d['keys']]
    d['target']=(sum(x for x,y in pts)/len(pts)+25.92,sum(y for x,y in pts)/len(pts))
    d['region']=(self.bx(cc),self.by(rr)-self.a.ch,self.bx(cc)+m.B,self.by(rr)+m.B+self.a.ch);d['prio']=-2
   for node,d in list(self.st.items()):
    fm=re.fullmatch(r'F(\d+)p(\d+)',node)
    if not fm:continue
    ss,ii=map(int,fm.groups());rr=self.row_of[ss];cc=(ss//8)%2;start=self.st[f'F{ss}a']['target'];end=self.st[f'F{ss}b']['target'];ratio=(ii+1)/(a.ns+1)
    d['target']=tuple(x+(y-x)*ratio for x,y in zip(start,end));d['region']=(0.,self.by(rr)-self.a.ch,self.FW,self.by(rr)+m.B+self.a.ch);d['prio']=-1.5
   for node,d in list(self.st.items()):
    if not re.fullmatch(r'F\d+b',node):continue
    parent=next(iter(d['par'].values()));bridge=self.station('BF'+node,d['keys'],parent,d['target'],d['ck'],d['region'],prio=5);self.st[bridge]['placement_between']=(parent,node);self.st[bridge]['sink_nodes']=[(node,400)];d['par']={k:bridge for k in d['keys']};d['depth']+=1
   for ss in range(32):
    row=self.row_of[ss];cc=(ss//8)%2
    for ll in range(8):
     raw=f'u_s{ss}_b{ll}';join=f'u_s{ss}_j';tsn=['ts0','ts1','ts2','ts3'][ll//2];keys=[('TS',ss,ll,i) for i in range(512)]+[('SF',ss,ll)];pts=[]
     for i,key in enumerate(keys):
      self.root[key]=(f'ts_{ss}[{512*ll+i}]' if i<512 else f'sf_{ss}[{ll}]');self.rootpin[key]=self.tpin(raw,f'ts[{i}]' if i<512 else 'fault')
      dest=self.tpin(join,f'{tsn}[{512*(ll%2)+i}]' if i<512 else f'sf[{ll}]');src=self.rootpin[key];pts.append(((src[0]+dest[0])/2,(src[1]+dest[1])/2))
     tx=sum(x for x,y in pts)/len(pts);ty=sum(y for x,y in pts)/len(pts);node=self.station(f'TS{ss}B{ll}',keys,None,(tx,ty),f'col_clk[{ss}]',(self.bx(cc),self.by(row)-self.a.ch,self.bx(cc)+m.B,self.by(row)+m.B+self.a.ch),prio=-1)
     self.st[node]['destinations']={key:self.tpin(join,f'{tsn}[{512*(ll%2)+i}]' if i<512 else f'sf[{ll}]') for i,key in enumerate(keys)}
  for s in range(32):
   cell=f'u_s{s}_j' ;_,x,y,w,h,_=self.cells[cell]
   for q in range(2):
    keys=[('Y',s,q,i) for i in range(256)]+[('YV',s,q)]
    for i,k in enumerate(keys):
     self.root[k]=(f'out_leaf[{512*s+256*q+i}]' if i<256 else f'yv_w[{s}]');self.rootpin[k]=self.tpin(cell,f'y[{256*q+i}]' if i<256 else 'y_valid')
    self.station(f'Y{s}Q{q}',keys,None,(x+w+32.4,y+h/2+(.5-q)*60),f'col_clk[{s}]',(x+w+17.28,y-17.28,x+w+(86.4 if a.wide_local else 64.8)-17.28,y+h+17.28),prio=-3)
 m.Gen.add_local_landings=add_local
 oldrs=m.Gen.rs_hops
 def rs_hops(self,bout):
  oldpin=self.tpin
  def landed_pin(cell,pin):
   import re
   match=re.fullmatch(r'u_s(\d+)_j',cell)
   if match:
    s=int(match[1]);yy=re.fullmatch(r'y\[(\d+)\]',pin)
    if yy:i=int(yy[1]);return bout[(f'Y{s}Q{i//256}',('Y',s,i//256,i%256))]
    if pin=='y_valid':return bout[(f'Y{s}Q0',('YV',s,0))]
   return oldpin(cell,pin)
  self.tpin=landed_pin
  try:return oldrs(self,bout)
  finally:self.tpin=oldpin
 m.Gen.rs_hops=rs_hops
if a.wide_local:
 m.B=734.4;m.BLOCK_H=691.2;m.PV_JOIN=(259.2,237.6,'R0');m.PV_BANK={0:(0.,0.,'R0'),1:(280.8,0.,'R0'),2:(0.,259.2,'MX'),3:(0.,518.4,'MX'),4:(280.8,518.4,'MX'),5:(561.6,518.4,'MX'),6:(561.6,0.,'R0'),7:(561.6,259.2,'R0')}
pins=json.load(open(a.join_pins));pins=[dict(pin=k,**v) for k,v in pins.items()] if isinstance(pins,dict) else pins;assert len(pins)==4621;assert len({p['pin'] for p in pins})==4621
orig=m.Gen.__init__
def init(self,args):
 orig(self,args);self.views['ot_qwen_tp8_pv_join_t']=((216.,216.),{p['pin']:(p['x'],p['y']) for p in pins})
m.Gen.__init__=init
if a.small_relays:
 oldstation=m.Gen.station
 def station(self,name,keys,src,target,ck,region,**kwargs):
  node=oldstation(self,name,keys,src,target,ck,region,**kwargs)
  if name.startswith(('G','L','J','TS','Y','BF','S')):
   widths=[1] if len(keys)==1 else [36]*((len(keys)+35)//36);self.st[node]['sizes']=widths
   self.wires[-1]=(self.wires[-1][0],sum(widths))
  return node
 m.Gen.station=station
# Compute compiler offsets from each actual key path, rather than a stale fixed stage-count formula.
text_delta='delta[gg] = ds.pop() - (g.v_entry_stages + 2)'
# main() was compiled above; patch its code by recompiling only that function's definition.
main_text=text[text.index('def main('):text.index("if __name__",text.index('def main('))] if "if __name__" in text[text.index('def main('):] else text[text.index('def main('):]
assert text_delta in main_text;main_text=main_text.replace(text_delta,'delta[gg] = g.exact_chunk_delta()[gg]');exec(compile(main_text,str(base),'exec'),m.__dict__)
def exact_delta(self):
 from functools import lru_cache
 @lru_cache(None)
 def age(node,key):
  if node is None:return 0
  return age(self.st[node]['par'][key],key)+1
 groups=collections.defaultdict(set);records=[]
 for (s,t),node in self.s1_of.items():
  if t=='j':continue
  vk,ek,ck=self.tile_srcs(s//8,s%8,t);ca=age(node,('C',0));vv={age(node,k) for k in vk};ee={age(node,k) for k in ek};assert len(vv)==1 and ee=={ca},(s,t,ca,vv,ee)
  va=next(iter(vv));groups[s%8].add(ca-va);records.append(dict(column=s,tile=t,command_edges=ca,v_edges=va,chunk_delta=ca-va,reset_edges=age(self.rst_of[(s,t)],('R',))))
 assert all(len(v)==1 for v in groups.values()),groups
 result={g:next(iter(v)) for g,v in groups.items()};(out/'compiler_age_graph.json').write_text(json.dumps(dict(records=records,chunk_delta=result,scope='exact graph edge counts; no functional/timing qualification'),indent=1)+'\n');return result
m.Gen.exact_chunk_delta=exact_delta
if a.epoch_v4:
 def timing(self):
  dc={};rc={}
  for ss in range(32):
   dc[ss]=self.st[self.s1_of[(ss,'j')]]['depth'];row=self.row_of[ss];ent=self.flag_chain.index(f'FD{row+1}');rc[ss]=self.st[f'F{ss}b']['depth']+len(self.flag_chain)-ent
  return dc,rc
 m.Gen.timing=timing
if a.constrained:
 def bitpin(self,node,key,port):
  dd=self.st[node]
  if not dd.get('reps') or key not in dd.get('idx',{}):return None
  idx=dd['idx'][key]
  for width,(xx,yy) in dd['reps']:
   if idx<width:
    if width not in m.STD:return None
    px,py=self.views[f'qkd_rlys_{width}'][1][f'{port}[{idx}]'];return xx+px,yy+py
   idx-=width
  return None
 def bounds(self,node,replica,width):
  dd=self.st[node]
  if dd.get('kind') or width not in m.STD:return None
  limits=[-float('inf'),float('inf'),-float('inf'),float('inf')]
  def constrain(point,pin,budget=400):
   cx,cy=point[0]-pin[0],point[1]-pin[1];limits[0]=max(limits[0],cx+cy-budget);limits[1]=min(limits[1],cx+cy+budget);limits[2]=max(limits[2],cx-cy-budget);limits[3]=min(limits[3],cx-cy+budget)
  offset=sum(dd['sizes'][:replica]);pins=self.views[f'qkd_rlys_{width}'][1]
  for i in range(width):
   if offset+i>=len(dd['keys']):break
   key=dd['keys'][offset+i];parent=dd['par'][key];point=self.rootpin.get(key) if parent is None else bitpin(self,parent,key,'b')
   if point is not None:constrain(point,pins[f'a[{i}]'])
   dest=dd.get('destinations',{}).get(key)
   if dest is not None:constrain(dest,pins[f'b[{i}]'])
   for sink,budget in dd.get('sink_nodes',[]):
    point=bitpin(self,sink,key,'a')
    if point is not None:constrain(point,pins[f'b[{i}]'],budget)
  self._last_bounds=dict(node=node,replica=replica,width=width,uv_bounds=limits,empty_intersection=(limits[0]>limits[1] or limits[2]>limits[3]),region=dd['region'],target=dd['target']);(out/'last_geometric_admission.json').write_text(json.dumps(self._last_bounds,indent=1)+'\n')
  return limits
 m.Gen.geometric_bounds=bounds
oldplace=m.Gen.place_all
def place(self):
 counts=collections.Counter();area=0.;padded=0.
 inventory=[]
 for name,dd in self.st.items():
  if dd.get('kind'):continue
  dims=[m.STD[width] for width in dd['sizes']]
  inventory.append(dict(name=name,payload_bits=len(dd['keys']),registered_bits=sum(dd['sizes']),stage_depth=dd['depth'],clock=dd['ck'],region=dd['region'],target=dd['target'],priority=dd['prio'],macro_count=len(dims),body_um2=sum(w*h for w,h in dims),halo_um2=sum((w+8.64)*(h+8.64) for w,h in dims),parents=dict(collections.Counter(str(p) for p in dd['par'].values()))))
 (out/'station_inventory.json').write_text(json.dumps(inventory,indent=1)+'\n')
 for dd in self.st.values():
  for width in dd['sizes']:
   w,h=(m.STD|m.RS_STD)[width];counts[str(width)]+=1;area+=w*h;padded+=(w+8.64)*(h+8.64)
 leaf=sum(w*h for master,x,y,w,h,o in self.cells.values());leaf_pad=sum((w+34.56)*(h+34.56) for master,x,y,w,h,o in self.cells.values());frame=self.FW*self.FH
 (out/'resource_admission.json').write_text(json.dumps(dict(scope='exact model inventory before placement; native/synthesis/route still required',replicas=counts,station_area_um2=area,station_halo_area_um2=padded,leaf_area_um2=leaf,leaf_halo_area_um2=leaf_pad,frame_area_um2=frame,body_utilization=(leaf+area)/frame,halo_utilization=(leaf_pad+padded)/frame),indent=1)+'\n');return oldplace(self)
m.Gen.place_all=place
oldverify=m.Gen.verify
def verify(self):
 oldpin=self.tpin
 if a.epoch_v4:
  def output_pin(node,key):
   d=self.st[node];idx=d['idx'][key]
   for width,(xx,yy) in d['reps']:
    if idx<width:px,py=self.views[f'qkd_rlys_{width}'][1][f'b[{idx}]'];return xx+px,yy+py
    idx-=width
   raise AssertionError((node,key))
  def staged_pin(cell,pin):
   match=re.fullmatch(r'u_s(\d+)_b(\d+)',cell)
   if match:
    ss,ll=map(int,match.groups());mm=re.fullmatch(r'ts\[(\d+)\]',pin)
    if mm:return output_pin(f'TS{ss}B{ll}',('TS',ss,ll,int(mm[1])))
    if pin=='fault':return output_pin(f'TS{ss}B{ll}',('SF',ss,ll))
   return oldpin(cell,pin)
  self.tpin=staged_pin
 try:rows=oldverify(self)
 finally:self.tpin=oldpin
 groups={}
 for dist,hop,key in rows:
  if dist<=405:continue
  category=re.sub(r'\d+','#',hop)+' | '+re.sub(r'\d+','#',key)
  g=groups.setdefault(category,dict(count=0,max_um=0,examples=[]));g['count']+=1;g['max_um']=max(g['max_um'],dist)
  if len(g['examples'])<3:g['examples'].append([dist,hop,key])
 (out/'reach_failures_405.json').write_text(json.dumps(dict(count=sum(g['count'] for g in groups.values()),groups=groups),indent=1)+'\n');return rows
m.Gen.verify=verify
result={'scope':'MODEL_ONLY; candidate pins, original station pin abstractions; not routed view or measured reach','baseline_source_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'join_pins_sha256':hashlib.sha256(Path(a.join_pins).read_bytes()).hexdigest(),'block_um':[m.B,getattr(m,'BLOCK_H',m.B)],'wide_local':a.wide_local,'constrained_coordinates':a.constrained,'small_local_relays':a.small_relays,'landed_structural':a.landed,'epoch_v3':a.epoch_v3,'epoch_v4':a.epoch_v4,'input_edges_added':(3 if a.epoch_v4 else 2 if a.epoch_v3 else int(a.landed)),'result_edges_added':int(a.landed),'reset_release_extra_local_edges':(4 if a.epoch_v4 else 2 if a.epoch_v3 else int(a.landed)),'health_fault_arrival_extra_local_edges':(5 if a.epoch_v4 else 2 if a.epoch_v3 else int(a.landed)),'join_um':[216,216],'leaf_extra_reset_edges_preaccepted':2,'total_extra_reset_edges_before_external_replan':(6 if a.epoch_v4 else 4 if a.epoch_v3 else 3 if a.landed else 2),'leaf_lef_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in m.LEAF_LEF.items() if k!='ot_qwen_tp8_pv_join_t'},'join_interface_alias_only':'ot_qwen_tp8_pv_join_t is a planner port alias; newS32 RTL/native view not adopted','ct_um':a.ct,'ns':a.ns}
try:
 m.main(['--ct',str(a.ct),'--ns',str(a.ns),*(['--rs-inj-y','345.6','--rs-r1-y','633.6','--rs-r2-y','57.6'] if a.landed else []),'--out-sv',str(out/'candidate.sv'),'--out-plan',str(out/'plan.json')]);d=json.load(open(out/'plan.json'));bad=json.load(open(out/'reach_failures_405.json'));result.update(status=('PLAN_REACH_FAIL' if bad['count'] else 'PLAN_REACH_PASS_ONLY'),hops_over_405=bad['count'],frame_um=d['frame_um'],hops_over_400=d['hops_over_400'],hops_total=d['hops_total'],worst_hops=d['worst_hops'],trunk_d=d['trunk_d'],flag_d=d['flag_d'],result_trunk=d.get('result_trunk'),col_extra_edges=d['col_extra_edges'],chunk_delta_vs_header=d['chunk_delta_vs_header'],station_flops=d['station_flops'])
except BaseException as exc:
 traceback.print_exc();result.update(status='REFUSED_MODEL',error=repr(exc))
(out/'result.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result),flush=True)
raise SystemExit(0 if result['status']=='PLAN_REACH_PASS_ONLY' else 1)
