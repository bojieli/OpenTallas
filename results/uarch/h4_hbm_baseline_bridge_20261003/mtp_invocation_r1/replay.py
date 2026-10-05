#!/usr/bin/env python3
"""Frozen source iteration-control example; no numerical golden invocation."""
import argparse, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
s=importlib.util.spec_from_file_location('mtp_example',ROOT/'tools/h4_hbm_mtp_invocation_model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def derive():
 binding=[dict(rank=17,SM=3,scope='protocol_control',directory_sha256='explicit-control-directory',provider_reference='explicit-control-state-provider')]
 plan=m.InvocationCompiler().compile(0,7,9,[10,11,12,13,14],[10,11,100,101,102,103],2,binding)
 spans=[dict(eventID=v['eventID'],ns=1.0,source_receipt='protocol-'+v['eventID'],clock_source='positive protocol test; not sourceSS clock',scope='protocol_control') for v in plan['invocations']]
 return {'model.json':m.canonical(m.model()),'selected_control_iteration.json':m.canonical(plan),
 'selected_control_intervals.json':m.canonical(m.compose_selected_intervals(plan,spans))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args();out=HERE if a.verify else a.out
 if out is None:raise ValueError('explicit output')
 out.mkdir(parents=True,exist_ok=True)
 for name,raw in derive().items():
  if a.verify:
   if (out/name).read_bytes()!=raw:raise ValueError('exact MTP source-control replay '+name)
  else:(out/name).write_bytes(raw)
 print('PASS exact MTP source-control replay; actual native MTP admission remains FAIL')
if __name__=='__main__':main()
