#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
lines=(P/'base.log').read_text().splitlines();ages={};partials={}
for line in lines:
 m=re.fullmatch(r'NORM_PRODUCER leaf(\d+) norm_pin\d+ n_go_age(\d+) partial_age(\d+) data([0-9a-f]{8})',line)
 if m:ages[int(m[1])]=(int(m[2]),int(m[3]));partials[int(m[1])]=m[4]
assert sorted(ages)==list(range(80))and set(ages.values())=={(5,116)}
# The original late pd diagnostic can drift after p_v; use only valid-time dump.
valid=(P.parent/'valid_capture/actual_partials80.hex').read_text().split()
assert len(valid)==80
partials={i:word for i,word in enumerate(valid)}
assert 'BASE_RC=0\nPAYLOAD_RC=1\nAGE_RC=1\nGATE_PASS'in(P/'status.txt').read_text()
routes=json.loads((P.parent/'leaf_routes.json').read_text());native=json.loads((P/'native_params.json').read_text())
assert len(native['leaves'])==80 and all(r['a']['params']==dict(LA=6,LM=5)and r['b']['params']==dict(HW_STAGE=0,LA=6,LM=5)and r['vp_n_go_to_vn_edges']==0 and r['vn_chain_extra_edges']==0 for r in native['leaves'])
cohorts=[]
for sid in range(16):
 rows=[r for r in routes['leaves']if r['sid']==sid];groups={}
 for r in rows:groups.setdefault(r['crossing_plus_pdsk_edges']+116,[]).append(r['leaf'])
 ties=[g for g in groups.values()if len(g)>1]
 cohorts.append(dict(sid=sid,slice=rows[0]['slice'],path_plus_current_producer_pdsk_edges=[r['crossing_plus_pdsk_edges']+116 for r in rows],
  same_engine_forced_same_issue_leaf_groups=ties,issuer_only_stagger_feasible_necessary_condition=not ties))
result=dict(schema='opentallas.s81.current_norm_producer_boundary_constraints.v1',status='BLOCKED_CURRENT_PDSK_SLOT_COLLISION',
 source_top_sha256=routes['source_top_sha256'],producer=dict(VP_public_command_pin_to_n_go_edges=5,VP_public_command_pin_to_VN_b_partial_output_edges=116,
  boundary='drive public c_v/c_d immediately after edge t; first VP cv_c/cd_c capture t+1 included. Down transport ends before that capture at native leafdn_i*_q. VN_b output register included116; up begins at that output, no duplicate boundary capture',
  actual_partial_count=80,actual_partial_data=partials,clock_ps=833,source_sha256=json.loads((P/'stage.json').read_text())['source_sha256']),
 cohorts=cohorts,blocked_sids=[r['sid']for r in cohorts if r['same_engine_forced_same_issue_leaf_groups']],
 collector=dict(actual_source_sha256='59a53960b2c66851b14fbfcc615e451d380774ac483f2987a5f806abeb0cffa9',
  source_path='/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv',
  strict_fault_line=884,strict_fault='fb <= ((|pv) && pv != 5\'b11111) | ((|pv) && prun) | ...',
  launch_line=819,launch='if (|pv) begin prun <= 1\'b1; pi <= 3\'d0; end',
  buffering='PDSK is fixed per-leaf shift registers; pq byte capture exists but does not wait for or accumulate an asynchronous partial set before launch/fault'),
 candidate_not_applied=dict(affected_sids=[0,5],affected_slices=['u_s_0S','u_s_2N'],change='leaf2 PDSK2->3 only;15\'o01234->15\'o01334',
  extra_data_ff=64,extra_valid_ff=2,total_extra_ff=66,local_NORM_max_path_delta_edges=0,
  qualification='source/physical hardfreeze exception required; no RTL/plan/strap adoption, no physical area/timing proof'),
 go_readiness_qualified=False,global_exchange_qualified=False,physical_START_qualified=False,full_token=False,added_rtl_cycles=0)
(P/'composition_valid_capture.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],result['blocked_sids'],'producer116,80actualpartials, candidate unapplied')
