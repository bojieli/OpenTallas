"""Move col_h10_r0_p1 tap28 into the existing south macro-edge corridor.

The old tap at the east edge of u_r0.u_e4 takes both its south-facing data
flops and the east SRAM flops, max L1 reach217.917um. South-edge(879.12)
serves both clusters within161.271um; keep port count/identity and constraints.
"""
import argparse,json,re,copy
from pathlib import Path
NAMES=('col_h10_r0_p1__t1__cl574cc59d','col_h10_r0_p1__t1__cl911743eb')
def apply(raw):
 for n in NAMES:
  q=next(q for q in raw['partition_types'][n]['clock']['added_taps'] if q['name']=='clk_t28')
  assert q['xy'] in ([1150.308,954.666],[1150.308,879.12]),(n,q)
  q['xy']=[1150.308,879.12]
 return raw
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('src');p.add_argument('dst');a=p.parse_args()
 text=Path(a.src).read_text();expected=apply(copy.deepcopy(json.loads(text)))
 for n in NAMES:
  i=text.index(json.dumps(n)+': {')
  head,tail=text[:i],text[i:]
  tail,count=re.subn(r'("name": "clk_t28",\s+"xy": \[\s+1150[.]308,\s+)(954[.]666|879[.]12)',lambda m:m[1]+'879.12',tail,count=1)
  assert count==1,n
  text=head+tail
 assert json.loads(text)==expected
 Path(a.dst).write_text(text)
