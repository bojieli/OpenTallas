"""Conservative all-combinational-arc stage walk on exact native placed pin geometry."""
import csv,json,collections
from pathlib import Path
p=Path(__file__).resolve().parent
rows=list(csv.DictReader((p/'driver_reach.tsv').open(),delimiter='\t')); roles=collections.defaultdict(set)
for r in csv.DictReader((p/'register_pins.tsv').open(),delimiter='\t'):roles[r['role']].add(r['pin'].replace('\\[','[').replace('\\]',']'))
nets=collections.defaultdict(list);pins={};instout=collections.defaultdict(set)
for r in rows:
 n=r['endpoint'].replace('\\[','[').replace('\\]',']');b=[float(r[k])for k in('xlo','ylo','xhi','yhi')]
 if n in pins:
  q=pins[n]['box'];b=[min(b[0],q[0]),min(b[1],q[1]),max(b[2],q[2]),max(b[3],q[3])]
 pins[n]={**r,'box':b};nets[r['net']].append(n)
 if r['io']=='OUTPUT':instout[n.rsplit('/',1)[0]].add(n)
macro=lambda n:n in roles['macro_output'] or n in roles['macro_data']
starts=set(roles['output'])|{n for n,r in pins.items()if macro(n)and r['io']=='OUTPUT'}|{n for n,r in pins.items()if r['io']=='PORT_INPUT'and n not in {'PORT/clk','PORT/hclk','PORT/ck','PORT/ckh'}}
stops=set(roles['data'])|set(roles['async'])|{n for n,r in pins.items()if macro(n)and r['io']=='INPUT'}|{n for n,r in pins.items()if r['io']=='PORT_OUTPUT'}
clocks=roles['clock']|{'PORT/clk','PORT/hclk','PORT/ck','PORT/ckh'};starts-=clocks;stops-=clocks
adj=collections.defaultdict(set)
for ns in nets.values():
 ds={n for n in ns if pins[n]['io']in('OUTPUT','PORT_INPUT')};ls={n for n in ns if pins[n]['io']in('INPUT','PORT_OUTPUT')}
 for d in ds:adj[d]|=ls-clocks
for n,r in pins.items():
 if r['io']=='INPUT'and n not in stops and n not in clocks:adj[n]|=instout[n.rsplit('/',1)[0]]
edges=[];dead=[];census=[]
for start in sorted(starts):
 seen={start};todo=list(adj[start]);ends=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  if n in stops:ends.add(n);continue
  todo.extend(adj[n]-seen)
 if not ends:dead.append(start)
 census.append({'driver':start,'stage_sinks':len(ends),'visited_nodes':len(seen)})
 for end in ends:
  a=pins[start]['box'];b=pins[end]['box'];upper=max(abs(a[i]-b[j])for i in(0,2)for j in(0,2))+max(abs(a[i]-b[j])for i in(1,3)for j in(1,3));edges.append({'driver':start,'sink':end,'bbox_manhattan_upper_um':upper})
summary={'scope':'All source/soft-register/hard-child boundary stages through conservative combinational all-input-to-all-output walk; actual detailed-placement pin bounding-box Manhattan upper bounds, not routed pathlength. Memory internals are separately modeled; no CTS/native/timing qualification implied. Clock pins excluded from data walk and retained in net census. Async reset pins are explicit endpoints.','starts':len(starts),'endpoints':len(stops),'stage_pairs':len(edges),'driver_roles':{k:len(v)for k,v in roles.items()},'missing_pin_geometry':sorted((starts|stops)-set(pins)),'drivers_without_stage_sinks':dead,'worst':sorted(edges,key=lambda r:r['bbox_manhattan_upper_um'],reverse=True)[:20],'over405':sum(r['bbox_manhattan_upper_um']>405for r in edges)}
(p/'stage_reach_summary.json').write_text(json.dumps(summary,indent=1)+'\n');(p/'stage_driver_census.json').write_text(json.dumps(census,indent=1)+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in('drivers_without_stage_sinks','missing_pin_geometry','worst')},indent=1));print('worst',summary['worst'][:3]);print('missing',len(summary['missing_pin_geometry']),'dead',len(dead))

over=[e for e in edges if e['bbox_manhattan_upper_um']>405]
extra={'over405':len(over),'over405_async':sum(e['sink']in roles['async'] for e in over),'max_nonasync':max((e['bbox_manhattan_upper_um']for e in edges if e['sink']not in roles['async']),default=0),'over405_pairs':over,'dead_memory_tail_bits':len(dead),'dead_all_macro_outputs':all(n in roles['macro_output']for n in dead)}
(p/'stage_extra.json').write_text(json.dumps(extra,indent=2)+'\n')
print({k:v for k,v in extra.items()if k!='over405_pairs'})
