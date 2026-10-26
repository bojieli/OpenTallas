#!/usr/bin/env python3
"""Replay the actual r10 ABI fixture through the production partition guard."""
from pathlib import Path
import copy
import json
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_split.static_link_bind import validate_source_partition

def main():
 row=json.loads(Path(__file__).with_name('static_partition_fixture.json').read_text())
 args=[row[k] for k in ('physical_ports','source_ports','joins','fault_bits')]
 validate_source_partition(*args)
 # Identical shared-master contracts from multiple instances are legal.
 same=copy.deepcopy(args);same[3].append(dict(same[3][0],inst='same_master_other_instance'))
 validate_source_partition(*same)
 results=[]
 for mode in ('missing','repeat','unknown','wrong_width','input_fragment','wrong_contract','conflicting_contract'):
  a=copy.deepcopy(args)
  if mode=='missing':del a[0]['flt_transport_fault_7']
  elif mode=='repeat':a[2]['flt_transport_fault_7'][1]=[6];a[3][-1]['bit']=6
  elif mode=='unknown':a[0]['invented']=['pins',1]
  elif mode=='wrong_width':a[0]['flt_transport_fault_0'][1]=2
  elif mode=='input_fragment':a[1]['transport_fault'][1]='input'
  elif mode=='wrong_contract':a[3][-1]['bit']=0
  else:a[3].append(dict(a[3][0],bit=1))
  try:validate_source_partition(*a)
  except ValueError as e:results.append(dict(mode=mode,rejected=str(e)))
  else:raise AssertionError('accepted invalid actual source partition: '+mode)
 print(json.dumps(dict(verdict='PASS',source_bits=sum(w for w,d in row['source_ports'].values()),identical_instance_contracts='PASS',negative_controls=results),indent=2))
if __name__=='__main__':main()
