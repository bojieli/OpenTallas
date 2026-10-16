#!/usr/bin/env python3
"""Source-derived ABI and explicit unqualified hardware/model costs for b2 join."""
import sys,json,hashlib,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
from die_port_bind import parse_modules
files=['rtl/qwen_split/qfd_res_train_half_b2_wrappers.sv','rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_b2_parent.sv','rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_tree_b2.sv','rtl/qwen_split/qfd_b2_train_source.sv','rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_b2.sv','rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_b2.sv','rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3.sv','rtl/qwen_split/qfd_res_train_half_b2.sv','rtl/qwen_split/qfd_res_train_issue_b2.sv']
out=[]
for x in files:
 t=(R/x).read_text()
 parsed=re.sub(r'`ifdef OT_QFD_B2_AM_MUT\n.*?`else\n(.*?)`endif',r'\1',t,flags=re.S)
 for m in parse_modules(re.sub(r'^`(?:ifdef|endif).*\n','',parsed,flags=re.M),x):
  assert not m.port_parse_errors,m.port_parse_errors
  out.append(dict(source=x,sha256=hashlib.sha256(t.encode()).hexdigest(),top=m.name,ports={n:dict(direction=m.ports[n][0],bits=m.width(n,m.env()))for n in m.order}))
a=dict(status='SOURCE_ONLY_UNQUALIFIED',sources=out,
 cycles=dict(controller_execution_added_logic=0,train_source_copy_edges=1,cold_reset_release_edges=1,am_station_added_vs_old_master=0,vm_ingress_added_logic=0,return_ro=6,return_pin_input=1),
 calendar='Six parallel halftrain F=D+HB*NH+t*max(8NH,stride)+i*NH+j. NH(split7..11)=4,2,1,3,1. Actual24 capturebanks and64 headonlymarkers. VM PAR_RB1/NB6. Per-route padding unassigned.',
 sizing=dict(capture_bits_per_half=24*2212,capture_and_emit_ff_per_half=24*(2212+551+1),parent_output_ff_per_half=551,parent_control_ff_census='66507 total genericFF before cold reset stations; +25 resetFF in successor, rerun pending',clock_entries_per_half=25,per_bank_ff=2764,
 max_capture_bits_per_edge=6*2213,max_result_bits_per_edge=6*551,
 new_external_vm_payload_pins=3*551,tt_extra_control_pins=3*341+3*26+6+1+50,
 normal_cycles_from_capture_zero_to_last_payload_pin='D+5NH+(tiles-1)*max(8NH,stride)+7NH+NH-1+1 (observe after output-register edge); marker-only has one fewer edge',
 outline_um=None,area='UNASSIGNED: actual source cell area/pin/clock assignment required; no inherited serializer grant'),
 limits=['No inherited physical view','Whole native layer/token qualification OPEN','Other VM writers and die path ages require exact composed static calendar','Native E3 specialized master still requires its physical closure','Controller underlying arithmetic retained; literal ABI bench does not substitute full controller compute qualification'])
p=R/'results/arch/qwen_split_compute_1014/b2_join/interfaces.json';p.write_text(json.dumps(a,indent=2)+'\n')
