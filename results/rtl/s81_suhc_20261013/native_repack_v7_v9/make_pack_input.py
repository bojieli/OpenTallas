import json,sys,pathlib
sys.path.insert(0,'tools/s81_suhc');import native_comb_seams as S
r=pathlib.Path('results/rtl/s81_suhc_20261013/native_repack_v7_v9');p=json.load(open(r/'retained_14_child_plan.json'));s=json.load(open(r/'retained_14_child_plan_seams.json'));geoms={}
for l in p['instances']:
 ox,oy=l['origin_um'];w,h=l['outline_um']
 if l.get('pin_assignment'):
  q=json.load(open(l['pin_assignment']));g={}
  for bus,port in q['ports'].items():
   for bit,(face,layer,offset,depth) in enumerate(port['per_bit']):
    name=bus if port['bits']==1 else f'{bus}[{bit}]';g[name]={'N':(offset,h-depth/2),'S':(offset,depth/2),'W':(depth/2,offset),'E':(w-depth/2,offset)}[face]
 else:g={n:(x-ox,y-oy) for n,(x,y) in S.pins(l).items()}
 geoms[l['instance']]=g
constraints=[]
for z in s['seams']:
 t=z['timing'];reach=t.get('reach_um')
 if reach is None:continue
 ai,ap=z['a'];bi,bp=z['b'];w=z['width'];ao=z['a_offset'];bo=z['b_offset']
 ds=[]
 for k in range(w or 1):
  an=f'{ap}[{k+ao}]' if w else ap;bn=f'{bp}[{k+bo}]' if w else bp
  a=geoms[ai][an];b=geoms[bi][bn];ds.append([a[0]-b[0],a[1]-b[1]])
 for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:constraints.append(dict(a=ai,b=bi,sx=sx,sy=sy,ub=reach-max(sx*dx+sy*dy for dx,dy in ds),bus_a=ap,bus_b=bp))
json.dump(dict(instances=p['instances'],constraints=constraints,status='R0 conservative worst-bus actual pin geometry feasibility only'),open('/tmp/codex-s81ccf/pack_input.json','w'),indent=2)
