#!/usr/bin/env bash
# HARD-S81-SERDES-1 2026-11-13: lock-step bench of the ot_pdie_serdes_col LANE rows (tb_s81_col_lane) and the loopback
# latency bench tb_s81_col_rlat built with the LANE defines.
# usage: [LANE="PIN TXA RXI RXO"] run_serdes_lane_bench.sh MODE OUTDIR      (LANE default "3 4 4 3")
#   MODE: lane (PASS) | mut8 / mut9 / mut10 (FAIL) | xtx / xrx (FAIL: expected shift one edge off) |
#         rlat0 (reference loopback latency, no LANE define) | rlatd (+define+OT_S81_SERDES_LANE) | rlat (LANE defines; with RT_EXPECT=<cycles> PASS needs that latency)
# EXTRA_DEFS="A B ..." adds +define+ for every mode (both columns and the peer), e.g. the vB cone set under LANE.
# Verilator (fleet image); never on localhost.
set -u
mode=${1:?mode}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link; M=$R/physical/asap7_memory_macros
VL=${VERILATOR:-verilator}
set -- ${LANE:-3 4 4 3}; P=$1; A=$2; I=$3; O=$4
g="-GPIN=$P -GTXA=$A -GRXI=$I -GRXO=$O"; d=""; top=tb_s81_col_lane
case $mode in
  lane) ;; mut8) g="$g -GMUT=8";; mut9) g="$g -GMUT=9";; mut10) g="$g -GMUT=10";;
  xtx) g="$g -GXTX=1";; xrx) g="$g -GXRX=1";;
  rlat0) top=tb_s81_col_rlat; g="";;
  rlat) top=tb_s81_col_rlat; g=""
        d="+define+OT_S81_SERDES_LANE_PIN=$P+OT_S81_SERDES_LANE_TXA=$A+OT_S81_SERDES_LANE_RXI=$I+OT_S81_SERDES_LANE_RXO=$O";;
  rlatd) top=tb_s81_col_rlat; g=""; d="+define+OT_S81_SERDES_LANE";;      # the plan define: PIN 3 / TXA 4 / RXI 5 / RXO 3
  *) echo "LANE BAD_MODE $mode"; exit 2;; esac
for x in ${EXTRA_DEFS:-}; do d="$d +define+$x"; done
[ -n "${RT_EXPECT:-}" ] && g="$g -GEXPECT_LAT=$RT_EXPECT"
[ -n "${RLAT_RST:-}" ] && g="$g -GRST_EDGES=$RLAT_RST"   # rlat modes only: power-up reset length
$VL --version > "$out/verilator.version" 2>&1
$VL --binary --timing -j ${COL_J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTITOP +incdir+$L \
  $d --top-module $top $g --Mdir "$out/obj" -o tb "$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" \
  "$L/ot_s81_kp4_bm.sv" "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" \
  "$L/ot_s81_kp4_dec.sv" "$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv" "$L/native/ot_s81_kp4_dec_native_flat.sv" \
  "$L/lp/ot_s81_kp4_dec_native_flat_lp.sv" "$R/rtl/common/landed_parent/ot_pl_land.sv" "$L/col/ot_pdie_serdes_col.sv" \
  "$M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" \
  "$L/col/$top.sv" > "$out/build.log" 2>&1 || { echo "LANE BUILD_FAIL $mode"; tail -5 "$out/build.log"; exit 2; }
"$out/obj/tb" +verilator+seed+${COL_SEED:-11} > "$out/run.log" 2>&1
grep -E '^(ERR|TX lock|RCK lock|%Error)' "$out/run.log" | head -3
grep -E '^TB_S81_(COL_LANE|COL_RLAT)' "$out/run.log" | tail -2
grep -qE '^TB_S81_(COL_LANE|COL_RLAT) PASS$' "$out/run.log"
