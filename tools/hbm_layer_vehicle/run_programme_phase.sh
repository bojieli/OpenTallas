#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
/usr/bin/time -v verilator --binary --timing -O0 -Wno-fatal --top-module tb --Mdir obj_dir -j 2 -CFLAGS -O0 ot_dp_st.sv ot_sram_1r1w_512x256_m1_r2c2.sv ot_hgi_sfu_store_stripe_leaf_r10.sv ot_hgi_sfu_programme_store_r10.sv ot_hbm_static_cfg_collar.sv phase_units.sv tb_programme_phase.sv > compile.log 2>&1
/usr/bin/time -v ./obj_dir/Vtb > positive.log 2>&1
python3 - <<'PY'
from pathlib import Path
if 'PASS_NATIVE_PROGRAMME_PHASE'not in Path('positive.log').read_text():raise SystemExit('native positive completion missing')
PY
for case_id in 1 2 4; do
 set +e
 /usr/bin/time -v ./obj_dir/Vtb +MUT=$case_id > mutant_$case_id.log 2>&1
 case_rc=$?
 set -e
 python3 - "$case_id" "$case_rc" <<'PY'
import sys
from pathlib import Path
case,rc=int(sys.argv[1]),int(sys.argv[2]);s=Path(f'mutant_{case}.log').read_text();marks={1:['CONTROL_PHASE','IO_PHASE','STATUS_PHASE'],2:['CONTROL_PHASE','STATUS_PHASE','NATIVE_ROW_COUNTS'],4:['ASYNC_RESET_ASSERTION']}
if not rc or not any(m in s for m in marks[case]):raise SystemExit('mutant not caught by native contract: '+str((case,rc)))
print('PASS_NATIVE_MUTANT_CAUGHT',case)
PY
done
