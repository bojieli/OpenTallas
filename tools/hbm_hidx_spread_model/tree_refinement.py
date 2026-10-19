"""Read-only native-pin tree/corner-cap refinement of FROZEN model site plan.
No coordinates, source graph, boundary load or clock budget are changed.
"""
import json,gzip,hashlib,collections,re,sys,math
from pathlib import Path
import strict_contract as S
P=Path('/work');O=P/'out';native=json.load(gzip.open(P/'input/native_pin_geometry.json.gz','rt'));old=json.loads((P/'input/positions.json').read_text());plan=json.load(gzip.open(O/'site_plan.json.gz','rt'));caps=json.load(gzip.open(P/'input/loaded_caps.json.gz','rt'));domains=json.loads((P/'input/native_arc_domains.json').read_text());u=native['units']
before=hashlib.sha256((O/'site_plan.json.gz').read_bytes()).hexdigest();cells=old['insts'];byname={p['canonical_cell']:p['cell'] for p in native['pins']};contacts={(p['canonical_cell'],p['pin']):p for p in native['pins']};ports={p['port']:p for p in native['ports']};clocknets={p['net'] for p in native['pins'] if p['role']=='CLOCK'}
for net in caps['all_driver_nets']:
 drv=net['driver']
 if drv['cell'] is None and drv['pin'] not in ports:
  ids={contacts[c['cell'],c['pin']]['net'] for c in net['contacts']};assert ids==clocknets and len(net['contacts'])==2904
  actual=[p for p in native['ports'] if p['net'] in ids];assert len(actual)==1;ports[drv['pin']]=actual[0]
def center(shapes):
 _,b=max(shapes,key=lambda z:((z[1][2]-z[1][0])*(z[1][3]-z[1][1]),z[0],z[1]));return ((b[0]+b[2])/2/u,(b[1]+b[3])/2/u)
def point(c,p):
 if c is None:return center(ports[p]['shapes'])
 q=center(contacts[c,p]['shapes']);oc=cells[byname[c]];nc=plan[byname[c]];ob=oc['bbox'];nb=nc['bbox_dbu'];dx=(nb[0]-ob[0])/u
 return (q[0]+dx,q[1]+(nb[1]-ob[1])/u) if oc['orient']==nc['orient'] else (q[0]+dx,(nb[1]+nb[3])/2/u-(q[1]-(ob[1]+ob[3])/2/u))
libraries={};libfacts={};maxcaps={};native_domains={};used={c['master'] for c in plan.values()}|{'BUFx24_ASAP7_75t_R'}
def blocks(text,kind):
 for z in re.finditer(r'\b'+kind+r'\s*\(\s*([^)]*)\)\s*\{',text):
  a=text.index('{',z.start());i=a+1;depth=1
  while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
  yield z[1].strip('" '),text[a+1:i-1]
for corner in ['TT','FF']:
 files=[Path(line.split()[1]) for line in (P/'kit/lib_SHA256SUMS').read_text().splitlines() if '_RVT_'+corner+'_' in line];assert len(files)==5
 libraries[corner]=S.native_cells(files,used_masters=used);assert set(libraries[corner])==used
 seq=[f for f in files if '_SEQ_' in f.name];assert len(seq)==1;text=S._read_text(seq[0]);templates=dict(blocks(text,'lu_table_template'))
 cell=dict(blocks(text,'cell'))['DFFHQNx1_ASAP7_75t_R'];pin=dict(blocks(cell,'pin'))['QN'];drows=[]
 for _,timing in blocks(pin,'timing'):
  for typ in ['cell_rise','cell_fall']:
   for template,table in blocks(timing,typ):
    body=templates[template];roles={str(i):re.search(r'variable_'+str(i)+r'\s*:\s*([^;]+)',body)[1].strip('" ') for i in [1,2]}
    axes={str(i):list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',re.search(r'index_'+str(i)+r'\s*\((.*?)\)\s*;',table,re.S)[1]))) for i in [1,2]}
    assert roles=={'1':'input_net_transition','2':'total_output_net_capacitance'}
    drows.append(dict(type=typ,template=template,axis_roles=roles,axes=axes,native_source=str(seq[0]),native_sha256=hashlib.sha256(seq[0].read_bytes()).hexdigest(),template_body_sha256=hashlib.sha256(body.encode()).hexdigest()))
 assert len(drows)==2;native_domains[corner]=drows

 libfacts[corner]=[dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files]
 maxcaps[corner]={}
 for f in files:
  parsed=S._parse_groups(S._strip_heavy(S._read_text(f)))
  for kind,args,lib in parsed['groups']:
   if kind!='library':continue
   for ck,ca,cell in lib['groups']:
    if ck!='cell' or ca[0] not in used:continue
    for pk,pa,pin in cell['groups']:
     if pk=='pin' and 'max_capacitance' in pin['attrs']:maxcaps[corner][ca[0],pa[0]]=float(pin['attrs']['max_capacitance'])
def cap(master,pin,corner):
 p=libraries[corner][master]['pins'][pin];assert p['capacitance_unit']==['1','ff'],p['capacitance_unit'];return float(p['native_capacitance']['capacitance'])
def mst(points):
 n=len(points);chosen={0};remaining=set(range(1,n));edges=[]
 while remaining:
  d,a,b=min((abs(points[a][0]-points[b][0])+abs(points[a][1]-points[b][1]),a,b) for a in chosen for b in remaining)
  edges.append((a,b,d));chosen.add(b);remaining.remove(b)
 return edges
ledger=[];ffrows=[];hsegments=[];vsegments=[]
for ni,net in enumerate(caps['all_driver_nets']):
 drv=net['driver'];cs=net['contacts']
 if drv['cell'] is None and ports[drv['pin']]['net'] in clocknets:continue
 points=[point(drv['cell'],drv['pin'])]+[point(c['cell'],c['pin']) for c in cs];edges=mst(points);length=sum(d for a,b,d in edges)
 dist={0:0.};adj=collections.defaultdict(list)
 for a,b,d in edges:adj[a].append((b,d));adj[b].append((a,d))
 stack=[0]
 while stack:
  a=stack.pop()
  for b,d in adj[a]:
   if b not in dist:dist[b]=dist[a]+d;stack.append(b)
 records=[drv]+cs;cornercaps={}
 for corner in ['TT','FF']:
  base=sum(cap(c['master'],c['pin'],corner) if c['cell'] is not None else 80. for c in cs)
  if corner=='TT':assert abs(base-net['cap_ff'])<1e-8
  cornercaps[corner]=dict(native_plus_external_fF=base,nominal_RMST_wire_fF=length*.165790,total_model_fF=base+length*.165790)
 row=dict(driver=drv,native_max_cap_fF={c:maxcaps[c].get((drv['master'],drv['pin'])) for c in ['TT','FF']},access_points_um=points,RMST_edges=edges,RMST_length_um=length,max_tree_root_path_um=max(dist.values()),corner_cap=cornercaps)
 ledger.append(row)
 if (drv['master'] or '').startswith('DFF'):
  limits={}
  for corner in ['TT','FF']:
   assert drv['master']=='DFFHQNx1_ASAP7_75t_R' and drv['pin']=='QN';tables=native_domains[corner]
   ranges=[]
   for t in tables:
    axis=[k for k,role in t['axis_roles'].items() if role=='total_output_net_capacitance'];assert len(axis)==1;ranges.append([min(t['axes'][axis[0]]),max(t['axes'][axis[0]])])
   lo=max(a for a,b in ranges);hi=min(b for a,b in ranges);value=cornercaps[corner]['total_model_fF'];limits[corner]=dict(load_axis_fF=[lo,hi],load_model_fF=value,in_table=lo<=value<=hi,missing_native_wire_or_pin_cap_to_table_fF=max(0,lo-value),actual_clock_slew='UNQUALIFIED: no CTS; this table check does not qualify CQ or hold')
  ffrows.append(dict(driver=drv,corners=limits))
 # Concrete unobstructed M3(vertical)/M4(horizontal) tree construction. Boundary
 # W/E legs turn at real port Y; N/S legs turn at real port X. Access/vias OPEN.
 for a,b,d in edges:
  x0,y0=points[a];x1,y1=points[b];port=None;pi=None
  if records[a]['cell'] is None:port=records[a]['pin'];pi=a
  elif records[b]['cell'] is None:port=records[b]['pin'];pi=b
  if port is not None:
   bx,by=point(None,port)
   if abs(bx)<.1 or abs(bx-140.4)<.1:
    # horizontal leg ends at the actual W/E face; vertical is at internal X.
    ix,iy=points[b if pi==a else a];hsegments.append((ni,by,min(ix,bx),max(ix,bx)));vsegments.append((ni,ix,min(iy,by),max(iy,by)))
   else:
    ix,iy=points[b if pi==a else a];hsegments.append((ni,iy,min(ix,bx),max(ix,bx)));vsegments.append((ni,bx,min(iy,by),max(iy,by)))
  else:hsegments.append((ni,y0,min(x0,x1),max(x0,x1)));vsegments.append((ni,x1,min(y0,y1),max(y0,y1)))
def union_segments(segments):
 by=collections.defaultdict(list)
 for ni,c,a,b in segments:
  if b>a:by[ni,c].append((a,b))
 result=[]
 for (ni,c),pairs in by.items():
  pairs.sort();a,b=pairs[0]
  for x,y in pairs[1:]:
   if x<=b:b=max(b,y)
   else:result.append((ni,c,a,b));a,b=x,y
  result.append((ni,c,a,b))
 return result
hsegments=union_segments(hsegments);vsegments=union_segments(vsegments)
def peak(segments,band=False):
 events=[]
 for ni,c,a,b in segments:
  if band and not 56.16<=c<=84.24:continue
  events.extend([(a,1),(b,-1)])
 active=0;best=(0,None)
 for x,group in itertools_group(events):
  active+=sum(v for _,v in group)
  if active>best[0]:best=(active,x)
 return dict(max_segment_crossings=best[0],cut_um=best[1])
def itertools_group(events):
 import itertools
 return itertools.groupby(sorted(events),key=lambda z:z[0])
summary=dict(scope='READONLY refinement of frozen SOURCE MODEL; same coordinates/source/load/edge counts, no physical engine',site_plan_sha256=before,nets=len(ledger),topology='Native-pin rectilinear MST plus explicit unobstructed M3V/M4H doglegs; shared collinear same-net segments unioned. Real track assignment, PG avoidance, pin access, vias and extracted timing remain OPEN.',corners={},FF_CQ_domain=dict(total=len(ffrows),TT_outside=[r for r in ffrows if not r['corners']['TT']['in_table']],FF_outside=[r for r in ffrows if not r['corners']['FF']['in_table']],scope='All2904 FF native load-axis checks with actual corner pin caps and nominal wire model. No early-CQ or hold guarantee.'),clock={},cuts=dict(M4_full=peak(hsegments),M4_inside_band=peak(hsegments,True),M3_full=peak(vsegments),gross_M4_tracks_full_face=2925,gross_M4_tracks_core=2835,gross_M4_tracks_inside_band=585,gross_M3_tracks_full_face=2925,gross_M3_tracks_core=2835,scope='Gross pitch-only capacities before real PG/cell blockage/spacing/access, not a routability PASS'),native_libraries=libfacts,actual_native_CQ_domains=native_domains,original_merged_TT_unbound_axis_receipt_tables=sum(t['axis_roles'] is None for a in domains['corners']['TT']['arcs'] if a['master']=='DFFHQNx1_ASAP7_75t_R' and a['pin']=='QN' for t in a['tables'] if t['type'] in ['cell_rise','cell_fall']))
for corner in ['TT','FF']:
 summary['corners'][corner]=dict(total_RMST_length_um=sum(r['RMST_length_um'] for r in ledger),max_tree_root_path_um=max(r['max_tree_root_path_um'] for r in ledger),cap_over_limit=[r for r in ledger if r['native_max_cap_fF'][corner] and r['corner_cap'][corner]['total_model_fF']>r['native_max_cap_fF'][corner]])
 sink=sum(cap('DFFHQNx1_ASAP7_75t_R','CLK',corner) for _ in range(2904));extra=265*cap('BUFx24_ASAP7_75t_R','A',corner);summary['clock'][corner]=dict(real_sink_input_cap_fF=sink,budget265_BUFx24_input_cap_fF=extra,total_model_input_cap_before_wire_fF=sink+extra,clock_wire='UNIMPLEMENTED; no actual tree/clock slew/spread')
assert len(ffrows)==2904
assert hashlib.sha256((O/'site_plan.json.gz').read_bytes()).hexdigest()==before
(O/'WIRE_REFINEMENT.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(O/'native_RMST_tree_ledger.json.gz','wt') as f:json.dump(ledger,f,separators=(',',':'))
with gzip.open(O/'all_FF_CQ_domain_ledger.json.gz','wt') as f:json.dump(ffrows,f,separators=(',',':'))
print(json.dumps(dict(nets=len(ledger),corners={c:{k:(len(v) if k=='cap_over_limit' else v) for k,v in r.items()} for c,r in summary['corners'].items()},TT_outside=len(summary['FF_CQ_domain']['TT_outside']),FF_outside=len(summary['FF_CQ_domain']['FF_outside']),cuts=summary['cuts'],clock=summary['clock'])))
