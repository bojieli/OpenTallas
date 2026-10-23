#!/bin/bash
set -euo pipefail
python3 - <<'PYS'
from pathlib import Path
p=Path('rtl/qwen_split/f16/qfd_sys_face_lctx3_core_f16.sv')
s=p.read_text()
assert s.count('{begin_v, rp_program_ready, rp_cap, rp_program_digest, rp_program_epoch}')==1
Path('auth_wrong_source.sv').write_text(s.replace('{begin_v, rp_program_ready, rp_cap, rp_program_digest, rp_program_epoch}', '{begin_v, rp_auth_v, rp_cap, rp_program_digest, rp_program_epoch}'))
p=Path('rtl/qwen_split/f16/qfd_sys_face_lctx3_wrapped_f16.sv');s=p.read_text()
assert s.count('assign f16_auth = f16_auth__ot_q;')==1
Path('auth_no_capture.sv').write_text(s.replace('assign f16_auth = f16_auth__ot_q;', 'assign f16_auth = f16_auth__ot_pr;'))
base=Path('results/arch/codex_f16bind_2140/sources.txt').read_text()
Path('wrong_sources.txt').write_text(base.replace('rtl/qwen_split/f16/qfd_sys_face_lctx3_core_f16.sv','auth_wrong_source.sv'))
Path('comb_sources.txt').write_text(base.replace('rtl/qwen_split/f16/qfd_sys_face_lctx3_wrapped_f16.sv','auth_no_capture.sv'))
PYS
iverilog -g2012 -I rtl/qwen_sys/d2d_static_20261015 -s tb_auth_export -o auth_export.vvp -f results/arch/codex_f16bind_2140/sources.txt results/arch/codex_f16bind_2140/tb_auth_export.sv > compile.log 2>&1
vvp auth_export.vvp > selected.log 2>&1
grep -q 'PASS F16_AUTH_EXPORT' selected.log
if grep -q 'ERROR:' selected.log; then cat selected.log; exit 1; fi
for case in wrong comb; do
  iverilog -g2012 -I rtl/qwen_sys/d2d_static_20261015 -s tb_auth_export -o "${case}.vvp" -f "${case}_sources.txt" results/arch/codex_f16bind_2140/tb_auth_export.sv > "${case}_compile.log" 2>&1
  if vvp "${case}.vvp" > "${case}.log" 2>&1; then echo "MUTANT SURVIVED $case"; exit 1; fi
  grep -Eq 'AUTH_CAPTURE|AUTH_COMB_LEAK|AUTH_RESET' "${case}.log"
done
cat selected.log
cat wrong.log
cat comb.log
