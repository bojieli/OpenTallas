"""Source-bound native boundary and clock-root census; no synthesis or source edits."""
import argparse,collections,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('mapped');p.add_argument('--top',required=True);p.add_argument('--output');a=p.parse_args();path=pathlib.Path(a.mapped);m=json.loads(path.read_text())['modules'][a.top];cells=m['cells'];drivers=collections.defaultdict(list);loads=collections.defaultdict(list);aliases=collections.defaultdict(list)
def ff(t):return t.upper().startswith(('DFF','SDFF','ADFF','LATCH'))
def transparent(t):return bool(re.match('^(INV|BUF)',t))
for n,v in m['netnames'].items():
 for b in v['bits']:aliases[b].append(n)
for n,c in cells.items():
 for pn,bs in c['connections'].items():
  for b in bs:(drivers if c['port_directions'][pn]=='output' else loads)[b].append((n,c['type'],pn))
def origins(b,seen=None):
 if not isinstance(b,int):return {'constant'}
 seen=set() if seen is None else seen
 if b in seen:return {'cycle'}
 result=set()
 for cn,t,pn in drivers[b]:
  if transparent(t):
   for ip,bs in cells[cn]['connections'].items():
    if cells[cn]['port_directions'][ip]=='input':
     for ib in bs:result.update(origins(ib,seen|{b}))
  elif ff(t):result.add('FF_Q' if pn.startswith('Q') else 'FF_NON_Q')
  elif t.startswith('ot_sram_'):result.add('SRAM_OUTPUT')
  elif cells[cn].get('attributes',{}).get('blackbox') or t in ('ot_hbm_svc_static_sm_packed136_native_safe','ot_hbm_svg_landing_pair_native','ot_smh_calendar_static_x'):result.add('QUALIFIED_BOUNDARY_OUTPUT')
  else:result.add('COMBINATIONAL')
 return result or {'INPUT_OR_UNDRIVEN'}
def terminals(b,seen=None):
 seen=set() if seen is None else seen
 if b in seen:return set()
 result=set()
 for cn,t,pn in loads[b]:
  if transparent(t):
   for op,bs in cells[cn]['connections'].items():
    if cells[cn]['port_directions'][op]=='output':
     for ob in bs:result.update(terminals(ob,seen|{b}))
  else:result.add((cn,t,pn))
 return result
out={};inp={};clock=collections.Counter();clocktypes=collections.defaultdict(collections.Counter)
for n,v in m['ports'].items():
 if v['direction']=='output':
  bins=collections.Counter('+'.join(sorted(origins(b))) for b in v['bits']);out[n]=dict(width=len(v['bits']),origins=dict(bins))
 else:
  bins=collections.Counter();maxloads=0
  for b in v['bits']:
   ts=terminals(b);maxloads=max(maxloads,len(ts));bins['no_load' if not ts else 'all_FF_D' if all(ff(t) and pn=='D' for _,t,pn in ts) else 'all_FF_clock' if all(ff(t) and pn in ('CLK','CK','C','CLOCK') for _,t,pn in ts) else 'functional_or_mixed']+=1
  inp[n]=dict(width=len(v['bits']),bits=dict(bins),max_collapsed_load=maxloads)
for cn,c in cells.items():
 if ff(c['type']) or c['type'].startswith('ot_sram_'):
  for pn,bs in c['connections'].items():
   if (ff(c['type']) and pn in ('CLK','CK','C','CLOCK')) or (c['type'].startswith('ot_sram_') and pn.upper() in ('CLK','RCLK','WCLK','CLKR','CLKW')):
    for b in bs:
     label=('|'.join(aliases[b][:3]) or 'unnamed')+' bit='+str(b);clock[label]+=1;clocktypes[label][c['type']]+=1
report=dict(top=a.top,mapped_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rule='Output origins cross BUF/INV only; combinational paths not registered. Input capture counts physical terminal cells. Clock ports exempt only on sequential or SRAM cells.',input_ports=inp,output_ports=out,clock_roots=[dict(net=k,sinks=v,cell_types=dict(clocktypes[k])) for k,v in clock.most_common()]);s=json.dumps(report,indent=2);pathlib.Path(a.output).write_text(s) if a.output else print(s)
