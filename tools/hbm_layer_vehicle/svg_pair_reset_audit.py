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
profiles={}
for root in ['pair_hbm_rst_n','pair_rst_n','return_rst_n']:
 first,bs=async_sinks(m['ports'][root]['bits']);seconds=set();first_report=[]
 for n in first:
  sinks,bufs=async_sinks(outputs(n));seconds.update(sinks)
  first_report.append(dict(cell=n,async_ff_count=len(sinks),buffers=bufs))
 final_report=[]
 for n in sorted(seconds):
  sinks,bufs=async_sinks(outputs(n));final_report.append(dict(cell=n,async_ff_count=len(sinks),buffers=bufs))
 profiles[root]=dict(raw_async_ff_count=len(first),raw_buffers=bs,first_stage=first_report,second_stage=final_report,
  max_first_async_ff_count=max((x['async_ff_count'] for x in first_report),default=0),
  max_second_async_ff_count=max((x['async_ff_count'] for x in final_report),default=0))
print(json.dumps(dict(mapped_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),profiles=profiles,
 scope='async sinks traced through INV/BUF only; explicit internal FIFO AND/reset equations separately audited',physical_claim=False),indent=2))
