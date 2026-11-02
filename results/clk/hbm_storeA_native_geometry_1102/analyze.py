import csv,json,collections,sys,hashlib
from pathlib import Path
R=Path.cwd();cells={};bterms={};inputs=collections.defaultdict(list);outputs=collections.defaultdict(list)
for x in csv.DictReader(open(R/'graph.tsv'),delimiter='\t'):
 x={k:sys.intern(v)for k,v in x.items()}
 if x['kind']=='BTERM':bterms[x['owner']]=x;continue
 c=cells.setdefault(x['owner'],dict(master=x['master'],mastertype=x['mastertype'],placement=x['placement'],xy_dbu=[int(x['x']),int(x['y'])],pins=[]));c['pins'].append((x['pin'],x['io'],x['signal'],x['net']))
for name,c in cells.items():
 c['kind']='macro'if c['mastertype']=='BLOCK'else'ff'if any(s=='CLOCK'and io=='INPUT'for p,io,s,n in c['pins'])else'comb'
 for pin,io,sig,net in c['pins']:
  if net:(outputs if io=='OUTPUT'else inputs)[net].append((name,pin,sig))
for name,b in bterms.items():
 if b['net']:(outputs if b['io']=='INPUT'else inputs)[b['net']].append(('@'+name,name,b['signal']))
ffs={n:c for n,c in cells.items()if c['kind']=='ff'};macros={n:c for n,c in cells.items()if c['kind']=='macro'};std=len(cells)-len(macros)
print('INVENTORY',std,len(ffs),len(macros),flush=True)
# Each query terminates at sequential/macro/ABI boundaries; combinational cell
# connectivity is conservative all-input/all-output reach, not timing arcs.
def frontier(net,direction):
 todo=[net];seen=set();ends=set();visited_comb=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  for owner,pin,sig in (outputs if direction=='up'else inputs).get(n,[]):
   if owner.startswith('@'):ends.add(('port',owner[1:],pin));continue
   c=cells[owner];kind=c['kind']
   if kind=='comb':
    if owner in visited_comb:continue
    visited_comb.add(owner)
    todo.extend(z for p,io,s,z in c['pins']if z and io==('INPUT'if direction=='up'else'OUTPUT')and s!='CLOCK')
   elif kind=='ff':
    if direction=='up' or pin=='D':ends.add(('ff',owner,pin))
   else:ends.add(('macro',owner,pin))
 return sorted(ends),len(visited_comb)
clock_input_nets={net for c in cells.values()for pin,io,sig,net in c['pins']if io=='INPUT'and sig=='CLOCK'}
roots=[]
for name,b in bterms.items():
 if b['io']=='INPUT'and b['net']in clock_input_nets:
  loads=inputs.get(b['net'],[]);roots.append(dict(port=name,net=b['net'],FF_CLK=[dict(inst=n,pin=p)for n,p,s in loads if n in ffs and s=='CLOCK'],macro_CLK=[dict(inst=n,pin=p,master=cells[n]['master'])for n,p,s in loads if n in macros and s=='CLOCK'],other_loads=[dict(inst=n,pin=p,sigtype=s)for n,p,s in loads if s!='CLOCK']))
report=[]
for i,(name,c)in enumerate(sorted(macros.items())):
 q=dict(instance=name,master=c['master'],placement=c['placement'],xy_dbu=c['xy_dbu'],clock_pins=[],pin_groups={})
 for pin,io,sig,net in c['pins']:
  if sig=='CLOCK':q['clock_pins'].append(dict(pin=pin,net=net,actual_input_ports=[n for n,b in bterms.items()if b['io']=='INPUT'and b['net']==net]));continue
  group=pin.split('[')[0];g=q['pin_groups'].setdefault(group,dict(direction=io,pins=[]))
  ends,count=frontier(net,'up'if io=='INPUT'else'down')
  g['pins'].append(dict(pin=pin,net=net,frontier=ends,combinational_cells_visited=count))
 for group,g in q['pin_groups'].items():
  g['frontier_union']=sorted({tuple(e)for p in g['pins']for e in p['frontier']});g['bit_count']=len(g['pins'])
 report.append(q);print('MACRO',i+1,name,[(k,len(v['frontier_union']))for k,v in q['pin_groups'].items()],flush=True)
 (R/'macro_progress.json').write_text(json.dumps(report,indent=2)+'\n')
# Native output FF frontier, suitable for grouping each real ABI output at floorplan.
abi=[]
for name,b in sorted(bterms.items()):
 if b['io']=='OUTPUT':
  ends,count=frontier(b['net'],'up');abi.append(dict(port=name,net=b['net'],frontier=ends,combinational_cells_visited=count))
(R/'clock_roots.json').write_text(json.dumps(roots,indent=2)+'\n');(R/'macro_ownership.json').write_text(json.dumps(report,indent=2)+'\n');(R/'output_capture_frontiers.json').write_text(json.dumps(abi,indent=2)+'\n')
freeze=json.load(open(R/'freeze.json'));actual=dict(std_cells=std,FF=len(ffs),SRAM=len(macros),ABI=len(bterms));expected=dict(std_cells=147354,FF=2914,SRAM=32,ABI=6040)
res=dict(status='PASS_SAVED_NATIVE_CONNECTIVITY_CENSUS'if actual==expected else'FAIL_NATIVE_INVENTORY_MISMATCH',module=freeze['module'],source_odb_sha256=(R/'source_odb.sha256').read_text().split()[0],source_odb=(R/'source_odb.sha256').read_text().split()[1],source_EQ='28ea41ddd actual0435 receipt; old0048 UNPROVEN unchanged',actual=actual,expected=expected,clock_roots=[dict(port=q['port'],net=q['net'],FF_CLK=len(q['FF_CLK']),macro_CLK=len(q['macro_CLK']),other_loads=len(q['other_loads']))for q in roots],placement_status_counts=dict(collections.Counter(c['placement']for c in cells.values())),macro_masters=dict(collections.Counter(c['master']for c in macros.values())),scope='saved native synth ODB direct clock roots and FF/SRAM/ABI combinational connectivity frontiers; logical floorplan neighborhoods only',holds=['No placement coordinates inferred from unplaced synth database','Connectivity through combinational cells is conservative structural reach, not Boolean sensitization/STA timing arcs','No new proof/PLACE/CTS/route/PG/timing/source/default activation'])
(R/'result.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res),flush=True)
