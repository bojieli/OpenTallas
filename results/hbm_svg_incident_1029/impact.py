"""Exact selected-source SVG per-bit endpoint impact; no plan edits or invented stations."""
import json,sys,hashlib,collections,math,re
from pathlib import Path
P,G,N,O=map(Path,sys.argv[1:]);O.mkdir(parents=True,exist_ok=True)
D=json.load(open(P/'die_plan.json'));A=json.load(open(G));new=json.load(open(N));types=D['partition_types'];parts={p['name']:p for p in D['partitions']};cache={};rows=[]
def pinmap(path):
 if path not in cache:cache[path]={p['name']:p for p in json.load(open(P/path))}
 return cache[path]
def hc(part,inst):
 pp=parts.get(part)
 if not pp:return None
 return next((h for h in types[pp['type']].get('hard_cores',[])if h['inst']==inst),None)
def xy(h,p):
 x,y=p['x'],p['y'];w,z=h['outline_um'];ori=h.get('orient','R0')
 if ori in ('MY','R180'):x=w-x
 if ori in ('MX','R180'):y=z-y
 assert ori in ('R0','MX','MY','R180'),ori
 return [x+h['origin_um'][0],y+h['origin_um'][1]]
def point(h,port,bit,revised=False):
 ps={p['name']:p for p in new}if revised and 'svc_sm_group' in h['module']else pinmap(h['pins_file'])
 p=ps.get(f'{port}[{bit}]')or(ps.get(port)if bit==0 else None)
 return xy(h,p)if p else None
for e in A['edges']:
 if not(e['src_path'].startswith('svg_')or e['dst_path'].startswith('svg_')):continue
 sh=hc(e['src_partition'],e['src_plan_instance']);dh=hc(e['dst_partition'],e['dst_plan_instance'])
 row={k:e[k]for k in ('src_path','src_partition','src_plan_instance','src_port','dst_path','dst_partition','dst_plan_instance','dst_port','width')};measure=[];missing=[]
 if sh is None or dh is None:row['status']='MISSING ACTUAL PEER SLOT';rows.append(row);continue
 if e['src_partition']!=e['dst_partition']:row['status']='CROSS-PARTITION - requires composed die transform';rows.append(row);continue
 for sb,db in e['bit_pairs']:
  a=point(sh,e['src_port'],sb);b=point(dh,e['dst_port'],db);an=point(sh,e['src_port'],sb,True);bn=point(dh,e['dst_port'],db,True)
  if None in (a,b,an,bn):missing.append([sb,db]);continue
  old=sum(abs(x-y)for x,y in zip(a,b));newlen=sum(abs(x-y)for x,y in zip(an,bn));measure.append((old,newlen,sb,db,a,b,an,bn))
 row.update(measured_bits=len(measure),missing_pin_bits=len(missing),missing_first=missing[:3])
 if measure:
  w=max(measure,key=lambda r:r[1]);row.update(status='PIN-ENDPOINT LOWER BOUND ONLY',old_max_um=round(max(x[0]for x in measure),6),new_max_um=round(w[1],6),new_min_um=round(min(x[1]for x in measure),6),new_bits_gt405=sum(x[1]>405+1e-6 for x in measure),max_bit_delta_um=round(max(x[1]-x[0]for x in measure),6),min_bit_delta_um=round(min(x[1]-x[0]for x in measure),6),worst_bit=dict(src=w[2],dst=w[3],old_src=w[4],old_dst=w[5],new_src=w[6],new_dst=w[7]),minimum_stations_lower_bound=max(0,math.ceil(w[1]/405)-1))
 rows.append(row)
packets=[r for r in rows if r['src_path'].startswith('svg_')and r['src_port']=='sm_packet']
stale=[]
for pn,p in parts.items():
 t=types[p['type']]
 for si,s in enumerate(t.get('internal_stations',[])):
  if 'sm_packet'in s.get('launch','')or'sm_packet'in s.get('capture',''):
   stale.append(dict(partition=pn,type=p['type'],index=si,launch=s.get('launch'),capture=s.get('capture'),from_um=s.get('from_um'),to_um=s.get('to_um'),station_count=len(s.get('regs_um',[])),bits=s.get('bits')))
report=dict(status='FAIL FOR ROUTE; actual source outputs need matching source-bound station paths',source_graph_sha256=hashlib.sha256(G.read_bytes()).hexdigest(),plan_sha256=hashlib.sha256((P/'die_plan.json').read_bytes()).hexdigest(),candidate_pins_sha256=hashlib.sha256(N.read_bytes()).hexdigest(),actual_packet_edges=len(packets),actual_packet_bits=sum(r['width']for r in packets),direct_packet_bits_gt405=sum(r.get('new_bits_gt405',0)for r in packets),incident_edge_groups=len(rows),incident_bit_pairs=sum(r['width']for r in rows),existing_sm_packet_station_rows=len(stale),existing_station_direction_wrong=sum('sm_packet'in r['capture']for r in stale),packet_edges=packets,all_incident=rows,stale_station_rows=stale,note='Exact actual bit mapping and orient-aware planned pin terminals, not routed RC/reach. Only SVG sm_packet pin coordinates changed; source/RTL/cycles/macros/clocks/reset/other6589pins are unchanged. The native source graph has sm_packet OUTPUT; all existing named station rows instead mark it CAPTURE. They cannot qualify these source paths. New South provider connections absent from this selected graph require new actual source census.')
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
for r in packets:print(r['src_path'],'->',r['dst_plan_instance'],'bits',r.get('measured_bits'),r.get('status'),'old/new max',r.get('old_max_um'),r.get('new_max_um'),'bad',r.get('new_bits_gt405'),'minstations',r.get('minimum_stations_lower_bound'))
print('allincident',len(rows),'bits',report['incident_bit_pairs'],'stale_sm_capture',len(stale))
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
f,aa=plt.subplots(1,2,figsize=(15,5))
for ax,pn in zip(aa,('NW_hub','NE_hub')):
 t=types[parts[pn]['type']]
 for h in t['hard_cores']:
  x,y=h['origin_um'];w,z=h['outline_um'];ax.add_patch(Rectangle((x,y),w,z,facecolor='lightgrey',edgecolor='grey',linewidth=.2,alpha=.5))
 for r in packets:
  if r['src_partition']!=pn or'worst_bit'not in r:continue
  a=r['worst_bit']['new_src'];b=r['worst_bit']['new_dst'];ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color='red',linewidth=1.4));ax.plot(*a,'ro');ax.plot(*b,'bo');ax.annotate(r['src_plan_instance'],a,fontsize=7);ax.annotate(r['dst_plan_instance'],b,fontsize=6)
 ax.set(xlim=(0,7500),ylim=(0,4350),aspect='equal',title=pn+' actual SVG output -> keybuf (direct FAIL)')
f.suptitle('Coherent pin spread fixes density; source-bound stations still missing / reversed\nEach arrow represents all1099 exact bits; no route/adoption claim');f.tight_layout();f.savefig(O/'incident_review.png',dpi=140)
