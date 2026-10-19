"""Structural audit of the immutable mapped cache JSON; run on fleet."""
import argparse,collections,hashlib,json,pathlib,functools
p=argparse.ArgumentParser();p.add_argument('mapped');p.add_argument('--top',default='ot_hbm_svc_static_sm_packed136_native_safe');a=p.parse_args();src=pathlib.Path(a.mapped);design=json.loads(src.read_text());m=design['modules'][a.top];cells=m['cells'];loads=collections.defaultdict(list);drivers={};aliases=collections.defaultdict(list)
for n,v in m['netnames'].items():
 for b in v['bits']:
  if isinstance(b,int):aliases[b].append(n)
for n,c in cells.items():
 for port,bs in c['connections'].items():
  for b in bs:
   if isinstance(b,int):
    if c['port_directions'][port]=='output':drivers[b]=(n,c)
    else:loads[b].append((n,port))
def ff(c):return c['type'].upper().startswith(('DFF','SDFF','ADFF'))
def macro(c):return c['type'].startswith('ot_sram_')
def buf(c):return c['type'].upper().startswith(('INV','BUF'))
def async_sinks(bits):
 todo=list(bits);seen=set();found=set();comb=[]
 while todo:
  b=todo.pop()
  if b in seen:continue
  seen.add(b)
  for n,port in loads[b]:
   c=cells[n]
   if ff(c):
    if port in ('RESETN','SETN','RN','SN','RESET','SET'):found.add(n)
   elif buf(c):
    comb.append(n)
    for k,bs in c['connections'].items():
     if c['port_directions'][k]=='output':todo+=bs
 return sorted(found),sorted(set(comb))
def outputs(n):
 c=cells[n];return [b for k,bs in c['connections'].items() if c['port_directions'][k]=='output' for b in bs]
raw=m['ports']['rst_n']['bits'];first,raw_buffers=async_sinks(raw);second=set();first_report=[]
for n in first:
 fs,bs=async_sinks(outputs(n));second.update(fs);first_report.append(dict(cell=n,second_stage_ff_count=len(fs),combinational_buffer_cells=bs))
second_report=[];final=set()
for n in sorted(second):
 fs,bs=async_sinks(outputs(n));final.update(fs);second_report.append(dict(cell=n,final_async_ff_count=len(fs),combinational_buffer_cells=bs))
clock=set(m['ports']['clk']['bits']);fanouts=[dict(bit=b,fanout=len(ls),names=aliases[b]) for b,ls in loads.items() if b not in clock];fanouts.sort(key=lambda x:x['fanout'],reverse=True)
# Longest logic path ending at actual data D; all FF/macro outputs are launch points.
@functools.lru_cache(None)
def depth(b):
 if not isinstance(b,int) or b not in drivers:return 0
 n,c=drivers[b]
 if ff(c) or macro(c):return 0
 return 1+max((depth(x) for k,bs in c['connections'].items() if c['port_directions'][k]=='input' for x in bs),default=0)
deps=[]
for n,c in cells.items():
 if ff(c) and 'D' in c['connections']:
  deps.append(dict(cell=n,logic_cell_levels=max(depth(b) for b in c['connections']['D'])))
deps.sort(key=lambda x:x['logic_cell_levels'],reverse=True)
# Trace every exported output bit back through wires/inverters to a real Q or macro output.
def origin(b,path=()):
 if not isinstance(b,int):return 'constant'
 if b not in drivers:return 'input_or_undriven'
 n,c=drivers[b]
 if ff(c):return 'FF_Q'
 if macro(c):return 'SRAM_Q'
 if buf(c):
  inp=[x for k,bs in c['connections'].items() if c['port_directions'][k]=='input' for x in bs]
  if len(inp)==1:return origin(inp[0],path+(n,))
 return 'COMBINATIONAL'
outs={}
for n,v in m['ports'].items():
 if v['direction']=='output':outs[n]=dict(collections.Counter(origin(b) for b in v['bits']))
r=dict(mapped_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),top=a.top,profile='source-bound strict two registered reset levels; raw<=12 first<=24 final<=30',raw_async_ff_sinks=len(first),raw_combinational_buffers=raw_buffers,first_stage=first_report,second_stage_count=len(second),second_stage=second_report,final_async_ff_count=len(final),max_first_stage_ff_fanout=max(x['second_stage_ff_count'] for x in first_report),max_second_stage_ff_fanout=max(x['final_async_ff_count'] for x in second_report),max_nonclock_pin_fanout=fanouts[0]['fanout'],over32=[x for x in fanouts if x['fanout']>32],output_origins=outs,max_data_logic_levels=deps[0]['logic_cell_levels'],top10_data_depth=deps[:10],physical_claim=False,physical_open=['placed reset-clear slew/reach','clock tree and pin-flop spread','actual stage delay','macro dense-face and PG access'])
r['reset_profile_pass']=r['raw_async_ff_sinks']<=12 and r['max_first_stage_ff_fanout']<=24 and r['max_second_stage_ff_fanout']<=30 and not raw_buffers
r['all_outputs_native_q']=all(set(v)<= {'constant','FF_Q','SRAM_Q'} for v in outs.values())
print(json.dumps(r,indent=2))
