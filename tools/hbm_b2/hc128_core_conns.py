#!/usr/bin/env python3
"""Derive native HC core connectivity from actual composed adapters and B2 bindings.

Non-core logic is traversed in signal direction, including original registers;
clock/reset never create data dependencies. Existing non-HC sidecars are retained. Multi-lane external bundles retain
all reported endpoint targets; this sidecar is not a per-bit lane assignment.
"""
import argparse,collections,json,re,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--old-conns',type=Path,required=True);ap.add_argument('--native-report',type=Path,required=True);ap.add_argument('--b2-top',type=Path,required=True);ap.add_argument('--adapters',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
plan=json.loads(a.plan.read_text());report=json.loads(a.native_report.read_text());conn=json.loads(a.old_conns.read_text());parts={p['name']:p for p in plan['partitions']};ports={p['id']:p for p in plan['ports']};lanes={p['id']:p for p in plan['lanes']};text=a.b2_top.read_text();bindings={}
for mat in re.finditer(r'\b(hcb_N[WE][0-7]|hc_N[WE])\s*\(\s*(.*?)\n  \);',text,re.S):bindings[mat[1]]={n:e for n,e in re.findall(r'\.(\w+)\(([^\n]*)\)',mat[2])}
# Both directions of each lane are determined by its actual endpoint objects.
produced=collections.defaultdict(list)
for row in report['lane_capacity']:
 for lid in row.get('lanes',[]):
  lane=lanes[lid];src=ports[lane['ports'][0]]['src'];dst=ports[lane['ports'][-1]]['dst']
  for p in row.get('source_ports',[]):produced[p].append((src,dst))

def bus_ports(inst,part):
 out=collections.defaultdict(set)
 for key,rows in produced.items():
  if key.startswith(inst+'.'):
   for src,dst in rows:
    if src['part']==part:out[key.split('.',1)[1]].add('bus:'+src['bus'])
 for port,expr in bindings[inst].items():
  for srcinst,srcport in re.findall(r'\b(\w+)__(\w+)',expr):
   for src,dst in produced.get(srcinst+'.'+srcport,[]):
    if dst['part']==part:out[port].add('bus:'+dst['bus'])
 return out

def derive(j,top,core_names,toplinks,parent):
 m=j['modules'][top];cells=m['cells'];back=collections.defaultdict(list);fwd=collections.defaultdict(list);cins={};couts={};endpoint=collections.defaultdict(set)
 for pn,p in m['ports'].items():
  if pn in ('clk','rst_n'):continue
  for b in p['bits']:
   if isinstance(b,int):endpoint[(p['direction'],b)].update(toplinks.get(pn,()))
 for n,c in cells.items():
  if n in core_names:
   for pn,bs in c['connections'].items():
    if pn in ('clk','rst_n'):continue
    for b in bs:
     if isinstance(b,int):endpoint[(c['port_directions'][pn],b)].add('core:'+core_names[n])
   continue
  if c['type'].startswith('ot_hbm_hc_q_static'):
   for pn,bs in c['connections'].items():
    if pn in ('clk','rst_n'):continue
    for b in bs:
     if isinstance(b,int):endpoint[(c['port_directions'][pn],b)].add('leaf:'+parent)
   continue
  ins=set();outs=set()
  for pn,bs in c['connections'].items():
   if pn in ('CLK','C','ARST','SRST','clk','rst_n'):continue
   (ins if c['port_directions'][pn]=='input' else outs).update(b for b in bs if isinstance(b,int))
  cins[n]=ins;couts[n]=outs
  for b in ins:fwd[b].append(n)
  for b in outs:back[b].append(n)
 result={};miss=[]
 for n,inst in core_names.items():
  c=cells[n];pc={}
  for pn,bs in c['connections'].items():
   if pn in ('clk','rst_n'):continue
   direction=c['port_directions'][pn];q=list(b for b in bs if isinstance(b,int));seen=set(q);visited=set();tg=set()
   while q:
    b=q.pop();tg.update(x for x in endpoint.get((('input' if direction=='input' else 'output'),b),()) if x.startswith('bus:'))
    # Core endpoints are opposite in direction from the querying core port.
    tg.update(x for x in endpoint.get((('output' if direction=='input' else 'input'),b),()) if x.startswith(('core:','leaf:')))
    for cell in (back if direction=='input' else fwd).get(b,()):
     if cell in visited:continue
     visited.add(cell)
     for bb in (cins if direction=='input' else couts)[cell]-seen:seen.add(bb);q.append(bb)
   tg.discard('core:'+inst)
   if tg:pc[pn]=sorted(tg)
   elif any(isinstance(b,int) for b in bs):miss.append((inst,pn))
  result[inst]=pc
 return result,miss

summary=[];port_roles={}
for tn,t in plan['partition_types'].items():
 cores=[c for c in t.get('hard_cores',[]) if c['module'].startswith(('ot_hbm_hc_bank128','ot_hbm_hc_subtree32'))]
 if not cores:continue
 part=next(p['name'] for p in plan['partitions'] if p['type']==tn and p['name'].startswith('NE' if tn.endswith('ne') else 'NW'))
 if tn.startswith('q_b'):
  idx=int(re.search(r'Q(\d+)',cores[0]['parent_instance'])[1]);asb='hcb_NW'+str(idx);top=next(c['module'] for c in t['contents'] if c['inst']==cores[0]['parent_instance'])
 else:asb='hc_NW' if tn.endswith('nw') else 'hc_NE';top='ot_hbm_hc_qhub_static';part=next(p['name'] for p in plan['partitions'] if p['type']==tn and p['name'].startswith('NE' if tn.endswith('ne') else 'NW'))
 jp=a.adapters/(top+'.json');j=json.loads(jp.read_text());work=a.out/(tn+'_flat.json');ys=a.out/(tn+'.ys');ys.write_text(f'read_json {jp.resolve()}\nsetattr -unset keep_hierarchy\nsetattr -mod -unset keep_hierarchy\nhierarchy -top {top}\nflatten\nwrite_json {work.resolve()}\n');subprocess.run([str(Path.home()/'.local/opentallas-tools/bin/yosys'),'-ql',str(a.out/(tn+'.log')),'-s',str(ys)],check=True);j=json.loads(work.read_text());cn={c['cut_instance']:c['inst'] for c in cores};port_roles[tn]={inst:{pn:dict(direction=j['modules'][top]['cells'][n]['port_directions'][pn],bits=len(bs)) for pn,bs in j['modules'][top]['cells'][n]['connections'].items()} for n,inst in cn.items()};new,miss=derive(j,top,cn,bus_ports(asb,part),cores[0]['parent_instance']);conn[tn]={k:v for k,v in conn.get(tn,{}).items() if not k.startswith(cores[0]['parent_instance'])};conn[tn].update(new);assert all(pn=='valid_out' and inst.endswith(('subtree32_1','subtree32_3')) for inst,pn in miss),(tn,miss);summary.append(dict(type=tn,core_count=len(new),port_groups=sum(len(p) for p in new.values()),unconnected=miss))
(a.out/'core_port_roles.json').write_text(json.dumps(port_roles,indent=2)+'\n');(a.out/'core_conns.json').write_text(json.dumps(conn,indent=1)+'\n');(a.out/'connectivity_receipt.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
