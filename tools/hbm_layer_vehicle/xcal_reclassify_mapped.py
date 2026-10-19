#!/usr/bin/env python3
"""Reclassify an existing mapped census without synthesis or source mutation."""
import argparse,collections,json,pathlib,re
p=argparse.ArgumentParser(description=__doc__);p.add_argument('mapped');p.add_argument('census');p.add_argument('--output',required=True);a=p.parse_args()
report=json.loads(pathlib.Path(a.census).read_text());top=report['top'];mod=json.loads(pathlib.Path(a.mapped).read_text())['modules'][top]
job={'clock_ports':['clk','clk_core','clk_bank0','clk_bank1','clk_calendar','clk_desc']}
aliases=collections.defaultdict(list)
for name,net in mod['netnames'].items():
    for bit in net['bits']:
        if isinstance(bit,int):aliases[bit].append(name)
loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
for name,c in mod['cells'].items():
    for port,bits in c['connections'].items():
        dest=drivers if c['port_directions'].get(port)=='output' else loads
        for bit in bits:
            if isinstance(bit,int):dest[bit].append([name,c['type'],port])
nets=[]
for bit,sinks in loads.items():
    names=aliases[bit];reset=any('rst' in n or 'reset_landing' in n or 'reset_' in n for n in names)
    clock_names=set(job.get('clock_ports',[]))|{job.get('clock_port','clk'),'clk_desc'}
    clock=any(n in clock_names for n in names) or all((c[1].startswith(('DFF','SDFF','DFFHQ','DFFASR','ot_sram_')) and c[2].upper() in ['CLK','CK','C','CLOCK']) for c in sinks)
    nets.append(dict(bit=bit,fanout=len(sinks),names=names,drivers=drivers[bit],reset=reset,clock=clock,sinks=sinks))
nets.sort(key=lambda x:x['fanout'],reverse=True)
# Collapse buffers/inverters recursively, including QN->INV->Q, without
# crossing any logical or sequential cell. Count unique physical input pins.
def collapse(bit,seen=None):
    seen=set() if seen is None else seen
    if bit in seen:return set(),set()
    seen=seen|{bit};terminal=set();visited={bit}
    for cn,ct,pt in loads[bit]:
        if re.match(r'^(INV|BUF)',ct):
            for op,bs in mod['cells'][cn]['connections'].items():
                if mod['cells'][cn]['port_directions'][op]=='output':
                    for ob in bs:
                        ts,vs=collapse(ob,seen);terminal.update(ts);visited.update(vs)
        else:terminal.add((cn,ct,pt))
    return terminal,visited
collapsed=[]
for n in nets:
    pins,visited=collapse(n['bit']);names=list(dict.fromkeys(x for b in visited for x in aliases[b]))
    reset=n['reset'] or any('rst' in x or 'reset_' in x for x in names)
    collapsed.append(dict(bit=n['bit'],names=names,fanout=len(pins),drivers=n['drivers'],reset=reset,clock=n['clock'],sinks=sorted(pins)))
collapsed.sort(key=lambda x:x['fanout'],reverse=True)
report.update(over32_data_control=[n for n in nets if n['fanout']>32 and not n['reset'] and not n['clock']],clock_networks=[n for n in nets if n['clock']],reset_networks=[n for n in nets if n['reset']],top50=nets[:50],buffer_collapsed_over32_data_control=[n for n in collapsed if n['fanout']>32 and not n['reset'] and not n['clock']],buffer_collapsed_reset_networks=[n for n in collapsed if n['reset']],clock_classifier='declared clock ports OR sequential/macro clock cell input pins; combinational C is data')
pathlib.Path(a.output).write_text(json.dumps(report,indent=2)+'\n')
print(top,'direct',len(report['over32_data_control']),'collapsed',len(report['buffer_collapsed_over32_data_control']))
