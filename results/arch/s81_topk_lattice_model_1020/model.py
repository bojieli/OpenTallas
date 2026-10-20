import json,gzip,re,math,hashlib
from pathlib import Path
from collections import Counter
P=Path(__file__).parent
A=json.load(gzip.open(P/'actual_hk1l_3place_geometry.json.gz'))
boxes=[]
for a in A['macros']:
 n=a['name'].replace('\\','');r=a['box'];w=r[2]-r[0];h=r[3]-r[1];x,y=r[:2]
 if '.u_mem.g_b[' in n:
  b,k=map(int,re.search(r'g_b\[(\d+)\].g_w\[(\d+)\]',n).groups());x=388.8+b*129.6;y=43.2+k*86.4
 elif '.u_ofq.g_bank[' in n:
  k=int(re.search(r'g_bank\[(\d+)\]',n).group(1));x=[43.2,129.6,216,43.2,129.6][k];y=216 if k<3 else 259.2
 elif '.u_fq.g_bank[' in n:
  k=int(re.search(r'g_bank\[(\d+)\]',n).group(1));x=43.2+k*86.4;y=388.8
 faces=Counter(p['nearest_face'] for p in a['pins'])
 boxes.append(dict(name=n,master=a['master'],at=[x,y],size=[w,h],orient='R0',faces=dict(faces),pins=[dict(p,x=p['x']-r[0]+x,y=p['y']-r[1]+y) for p in a['pins']]))
viol=[];nonpin=[]
for a in boxes:
 x,y=a['at'];w,h=a['size']
 if any(abs(v/43.2-round(v/43.2))>1e-7 for v in [x,y]):viol.append(['LATTICE',a['name']])
 if x<0 or y<0 or x+w>648+1e-8 or y+h>648+1e-8:viol.append(['OUTLINE',a['name']])
 if min(y+h,367.2)>max(y,302.4)+1e-8:viol.append(['BAND_INTRUSION',a['name']])
 for f,margin in [('W',x),('E',648-x-w),('S',y),('N',648-y-h)]:
  if a['faces'].get(f,0) and margin<20-1e-8:viol.append(['PIN_EDGE',a['name'],f,margin])
 for f,c in a['faces'].items():
  density=c/(h if f in ['W','E'] else w)
  if density>6+1e-8:viol.append(['PIN_DENSITY',a['name'],f,density])
for i,a in enumerate(boxes):
 ax,ay=a['at'];aw,ah=a['size']
 for b in boxes[i+1:]:
  bx,by=b['at'];bw,bh=b['size'];ox=min(ax+aw,bx+bw)-max(ax,bx);oy=min(ay+ah,by+bh)-max(ay,by)
  if ox>1e-8 and oy>1e-8:viol.append(['OVERLAP',a['name'],b['name']]);continue
  if ox>0 and (ay+ah<=by or by+bh<=ay):
   low,high=(a,b) if ay<by else(b,a);gap=high['at'][1]-(low['at'][1]+low['size'][1]);facing=low['faces'].get('N',0)+high['faces'].get('S',0)
  elif oy>0 and (ax+aw<=bx or bx+bw<=ax):
   low,high=(a,b) if ax<bx else(b,a);gap=high['at'][0]-(low['at'][0]+low['size'][0]);facing=low['faces'].get('E',0)+high['faces'].get('W',0)
  else:continue
  if gap<20-1e-8:
   if facing:viol.append(['PIN_FACE_GAP',a['name'],b['name'],gap,facing])
   else:nonpin.append(dict(a=a['name'],b=b['name'],gap_um=gap,signal_pins_on_facing_faces=0,required='explicit placement+row blockage over nonpin gap; not an implicit warning exception'))
anchors={'coarse_W':[183.6,302.4],'fine_W':[183.6,367.2],'coarse_E_capture':[226.8,302.4],'fine_E_capture':[226.8,367.2],'common_packer':[270,334.8],'line_bank0_capture':[367.2,169.836],'line_bank1_capture':[496.8,169.836]}
reach={}
for side in ['coarse','fine']:
 for f,anchor in [('W',anchors[side+'_W']),('E',anchors[side+'_E_capture'])]:
  pins=[p for b in boxes if ('.u_hc.' in b['name'] if side=='coarse' else '.u_hf.' in b['name']) for p in b['pins'] if p['nearest_face']==f]
  reach[side+'_'+f+'_actual_native_pin_anchor']=max(abs(p['x']-anchor[0])+abs(p['y']-anchor[1]) for p in pins)
for bank in [0,1]:
 anchor=anchors['line_bank'+str(bank)+'_capture'];pins=[p for b in boxes if '.u_mem.g_b['+str(bank)+']' in b['name'] for p in b['pins']]
 reach['line'+str(bank)+'_native_pin_anchor']=max(abs(p['x']-anchor[0])+abs(p['y']-anchor[1]) for p in pins)
 reach['packer_to_line'+str(bank)+'_capture']=sum(abs(x-y) for x,y in zip(anchor,anchors['common_packer']))
for queue in ['u_fq','u_ofq']:
 pins=[p for b in boxes if '.'+queue+'.' in b['name'] for p in b['pins']]
 anchor=anchors['common_packer'];reach[queue+'_all_native_pin_common_anchor']=max(abs(p['x']-anchor[0])+abs(p['y']-anchor[1]) for p in pins)
for k,v in reach.items():
 if v>405:viol.append(['PLANNING_REACH',k,v])
area=sum(b['size'][0]*b['size'][1] for b in boxes);logical_std=sum(c['area'] for c in A['std_cells'] if not c['master'].startswith('TAPCELL'))
out=dict(status='MODEL_ONLY_NOT_READY_NO_KIT_NO_GATE',source='8dec8d8d5 exact actual hk1l3_place master dimensions/native pin geometry',shape=[648,648],band=[0,302.4,648,367.2],geometry_status='FAIL' if viol else 'PASS_FOR_MODELED_32_BOXES_ONLY',violations=viol,blocks=boxes,nonpin_gap_row_blockages=nonpin,anchors=anchors,planning_reach_um=reach,actual_old_logical_std_area=logical_std,logical_std_if_all_in_band=logical_std/(648*64.8),clock_growth_reserve_20percent_band_fill=logical_std*1.2/(648*64.8),effective_total_fill=(area+logical_std)/(648**2),delta_from_hk1=[129.6,0],delta_fulltopk_area_mm2=4*(648**2-518.4*648)/1e6,delta_from_old_release_fulltopk_area_mm2=4*(648**2-324*540)/1e6,data_edges_added_TARGET=0,data_edge_qualification='OPEN: criticalgroup nativepin anchors only; actual all-stage graph/IOlanding/replica/root/reset proof required. Any failed405stage must be pipelined and exactly repriced before gate.',reset_edges_added_TARGET=0,clock='UNRESOLVED: inherited split hardchild spine/K16 produced SRAM hold grind; coherent parent/hardchild/SRAM actual TT+FF both-edge phases required, no arc transplant',eligibility='NO parentdie adoption, no closed view, no timing/reach/PG/native release claim. 34percent totalfill is pin-limited tradeoff OPEN versus40..60 guideline, not silently waived.')
(P/'model.json').write_text(json.dumps(out,indent=2)+'\n')
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 730">','<rect width="700" height="730" fill="white"/>','<text x="20" y="24">MODEL ONLY 648 x 648: literal32 macro origins; clock/fullgraph OPEN</text>','<g transform="translate(20,690) scale(1,-1)">','<rect width="648" height="648" fill="#eef3fa" stroke="black"/>','<rect x="0" y="302.4" width="648" height="64.8" fill="#b8edca"/>']
for b in boxes:
 x,y=b['at'];w,h=b['size'];svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#a3aaba" stroke="#344"/>')
svg+=['</g>','</svg>'];(P/'model.svg').write_text('\n'.join(svg))
print(out['geometry_status'],len(viol),'reach',reach,'bandfill',out['logical_std_if_all_in_band'],'fill',out['effective_total_fill'])
