#!/bin/bash
# QW-KVATTN2 10-19: the KV-die ATTENTION STEP on the cut attention vehicle qwk_slice_attn (kvs14p netlist slice).
# One Verilator 5.050 build of tb_qwk_slice_attn (slice_smoke.py + drive_qwk_slice_attn.svh + kva_grp_map.svh), then the
# runs named in RUNS ("name:vecdir:plusargs..." entries, ';'-separated plusargs), all in parallel.
# usage: run_kv_attn.sh SLICE_DIR WORK KSRC "RUNS"
# Every netlist bench on a die with a land plan first runs tools/qwen_split/land_lag_sim.py annotate (TOK-QW facts rule);
# its verdict is recorded in WORK/land_lag.log (the KV die's landings are qkd_landsh*, not the compute die_glue family).
set -u
SL=$(readlink -f "$1"); W=$(mkdir -p "$2" && readlink -f "$2"); KSRC=$3; RUNS=$4
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../.." && pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
TOP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['top'])" $SL/slice.json)
python3 $R/tools/qwen_split/land_lag_sim.py annotate $SL --lanes ${KVA_LANES:-/dev/null} > $W/land_lag.log 2>&1; echo "land_lag_sim annotate exit $?" >> $W/land_lag.log
python3 $H/slice_smoke.py $SL/slice.json --out $W/tb_$TOP.sv --src 'i_n_clk_hbm_.*=hck' || exit 2
MAC=$KSRC/physical/qkd_astk_strip/macros
verilator --version > $W/verilator.version
O=$W/obj
if [ ! -x $O/Vtb_$TOP ] || [ -n "${KVA_REBUILD:-}" ]; then
/usr/bin/time -f "%e s %M KB" -o $W/build.time verilator --binary --timing -j ${KVA_J:-32} -O1 -Wno-fatal -Wno-lint -Wno-style \
    -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN --x-assign unique --x-initial unique \
    --top-module tb_$TOP -GMUT=0 -Mdir $O +define+SLICE_DRIVE=\"$H/drive_qwk_slice_attn.svh\" +define+IDLE_EDGES=200 \
    +define+TAIL_EDGES=50 +incdir+$H +incdir+$SL \
    -f $SL/$TOP.f $MAC/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v \
    $MAC/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v \
    $KSRC/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v $W/tb_$TOP.sv > $W/build.log 2>&1
fi
echo "build: $(cat $W/build.time 2>/dev/null)"
if [ ! -x $O/Vtb_$TOP ]; then echo "KVA_BUILD_FAIL $TOP (see $W/build.log)"; grep -m20 -E '%Error' $W/build.log; exit 3; fi
IFS=' ' read -r -a LIST <<< "$RUNS"
for e in "${LIST[@]}"; do
    n=${e%%:*}; rest=${e#*:}; vec=${rest%%:*}; pa=${rest#*:}; [ "$pa" = "$rest" ] && pa=""
    ( /usr/bin/time -f "%e s %M KB" -o $W/run_$n.time $O/Vtb_$TOP +verilator+rand+reset+2 +verilator+seed+1 \
        +verilator+error+limit+1000000 +VEC=$vec $(echo "$pa" | tr ';' ' ') > $W/run_$n.log 2>&1; echo "exit $?" >> $W/run_$n.log ) &
done
wait
for e in "${LIST[@]}"; do n=${e%%:*}
    echo "== $n: $(grep -hE 'SMOKE_(PASS|FAIL)' $W/run_$n.log | head -1) ($(cat $W/run_$n.time 2>/dev/null | tr '\n' ' '))"
    grep -hE '^KVA_(RESULT|DIE_ATTN|CYC|FAULT first|FIN)|^SMOKE_ERR' $W/run_$n.log | head -8
done
