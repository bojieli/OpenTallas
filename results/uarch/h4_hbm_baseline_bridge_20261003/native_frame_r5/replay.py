#!/usr/bin/env python3
"""Cold representative protocol controls; no production/checkpoint arithmetic."""
import argparse, importlib.util, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def derive():
 t=module('frame_examples',ROOT/'tests/test_h4_hbm_native_frame_emitter.py')
 t.FrameEmitterTests.setUpClass();case=t.FrameEmitterTests();m=t.m
 a,r=case.runtime();case.complete(a,r)
 profile={k:dict(ns=1.0,domain='PROTOCOL_CONTROL_ONLY',source='explicit positive protocol exercise; NOT prospective hardware bound') for k in m.COSTS}
 return {'model.json':m.canonical(m.model()),'selected_protocol_plan.json':m.canonical(case.plan),
 'selected_protocol_calendar.json':m.canonical(m.calendar(case.plan,profile)),
 'selected_protocol_completion.json':m.canonical(dict(native_owner64=case.command['owner_tag'],native_generation64=case.command['generation'],
 child_acceptances=len(a.parents[0]['accepted']),retained_children=len(r.children),matched_reverse_children=len(r.reverse),
 continued_captures=r.capture_releases,parent_ready=r.parent_ready(),production_operand_views_admitted=False,
 arithmetic_executed=False,hardware_qualified=False))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true');args=p.parse_args()
 data=derive();out=HERE if args.verify else args.out
 if out is None:raise ValueError('explicit output')
 out.mkdir(parents=True,exist_ok=True)
 for name,raw in data.items():
  if args.verify:
   if (out/name).read_bytes()!=raw:raise ValueError('exact representative replay '+name)
  else:(out/name).write_bytes(raw)
 print('PASS exact native-frame protocol controls; production operand views and physical admission remain FAIL')
if __name__=='__main__':main()
