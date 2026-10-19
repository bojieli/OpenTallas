#!/bin/bash
# MU-D2D-OVL 10-19: 4-user overlapping-segment D2D link co-sim (tb_d2d_ovl_mu.sv), Verilator 5.050, repository root.
# usage: run_d2d_ovl_mu.sh OUTDIR CALROOT [CONFIG ...]; CALROOT/cal_{pass,collide,slot,user} = the compiler outputs
#   (python3 -m qwen_static_schedule.mu_d2d_ovl --out CALROOT/cal_<m> [--mut <m>], from tools/).  One line a config:
#   <name> expect=<PASS|FAIL> got=<PASS|FAIL> -> OK | UNEXPECTED ; exit 0 only when every config met its expectation.
set -u
OUT=$1; CR=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015; S=rtl/qwen_sys/split_20261014
CONFIGS=("pass|PASS|pass|1" "asbuilt_one_playhead|FAIL|pass|0" "mut_collide|FAIL|collide|1" "mut_slot|FAIL|slot|1" "mut_user|FAIL|user|1")
SRC=("$S/ot_qwen_crc_parallel.sv" "$S/ot_qwen_static_slot_link.sv" "$S/ot_qkvd_d2d_llr.sv"
 "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv"
 "$D/ot_qwen_d2d_static.sv" "$D/ot_qwen_d2d_cal_seq.sv" "$D/ot_qwen_d2d_ovl_seq.sv" "rtl/test/qwen_split/tb_d2d_ovl_mu.sv")
mkdir -p "$OUT"; "$V" --version > "$OUT/verilator.txt"
sha256sum "${SRC[@]}" "$0" "$CR"/cal_*/ovl.json > "$OUT/source.sha256"
want=("$@")
one() {
  local name=$1 exp=$2 cal=$CR/cal_$3 ovl=$4 o=$OUT/$1
  mkdir -p "$o"
  "$V" --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
     -DOT_MEM_NO_INIT -I"$cal" --top-module tb_d2d_ovl_mu -GOVL=$ovl -GCALDIR="\"$cal\"" --Mdir "$o/obj" "${SRC[@]}" \
     > "$o/build.log" 2>&1 || { echo "$name expect=$exp got=BUILD_FAIL -> UNEXPECTED"; grep -m6 '%Error' "$o/build.log"; return; }
  "$o/obj/Vtb_d2d_ovl_mu" > "$o/run.log" 2>&1
  rm -rf "$o/obj"
  local got=FAIL; grep -q '^D2DOVL_PASS' "$o/run.log" && got=PASS
  echo "$name expect=$exp got=$got -> $([ $got = $exp ] && echo OK || echo UNEXPECTED)"
  grep -E '^D2DOVL_(USER|MEAS|ERR|PASS|FAIL)' "$o/run.log" | sed 's/^/    /'
}
pids=()
for c in "${CONFIGS[@]}"; do
  IFS='|' read -r name exp cal ovl <<< "$c"
  if [ ${#want[@]} -gt 0 ] && ! printf '%s\n' "${want[@]}" | grep -qx "$name"; then continue; fi
  one "$name" "$exp" "$cal" "$ovl" > "$OUT/$name.summary" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
cat "$OUT"/*.summary | tee "$OUT/SUMMARY.txt"
! grep -q 'UNEXPECTED' "$OUT/SUMMARY.txt"
