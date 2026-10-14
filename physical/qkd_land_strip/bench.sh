#!/usr/bin/env bash
# KV landing strip masters (el1013-qwen-kvstrips): exact benches.
#   bench.sh rd  OUT_DIR [GM [PM]]    4 x qkd_land_pc + qkd_land_grp (landing read path of one row engine)
#   bench.sh emb OUT_DIR [MUT [PM]]   qkd_land_emb + 32 x qkd_land_pc against the monolithic ot_qfd_emb_strip
# Prints "PASS qkd_land_<x> ..." (rc 0) or "FAIL qkd_land_<x> ..." (rc 1).
set -u
WHAT=$1; OUT=$2; M1=${3:-0}; M2=${4:-0}
R=$(cd "$(dirname "$0")/../.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
K=$R/rtl/qwen_sys/kv_die_20261009
SRC="$K/qkd_land_strip.sv $K/ot_qkvd_emb_strip_c.sv $K/ot_qkvd_kv_merge.sv $K/ot_qkvd_fifo.sv $K/ot_qkvd_fifo_sl.sv $K/ot_qkvd_fifo_sb.sv"
if [ "$WHAT" = rd ]; then TOP=tb_qkd_land_rd; G="-GGM=$M1 -GPM=$M2"; X=""
else TOP=tb_qkd_land_emb; G="-GMUT=$M1 -GPM=$M2"; X="$R/rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_strip.sv"; fi
$V --binary --timing -O2 -j ${JOBS:-4} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
   --top-module $TOP $G --Mdir "$OUT/obj" $SRC $X "$R/rtl/test/qwen_kv_die/$TOP.sv" > "$OUT/build.log" 2>&1 \
   || { tail -20 "$OUT/build.log"; echo "FAIL qkd_land_$WHAT build"; exit 1; }
"$OUT/obj/V$TOP" > "$OUT/run.log" 2>&1
grep -E '^(MISMATCH|PASS|FAIL)' "$OUT/run.log" | head -8
if grep -q "^PASS qkd_land_$WHAT" "$OUT/run.log" && ! grep -q '^FAIL' "$OUT/run.log"; then exit 0; fi
echo "FAIL qkd_land_$WHAT mutant $M1/$M2 detected"; exit 1
