"""Read-only 455fc9ff4 BUF/INV terminal-pin rule, with exact clock/reset classes."""
import argparse,collections,functools,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('mapped');p.add_argument('--analyzer-sha256');p.add_argument('--top',required=True);p.add_argument('--clock-port',action='append',default=[]);a=p.parse_args();path=pathlib.Path(a.mapped);m=json.loads(path.read_text())['modules'][a.top];cells=m['cells'];aliases=collections.defaultdict(list);loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
for n,v in m['netnames'].items():
 for b in v['bits']:
  if isinstance(b,int):aliases[b].append(n)
for n,c in cells.items():
 for port,bs in c['connections'].items():
  for b in bs:
   if isinstance(b,int):(drivers if c['port_directions'][port]=='output' else loads)[b].append((n,c['type'],port))
inputbits={b for v in m['ports'].values() if v['direction']=='input' for b in v['bits']};clockbits={b for n in a.clock_port for b in m['ports'][n]['bits']};resetbits={b for n,v in m['ports'].items() if v['direction']=='input' and ('rst' in n or 'reset' in n) for b in v['bits']}
def ff(t):return t.upper().startswith(('DFF','SDFF','ADFF','LATCH'))
def collapse(bit,seen=None):
 seen=set() if seen is None else seen
 if bit in seen:return set(),set()
 seen=seen|{bit};terminal=set();visited={bit}
 for cn,ct,pt in loads[bit]:
  if re.match(r'^(INV|BUF)',ct):
   for op,bs in cells[cn]['connections'].items():
    if cells[cn]['port_directions'][op]=='output':
     for ob in bs:
      ts,vs=collapse(ob,seen);terminal.update(ts);visited.update(vs)
  else:terminal.add((cn,ct,pt))
 return terminal,visited
rows=[]
for bit in list(loads):
 pins,visited=collapse(bit);names=list(dict.fromkeys(x for b in visited for x in aliases[b]));clock=bit in clockbits or bool(pins) and all(ff(t) and port in ('CLK','CK','C','CLOCK') for _,t,port in pins);reset=bit in resetbits or any(ff(t) and port in ('RESETN','SETN','RN','SN','RESET','SET') for _,t,port in pins)
 typ='INPUT' if bit in inputbits else 'FF_Q' if any(ff(t) for _,t,_ in drivers[bit]) else 'SRAM_Q' if any(t.startswith('ot_sram_') for _,t,_ in drivers[bit]) else 'LOGIC'
 rows.append(dict(bit=bit,names=names,fanout=len(pins),direct_pin_loads=len(loads[bit]),source_type=typ,drivers=drivers[bit],clock=clock,reset=reset,sinks=sorted(pins)))
rows.sort(key=lambda x:x['fanout'],reverse=True);bad=[r for r in rows if not r['clock'] and not r['reset'] and r['fanout']>32];resets=[r for r in rows if r['reset']];sources=[r for r in rows if r['source_type'] in ('INPUT','FF_Q','SRAM_Q') and not r['clock']];report=dict(top=a.top,analyzer_sha256=a.analyzer_sha256 or hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),mapped_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rule='455fc9ff4 recursive unique terminal(cell,type,inputport), BUF/INV collapsed; C clock only on sequential cells',no_resynthesis=True,max_data_control=max((r['fanout'] for r in rows if not r['clock'] and not r['reset']),default=0),over32_data_control=bad,max_reset=max((r['fanout'] for r in resets),default=0),reset_top20=resets[:20],source_over32=[r for r in sources if r['fanout']>32],top20=rows[:20]);print(json.dumps(report,indent=2))
