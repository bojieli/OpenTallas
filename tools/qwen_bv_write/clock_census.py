#!/usr/bin/env python3
"""Audit actual elaborated source E3 Q-bit/root mapping, with a clock-tie negative."""
import argparse,collections,copy,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
def audit(m):
 roots=m['ports']['write_ck']['bits'];owned={};counts=collections.Counter()
 for c in m['cells'].values():
  if c['type']in['$dff','$adff']:
   clk=c['connections']['CLK'][0]
   for bit in c['connections']['Q']:
    assert bit not in owned,'duplicate Q owner'
    owned[bit]=clk;counts[clk]+=1
 assert len(roots)==240 and len(set(roots))==240
 assert set(counts)==set(roots),'missing/extra actual clock roots'
 for prefix,banks,base,law in [('bw',64,0,8),('ws',16,64,10)]:
  widths=dict(data=512,line=law,mask=16,we=1)
  if prefix=='bw':widths['src']=3
  for n,w in widths.items():
   bits=m['ports']['o_'+prefix+'_'+n]['bits'];assert len(bits)==banks*w
   for bank in range(banks):
    for bit in range(w):
     root=3*(base+bank)+(bit//256 if n=='data'else 2)
     assert owned[bits[bank*w+bit]]==roots[root],f'{prefix}[{bank}].{n}[{bit}] root mismatch'
 assert len(owned)==43184
 return dict(source_Q_bits=len(owned),distinct_clock_roots=len(counts),sinks_histogram=dict(collections.Counter(counts.values())),max_sinks=max(counts.values()),all_43184_Q_bits_have_exact_expected_root=True)
m=json.loads(a.netlist.read_text())['modules']['dut'];result=audit(m)
mut=copy.deepcopy(m);first=next(c for c in mut['cells'].values()if c['type']=='$dff'and len(c['connections']['Q'])==256)
first['connections']['CLK']=[m['ports']['write_ck']['bits'][-1]]
try:audit(mut)
except AssertionError as e:result['clock_tie_mutant']='observed FAIL: '+str(e)
else:raise AssertionError('clock tie escaped')
result.update(scope='source-extracted full64BW+16WS E3 actual RTL only; physical clocks/phase/native limits unqualified',netlist_sha256=hashlib.sha256(a.netlist.read_bytes()).hexdigest())
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
