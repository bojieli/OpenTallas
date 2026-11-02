"""Read-only typed source join; never fabricates provider clock aliases or physical phase."""
import argparse,json,re,pathlib,hashlib,collections
ap=argparse.ArgumentParser();ap.add_argument('--ctree',required=True);ap.add_argument('--tree',required=True);ap.add_argument('--provider',required=True);ap.add_argument('--selected',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();text=pathlib.Path(a.ctree).read_text();tree=json.load(open(a.tree));prov=json.load(open(a.provider));selected=json.load(open(a.selected));stages=prov['stages'];wanted={s['id']for s in selected['stages']};cells={};drivers={};loads=collections.Counter();aliases={};unknown=[]
for line in text.splitlines():
 m=re.fullmatch(r'\s*(\S+)\s+(\S+)\s+\(\.A\(([^)]+)\),\s*\.Y\(([^)]+)\)\);',line)
 if m:
  master,name,inp,out=m.groups();cells[name]=dict(master=master,A=inp,Y=out);assert out not in drivers,out;drivers[out]=name;loads[inp]+=1
 m=re.fullmatch(r'\s*assign\s+(\S+)\s*=\s*(\S+);',line)
 if m:aliases[m[1]]=m[2]
cache={'root':0};active=set()
def parity(net):
 if net in cache:return cache[net]
 if net in active:return None
 active.add(net);v=None
 if net in aliases:v=parity(aliases[net])
 elif net in drivers:
  c=cells[drivers[net]];p=parity(c['A']);inv=1 if c['master'].startswith(('INV','CKINV'))else 0 if c['master'].startswith(('BUF','CKBUF'))else None
  if p is not None and inv is not None:v=p^inv
 active.remove(net);cache[net]=v;return v
rows=[]
for s in stages:
 node=s['node_cell'];c=cells.get(node);side=s['clock_from'];assert side in ['A','Y'],side;net=c.get(side)if c else None;drv=drivers.get(net)if net else None;site=tree['sites'].get(node);binding_port=s['clock_port'];alias_net=aliases.get(binding_port)
 rows.append(dict(id=s['id'],clock_port=binding_port,node_cell=node,node_cell_exists=c is not None,node_master=c['master']if c else None,clock_from=side,source_net=net,source_driver_cell=drv,source_driver_master=cells[drv]['master']if drv else None,source_node_origin_um=site,source_driver_origin_um=tree['sites'].get(drv),relative_root_inversion_parity=parity(net)if net else None,expected_driver=s.get('actual_clock_driver'),expected_clock_net=s.get('clock_net'),driver_matches_retained=s.get('actual_clock_driver')==drv if c else False,net_matches_retained=s.get('clock_net')==net if c else False,node_xy_matches_retained=site==s.get('node_xy_um'),retained_receiver_clock_pin_um=s.get('clock_pin_xy_um'),retained_stage_rect_um=s.get('rect_um'),source_declares_provider_clock_alias=binding_port in aliases,declared_alias_net=alias_net,provider_flops_to_attach=s['flops'],provider_reset_flops=s.get('reset_flops'),source_clock_cell_input_loads_only=loads[net]if net else None,source_native_aliases_on_net=sum(n==net for n in aliases.values())if net else None))
def packet(rs):
 return dict(status='TYPED_CLOCK_SOURCE_JOIN_ONLY_NO_PHASE_OR_PHYSICAL_CREDIT',stage_count=len(rs),node_cell_present=sum(x['node_cell_exists']for x in rs),missing_node_cells=[x['id']for x in rs if not x['node_cell_exists']],retained_driver_mismatches=sum(not x['driver_matches_retained']for x in rs),retained_net_mismatches=sum(not x['net_matches_retained']for x in rs),retained_node_xy_mismatches=sum(not x['node_xy_matches_retained']for x in rs),provider_clock_aliases_actually_declared=sum(x['source_declares_provider_clock_alias']for x in rs),rows=rs,holds=['Logical inversion parity only, no native arrivals/frequency/phase/graft/placement/import/PG/routing/STA credit','Retained receiver rectangles are historical source fields and are not new physical landing evidence','If provider port aliases are absent, actual provider clock wiring/load producer is OPEN; this tool does not invent aliases or claim additional load is balanced','All3 SerDes regional833 bindings remain unqualified for their1GHzFDI calendar; core joins do not release PHY'])
o=pathlib.Path(a.out);o.mkdir(exist_ok=True);cohort={k:hashlib.sha256(pathlib.Path(v).read_bytes()).hexdigest()for k,v in [('ctree',a.ctree),('tree',a.tree),('provider',a.provider),('selected',a.selected)]}
for name,rs in [('FULL3266',rows),('SELECTED78',[x for x in rows if x['id']in wanted])]:
 p=packet(rs);p['cohort_sha256']=cohort;(o/(name+'_TYPED_SOURCE_JOIN.json')).write_text(json.dumps(p,indent=2)+'\n');print(name,{k:v for k,v in p.items()if k not in ['rows','holds','cohort_sha256','missing_node_cells']})
