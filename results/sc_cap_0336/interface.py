from pathlib import Path
import json,re,hashlib
b=Path('/srv/opentallas-scratch2/claude/codex-sc-cap-0336');i=b/'input';leaf=(i/'qfd_dv_s5_sc2_leaf.sv').read_text();bound=(i/'qfd_qc_sle_sc__sle_sc_v2.sv').read_text();ports=[]
for direction,hi,name in re.findall(r'^\s*(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)\s*[,\n]',leaf,re.M):ports.append(dict(name=name,direction=direction,bits=int(hi)+1 if hi else 1))
connections={m[0]:m[1] for m in re.findall(r'^\s*\.(\w+)\((.*)\),?\s*$',bound.split('qfd_dv_s5_sc2_leaf u_core (',1)[1].split('\n    );',1)[0],re.M)}
for p in ports:p['parent_net']=connections.get(p['name'])
assert sum(p['bits'] for p in ports)==572
(i/'port_interface.json').write_text(json.dumps(dict(total_bits=572,input_bits=sum(p['bits'] for p in ports if p['direction']=='input'),output_bits=sum(p['bits'] for p in ports if p['direction']=='output'),clock='ck=clk',reset='rst_n=rst_n (existing mission reset, unchanged)',ports=ports),indent=2)+'\n')
bands=[]
for prefix,rect,tag in re.findall(r'^\s*\{([^\s]+)\s+\{([^}]+)\}\s+([^}]+)\}',(i/'landing_placement.tcl').read_text().split('set cland_status',1)[0],re.M):
 try:r=list(map(float,rect.split()))
 except ValueError:continue
 if len(r)==4:bands.append(dict(prefix=prefix,rect_um=r,role=tag))
ps=json.load(open(i/'pins.json'));lookup={(p['bus'],p['bit']):p for p in ps};slots=json.load(open(i/'land_slots.json'))['buses'];targets=[]
def zroute(a,z,fi,fo):
 ax,ay=a;bx,by=z
 if abs(ax-bx)<1 or abs(ay-by)<1:return[a,z]
 if (fi in 'EW')!=(fo in 'EW'):return[a,(bx,ay),z] if fi in 'EW' else[a,(ax,by),z]
 return[a,((ax+bx)/2,ay),((ax+bx)/2,by),z] if fi in 'EW' else[a,(ax,(ay+by)/2),(bx,(ay+by)/2),z]
def at(points,t):
 for a,z in zip(points,points[1:]):
  d=sum(abs(x-y) for x,y in zip(a,z))
  if t<=d:return[a[q]+(0 if d==0 else t/d)*(z[q]-a[q]) for q in [0,1]]
  t-=d
 return list(points[-1])
for line in (i/'ft_stations.txt').read_text().splitlines():
 if line.startswith('#') or not line.strip():continue
 n,k,fi,fo=line.split()[:4];k=int(k);bits=sorted(p['bit'] for p in ps if p['bus']==n+'_i');landed=n+'_i' in slots
 stage_points={j:[] for j in range(k)}
 for bit in bits:
  a=lookup[(n+'_i',bit)];z=lookup.get((n+'_o',bit))
  if z is None:continue
  route=zroute((a['x'],a['y']),(z['x'],z['y']),fi,fo);length=sum(sum(abs(x-y) for x,y in zip(a,z)) for a,z in zip(route,route[1:]))
  for j in range(k):stage_points[j].append(at(route,length*((j+1) if landed else j)/k))
 rows=[]
 for j,xy in stage_points.items():
  if xy:rows.append(dict(stage=j,bit_count=len(xy),ideal_bbox_um=[round(min(q[0] for q in xy),3),round(min(q[1] for q in xy),3),round(max(q[0] for q in xy),3),round(max(q[1] for q in xy),3)]))
 targets.append(dict(slot=n,stations=k,in_face=fi,out_face=fo,landed=landed,stages=rows))
(i/'reserved_corridors.json').write_text(json.dumps(dict(scope='MODEL targets from actual generated hook and pin table, NOT actual FIRM/DPL footprints; parent CAP_HOLD is before floorplan',parent_outline_um=[613.44,1339.2],landing_groups=bands,ft_target_envelopes=targets,actual_FIRM_available=False,footprint_limitation='row/site legalization, TAP occupancy and actual FF body widths must be included before placing a child; target boxes are not keepout clearance'),indent=2)+'\n')
# Actual public interface face spans, retaining all bits and layers.
groups={}
for p in ps:
 k=p['bus'];g=groups.setdefault(k,dict(bus=k,bits=0,faces=set(),layers=set(),xmin=1e30,ymin=1e30,xmax=-1e30,ymax=-1e30));g['bits']+=1;g['faces'].add(p['face']);g['layers'].add(p['layer']);g['xmin']=min(g['xmin'],p['x']);g['xmax']=max(g['xmax'],p['x']);g['ymin']=min(g['ymin'],p['y']);g['ymax']=max(g['ymax'],p['y'])
for g in groups.values():g['faces']=sorted(g['faces']);g['layers']=sorted(g['layers'])
(i/'public_faces.json').write_text(json.dumps(dict(scope='actual generated pins.json payload/epoch public bus face/layer spans, unchanged',buses=list(groups.values())),indent=2)+'\n')
print('CHILD_PORTS',len(ports),'BITS',sum(p['bits'] for p in ports),'IN',sum(p['bits'] for p in ports if p['direction']=='input'),'OUT',sum(p['bits'] for p in ports if p['direction']=='output'),'GROUPS',len(bands),'FT',len(targets))
