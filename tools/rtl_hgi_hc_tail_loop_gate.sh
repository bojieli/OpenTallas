#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "${1:?output directory}")
mkdir -p "$OUT"
cd "$ROOT"
python3 tools/lower_hbm_hc_tail_loop_calendar.py --out "$OUT"
SOURCES=(rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_programme_mtp_static.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_program_stripe_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/tb_hgi_hc_tail_loop_issuer.sv)
/usr/bin/time -v -o "$OUT/compile.time" iverilog -g2012 -s tb_hgi_hc_tail_loop_issuer -o "$OUT/gate.vvp" "${SOURCES[@]}" >"$OUT/compile.log" 2>&1
(cd "$OUT"; /usr/bin/time -v -o positive.time vvp gate.vvp >positive.log 2>&1)
grep 'HC_TAIL_LOOP PASS' "$OUT/positive.log"
set +e
(cd "$OUT"; /usr/bin/time -v -o mutant.time vvp gate.vvp +MUTANT >mutant.log 2>&1)
rc=$?
set -e
[[ $rc != 0 ]];grep 'FATAL:.*tail counter/slot mismatch' "$OUT/mutant.log"
rm "$OUT/gate.vvp"
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);paths=sys.argv[2:]+['tools/lower_hbm_hc_mtp_static_calendar.py','tools/lower_hbm_hc_tail_loop_calendar.py','tools/rtl_hgi_hc_tail_loop_gate.sh']
r={'scope':'actual two-programme-SRAM HC issuer looped tail control only, no arithmetic or physical qualification','source_sha256':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in paths},'positive':'PASS','actual_counter_state_mutant':'KILLED','runs':[6,8,8,6],'period':497,'sink_divisor':7,'sink_launch_relative':203,'sink_capture_relative':492,'tail_result_expected_relative':493,'TAIL_LOOP_default':0,'all51_idle_zero':True,'logs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
