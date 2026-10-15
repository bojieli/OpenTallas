#!/usr/bin/env python3
"""Hierarchical RTL state census by physical clock entry. No mapped area claim."""
import subprocess,sys,json,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
import hc_gate as H
topname=sys.argv[2] if len(sys.argv)>2 else 'dsfd_engram_mix_c'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
extras=['rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv','rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv','rtl/dsrom_sys/engram/mix/dsfd_engram_mix_c.sv','rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']
libs=[x for x in H.RTL if '/hdc/' in x];sources=[ROOT/x for x in H.FP['rtl']+libs+extras]
(out/'sources.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
y='read_verilog -sv -DSYNTHESIS '+' '.join(map(str,sources))+f'\nhierarchy -check -top {topname}\nproc\nopt\nmemory_collect\nopt_clean\nstat -width\nwrite_json '+str(out/'hierarchical.json')+'\n'
(out/'census.ys').write_text(y)
with (out/'census.log').open('w') as log:r=subprocess.run(['yosys','-s',str(out/'census.ys')],stdout=log,stderr=subprocess.STDOUT)
if r.returncode:sys.exit(r.returncode)
z=json.loads((out/'hierarchical.json').read_text());mods=z['modules'];ff=collections.Counter();mem=collections.Counter();ops=collections.Counter();instances=[]
def number(x):return int(x,2) if isinstance(x,str) else int(x)
def walk(name,path,mapping):
 m=mods[name]
 def bit(x):return mapping.get(x,f'{path}:{x}') if isinstance(x,int) else str(x)
 for cn,c in m.get('cells',{}).items():
  t=c['type'];cp=path+'/'+cn;co=c['connections'];pa=c.get('parameters',{})
  if t in mods:
   sm=mods[t];mp={}
   for pn,p in sm['ports'].items():
    for local,remote in zip(p['bits'],co.get(pn,[])):mp[local]=bit(remote)
   walk(t,cp,mp)
  elif 'dff' in t.lower() or t=='$ff':
   width=number(pa.get('WIDTH',1));clocks=co.get('CLK',co.get('C',[]));root=bit(clocks[0]) if clocks else 'unclocked';ff[root]+=width
  elif t=='$mem_v2':
   size=number(pa['SIZE'])*number(pa['WIDTH']);roots={bit(x) for x in co.get('WR_CLK',[]) if x not in ('0','1','x','z')}
   for root in roots:mem[root]+=size
  elif t.startswith('$'):ops[t]+=1
 instances.append({'path':path,'module':name})
top=mods[topname];mapping={b:f'ck[{i}]' for i,b in enumerate(top['ports']['ck']['bits'])}
walk(topname,topname,mapping)
res={'scope':'hierarchical proc/opt RTL state; not mapped area, CTS, pin reach or native qualification','flop_bits_by_clock':dict(ff),'inferred_memory_upper_bound_by_clock':dict(mem),'flop_plus_memory_upper_bound':{k:ff[k]+mem[k] for k in ff.keys()|mem.keys()},'operator_instances':dict(ops),'total_flop_bits':sum(ff.values()),'total_memory_upper_bound':sum(mem.values())}
(out/'census.json').write_text(json.dumps(res,indent=2)+'\n');(out/'instances.json').write_text(json.dumps(instances,indent=1)+'\n');print(json.dumps(res,indent=2))
