import json,sys,hashlib,re,collections
from pathlib import Path
sys.path.insert(0,'tools');sys.path.insert(0,'tools/ref_tile')
import check_macro_track_alignment as C
import layout_png as L
out=Path('results/arch/codex_xs_lattice_1020')
for label in ['d','e']:
 name=f'smh_xs_p192{label}_lattice';s=json.load(open('physical/ref_tile/'+name+'/spec.json'))
 d={'die':[0,0,s['outline']['w'],s['outline']['h']],'blocks':[],'pins':[],'clocks':[],'top':name,'stats':{}}
 records=[];pinlines=['inst\tpin\tuse\tlayer\tx0\ty0\tx1\ty1'];cache={}
 for child in s['macros']:
  path=Path(child['view']);lef=next(path.glob('*.lef'))
  if str(lef) not in cache:cache[str(lef)]=C.parse_lef(lef.read_text())[0]
  m=cache[str(lef)];x,y=child['at'];w,h=m['W']/1000,m['H']/1000;orient=child.get('orient','R0');inst=child['inst'];track=C.check_placement(m,orient,round(x*1000),round(y*1000))
  assert abs(x/43.2-round(x/43.2))<1e-6 and abs(y/43.2-round(y/43.2))<1e-6
  assert all(v['offtrack']==0 for v in track['layers'].values()),track
  faces=collections.defaultdict(list);pgfaces=collections.defaultdict(list)
  for pin in m['pins']:
   pinfaces=set()
   for layer,r in pin['rects']:
    q=C.transform_rect(r,orient,m['W'],m['H']);q=[v/1000 for v in q]
    face=min([('W',q[0]),('E',w-q[2]),('S',q[1]),('N',h-q[3])],key=lambda z:z[1])[0];pinfaces.add(face)
    coords=[q[0]+x,q[1]+y,q[2]+x,q[3]+y]
    pinlines.append('\t'.join(map(str,[inst,pin['name'],pin['use'],layer,*coords])))
    if pin['use'] not in ['POWER','GROUND']:d['pins'].append([inst+'/'+pin['name'],layer,*coords])
   for face in pinfaces:(pgfaces if pin['use'] in ['POWER','GROUND'] else faces)[face].append(pin['name'])
  density={f:len(set(v))/(h if f in ['W','E'] else w) for f,v in faces.items()}
  assert max(density.values())<=6,density
  records.append({'inst':inst,'master':m['name'],'origin':[x,y],'orient':orient,'bbox':[x,y,x+w,y+h],'lef_sha256':hashlib.sha256(lef.read_bytes()).hexdigest(),'literal_lattice':True,'signal_pin_faces':{f:len(set(v)) for f,v in faces.items()},'signal_pins_per_um':density,'pg_pin_face_access':{f:sorted(set(v)) for f,v in pgfaces.items()},'pin_track':track})
  d['blocks'].append([inst,m['name'],x,y,x+w,y+h])
 # Fixed bit-order N bands align direct SRAM-read output captures with their macros.
 reach=[]
 for port,nbits,group in [('o_iw',788,128),('o_ix',788,256)]:
  lo,hi=s['pin_ranges'][port]
  for bit in range(nbits):
   idx=(4+bit//group) if port=='o_iw' else bit//group
   child=s['macros'][idx];m=cache[str(next(Path(child['view']).glob('*.lef')))];x,y=child['at']
   pin=next(p for p in m['pins'] if p['name']==f'rd_out[{bit%group}]')
   tx=lo+(hi-lo)*(bit+0.5)/nbits;ty=s['outline']['h']
   distance=min(abs(tx-((r[0]+r[2])/2000+x))+abs(ty-((r[1]+r[3])/2000+y)) for lay,r in pin['rects'])
   reach.append({'port':f'{port}[{bit}]','macro':child['inst'],'macro_pin':pin['name'],'capture_pin_target':[tx,ty],'manhattan_um':distance})
 worst=max(reach,key=lambda q:q['manhattan_um'])
 assert worst['manhattan_um']+10<=405,worst
 d['clocks']=['clk'];clo,chi=s['pin_ranges']['clk'];d['pins'].append(['clk','M4',(clo+chi)/2, s['outline']['h'],(clo+chi)/2+0.024,s['outline']['h']+0.024])
 overlaps=[];hgap=[];vgap=[]
 for i,a in enumerate(records):
  ax,ay,ar,at=a['bbox']
  for b in records[i+1:]:
   bx,by,br,bt=b['bbox'];ix=min(ar,br)-max(ax,bx);iy=min(at,bt)-max(ay,by)
   if ix>0 and iy>0:overlaps.append([a['inst'],b['inst']])
   if iy>0 and ix<=0:hgap.append(-ix)
   if ix>0 and iy<=0:vgap.append(-iy)
 assert not overlaps
 result={'scope':'Exact spec+immutable LEF planning geometry; NOT placed/CTS/route evidence','outline':s['outline'],'macros':records,'overlaps':overlaps,'min_horizontal_channel_um':min(hgap),'min_vertical_channel_um':min(vgap),'source_mapped_std_area_um2':11255.0,'source_gate_macro_area_um2':44902.6,'source_unchanged':True,'direct_macro_read_capture_reach':{'metric':'Manhattan, exact macro pins to fixed IO capture targets;10um allowed for local FF placement','worst':worst,'with10umplacement_allowance':worst['manhattan_um']+10},'clock':{'source':'clk','edge':'posedge','period_ns':0.833333,'io_hold_ns':0.03,'regional_k':s['orfs_vars']['OT_CKKM_K'],'phase_change':False,'new_insertion_spread':'unmeasured until CTS'}}
 (out/(name+'_read_capture_reach.json')).write_text(json.dumps(reach,indent=2)+'\n');(out/(name+'_geometry.json')).write_text(json.dumps(result,indent=2)+'\n');(out/(name+'_pins.tsv')).write_text('\n'.join(pinlines)+'\n');(out/(name+'_layout.json')).write_text(json.dumps(d)+'\n')
 L.render_floorplan(d,out/(name+'_planned.png'),name+' EXACT LEF PLAN NOT PLACED')
 print(name,'macros',len(records),'channels',min(hgap),min(vgap),'pin_density',max(max(r['signal_pins_per_um'].values()) for r in records),'zeroofftrack')
