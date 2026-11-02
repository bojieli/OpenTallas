from pathlib import Path
import re,json
b=Path('/srv/opentallas-scratch2/claude/die-head-48/dh53/v1/tile/run/results/asap7/dp_hd_tile/base')
s=(b/'6_final.v').read_text(); cells={};nets={}
for m in re.finditer(r'^\s*(\w+)\s+\\?(\S+)\s+\((.*?)\);',s,re.M|re.S):
 master,inst,body=m.groups(); ps={p:n.strip().lstrip('\\') for p,n in re.findall(r'\.(\w+)\(\s*([^)]*?)\s*\)',body)};cells[inst]={'master':master,'ports':ps}
 for p,n in ps.items():nets.setdefault(n,[]).append([inst,p])
pins=['u_core.c_cb[31]$_DFF_P_/QN', 'load_slew37926/Y', 'place11277/Y', 'wire37657/Y', '_48035_/Y', 'wire36546/Y', 'wire36545/Y', '_48040_/Y', 'wire36031/Y', 'wire36030/Y', 'rebuffer38085/Y', '_48211_/Y', 'wire35913/Y', 'wire35912/Y', '_48213_/Y', 'wire35903/Y', 'wire35902/Y', '_48214_/Y', '_48216_/Y', '_48222_/Y', '_48265_/Y', 'u_core.kh_gt$_DFF_P_/D']
ns=[cells[i.rsplit('/',1)[0]]['ports'][i.rsplit('/',1)[1]] for i in pins[:-1]];insts=set(i.rsplit('/',1)[0] for i in pins)
for n in ns:
 for i,p in nets.get(n,[]):insts.add(i)
coords={};netdefs={};section='';entry=[]
with (b/'6_final.def').open() as f:
 for l in f:
  l=l.lstrip()
  if l.startswith('COMPONENTS '):section='comp'
  elif l.startswith('NETS '):section='net'
  elif l.startswith('END COMPONENTS') or l.startswith('END NETS'):section=''
  if section and l.startswith('- '):entry=[l]
  elif entry:entry.append(l)
  if entry and ';' in l:
   txt=''.join(entry);entry=[];m=re.match(r'-\s+(\S+)',txt);name=m.group(1).replace('\\','') if m else ''
   if section=='comp' and name in insts:
    pos=re.search(r'\+ (PLACED|FIXED) \( (\d+) (\d+) \) (\S+)',txt);coords[name]={'placement':pos.groups() if pos else None,'master':cells.get(name,{}).get('master')}
   elif section=='net' and name in ns:netdefs[name]=txt
out={'nets':{n:{'connections':nets.get(n,[]),'route_def':netdefs.get(n)} for n in ns},'cells':{i:{**cells.get(i,{}),**coords.get(i,{})} for i in sorted(insts)}}
print(json.dumps(out,indent=1))
