"""Conditional geometry projection only; never writes source or a physical ODB."""
from pathlib import Path
import json,collections
import geom_rules as G
R=Path(__file__).resolve().parent;D=G.Design(R/'complete_model.tsv')
manifest=json.loads((R/'complete_clock_reset_manifest.json').read_text())
assert manifest['parent_boot_START_join']=='HELD'
names={c[-1]:i for i,c in D.cells.items()};seen=set();changed=[]
for row in manifest['reset_direct_eligible']:
 cap=names[row['target']];n=row['input_net_index'];key=(cap,n)
 if key in seen:continue
 seen.add(key)
 old,new=row['old'],row['new']
 assert old['clock']==new['clock']=='clk' and old['root']==new['root']=='rst_root_n' and old['depth']==new['depth']==7
 if old['name']==new['name']:continue
 sig,drv,sinks=D.nets[n];refs=[s for s in sinks if s[0]=='i' and s[1]==cap and not s[2]]
 assert refs,(row,n)
 D.nets[n]=(sig,drv,[s for s in sinks if s not in refs])
 j=names[new['name']];D.nets.append((sig,('i',j,False),refs))
 changed.append(dict(target=row['target'],old=old['name'],new=new['name'],old_input_net=n,input_refs=len(refs),retained_INV_parity=row['actual_buffer_INV_parity'],new_reach_um=row['new_reach_um']))
D.drives=collections.defaultdict(list);D.cell_in=collections.defaultdict(list)
for n,(_sig,drv,sinks) in enumerate(D.nets):
 if drv and drv[0]=='i':D.drives[drv[1]].append(n)
 for s in sinks:
  if s[0]=='i':D.cell_in[s[1]].append((n,s[2]))
bad=[];m=G.r2r_metrics(D,capture_pairs=bad)
out=dict(scope='CONDITIONAL GEOMETRY MODEL ONLY. Real terminal FF endpoints replace only source-qualified direct BUF/INV reset cones. No cells, stages, source, ODB or clock edges added/changed. Parent boot/START join still HELD; raw11reset failures retained in complete_footprint_proposal.json. These numbers are NOT physical signoff or an applied reset repair.',parent_boot_START_join='HELD',projected_metrics=m,projected_bad_pairs=bad,proposed_terminal_connections=changed)
(R/'conditional_reset_projection.json').write_text(json.dumps(out,indent=2));print('conditional projection',m,'changed inputs',len(changed))
