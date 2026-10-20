#!/usr/bin/env python3
"""Enumerate diagnostic D4K2 data-only windows; never emits timing exceptions."""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--mut-overwrite',action='store_true');p.add_argument('--endpoint-plan');a=p.parse_args();rows=[];T=833.333;D=4;K=2
for n in range(16,32):
 slot=(n-K)%D;launch=n-K;overwrite=launch+(2 if a.mut_overwrite else D)
 for phase in [-.4,0,.4]:
  capture=n+phase;setup=capture-launch;hold=overwrite-capture
  rows.append(dict(slot=slot,writer_launch_edge=launch,receiver_capture_edge=n,receiver_phase_T=phase,capture_time_T=capture,next_same_slot_overwrite_edge=overwrite,setup_age_T=round(setup,6),hold_gap_T=round(hold,6)))
minimum_setup=min(r['setup_age_T']for r in rows);minimum_hold=min(r['hold_gap_T']for r in rows);ok=minimum_setup>=1.6 and minimum_hold>=1.6
s=Path('rtl/physical/qcluster/qfd_c_land_safe.sv').read_bytes();o=dict(schema='opentallas.cb16.bank_window.v1',diagnostic_only=True,rtl_sha256=hashlib.sha256(s).hexdigest(),source='b25f19be20174b6f98218ed6fa9ca6641e99b166',D=D,K=K,T_ps=T,phase_envelope_T=[-.4,.4],minimum_setup_age_T=minimum_setup,minimum_hold_gap_T=minimum_hold,minimum_setup_age_ps=minimum_setup*T,minimum_hold_gap_ps=minimum_hold*T,enumeration_pass=ok,rows=rows,endpoint_scope='write b0..b3 flopQ to read o flopD DATA ONLY; select/status/writtenflags/epochs ordinary timing; no flags included without independent proof',release_ready=False,blockers=['actual TT/FF phi-R/rootspread envelope plus150ps setup/100ps hold reserves not yet certified in parent','local reset-order fixture and logical MODEL witnesses exist; actual placed/native reset epochs and transactions remain unqualified','routed bank/endpoint geometry405um, native launch/capture budgets and parent clock composition not qualified','finite max/min actual Tcl dispatch requires tool/schema owner and root review; no timing exceptions emitted'])
o['mut_overwrite']=a.mut_overwrite
if a.endpoint_plan:
 import sys
 sys.path.insert(0,str(Path(__file__).parent));from qc_safe_graph import extract
 graph=extract();epraw=Path(a.endpoint_plan).read_bytes();ep=json.loads(epraw);seams=[];ordinary=[]
 for bus in ep['bindings']:
  if bus['kind']=='written_flags':ordinary.append(bus);continue
  if bus['kind']!='bank_data':continue
  seam=dict(bus)
  for side in ['src','dst']:
   endpoint=dict(bus[side]);logical=endpoint['inst'].rsplit('_p',1)[0];endpoint['clock_domain']=graph['nodes'][logical]['region'];endpoint['parent_clock_port']='ck_'+endpoint['clock_domain'];endpoint['hard_child_clock_pin']='ck';seam[side]=endpoint
  seam.update(exception_authorized=False,endpoint_rule='DATA write-bank FFQ -> selected registered read-data FFD only; hard-macro bank pins require equivalent qualified native arc bounds',setup_TT_register_inequality='dmax <= K*T + delta_register_clock_R_minus_W_TT - tCQ_W_TT_max - tsetup_R_TT - Usetup - 150ps',hold_FF_register_inequality='dmin >= (K-D)*T + delta_register_clock_R_minus_W_FF + thold_R_FF + Uhold + 100ps - tCQ_W_FF_min',delta_scope='Actual paired register-clock edge arrival delta at TT/FF, including compensated root phase/delivery and local child clock insertion; not unqualified whole-bank extrema',dispatch_status='NO Tcl/schema emitted; tool/schema owner and ROOT approval required')
  seams.append(seam)
 o.update(endpoint_plan_sha256=hashlib.sha256(epraw).hexdigest(),physical_data_seams=seams,physical_data_bits=sum(v['bits']for v in seams),written_flag_ordinary_bindings=ordinary,written_flag_bits=sum(v['bits']for v in ordinary),setup_reserve_ps=150,hold_reserve_ps=100,clock_and_native_arc_terms_qualified=False,local_reset_fixture='results/arch/qwen_cluster_1017/q_cluster16/bench_safe_epoch_resetorders',logical_epoch_fixture='results/arch/qwen_cluster_1017/q_cluster16/bench_safe_fabric_v7')
Path(a.out).write_text(json.dumps(o,indent=1)+'\n');print('BANK_WINDOW',ok,'setupT',minimum_setup,'holdT',minimum_hold)
if not ok:raise SystemExit(1)
