#!/usr/bin/env python3
"""Report actual raw-state producer/consumer domains across the Q2NF cut.
This reports existing edges; it never assigns a first-clock face or inserts CDC.
"""
import collections,json,sys
from functools import lru_cache
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text())['modules']['ot_q2nf_rest'];cells=p['cells'];aliases=collections.defaultdict(list);drivers=collections.defaultdict(list);users=collections.defaultdict(list)
topinput={b:(n if len(q['bits'])==1 else f"{n}[{i+q.get('offset',0)}]") for n,q in p['ports'].items() if q['direction']=='input' for i,b in enumerate(q['bits'])};topoutput={b for q in p['ports'].values() if q['direction']=='output' for b in q['bits']}
for n,q in p['netnames'].items():
 for b in q['bits']:
  if isinstance(b,int):aliases[b].append(n)
for n,c in cells.items():
 for port,bs in c['connections'].items():
  if c['port_directions'][port]=='output':
   for b in bs:
    if isinstance(b,int):drivers[b].append(n)
  else:
   for b in bs:
    if isinstance(b,int):users[b].append((n,port))
def owner(n):return cells[n].get('attributes',{}).get('submod','rest_control')
def state_clock(c):
 b=c['connections'].get('CLK') or (c['connections'].get('clk') if c['type'].startswith('ot_sram') else None)
 if b:return tuple(topinput.get(q,'unresolved_clock_bit:'+str(q)) for q in b)
 return None
@lru_cache(None)
def producer(b):
 if isinstance(b,str):return ()
 if b in topinput:return ('external:'+topinput[b],)
 out=set()
 for n in drivers[b]:
  c=cells[n];ck=state_clock(c)
  if ck:out.update(ck)
  else:
   for port,bs in c['connections'].items():
    if c['port_directions'][port]=='input':
     for q in bs:out.update(producer(q))
 return tuple(sorted(out))
@lru_cache(None)
def consumer(b,target=None):
 out=set()
 for n,port in users[b]:
  if target is not None and owner(n)!=target:continue
  c=cells[n];ck=state_clock(c)
  if ck:out.update(ck)
  else:
   for po,bs in c['connections'].items():
    if c['port_directions'][po]=='output':
     for q in bs:
      if isinstance(q,int):out.update(consumer(q,target))
 return tuple(sorted(out))
def bitname(b):
 if b in topinput:return topinput[b]
 ns=aliases[b];good=[n for n in ns if 'u_body.' in n and not n.startswith('$')]
 return min(good or ns,key=lambda n:(len(n),n))
rows={};summary={};state=collections.defaultdict(collections.Counter)
for n,c in cells.items():
 ck=state_clock(c)
 if ck:state[owner(n)][','.join(ck)]+=len(c['connections'].get('Q',[])) or 1
for group in ['g_linkstore0','g_linkstore1','rest_control']:
 ins=set();outs=set()
 for n,c in cells.items():
  if owner(n)!=group or c['type']=='$scopeinfo':continue
  for port,bs in c['connections'].items():
   for b in bs:
    if not isinstance(b,int):continue
    if c['port_directions'][port]=='input':
     if b in topinput or any(owner(q)!=group for q in drivers[b]):ins.add(b)
    elif b in topoutput or any(owner(q)!=group for q,_ in users[b]):outs.add(b)
 out=[];counts=collections.Counter()
 for direction,bits in [('input',ins),('output',outs)]:
  for b in sorted(bits):
   roles=sorted({'clock' if port in ('CLK','clk') else 'reset' if port in ('ARST','SRST') else 'data_or_control' for n,port in users[b] if owner(n)==group})
   a=producer(b);z=consumer(b,group) if direction=='input' else consumer(b);counts[direction+':'+','.join(a)+' -> '+','.join(z)]+=1
   out.append({'direction':direction,'raw_bit':b,'net':bitname(b),'producer_domains':a,'consumer_domains':z,'child_sink_roles':roles})
 rows[group]=out;summary[group]={'input_bits':len(ins),'output_bits':len(outs),'clocked_items_by_actual_parent_clock':dict(state[group]),'boundary_domain_pairs':dict(counts)}
report={'schema':'q2nf.boundary_clocks.v1','source':'actual proc/flatten word cells and original parent input connections','assign_first_clock':False,'extra_cycles':0,'summary':summary,'boundaries':rows,'native_parent_requirement':'Retain actual clocks and existing CDC/reset semantics. Source/sink domain sets are findings, not permission to recapture a shared edge or insert a new register.'}
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2))
