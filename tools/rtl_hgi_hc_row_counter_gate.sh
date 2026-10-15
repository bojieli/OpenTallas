#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "${1:?output directory}")
mkdir -p "$OUT"
cd "$ROOT"
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,'tools')
from lower_hbm_hc_mtp_static_calendar import lower
for n in (6,8):
 words,_=lower('row',first_consumer_cycle=5,sink_divisor=7,sink_phase=0,row=0,slot=0,clear=True,npos=n,early=True)
 Path(sys.argv[1],f'n{n}.mem').write_text(''.join(f'{w:064x}\n' for w in words))
PY
SOURCES=(rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_programme_mtp_static.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_programme_mtp_static_div_reference.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_program_stripe_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/tb_hgi_hc_row_loop_counter.sv)
/usr/bin/time -v -o "$OUT/compile.time" iverilog -g2012 -s tb_hgi_hc_row_loop_counter -o "$OUT/gate.vvp" "${SOURCES[@]}" >"$OUT/compile.log" 2>&1
(cd "$OUT"; /usr/bin/time -v -o positive.time vvp gate.vvp >positive.log 2>&1)
grep 'HC_ROW_COUNTER PASS' "$OUT/positive.log"
set +e
(cd "$OUT"; /usr/bin/time -v -o mutant.time vvp gate.vvp +MUTANT >mutant.log 2>&1)
rc=$?
set -e
[[ $rc != 0 ]];grep 'FATAL:.*valid51 mismatch' "$OUT/mutant.log"
rm "$OUT/gate.vvp"
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);paths=sys.argv[2:]+['tools/lower_hbm_hc_mtp_static_calendar.py','tools/rtl_hgi_hc_row_counter_gate.sh']
r={'scope':'actual two-SRAM per issuer, fixed HC production24-row programmes; arithmetic/physical/throughput not qualified','source_sha256':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in paths},'reference_commit':'ee0dab7dc','positive':'PASS','mutant':'KILLED valid51 row-id mismatch','production_programmes':{'npos6':2,'npos8':2,'rows_per_programme':24,'periods':[1080,1400]},'mechanisms':['All51pins exact each valid output edge','Actual programme raw/ordinal/active/done/fault identical every checked edge','First start, earliest back-to-back starts, reset mid-execution and fresh start','Idle51pins nowzero; old division idleleak explicitly retained in log'],'logs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
