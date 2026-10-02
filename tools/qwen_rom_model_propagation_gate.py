#!/usr/bin/env python3
"""Fail-closed, source-bound propagation audit of the Qwen physical MAC price.

Replays the existing unified model's program/timing engine at unchanged TP4,
G6144, SU64, LV7, with only its arithmetic-latency input changed from the old
price to the pinned physical target. No RTL, simulator, P&R or rate adoption.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()


def replay_delta(context, target_extra=55, priced_extra=54):
 import uarch_model as U
 import arch_budget_qwen3 as Q
 import hdc_timing as T
 import hdc_isa as I
 import hdc_program as P
 shape=dict(Q.Q,NH=8,KV=2,FF=Q.Q['FF']//4,V=Q.Q['V']//4)
 original_sw=I.SU_WIDTH
 try:
  I.SU_WIDTH=64
  prog=P.build_program(Q.capped_layout(6144,None,shape))
 finally:
  I.SU_WIDTH=original_sw
 dyn=dict(H=Q.Q['H'],half=Q.Q['HD']//2,HD=Q.Q['HD'])
 wires=U.QWEN_W12_TP4_ME_EXTRA_SS
 measured=[]
 for extra in (priced_extra,target_extra):
  k=dict(T.K,me_lat=T.K['me_lat']+wires+extra+Q.SCALE_MUL_CYCLES,red_lv=7)
  issue_times,cycles=T.simulate(prog,context-1,groups=6144,dyn_shape=dyn,su_width=64,k=k)
  measured.append((issue_times,cycles))
 issue_delta=[b-a for a,b in zip(measured[0][0],measured[1][0])]
 me=[i for i,f in enumerate(prog) if f.get('unit')==I.UNIT_ME]
 return dict(context=context,TP=4,groups=6144,SU=64,LV=7,wire_cycles=wires,
  issued_me_instructions=len(me),weight_me_instructions=sum(not prog[i].get('me_wsrc') for i in me),
  kv_me_instructions=sum(bool(prog[i].get('me_wsrc')) for i in me),
  priced_arithmetic_extra=priced_extra,target_arithmetic_extra=target_extra,
  total_cycles_delta=measured[1][1]-measured[0][1],max_issue_time_shift=max(issue_delta),
  me_issue_deltas=[dict(instruction=i,kind='kv' if prog[i].get('me_wsrc') else 'weights_or_head',
                       issue_shift=issue_delta[i]) for i in me],
  program_sha256=hashlib.sha256(json.dumps(prog,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
  expected_scope='Python analytical sequencer replay, INT8 post-tree scale priced once. No cycle-exact RTL, collective/service/fill timing or published token-rate change.')


def run_gate():
 import qwen_rom_integration_preflight as J
 import uarch_model as U
 physical=ROOT/'results/rtl/qwen_rom_sidecar_20261002/tile_i518_terminal/00_physical.json'
 record=json.loads(physical.read_text());target=record['design']['parameters']
 for name,expected in J.ARITH.items():
  if target.get(name)!=expected:raise ValueError('Physical record parameter mismatch: '+name)
 target_extra=J.latency_extra(6144,target['ACC_LAT'],target['TREE_LAT'],target['MUL_LAT'])
 priced_extra=U.QWEN_SS['me_lat_extra']-U.QWEN_W12_TP4_ME_EXTRA_SS
 paths=['tools/uarch_model.py','tools/arch_budget_qwen3.py','tools/hdc_timing.py','tools/hdc_program.py',
  'tools/hdc_isa.py','tools/qwen_rom_integration_preflight.py','rtl/hdc/ot_qwen_w12_matvec.sv',
  'rtl/hdc/ot_qwen_rom_tile_w12.sv','rtl/test/tb_qwen_me_partition_w12.sv',
  'configs/models/qwen3-8b.json',str(physical.relative_to(ROOT))]
 pins={p:sha(ROOT/p) for p in paths}
 rows=[replay_delta(context,target_extra,priced_extra) for context in (1,8192)]
 if pins!={p:sha(ROOT/p) for p in paths}:raise ValueError('Source changed during analytical replay')
 mismatch=target_extra!=priced_extra
 return dict(schema='opentallas.qwen-rom-model-propagation-gate.v1',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  status='fail' if mismatch else 'pass',source_stable=True,source_sha256=pins,
  physical_raw_status=record['status'],physical_commit=record['git']['commit'],physical_target=target,
  target_extra=target_extra,priced_extra=priced_extra,model_price_joined=not mismatch,rows=rows,
  seven_runtime_gaps=list(J.MAPPING),
  propagation_requirements=['Driver must pass ACC7/TREE7/MUL6/FAST1/KV_PREP3 to both tile and die.',
   'Die and generated-core declarations and parameter forwarding must reach the spine with identical values.',
   'The global-KV result does not qualify KV_LOCAL1, KV_NH2, KV_VB131072, actual slice fill/read/mask/collision behavior.',
   'Model price must include MUL6: longest-tree +55, rather than +54; token replay delta must remain source-pinned.',
   'Same-source connected numerical gate, contextual MAC/macro SS setup and FF hold at 60ps/25ps, hub routing and actual die fit/power remain required.'],
  build_ready=False,adoption=False,new_jobs=0,
  objective='Keep current ROM die-count freedom; minimum single-user latency remains primary. This fixed TP4 replay binds the existing job and does not select a future die count.',
  claim_boundary='Analytical price-join FAIL, preserved independently of raw physical ERROR. The +217-cycle counterexample is not measured RTL timing, a failed new hardware lever, or rate adoption.')


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);a=ap.parse_args()
 if a.result.exists():ap.error('Refusing to overwrite a verdict')
 result=run_gate();result['verifier_sha256']=sha(Path(__file__))
 a.result.parent.mkdir(parents=True,exist_ok=True)
 with a.result.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(dict(status=result['status'],priced_extra=result['priced_extra'],target_extra=result['target_extra'],
  rows=[{k:r[k] for k in ['context','issued_me_instructions','total_cycles_delta','max_issue_time_shift']} for r in result['rows']]),indent=2))
 if result['status']!='pass':raise SystemExit(1)


if __name__=='__main__':main()
