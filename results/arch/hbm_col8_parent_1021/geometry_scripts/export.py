import json,re,hashlib,pathlib
R=pathlib.Path.cwd(); out=R/'results/arch/hbm_col8_parent_1021'
p=json.loads((out/'column_regions.json').read_text()); rect=[]
def add(n,k,x,y,w,h,owner,**kw):
 d=dict(name=n,kind=k,x_um=x,y_um=y,width_um=w,height_um=h,clock_owner=owner,orientation='R0',**kw);rect.append(d);return d
def pins(path,xy):
 s=(R/path).read_text(); d={}
 for m in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',s,re.S):
  q=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',m[2])
  if q:
   a,b,c,e=map(float,q.groups());d[m[1]]=(xy[0]+(a+c)/2,xy[1]+(b+e)/2)
 return d
orig=[(43.2,43.2),(648,43.2),(648,691.2),(43.2,691.2)]; pp=[]
for i,xy in enumerate(orig):
 v=p['region_types'][i+1]['view'];add(f'u_pair{i}','pair',*xy,216,172.8,f'cp[{i}]',view=v);pp.append(pins(v['LEF'],xy))
macro='physical/asap7_memory_macros/ot_sram_1r1w2c_64x516_m1/ot_sram_1r1w2c_64x516_m1.lef'
ms=[[(43.2,259.2),(43.2,388.8),(259.2,259.2)],[(475.2,259.2),(691.2,259.2),(475.2,388.8)],[(475.2,518.4),(691.2,518.4),(691.2,388.8)],[(259.2,388.8),(43.2,561.6),(259.2,561.6)]]
wp=[[(259.2,349.92),(259.2,388.8),(345.6,349.92)],[(420,300),(500,300),(400,250)],[(610,410),(700,450),(740,280)],[(445,510),(380,650),(575,680)]]
qp=[[(220,300),(220,360),(350,300)],[(690,230),(740,250),(690,350)],[(680,650),(720,660),(740,650)],[(220,650),(220,700),(280,720)]]
mp=[]
for s in range(4):
 banks=[];w=1177 if s==0 else 1210
 for b in range(3):
  n=min(516,w-516*b);xy=ms[s][b];add(f'l{s}.g_bank[{b}].u_mem','SRAM',*xy,169.56,76.68,{'write':'ctl' if s==0 else f'cp[{s-1}]','read':f'cp[{s}]'},master='ot_sram_1r1w2c_64x516_m1',reset_owner=f'reset_leaf[{s}]');banks.append(pins(macro,xy))
  for side,xy,clock in [('d_pin',wp[s][b],'ctl' if s==0 else f'cp[{s-1}]'),('q_pin',qp[s][b],f'cp[{s}]')]:
   nn=n if not(s==3 and b==2 and side=='d_pin') else 145
   ww,hh=(32.4,10.8) if nn>180 else (21.6,8.64)
   add(f'l{s}.{side}[{516*b}+:{nn}]','FF_band',xy[0]-ww/2,xy[1]-hh/2,ww,hh,clock,flops=nn,reset='data unreset',placement='Reserved band; center endpoints audited, detailed cells not placed')
 mp.append(banks)
add('l3.d_pin[1177+:33]','FF_band',575-5.4,700-2.16,10.8,4.32,'cp[2]',flops=33,reset='data unreset')
add('CTL_local_control_reserve','control_reserve',43.2,475.2,172.8,32.4,'ctl',reset_owner='u_reset',notes='Actual pointer/reset/control reserve; incoming chunk payload anchor is center. Shared chunk glue is outside this column, not replicated here.')
add('CTL_return_readers','FF_band',421.2,480.6,21.6,10.8,'ctl',flops=37,reset_owner='reset_leaf[4:8]')
for i,xy in enumerate([(330,300),(620,350),(640,650),(345,650)]):
 add(f'lrdy{i}.writer_and_ring','FF_band',xy[0]-5.4,xy[1]-4.32,10.8,8.64,f'cp[{i}]',flops=8,reset_owner=f'reset_leaf[{5+i}]')
add('lret.writer_and_ring','FF_band',334.8,666.9,21.6,16.2,'cp[3]',flops=136,reset_owner='reset_leaf[4]')
checks=[]
def ck(n,a,b):checks.append(dict(net=n,from_um=a,to_um=b,manhattan_um=round(abs(a[0]-b[0])+abs(a[1]-b[1]),6)))
def wpoint(s,b,j):return (575,700) if s==3 and b==2 and j>=145 else wp[s][b]
for s in range(4):
 w=1177 if s==0 else 1210
 for bit in range(w):
  b,j=divmod(bit,516);d=wpoint(s,b,j);q=qp[s][b]
  ck(f'l{s}.d_pin[{bit}]->SRAM',d,mp[s][b][f'wd_in[{j}]']);ck(f'l{s}.SRAM->q_pin[{bit}]',mp[s][b][f'rd_out[{j}]'],q)
  if s==0:src=(129.6,491.4)
  elif bit<1177:src=qp[s-1][b]
  elif bit==1177:src=pp[s-1]['cf_out']
  else:src=pp[s-1][f'cs_out[{bit-1178}]']
  ck(f'l{s}.source[{bit}]->d_pin',src,d)
  pin=None
  if 16*s<=bit<16*s+16:pin=f'hid[{bit-16*s}]'
  elif 64<=bit<608:pin=f'key[{bit-64}]'
  elif 608<=bit<1176:pin=f'q_b[{bit-608}]'
  elif bit==1176:pin='qv_b'
  elif bit==1177:pin='cf_in'
  elif bit>=1178:pin=f'cs_in[{bit-1178}]'
  if pin and pin in pp[s]:ck(f'l{s}.q_pin[{bit}]->u_pair{s}.{pin}',q,pp[s][pin])
coll=[]
for i,a in enumerate(rect):
 for b in rect[i+1:]:
  if a['kind']=='control_reserve' or b['kind']=='control_reserve':continue
  dx=min(a['x_um']+a['width_um'],b['x_um']+b['width_um'])-max(a['x_um'],b['x_um']);dy=min(a['y_um']+a['height_um'],b['y_um']+b['height_um'])-max(a['y_um'],b['y_um'])
  if dx>1e-6 and dy>1e-6:coll.append([a['name'],b['name'],round(dx*dy,3)])
bad=sorted([c for c in checks if c['manhattan_um']>405],key=lambda c:-c['manhattan_um'])
result=dict(status='DIAGNOSTIC candidate geometry, not placed or CTS qualified',source_commit='08d38a78f',source_sha256=p['sha256'],scope='ONE actual column; 32 columns per quarter and 128 across four quarters',outline_um=[907.2,907.2],rectangles=rect,replication=p['replication'],clock_scope=p['clock_scope'],active_delta_edges=23,extra_die_hops='Not yet composed; price actual placement hops separately',reset_status='Baseline raw reset fails. Face-reset successor mechanism passed; physical qualification pending.',reach_audit=dict(kind='Exact LEF pin midpoint to reserved FF center, Manhattan only; not detailed-route timing or complete band-corner proof',net_count=len(checks),max_um=max(c['manhattan_um'] for c in checks),violations=bad,rectangle_overlaps=coll),source_bindings={x:hashlib.sha256((R/x).read_bytes()).hexdigest() for x in [macro,'rtl/hdc/v41x/ot_hbm_idx_col8_sram_landed.sv']},next='Resolve listed placement conflicts/reach violations before adoption; R3 exact CLOSED 32615a054; parent physical qualification remains open.')
(out/'column_geometry.json').write_text(json.dumps(result,indent=2)+'\n');(out/'column_geometry_paths.json').write_text(json.dumps(checks,indent=2)+'\n')
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 940 950">','<rect width="907.2" height="907.2" fill="white" stroke="black"/>']
for a in rect:
 color={'pair':'#9cbde0','SRAM':'#e1c88f','FF_band':'#9dc79d','control_reserve':'#d7b2ce'}[a['kind']];x,y,w,h=[a[k] for k in ['x_um','y_um','width_um','height_um']];svg.append(f'<rect x="{x}" y="{907.2-y-h}" width="{w}" height="{h}" fill="{color}" stroke="black" stroke-width="0.5"/><text x="{x}" y="{907.2-y-h+8}" font-size="7">{a["name"]}</text>')
svg.append('<text x="0" y="930" font-size="12">One column, 907.2 x 907.2 um. Diagnostic geometry. R3 exact CLOSED 32615a054; parent physical qualification remains open.</text></svg>');(out/'column_geometry.svg').write_text('\n'.join(svg))
print(json.dumps(result['reach_audit'],indent=2))
