"""Conservative full-source cone-of-influence inventory; never a logic waiver."""
from pathlib import Path
import importlib.util,sys,json,re,hashlib
sp=importlib.util.spec_from_file_location('tl','textbook_lint.py');m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
g,_=m.flatten(m.parse_verilog(Path('resynth.v').read_text()),'qkd_hr_core_peer_n32');a=m.build(g,None)
i=json.load(open('protected_fence_inventory.json'));actual=set(i['eligible_FFs'])|set(i['protected_FFs']);macro={ci for ci,k in enumerate(a['kind'])if k=='macro'};assert len(macro)==3
source={name.replace('.','/'):ci for ci,(typ,name,pins)in enumerate(g.cells)if a['kind'][ci]=='ff'}
live=set(macro);todo=list(macro)
for port,(direction,n)in g.ports.items():
 if direction=='output':
  driver=a['driver'].get(n)
  if driver is not None and driver[0]>=0 and driver[0]not in live:live.add(driver[0]);todo.append(driver[0])
while todo:
 ci=todo.pop()
 for pn,bs in g.cells[ci][2].items():
  if a['pin_dir'][ci][pn]!='in':continue
  for n in bs:
   z=a['driver'].get(n)
   if z is not None and z[0]>=0 and z[0]not in live:live.add(z[0]);todo.append(z[0])
missing=set(source)-actual;dead={n for n,ci in source.items()if ci not in live};missing_live=missing-dead;present_dead=dead&actual
og,_=m.flatten(m.parse_verilog(Path('original.v').read_text()),None)
rows=[]
for n in sorted(missing):
 hit=re.fullmatch(r'u(\d+)_c(\d+)/u_cell',n);assert hit;oi,k=map(int,hit.groups());rows.append({'source_instance':n,'original':og.cells[oi][1],'source_master':g.cells[source[n]][0],'source_dead_by_full_cone':n in dead})
r={'schema':'peer.fullsource_FF_liveness_inventory.v1','source_mapped_sha256':hashlib.sha256(Path('resynth.v').read_bytes()).hexdigest(),'actual_odb_sha256':i['odb_sha256'],'status':'PASS_ALL_MISSING_SOURCE_FF_DEAD' if not missing_live else 'OPEN_MISSING_LIVE_FF','scope':'Conservative whole-source structural cone: all top outputs and all singleton macros are roots; traverse every actual input dependency including FF data/async/clock. No constant sensitization pruning, no equivalence alias or reset waiver. Does not establish actual pin correspondence for retained cells.','source_FF':len(source),'actual_FF':len(actual),'missing':len(missing),'missing_live':sorted(missing_live),'source_dead':len(dead),'present_dead':sorted(present_dead),'missing_rows':rows,'macro_roots':3}
Path('fullsource_FF_liveness.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items()if k!='missing_rows'})
