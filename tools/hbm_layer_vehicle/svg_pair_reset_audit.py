"""Structural audit of the immutable mapped cache JSON; run on fleet."""
import argparse,collections,hashlib,json,pathlib,functools
p=argparse.ArgumentParser();p.add_argument('mapped');p.add_argument('--top',default='ot_hbm_svg_landing_pair_native');a=p.parse_args();src=pathlib.Path(a.mapped);design=json.loads(src.read_text());m=design['modules'][a.top];cells=m['cells'];loads=collections.defaultdict(list);drivers={};aliases=collections.defaultdict(list)
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
def record(n):
 c=cells[n]
 return dict(cell=n,type=c['type'],clock={p:v for p,v in c['connections'].items() if p in ['CLK','CK','C']},
  D=c['connections'].get('D'),async_pins={p:v for p,v in c['connections'].items() if p in ['RESETN','SETN','RN','SN','RESET','SET']})
profiles={}
for root in ['pair_hbm_rst_n','pair_rst_n','return_rst_n']:
 first,bs=async_sinks(m['ports'][root]['bits']);seconds=set();first_report=[]
 for n in first:
  sinks,bufs=async_sinks(outputs(n));seconds.update(sinks)
  first_report.append(dict(**record(n),async_ff_count=len(sinks),buffers=bufs))
 final_report=[]
 for n in sorted(seconds):
  sinks,bufs=async_sinks(outputs(n));final_report.append(dict(**record(n),async_ff_count=len(sinks),buffers=bufs))
 profiles[root]=dict(raw_async_ff_count=len(first),raw_buffers=bs,first_stage=first_report,second_stage=final_report,
  max_first_async_ff_count=max((x['async_ff_count'] for x in first_report),default=0),
  max_second_async_ff_count=max((x['async_ff_count'] for x in final_report),default=0))
fifo=[]
for bit,names in aliases.items():
 if not any('.u_response.both_reset' in n for n in names):continue
 fs,bs=async_sinks([bit])
 qualifications=[]
 for n in fs:
  owned,bufs=async_sinks(outputs(n));qualifications.append(dict(**record(n),downstream_async_ff_count=len(owned),downstream_async_FFs=owned,buffers=bufs))
 drv=drivers.get(bit)
 fifo.append(dict(net_aliases=names,driver=None if drv is None else dict(cell=drv[0],type=drv[1]['type'],connections=drv[1]['connections']),
  async_reset_sync_FFs=qualifications,buffers=bs,
  equation='both_reset=hreset&&sreset; each wr/rd reset_pipe has two FFs asynchronously cleared by both_reset; q1 clears FIFO functional controls',
  release='native hreset/sreset E2 followed by two local FIFO reset synchronizer edges; online cross-domain qualification follows; unequal clocks/releases explicitly allowed'))
rootclock={'pair_hbm_rst_n':'pair_hbm_clk','pair_rst_n':'pair_clk','return_rst_n':'return_clk'}
for root,profile in profiles.items():
 expected=m['ports'][rootclock[root]]['bits']
 profile['first_and_second_clocks_match_root']=all(list(x['clock'].values())==[expected] for level in ['first_stage','second_stage'] for x in profile[level])
 profile['first_and_second_D_constant_one']=all(x['D']==['1'] for level in ['first_stage','second_stage'] for x in profile[level])
 profile['strict_native_profile_pass']=profile['raw_async_ff_count']<=12 and profile['max_first_async_ff_count']<=24 and profile['max_second_async_ff_count']<=30 and profile['first_and_second_clocks_match_root'] and profile['first_and_second_D_constant_one']
print(json.dumps(dict(mapped_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),profiles=profiles,internal_FIFO_reset_graph=fifo,
 scope='Native two-level landing graph plus explicitly separate, unchanged internal FIFO reset/online CDC qualification. Async sinks traced through real INV/BUF; FIFO AND roots enumerated separately. Whole leaf is not uniformly two-level.',physical_claim=False),indent=2))
