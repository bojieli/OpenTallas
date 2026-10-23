#!/bin/bash
set -euo pipefail
python3 - <<'PYS'
from pathlib import Path
p=Path('rtl/qwen_dv/f16/qfd_dv_cmd_cal_mu_f16.sv');s=p.read_text()
base=Path('results/arch/codex_f16bind_2140/context/context_seq_bench.py').read_text()
variants={'live_epoch':s.replace('pst[ru],f16_epoch[ru]','pst[ru],start_epoch'),'wrong_user':s.replace('pst[ru],f16_epoch[ru]','pst[ru],f16_epoch[(ru+1)%NU]'),'refused_start':s.replace('if(go_u[f16_u]&&!start_bad&&g_cnt_nz)','if(go_u[f16_u]&&g_cnt_nz)')}
for n,text in variants.items():
 assert text!=s
 path='results/arch/codex_f16bind_2140/context/mut_'+n+'.sv';Path(path).write_text(text)
 Path('results/arch/codex_f16bind_2140/context/mut_'+n+'.py').write_text(base.replace(str(p),path))
PYS
for case in live_epoch wrong_user refused_start;do
 if python3 -I "results/arch/codex_f16bind_2140/context/mut_$case.py" --work "$PWD/context_causal_$case" --mut 0 --verilator verilator --jobs 2 > "context_causal_$case.log" 2>&1;then echo "MUTANT SURVIVED $case";exit 1;fi
 # A behavioral identity mismatch must be the cause, never build/infra failure.
 grep -q F16_CAL_IDENTITY "context_causal_$case.log" || { cat "context_causal_$case.log";exit 1; }
 echo "PASS actual calendar causal $case rejected F16_CAL_IDENTITY"
done
