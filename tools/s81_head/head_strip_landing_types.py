#!/usr/bin/env python3
"""Separate equal-geometry HEAD spine ribbon masters by their landing mask."""
import argparse,copy,json
from pathlib import Path

def split(plan):
 p=copy.deepcopy(plan);aliases={}
 for side,rxbus in [('w','bw_i'),('e','be_i')]:
  old='hd_spn_'+side+'shim'
  if old not in p['partition_types']:continue
  t=p['partition_types'].pop(old)
  for role in ('rx','tx'):
   n=old+'_'+role;nt=copy.deepcopy(t);nt['module']=t['module']+'_'+role
   nt['note']=nt.get('note','')+' Landing-mask identity '+role+'; geometry/data circuitry unchanged.'
   p['partition_types'][n]=nt;aliases[n]=old
  for q in p['partitions']:
   if q['type']==old:q['type']=old+('_rx' if q['name'].endswith('_'+rxbus+'_shim') else '_tx')
 return p,{'type_alias':aliases,'physical_delta':'none','data_cycle_delta':0,'purpose':'RX link_i landed; TX link_i is same-region strip link'}

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('--out',required=True);a.add_argument('--report',required=True);a=a.parse_args();p,r=split(json.load(open(a.plan)));Path(a.out).write_text(json.dumps(p,indent=1));Path(a.report).write_text(json.dumps(r,indent=1));print(json.dumps(r))
if __name__=='__main__':main()
