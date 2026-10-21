#!/usr/bin/env python3
"""Distinct unclosed successor specs; same exact5de geometry, balanced prefix RTL.
Source proof/reset/real48+lateCFG receipts are mandatory. Actual native<=32 must
pass before launching layout; a new CLOSED record is required before binding.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'tools/ref_tile/specs_qw2_slice2_native';out.mkdir(parents=True,exist_ok=True)
 for variant,label,old in [('main','pfxa','qfd_dv_s8_station_tail1'),('fallback','pfxb','qfd_dv_s8_station_tail1_b')]:
  s=json.loads((R/f'tools/qwen_dv/s8_station_prefix_base/{variant}.json').read_text())
  name='qfd_dv_s8_station_tail1_'+label
  s['name']=name
  s['job'].update(owner='CODEX-Q-CB16-SLICE',branch='codex/q-s8-resume-1021',tag=label,
   purpose='Exact4state associative AND prefix repair; same1356state lines/ports/cycles, real48/reset proofs; original5de TT failure preserved',
   benches=[],views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}')
  s['job']['extra_paths']+=['physical/qwen_die_masters/io_ref_skew.sdc','physical/qwen_die_masters/io_flop_at_pins.tcl','physical/qwen_die_masters/out_flop_release.tcl','physical/common_flow']
  # No duplicated broad bench: exact actual executed evidence is pinned below.
  s['source_proof']={'math_sha256':hashlib.sha256((R/'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv').read_bytes()).hexdigest(),
   'full_registered_four_state':'results/arch/codex_slice2_native_1021/resume1340/prefix_reset_4d9/receipt.json',
   'selected_real48_and_late_cfg':'results/arch/codex_slice2_native_1021/resume1340/prefix_tail_363/receipt.json',
   'fixed_jb8_causal':'results/arch/codex_slice2_native_1021/resume1340/fixedjb8_40fcc/receipt.json',
   'mechanism':'results/arch/q_station_prefix_1021/FOUR_STATE_CERTIFICATE.json'}
  s['structural_change']='Distinct unclosed prefix successor: balanced33leaf AND tree, original XOR/synchronous reset network and all1356seq lines retained. No cycle/port/clock/geometry change; no oldviewalias. '+s.get('structural_change','')
  # All geometry fields compare exactly to the historical5de spec.
  b=json.loads((R/f'tools/qwen_dv/s8_station_prefix_base/{variant}.json').read_text())
  for k in ['top','sources','params','clock_port','reset_ports','outline','macros','pins','pin_ranges','pin_regs','reset_landing','route']:
   assert s[k]==b[k],k
  p=out/(name+'.json');p.write_text(json.dumps(s,indent=1)+'\n');print(p.relative_to(R))
if __name__=='__main__':main()
