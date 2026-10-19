#!/usr/bin/env python3
"""Fleet-only post-map native pair census; no STA/route/physical claims."""
import collections,hashlib,json,pathlib,re,sys
mapped=pathlib.Path(sys.argv[1]);base=json.loads(pathlib.Path(sys.argv[2]).read_text());out=pathlib.Path(sys.argv[3])
d=json.loads(mapped.read_text());m=d['modules'][base['top']];cells=m['cells'];aliases=collections.defaultdict(list)
for name,n in m['netnames'].items():
 for i,b in enumerate(n['bits']):
  if isinstance(b,int):aliases[b].append(name if len(n['bits'])==1 else name+'['+str(i+n.get('offset',0))+']')
loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
for name,c in cells.items():
 for p,bits in c['connections'].items():
  for b in bits:
   if isinstance(b,int):(drivers if c['port_directions'].get(p)=='output' else loads)[b].append(dict(cell=name,type=c['type'],port=p))
seq=lambda t:bool(re.search(r'DFF|LATCH|SDFF',t,re.I))
clockbits={b for p in ['pair_hbm_clk','pair_clk','return_clk'] for b in m['ports'][p]['bits']}
report=[]
for b,sinks in loads.items():
 if len(sinks)<=32:continue
 names=aliases[b];kind='clock' if b in clockbits else 'reset' if any(re.search('rst|reset',n,re.I) for n in names) else 'sequential_Q' if any(seq(x['type']) for x in drivers[b]) else 'SRAM_Q' if any(x['type'].startswith('ot_sram_') for x in drivers[b]) else 'top_input' if not drivers[b] else 'combinational'
 report.append(dict(bit=b,loads=len(sinks),kind=kind,names=names,drivers=drivers[b],sink_types=dict(collections.Counter(s['type'] for s in sinks)),sinks=sinks))
report.sort(key=lambda a:a['loads'],reverse=True)
ff=collections.Counter(c['type'] for c in cells.values() if seq(c['type']));groups=collections.Counter()
for name,c in cells.items():
 if seq(c['type']):groups['ingress_slices' if 'g_pin' in name else 'return_slices' if 'u_ring.g_slice[' in name else 'pair_slices' if 'u_pair.g_slice[' in name else 'other_native_control']+=1
def q_origin(bit,visited=None):
 visited=set() if visited is None else visited
 if bit in visited:return False
 visited.add(bit)
 ds=drivers[bit]
 if len(ds)!=1:return False
 d=ds[0]
 if seq(d['type']):return True
 if not re.match(r'(?:INV|BUF)',d['type']):return False
 cell=cells[d['cell']]
 ins=[b for port,bits in cell['connections'].items() if cell['port_directions'].get(port)=='input' for b in bits]
 return len(ins)==1 and q_origin(ins[0],visited)
qoutputs={};outputs_not_q=[]
for p,v in m['ports'].items():
 if v['direction']!='output':continue
 stats=collections.Counter()
 for b in v['bits']:
  ds=drivers[b]
  if any(seq(x['type']) for x in ds):stats['direct_FF_Q']+=1
  elif q_origin(b):stats['FF_Q_through_polarity_buffer']+=1
  elif ds:stats['non_FF_driver']+=1;outputs_not_q.append(dict(port=p,bit=b,names=aliases[b],drivers=ds))
  else:stats['undriven_or_constant']+=1
 qoutputs[p]=dict(stats)
# Boundary pin inputs are reported honestly as direct sequential versus first combinational load.
inputs={}
for p,v in m['ports'].items():
 if v['direction']!='input' or p in ['pair_hbm_clk','pair_clk','return_clk','pair_hbm_rst_n','pair_rst_n','return_rst_n']:continue
 c=collections.Counter()
 for b in v['bits']:
  sinks=loads[b];c['bits']+=1;c['direct_seq_D_loads']+=sum(seq(x['type']) and x['port'] not in ['CLK','CK','clock'] for x in sinks);c['comb_or_macro_loads']+=sum(not seq(x['type']) for x in sinks);c['pin_fanout_max']=max(c['pin_fanout_max'],len(sinks))
 inputs[p]=dict(c)
max_critical_load=max((len(v) for b,v in loads.items() if b not in clockbits),default=0)
result=dict(max_nonclock_load=max_critical_load,source_sha256=base['source_sha256'],mapped_json_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest(),physical_claim=False,std_area_um2=base['std_area_um2'],macro_counts=base['macro_counts'],unmapped_or_unknown=base['unmapped_or_unknown'],FF_cells_total=sum(ff.values()),FF_cell_types=dict(ff),FF_hierarchy_groups=dict(groups),output_boundary=qoutputs,output_non_FF_detail=outputs_not_q,input_boundary=inputs,over32_counts=dict(collections.Counter(a['kind'] for a in report)),over32=report,
 kept_instance_paths_remaining=[n for n,c in cells.items() if c['type'].startswith('$paramod')],
 qualification='mapped area/fanout only; physical reach, clock roots, native pin access and ordinary TT/FF timing remain OPEN')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['over32','output_non_FF_detail','input_boundary','source_sha256']},indent=2))
for a in report:
 print('NET',a['kind'],a['loads'],a['names'][:3],a['drivers'][:1])
