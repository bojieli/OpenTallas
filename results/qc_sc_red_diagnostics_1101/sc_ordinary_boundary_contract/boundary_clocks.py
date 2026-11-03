import sys,json,collections
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
D=g.Design('/srv/opentallas-scratch/claude/codex-sc49-actual-review-0441/sc_batch_buffer_geometry.tsv')
def clkroots(cid):
 todo=[n for n,ck in D.cell_in[cid] if ck];seen=set(todo);roots=set();bad=[]
 while todo:
  n=todo.pop();r=D.nets[n][1]
  if not r:bad.append('undriven');continue
  if r[0]=='p':roots.add(D.pin_by_k[r[1]]['name']);continue
  c=r[1]
  if D.cells[c][0] not in 'BK':bad.append(D.cells[c][6]);continue
  for ni,ck in D.cell_in.get(c,[]):
   if ni not in seen:seen.add(ni);todo.append(ni)
 return sorted(roots),bad
rows=[];unique=set()
for p in D.pins:
 if p['sig'] in ['POWER','GROUND']or p['name']=='ck':continue
 n=D.pin_net.get(p['k']);todo=[n];seen={n};caps=set();leaks=[]
 while todo:
  net=todo.pop()
  endpoints=D.nets[net][2] if p['io']=='INPUT'else[D.nets[net][1]]
  for s in endpoints:
   if not s:leaks.append('undriven');continue
   if s[0]=='p':leaks.append(D.pin_by_k[s[1]]['name']);continue
   if s[2]:continue
   c=s[1];k=D.cells[c][0]
   if k=='S':caps.add(c);continue
   if k!='B':leaks.append(D.cells[c][6]);continue
   ns=D.drives.get(c,[]) if p['io']=='INPUT'else[ni for ni,ck in D.cell_in.get(c,[])if not ck]
   for ni in ns:
    if ni not in seen:seen.add(ni);todo.append(ni)
 fs=[]
 for c in sorted(caps):
  roots,bad=clkroots(c);assert roots==['ck']and not bad,(D.cells[c][6],roots,bad)
  fs.append({'instance':D.cells[c][6],'master':D.cells[c][1],'clock_roots':roots,'clock_family':'clk','xy_um':list(g.ctr(D.cells[c]))});unique.add(c)
 rows.append({'pin':p['name'],'io':p['io'],'boundary_registers':fs,'other_first_endpoints':leaks,'SDC_external_clock':'vclk','SDC_internal_boundary_clock':'clk','contract_authority':'UNQUALIFIED_STANDALONE_RECIPE_FRAME_NOT_PARENT_MEASUREMENT'})
out={'scope':'Read-only exact actual SC49 first directional BUF/INV boundary registers and native clock root graph. No STA/CAD.','signal_bits_excluding_ck':len(rows),'unique_boundary_registers':len(unique),'rows_with_no_capture':sum(not r['boundary_registers']for r in rows),'other_first_endpoints':sum(len(r['other_first_endpoints'])for r in rows),'boundary_cardinality_histogram':dict(collections.Counter(len(r['boundary_registers'])for r in rows)),'all_observed_boundary_clock_roots':['ck'],'STA_named_clock_family':'clk','external_virtual_clock':'vclk','rows':rows}
Path(__file__).with_name('boundary_clocks.json').write_text(json.dumps(out,indent=1)+'\n')
print({k:v for k,v in out.items()if k!='rows'});print([(r['pin'],len(r['boundary_registers']))for r in rows if len(r['boundary_registers'])!=1])
