from pathlib import Path
import re,json
b=Path('/srv/opentallas-scratch2/claude/kit-wave/s81_head/l48x/items/hd_st_n4/gen/hd_st_n4/run/results/asap7/dp_hd_st_n4/base')
s=(b/'6_final.v').read_text(); cells={};nets={}
for m in re.finditer(r'^\s*(\w+)\s+\\(\S+)\s+\((.*?)\);',s,re.M|re.S):
 master,inst,body=m.groups(); ps={p:n.strip().lstrip('\\') for p,n in re.findall(r'\.(\w+)\(\s*([^)]*?)\s*\)',body)};cells[inst]={'master':master,'ports':ps}
 for p,n in ps.items():nets.setdefault(n,[]).append([inst,p])
targets=['u_ft_d2_s0/_0823_','u_ft_u1_s0/_0782_','u_ft_d1_s0/_0784_'];ns=[cells[t]['ports']['A'] for t in targets]+['u_cland_u2_i/net43674'];insts=set(['u_cland_agg_4/ready_o$_SDFF_PN0_','u_cland_agg_5/ready_o$_SDFF_PN0_'])
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
