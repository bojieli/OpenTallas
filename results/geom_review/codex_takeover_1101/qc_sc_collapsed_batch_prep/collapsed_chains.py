from pathlib import Path
from collections import Counter
import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design(str(P/'geom.tsv'))
clock=set();seen_nets=set();q=[n for cid,c in D.cells.items()if c[0]=='S'for n,ck in D.cell_in.get(cid,[])if ck]
while q:
 n=q.pop()
 if n in seen_nets:continue
 seen_nets.add(n);dr=D.nets[n][1]
 if not dr or dr[0]!='i':continue
 cid=dr[1]
 if D.kind(cid)=='S':continue
 clock.add(cid);q.extend(nn for nn,ck in D.cell_in.get(cid,[])if not ck)
def targets(net):return [s for s in D.nets[net][2]if s[0]=='p'or not s[2]]
def dataouts(cid):return [n for n in D.drives.get(cid,[])if D.nets[n][0]not in['CLOCK','POWER','GROUND']]
def pubinputs(cid):
 ports=set();todo=[n for n,ck in D.cell_in.get(cid,[])if not ck];seen=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n);dr=D.nets[n][1]
  if not dr:continue
  if dr[0]=='p':
   p=D.pin_by_k[dr[1]]
   if p['io']=='INPUT'and p['sig']not in['CLOCK','POWER','GROUND']:ports.add(p['name'])
  elif D.kind(dr[1])=='B':todo.extend(nn for nn,ck in D.cell_in.get(dr[1],[])if not ck)
 return sorted(ports)
rows=[];ambiguous=0
for source,c in D.cells.items():
 if c[0]!='S':continue
 for startnet in dataouts(source):
  if startnet in D.multi_drv:ambiguous+=1;continue
  sinks=targets(startnet)
  if len(sinks)!=1 or sinks[0][0]!='i':continue
  target=sinks[0][1];chain=[];edges=[];visited=set();driver=source;net=startnet;end=None;stop=''
  while True:
   if target in visited:stop='cycle';break
   visited.add(target);tc=D.cells[target]
   if target in clock:stop='clock_cone_excluded';break
   edges.append(dict(driver=D.cells[driver][6],sink=tc[6],net=net,fanout=len(targets(net)),centre_l1_um=round(sum(abs(a-b)for a,b in zip(g.ctr(D.cells[driver]),g.ctr(tc))),4)))
   if not tc[1].startswith('BUF'):
    end=target;stop='first_nonBUF';break
   chain.append(target);outs=dataouts(target)
   if len(outs)!=1:stop='nonunique_output';break
   net=outs[0]
   if net in D.multi_drv:stop='multidriver';break
   sinks=targets(net)
   if len(sinks)!=1:stop='nonunit_fanout';break
   if sinks[0][0]!='i':stop='public_output';break
   driver,target=target,sinks[0][1]
  if len(chain)<2:continue
  points=[g.ctr(D.cells[k])for k in chain];us=[x+y for x,y in points];vs=[x-y for x,y in points];span=max(max(us)-min(us),max(vs)-min(vs));first=edges[0]['centre_l1_um'];ports=pubinputs(source)
  row=dict(source_ff=c[6],source_master=c[1],source_centre_um=list(g.ctr(c)),public_input_candidates=ports,buffer_count=len(chain),buffers=[dict(name=D.cells[k][6],master=D.cells[k][1],bbox_um=list(D.cells[k][2:6]),centre_um=list(g.ctr(D.cells[k])),size_um=[round(D.cells[k][4]-D.cells[k][2],4),round(D.cells[k][5]-D.cells[k][3],4)])for k in chain],endpoint=None if end is None else dict(name=D.cells[end][6],master=D.cells[end][1],centre_um=list(g.ctr(D.cells[end]))),edges=edges,stop=stop,first_hop_centre_l1_um=first,longest_hop_centre_l1_um=max(x['centre_l1_um']for x in edges),buffer_cluster_l1_diameter_um=round(span,4),first_hop_over150_census_filter=first>150,repeaters_within10um_census_flag=span<=10)
  rows.append(row)
long=[r for r in rows if r['first_hop_over150_census_filter']];collapsed=[r for r in long if r['repeaters_within10um_census_flag']];refs=[r for r in rows if any(p in['dn_i[44]','dn_i[47]']for p in r['public_input_candidates'])]
res=dict(scope='READ-ONLY current actual three-BUF SC geometry and exact signal graph; no CAD/STA/target moves;150um and10um are census filters, not new gates',clock_cone_excluded=len(clock),serial_chains_with2plus_buffers=len(rows),first_hop_over150=len(long),collapsed_within10um=len(collapsed),length_counts=dict(Counter(r['buffer_count']for r in long)),ambiguous_source_nets_skipped=ambiguous,semantic_note='No reset/data meaning inferred from instance names; public input candidate strings are connectivity observations only.',long_first_hop_chains=sorted(long,key=lambda r:-r['longest_hop_centre_l1_um']),current_dn44_dn47_reference_chains=refs)
(P/'collapsed_chains.json').write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in['long_first_hop_chains','current_dn44_dn47_reference_chains']});print('top',[(r['source_ff'],r['public_input_candidates'],r['buffer_count'],r['first_hop_centre_l1_um'],r['buffer_cluster_l1_diameter_um'])for r in sorted(long,key=lambda r:-r['first_hop_centre_l1_um'])[:8]])
