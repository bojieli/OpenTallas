"""Realize declared scalar clock entries; preserve every port identity. Model-only until native bind + gates."""
import json,sys,pathlib,collections,re,hashlib
pd=pathlib.Path(sys.argv[1]);d=json.loads((pd/'die_plan.json').read_text());es=json.loads((pd/'clock_entries.json').read_text());by=collections.defaultdict(list);rep={'changed':[],'unresolved':[],'hcol_contract':'ef994fe77: scorer clk_hslice={256{clk}}; preserve clk_pair[0:1] ports, no bus collapse'}
for tn,t in d['partition_types'].items():
 for hc in t.get('hard_cores',[]):
  if hc.get('pins_file'):by[hc['pins_file']].append((tn,hc,es.get(tn,{}).get(hc['inst'])))
def pname(p):return p.get('name') or (str(p['bus'])+'['+str(p.get('bit',0))+']')
for pf,items in by.items():
 vals=[e for tn,h,e in items if e]
 if not vals:continue
 entry=vals[0];xy=entry['xy_um'];names=entry.get('merged_clock_ports') or ([entry.get('port')] if entry.get('port') else [])
 hcol=items[0][1]['module'] in ['ot_hbm_idx_score_hcol_h0','ot_hbm_idx_score_hcol_h1']
 if hcol:names=['clk_pair[0]','clk_pair[1]']
 if not names:continue
 table=json.loads((pd/pf).read_text());pins=table.get('pins',table) if isinstance(table,dict) else table;byname={pname(p):p for p in pins}
 for n in names:
  if n not in byname:
   matching=[p for p in pins if re.sub(r'\[\d+\]$','',pname(p))==n]
   if len(matching)==1:byname[n]=matching[0]
 if any(n not in byname for n in names):
  rep['unresolved'].append(dict(table=pf,ports=names,reason='base bus requires explicit same-domain bit contract; no automatic collapse'));continue
 if any(e['xy_um']!=xy for e in vals):raise ValueError(('one view has differing entry points',pf))
 for i,n in enumerate(names):
  p=byname[n];old=dict(p);x=round(.024+.048*round((xy[0]+(i-(len(names)-1)/2)*.096-.024)/.048),6);p.update(x=x,y=xy[1],layer='M5')
  if p!=old:rep['changed'].append(dict(table=pf,pin=n,old=old,new=dict(p)))
 if hcol:
  # Actual native outputs; move partial sums towards the next chunk, keep inputs on the N edge.
  outputs=[p for p in pins if re.sub(r'\[\d+\]$','',pname(p)) in ('cs_out','cf_out','prdy')]
  assert len(outputs)==35,(pf,len(outputs))
  w,h=items[0][1]['outline_um']
  outputs.sort(key=lambda p: (['cs_out','cf_out','prdy'].index(re.sub(r'\[\d+\]$','',pname(p))),int(re.search(r'\[(\d+)\]$',pname(p))[1]) if '[' in pname(p) else 0))
  for i,p in enumerate(outputs):p.update(x=w-.019,y=8.64+(h-17.28)*(i+.5)/len(outputs),layer='M4')
  for tn,hc,e in items:
   if e:e.update(port=None,merged_clock_ports=names,clock_bind_contract='one source domain ef994fe77, both separate ports preserved')
 (pd/pf).write_text(json.dumps(table,indent=1)+'\n')
(pd/'clock_entries.json').write_text(json.dumps(es,indent=1)+'\n');(pd/'clock_pin_entries_report.json').write_text(json.dumps(rep,indent=1)+'\n');print('clock pin updates',len(rep['changed']),'unresolved clocks',len(rep['unresolved']))
