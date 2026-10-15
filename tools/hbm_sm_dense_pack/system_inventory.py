#!/usr/bin/env python3
"""Actionable canonical SM inventory; never substitutes planned tile foractualLEF."""
import pathlib,json,hashlib,re,math,collections
R=pathlib.Path('/home/ubuntu/wt/hbm-smcompact-1014');O=pathlib.Path('results/hbm_sm_dense_pack');cp=R/'results/arch/hbm_native_1013/sm/component.json';C=json.load(open(cp));G=json.load(open(O/'complete35.json'));B={b['name']:b for b in G['children']};children=[];P={};missing=[]
for c in C['children']:
 n=c['instance'];b=B[n];q={k:v for k,v in c.items() if k not in ['xy_um','w_um','h_um','orientation']};q.update(xy_um=[b['x'],b['y']],w_um=b['outline_um'][0],h_um=b['outline_um'][1],orientation=b['orient']);q['clock_roots']=[k for k in c['boundary_ports']if k in('clk','clock','clk_a')]
 if c['view_lef']:
  path=R/c['view_lef'];t=path.read_text();pp={}
  for pin,body in re.findall(r'  PIN (\S+)\n(.*?)  END \S+\n',t,re.S):
   m=re.search(r'RECT\s+(\S+) (\S+) (\S+) (\S+)',body)
   if not m:continue
   x0,y0,x1,y1=map(float,m.groups());x=(x0+x1)/2;y=(y0+y1)/2;w,h=q['w_um'],q['h_um'];o=q['orientation']
   if o in('MY','R180'):x=w-x
   if o in('MX','R180'):y=h-y
   pp[pin]={'local_center_um':[(x0+x1)/2,(y0+y1)/2],'global_center_um':[b['x']+x,b['y']+y],'layer':re.search(r'LAYER (\S+)',body)[1]}
  q['actual_pins']=pp;q['actual_lef_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();q['geometry_status']='ACTUAL_IMMUTABLE_LEF_AT_NEW_ORIGIN_UNQUALIFIED_SEAMS';P[n]=pp
 else:
  q['geometry_status']='PLANNED_TILE_NO_ACTUAL_PARENT_LEF';q['actual_pins']=None;q['planned_internal_manifest']='complete16.json';q['planned_boundary_manifest']='complete16.json output_boundary_pairs/input_receiver_pairs';missing.append(n)
 children.append(q)
edges=[]
for net in C['connections']:
 if net['kind']in('clock','reset'):continue
 ep=[e for e in net['endpoints']if e['instance']!='$boundary']
 if len(ep)<2:continue
 width=max(e['width']for e in ep);known=[];unknown=[]
 for e in ep:
  n=e['instance'];pin=e['port'] if e['width']==1 else f"{e['port']}[{e['lsb']}]"
  if n in P and pin in P[n]:known.append((n,e))
  else:unknown.append((n,e['port']))
 actual=[]
 if len(known)==len(ep):
  for bit in range(width):
   xy=[]
   for n,e in known:
    pin=e['port']if e['width']==1 else f"{e['port']}[{e['lsb']+bit}]"
    if pin not in P[n]:break
    xy.append(P[n][pin]['global_center_um'])
   if len(xy)==len(ep):actual.append(max(v[0]for v in xy)-min(v[0]for v in xy)+max(v[1]for v in xy)-min(v[1]for v in xy))
 center=[]
 for e in ep:
  b=B[e['instance']];center.append([b['x']+b['outline_um'][0]/2,b['y']+b['outline_um'][1]/2])
 center_dist=max(v[0]for v in center)-min(v[0]for v in center)+max(v[1]for v in center)-min(v[1]for v in center)
 edges.append({'net':net['net'],'kind':net['kind'],'width_bits':width,'endpoints':ep,'actual_pin_distance_max_um':max(actual)if actual else None,'actual_pin_distance_sum_um':sum(actual)if actual else None,'actual_over500_bit_count':sum(x>500for x in actual)if actual else None,'actual_minimum_additional_stages_at500um':max(0,math.ceil(max(actual)/500)-1)if actual else None,'center_distance_um_DIAGNOSTIC_ONLY':center_dist,'center_bitweighted_um_DIAGNOSTIC_ONLY':width*center_dist,'missing_actual_pin_endpoints':unknown,'qualification':'ACTUAL_LEF_PIN_GEOMETRY'if actual else 'NO_ACTUAL_TILE_PORTS_UNQUALIFIED'})
edges.sort(key=lambda e:e['actual_pin_distance_sum_um'] if e['actual_pin_distance_sum_um']is not None else e['center_bitweighted_um_DIAGNOSTIC_ONLY'],reverse=True)
out={'schema':'opentallas.hbm_sm.canonical_actual_inventory.v1','source_root':str(R),'source_component':str(cp.relative_to(R)),'source_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'source_commit':C['source_commit'],'canonical_complete35_geometry':'complete35.json','frame_outline_um':G['frame_outline_um'],'frame_area_mm2':G['frame_area_mm2'],'sm_replica_count':32,'all32_area_mm2':G['all32_sm_frame_area_mm2'],'actual_parent_LEFs':len(children)-len(missing),'missing_actual_tile_LEFs':missing,'children':children,'edges':edges,'top20_bitweighted_routes':edges[:20],'allowed_search_orientations':['R0','MX','MY','R180'],'rotation90_allowed':False,'qualification':'COMPLETE35_OUTLINE_GEOMETRY_ONLY_NOT_NATIVE_SM_OR_SEAM_CLOSURE','clock_roots_status':'19actualfront/BErootpins areexistingchildclocks.16plannedtilesdonotcountasclosedroots; eachneeds10compute+6transportplusrealparentclockpartition. No clockmask.','cuts_status':'No fullSM cutcertification: actualtileLEFs/PG/PORTs missing. Sourcecomplete16 modelsM8uppergrosscapacity only.','system_usage':'Can search32wholeSMoutlineplacements andpricedorientation candidates; actualSMportpins mustderivefromstaticnativefront+tilecontract beforeclaimedlegalreach.','preserve':'No source/service136/currentjob mutation orheavylaunch.'}
(O/'canonical_system_inventory.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps({k:out[k]for k in ['frame_outline_um','frame_area_mm2','all32_area_mm2','actual_parent_LEFs','qualification']},indent=2));print('top20 routes:')
for e in edges[:20]:print(e['net'],e['width_bits'],e['actual_pin_distance_max_um'],e['center_distance_um_DIAGNOSTIC_ONLY'],e['qualification'])
