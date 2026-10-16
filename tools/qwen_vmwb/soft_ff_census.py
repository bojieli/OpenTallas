#!/usr/bin/env python3
"""Count every actual remaining sequential Q bit by source name/clock, no hardening credit."""
import argparse,collections,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--top',default='qfd_sp_vector_memory_par_partitioned_ro6');p.add_argument('--expected-parent-ff',type=int,default=55382);p.add_argument('--expected-bv-ff',type=int,default=53549);a=p.parse_args();mods=json.loads(a.netlist.read_text())['modules'];top=a.top;tm=mods[top]
labels={b:n if len(v['bits'])==1 else f'{n}[{i}]'for n,v in tm['ports'].items()for i,b in enumerate(v['bits'])};rows=[];physical=collections.Counter()
seq={'$dff','$adff','$sdff','$dffe','$adffe','$sdffe','$aldff','$dffsr'}
def base(n):return n.split('\\')[-1]
def wire(b,mp,path):return mp.get(b,f'{path}::bit{b}')if isinstance(b,int)else f'constant:{b}'
def walk(name,mp,path):
 m=mods[name];alias=collections.defaultdict(list)
 for n,v in m.get('netnames',{}).items():
  if not n.startswith('$'):
   for i,b in enumerate(v['bits']):alias[b].append(n if len(v['bits'])==1 else f'{n}[{i}]')
 for n,c in m.get('cells',{}).items():
  t=c['type'];cp=path+'.'+n;cc={k:[wire(b,mp,path)for b in v]for k,v in c['connections'].items()}
  if t in seq:
   names=collections.Counter()
   for b in c['connections']['Q']:
    ns=alias.get(b,[]);ns.sort(key=lambda z:(not z.startswith(('bw_','ws_')),len(z),z));names[ns[0]if ns else '<unnamed>']+=1
   group=[]
   for label,count in names.items():group.append((re.sub(r'\[\d+\]$','',label),count))
   groups=collections.Counter()
   for label,count in group:groups[label]+=count
   rows.append(dict(instance=cp,module=base(name),kind=t,bits=len(c['connections']['Q']),clock=cc['CLK'][0],source=c.get('attributes',{}).get('src'),signals=dict(groups)))
  elif t in mods:
   if mods[t].get('attributes',{}).get('blackbox'):physical[base(t)]+=1;continue
   cm={b:label for pn,pv in mods[t]['ports'].items()for b,label in zip(pv['bits'],cc.get(pn,[]))};walk(t,cm,cp)
walk(top,labels,top)
parent=[r for r in rows if r['clock']=='ck'];bv=[r for r in parent if r['module']=='ot_qfd_sp_vector_memory_bv'];signals=collections.Counter()
for r in bv:signals.update(r['signals'])
classes=collections.Counter()
for n,k in signals.items():
 group='bank_write'if n.startswith('bw_')else 'SU_replica_write'if n.startswith('ws_')else 'row_read'if n.startswith(('rr_','r_qr','rb'))else 'other_write_control'
 classes[group]+=k
out=dict(scope='Actual hierarchical source FF Q-bit census after proc/opt_clean, physical children blackboxed. Source FFs are unhardened and unqualified. No wires-only parent claim.',all_soft_ff_bits=sum(r['bits']for r in rows),parent_clock_ff_bits=sum(r['bits']for r in parent),BV_parent_clock_ff_bits=sum(r['bits']for r in bv),BV_categories=dict(classes),BV_signals=dict(sorted(signals.items())),parent_clock_module_totals=dict(collections.Counter({m:sum(r['bits']for r in parent if r['module']==m)for m in {r['module']for r in parent}})),physical_blackbox_instances=dict(physical),rows=rows)
a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['rows','BV_signals','physical_blackbox_instances']},indent=2))
assert out['parent_clock_ff_bits']==a.expected_parent_ff and out['BV_parent_clock_ff_bits']==a.expected_bv_ff
