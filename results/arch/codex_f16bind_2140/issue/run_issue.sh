#!/bin/bash
set -euo pipefail
mkdir -p issue_run
python3 - <<'PYS'
from pathlib import Path
s=Path('rtl/qwen_dv/f16/qfd_dv_f16_issue_tap.sv').read_text()
mutants={'wrong_user':s.replace('program_pidx[8:7]','program_pidx[1:0]'),'installed_epoch':s.replace(',command_context};',",{command_context[21:16],16'd7}};")}
cut=Path('rtl/qwen_dv/f16/qfd_dv_f16_dispatch_cut.sv').read_text()
Path('issue_run/wrong_pc.sv').write_text(cut.replace('.program_pidx(cmd_q[12:4])','.program_pidx(cmd_q[13:5])'))
for n,t in mutants.items():Path('issue_run/'+n+'.sv').write_text(t)
PYS
iverilog -g2012 -s tb_issue -o issue_run/selected.vvp rtl/qwen_dv/f16/qfd_dv_f16_issue_tap.sv rtl/qwen_dv/f16/qfd_dv_f16_dispatch_cut.sv results/arch/codex_f16bind_2140/issue/tb_issue.sv > issue_run/compile.log 2>&1
vvp issue_run/selected.vvp > issue_run/selected.log 2>&1
grep -q 'PASS F16_ACTUAL_DISPATCH_CUT' issue_run/selected.log
for case in wrong_user installed_epoch wrong_pc;do
 tap=rtl/qwen_dv/f16/qfd_dv_f16_issue_tap.sv
 cut=rtl/qwen_dv/f16/qfd_dv_f16_dispatch_cut.sv
 if [ "$case" = wrong_pc ];then cut=issue_run/wrong_pc.sv;else tap=issue_run/$case.sv;fi
 iverilog -g2012 -s tb_issue -o issue_run/$case.vvp "$tap" "$cut" results/arch/codex_f16bind_2140/issue/tb_issue.sv > issue_run/$case.compile.log 2>&1
 if vvp issue_run/$case.vvp > issue_run/$case.log 2>&1;then echo "MUTANT SURVIVED $case";exit 1;fi
 grep -q 'ACTUAL_DISPATCH_ID' issue_run/$case.log
done
cat issue_run/selected.log
cat issue_run/wrong_user.log
cat issue_run/installed_epoch.log
cat issue_run/wrong_pc.log
