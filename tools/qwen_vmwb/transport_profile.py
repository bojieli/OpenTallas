#!/usr/bin/env python3
"""Emit source-pinned VM transport cycle candidates without claiming physical release."""
import argparse,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def profile(ro):
 if type(ro)is not int or ro<1:raise ValueError('RO must be a positive implemented relay depth')
 count=8*(22+14*ro)+(6*(10+ro)+255)//256
 files=['rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory.sv','rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv','rtl/qwen_sys/dvm_20261014/ot_qfd_vm_q_export_fixed.sv','rtl/qwen_sys/vm_native_physical_20261015/qvm_bank_banked_native.sv','rtl/qwen_sys/vm_native_physical_20261015/qvm_su_bank_native.sv']
 return dict(schema='opentallas.qwen-vm-transport-candidate.v1',return_ro=ro,
  physical_profile_status='UNQUALIFIED',compiler_adopted=False,
  source_sha256={f:hashlib.sha256((R/f).read_bytes()).hexdigest()for f in files},
  fixed_core_cycles=dict(read_edges=12+ro,VM_response_edges=12+ro,SU_VL=13+ro,SU_request_to_answer_edges=14+ro,
   q_start_to_first_output_edges=13+ro,q_start_to_last_output_edges=44+ro,
   delta_vs_production_RO1=ro-1),
  relay_hardware=dict(master='qvm_data256_native',tiles=count,ff_bits=count*256,outline_um=[25.92,51.84],area_um2=count*25.92*51.84,
   unchanged_hard_memory_banks=dict(row=64,operand=48),distinct_relay_clock_entries=count),
  schedule='Compiler must use these fixed ages for every dependency, slot, occupancy, write visibility and deadline. No runtime credits or ready-driven rescheduling.',
  e2e_token_cost_status='UNMEASURED',accepted_cost_ledger_admitted=False,
  blockers=['New return/read-control leaf physical views and exact native timing','All relay homes, assigned pins and actual clock phi-R','Every incident boundary connection and cut after PG/clock/OBS/via subtraction','Static full programme native composition and measured token cost','Remaining parent write/control hardening'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--return-ro',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.write_text(json.dumps(profile(a.return_ro),indent=2)+'\n');print(a.out)
