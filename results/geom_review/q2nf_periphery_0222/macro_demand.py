from pathlib import Path
import re,json,collections
k=Path('/srv/opentallas-scratch2/claude/codex-q2nf-0222/kit')
s=(k/'run/results/asap7/hbc_ot_q2nf_rest/base/1_2_yosys.v').read_text()
rows=[];nets=collections.defaultdict(list)
for m in re.finditer(r'(ot_sram_\w+)\s+(\\\S+|\S+)\s*\((.*?)\n\s*\);',s,re.S):
 master,inst,body=m.groups();ports={};uniq=set()
 for p,c in re.findall(r'\.(\w+)\((.*?)\)(?:,|\s*\n|$)',body,re.S):
  if p=='clk':continue
  c=re.sub(r"\d+'[bBoOdDhH][0-9a-fA-FxXzZ_]+",'',c)
  tok=re.findall(r'\\\S+|[A-Za-z_$][\w$]*(?:\[\d+\])?',c)
  ids=[v.rstrip(',} ').lstrip('\\')for v in tok]
  ports[p]=len(ids);uniq.update(ids)
  for v in set(ids):nets[v].append((inst.lstrip('\\'),p))
 rows.append(dict(master=master,inst=inst.lstrip('\\'),signal_port_tokens=ports,unique=len(uniq)))
shared={n:ps for n,ps in nets.items()if len({x[0]for x in ps})>1}
r=dict(macros=rows,distinct_signal_nets=len(nets),shared_signal_nets=len(shared),pin_incidence=sum(sum(x['signal_port_tokens'].values())for x in rows),shared=shared)
out=Path('/srv/opentallas-scratch2/claude/codex-q2nf-0222/macro_demand.json');out.write_text(json.dumps(r,indent=1));print({k:v for k,v in r.items()if k not in['macros','shared']});print('by_master',dict(collections.Counter(x['master']for x in rows)))
