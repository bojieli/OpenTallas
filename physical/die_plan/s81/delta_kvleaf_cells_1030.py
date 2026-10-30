"""Correct four measured S81 soft-partition censuses; no physical/RTL change."""
import argparse,json
from pathlib import Path
COUNTS={1:1904350,3:1940880,4:1931578,5:1891769}
def apply(plan):
 for t,n in COUNTS.items():
  ty=plan['partition_types'][f'ot_s81sl_kv_leaf__t{t}']
  ty['cells']=n
 return plan
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('output');a=p.parse_args()
 j=json.loads(Path(a.plan).read_text());apply(j);Path(a.output).write_text(json.dumps(j,indent=1)+'\n')
