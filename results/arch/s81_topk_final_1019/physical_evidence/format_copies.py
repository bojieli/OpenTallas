from pathlib import Path
import re,json,sys,collections
p=Path(sys.argv[1]);s=p.read_text()
names=sorted(set(re.findall(r'\\([^\s]*g_indexed_format\[\d+\]\.g_on\.f\[0\]\[0\])',s)))
# Mapped output pin connections must be distinct and explicitly flop-driven.
outputs={}
loads=collections.Counter()
for ctype,inst,ports in re.findall(r'\n\s*(\w+)\s+(\\?[^\s(]+)\s*\((.*?)\);',s,re.S):
 conns={pin:n.strip() for pin,n in re.findall(r'\.(\w+)\s*\(\s*([^()]+)\)',ports)}
 for pin,n in conns.items():
  if pin not in ('Y','Q','QN','QB'):loads[n]+=1
 if 'DFF' in ctype and 'g_indexed_format' in inst:
  q=conns.get('QN',conns.get('Q',conns.get('QB')))
  outputs[inst]={'q_net':q,'type':ctype}
for c in outputs.values():c['q_fanout']=loads[c['q_net']]
flag_loads={n:loads['\\'+n] for n in names}
report={'netlist':str(p),'declared_copy_nets':len(names),'distinct_flop_driven_copies':len(outputs),'copies':outputs,'flag_wire_loads':flag_loads,'max_flag_wire_loads':max(flag_loads.values(),default=0),'max_q_loads':max((c['q_fanout'] for c in outputs.values()),default=0),'pass_':len(names)==27 and len(outputs)==27}
Path(sys.argv[2]).write_text(json.dumps(report,indent=1)+'\n')
print('INDEXED13_KEPT_COPIES',report['pass_'],len(names),len(outputs))
if not report['pass_']:sys.exit(1)
