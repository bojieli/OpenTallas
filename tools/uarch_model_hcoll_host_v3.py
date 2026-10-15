#!/usr/bin/env python3
"""Actual raw-host target + native V3 quadrant composition budget."""
from uarch_model_hcoll_q_static_v3 import model as quadrant_model
from uarch_model_hcoll_program_join import model as target_model
import json

def model(npt=3,solo=True):
 q=quadrant_model(npt,solo)
 q.update(source_version='hcoll.host.quadrant.v3',host_target=52 if solo else '52+fixed QID1..3',
  assembler=target_model(),logical_clock_roots=q['logical_clock_roots']+1,
  assembler_root_FF_bound=3601,host_cfg_start_runtime_handshake=False,
  host_launch_to_native_start_edges=2,host_launch_to_first_uop_edges=5,
  host_launch_to_first_instruction_consumer_edges=6,
  lcp_producer_FF_to_local_launch_capture_edges=2,
  lcp_producer_FF_to_native_start_edges=4,lcp_producer_FF_to_first_uop_edges=7,
  lcp_producer_FF_to_first_consumer_edges=8,
  lcp_anchor='edge where actual loader LCP71 register Q first appears; overlay samples next edge',
  host_overlay_source='rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv',
  extra_joined_fault_report_edges=1,
  program_active_source='actual native hgi_busy, not a host-supplied alias',
  metadata_feedback='actual native issuer busy/fault/uop_v/pc6 production ports',
  identity='QID parameter fixed by physical quadrant; q3 QID0, q2 QID1..3',
  input_output_pin_counts='source-derived host_v3_join.json, clocks counted separately',
  mechanism_qualification='actual q2 native reduction composition; q3 parent not flattened by this gate',
  production_status='candidate composition; no physical or production-rate qualification')
 return q
if __name__=='__main__': print(json.dumps({'q3':model(3,True),'q2':model(2,False)},indent=2))
