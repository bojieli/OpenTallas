#!/usr/bin/env bash
# rd1 response calendar bench (COMPILER-CAL-3).  usage: run_bench.sh OUTDIR
# Cases: baseline RD1=0 +0 must pass (old body); rd1 body RD1=1 with the compiler calendar shifted +0 / +1 / +2:
# +1 must pass (every issued read/write answered, status 0); +0 and +2 must trip the sticky fault status[0].
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(realpath -m "${1:?output directory required}")
mkdir -p "$OUT"; cd "$ROOT"
D=rtl/hbm_accel/generic/vm/static
B=results/hbm_compiler_cal_rd1_1111
run() { # name rd1 shift trip
    python3 -I "$B/gen_resp_cal.py" "$OUT/$1.resp.mem" "$3" "$((10+$2))" >"$OUT/$1.gen.log"
    iverilog -g2012 -s tb_vms_hub_rd1_resp -Ptb_vms_hub_rd1_resp.RD1="$2" -Ptb_vms_hub_rd1_resp.EXPECT_TRIP="$4" -Ptb_vms_hub_rd1_resp.PERIOD="$((10+$2))" \
        -Ptb_vms_hub_rd1_resp.RESP_FILE="\"$OUT/$1.resp.mem\"" -o "$OUT/$1.vvp" "$D/ot_vms_hub_static.sv" "$B/tb_vms_hub_rd1_resp.sv" \
        >"$OUT/$1.build.log" 2>&1
    vvp "$OUT/$1.vvp" >"$OUT/$1.log" 2>&1 && rc=0 || rc=$?
    rm -f "$OUT/$1.vvp"
    echo "$1 rd1=$2 shift=+$3 expect_trip=$4 rc=$rc: $(grep -E 'RD1_BENCH|FATAL|fatal' "$OUT/$1.log" | head -1)"
    [[ $rc == 0 ]]
}
run base_old_body_p0 0 0 0
run rd1_p0 1 0 1
run rd1_p1 1 1 0
run rd1_p2 1 2 1
echo RD1_CAL_BENCH PASS
