#!/usr/bin/env python3
import importlib.util,json,re,sys,collections,gzip,hashlib
from pathlib import Path
s=importlib.util.spec_from_file_location('textbook','textbook_lint.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
net=Path('synth_c21j_r2/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base/1_2_yosys.v');mods=t.parse_verilog(net.read_text());g,top=t.flatten(mods,'dsdv_mu_hwin_capture_1019');A=t.build(g,None);clk,_=t.clock_nets(g,A)
areas=json.loads(Path('r2_master_areas.json').read_text());owners={};active=set()
def seed(ci):
 nm=g.cells[ci][1].replace('\\','')
 if '.start_r' in nm:return 'GLOBAL'
 m=re.search(r'g_event_(?:mem|broadcast)\[(\d+)\]',nm) or re.search(r'^u_ot_pr_core\.fd\[(\d+)\]',nm)
 return 'E'+m.group(1) if m else 'GLOBAL'
def leaves(ci):
 if ci in owners:return owners[ci]
 if ci in active:return {'GLOBAL'}
 if A['kind'][ci] in ('ff','macro'):owners[ci]={seed(ci)};return owners[ci]
 active.add(ci);out=set()
 for x in t._out_nets(g,A,ci):
  if A['out_ports'].get(x):out.add('GLOBAL')
  if x in clk:continue
  for li,_,_ in A['loads'].get(x,()):out.update(leaves(li))
 active.remove(ci);owners[ci]=out or {'GLOBAL'};return owners[ci]
# Original paid outline561.6x388.8; all SRAM positions remain unchanged.
fp=json.loads(Path('floorplan_c21h.json').read_text());evmac=collections.defaultdict(list)
for b in fp['blocks']:
 m=re.search(r'g_event_mem\?(\d+)\?',b['inst']) or re.search(r'g_event_mem\[(\d+)\]',b['inst'])
 if m:evmac[int(m.group(1))].append(b)
global_events=[];left=[];right=[]
for e,bs in evmac.items():
 if e in (6,7,8,9):global_events.append(e)
 elif sum(b['x'] for b in bs)/len(bs)<280:left.append(e)
 else:right.append(e)
left.sort();right.sort();boxes={'GLOBAL':[155.8,163.89,405.8,203.85]}
for es,x0,x1 in [(left,43.2,155.8),(right,405.8,518.4)]:
 for k,e in enumerate(es):boxes['E'+str(e)]=[x0+(x1-x0)*k/len(es),163.89,x0+(x1-x0)*(k+1)/len(es),203.85]
for e in global_events:boxes['E'+str(e)]=boxes['GLOBAL']
def region(owner):return 'GLOBAL' if owner in {'E'+str(e) for e in global_events} else owner
rows=[];hist=collections.defaultdict(lambda:dict(cells=0,area_um2=0));cell_group={}

for ci,(master,nm,pins) in enumerate(g.cells):
 if A['kind'][ci] in ('macro','phys'):continue
 o=leaves(ci);group=region(next(iter(o))) if len(o)==1 else 'GLOBAL';cell_group[ci]=group;area=areas[master]['area_um2'];hist[group]['cells']+=1;hist[group]['area_um2']+=area
 rows.append(dict(name=nm,master=master,group=group,area_um2=area))
native_rows=json.load(gzip.open('c21h_endpoint_roots.json.gz'));macro_xy={}
for nr in native_rows:
 for q in [nr['driver']]+nr['sinks']:
  if q['role']=='macro':
   x,y=q['xy'];macro_xy[q['pin'].replace('\\','')]=[x,y]
def term_box(ci,pn,bit=None):
 if A['kind'][ci]=='macro':
  nm=g.cells[ci][1].replace('\\','')+'/'+pn
  if bit is not None and len(g.cells[ci][2][pn])>1:nm+='['+str(bit)+']'
  if nm not in macro_xy:raise KeyError('missing native macro pin '+nm)
  x,y=macro_xy[nm];return[x,y,x,y]
 return boxes[cell_group[ci]]
def port_box(name,direction):
 # all port bundles remain width-identical; inputsS and outputsN share centre84.8um.
 return[238.4,0 if direction=='input' else 388.8,323.2,0 if direction=='input' else 388.8]
def distance(a,b):return max(abs(a[0]-b[2]),abs(a[2]-b[0]))+max(abs(a[1]-b[3]),abs(a[3]-b[1]))
bad=[];worst=0;checked=0
for x,d in A['driver'].items():
 if x<=3 or x in clk or (d[0]>=0 and A['kind'][d[0]] in ('tie','phys','buf')):continue
 if d[0]<0:db=port_box(d[1],'input')
 else:
  vals=g.cells[d[0]][2][d[1]];db=term_box(d[0],d[1],len(vals)-1-vals.index(x))
 stack=[x];seen=set()
 while stack:
  y=stack.pop()
  if y in seen:continue
  seen.add(y)
  for li,pn,bi in A['loads'].get(y,()):
   if A['kind'][li]=='buf':stack.extend(t._out_nets(g,A,li));continue
   sb=term_box(li,pn,bi);reach=distance(db,sb);checked+=1;worst=max(worst,reach)
   if reach>405.000001:bad.append(dict(driver=t.net_label(g,A,x),sink=g.cells[li][1]+'/'+pn,driver_box=db,sink_box=sb,reach_um=reach))
  for op in A['out_ports'].get(y,()):
   sb=port_box(op,'output');reach=distance(db,sb);checked+=1;worst=max(worst,reach)
   if reach>405.000001:bad.append(dict(driver=t.net_label(g,A,x),sink=op,driver_box=db,sink_box=sb,reach_um=reach))
for owner,h in hist.items():
 b=boxes[owner];h['box']=b;h['box_area_um2']=(b[2]-b[0])*(b[3]-b[1]);h['density']=h['area_um2']/h['box_area_um2']
result=dict(schema='opentallas.hwin_native_box_plan.v1',scope='source-bound conservative endpoint-box planning only; requires exact hard fences, regenerated pins, unchanged SRAM pin offsets and post-placement native verification; clock+constant/tie nets excluded from geometric bound; no physical qualification',netlist=str(net),groups=dict(hist),total_std_area_um2=sum(x['area_um2'] for x in rows),cells=rows,outline=[561.6,388.8],band=[2.16,163.89,559.44,203.85],global_events=global_events,event_left=left,event_right=right,boxes=boxes,pin_faces=dict(inputs='S',outputs='N'),pin_xrange=[238.4,323.2],paid_area_ratio=1.0,checked_endpoint_pairs=checked,planning_worst_um=worst,over405=bad,netlist_sha256=hashlib.sha256(net.read_bytes()).hexdigest())
Path('r2_thin_original_box_proof.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=1))
