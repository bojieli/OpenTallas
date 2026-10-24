#!/bin/bash
# TOK-FUNC2-QW-OVL 10-21: 4-user overlapping-segment D2D link co-sim on the RELEASE masters (tb_d2d_ovl_mu_rel.sv:
# qfd_d2d_static_ovl_sf7 <-> qkd_d2d_static_ovl_sfm3, kit params), Verilator 5.050, repository root.  Same interface as
# run_d2d_ovl_mu.sh:  run_d2d_ovl_mu_rel.sh OUTDIR CALROOT [CONFIG ...]; CALROOT/cal_{pass,collide,slot,user} = the compiler
#   outputs (python3 -m qwen_static_schedule.mu_d2d_ovl --out CALROOT/cal_<m> [--mut <m>], from tools/).  One line a config:
#   <name> expect=<PASS|FAIL> got=<PASS|FAIL> -> OK | UNEXPECTED ; exit 0 only when every config met its expectation.
set -u
OUT=$1; CR=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015; S=rtl/qwen_sys/split_20261014; M=physical/asap7_memory_macros_v2
CONFIGS=("pass|PASS|pass|1" "asbuilt_one_playhead|FAIL|pass|0" "mut_collide|FAIL|collide|1" "mut_slot|FAIL|slot|1" "mut_user|FAIL|user|1")
# the two release masters' kit source lists (qfd_d2d_static_sf7w c3baef180, qkd_d2d_static_ovl_sfm3) + the OVL sequencer
SRC=("rtl/lib/ot_rst_pipe.sv" "$S/ot_qwen_crc_parallel.sv" "$S/ot_qwen_static_slot_link.sv" "$S/ot_qkvd_d2d_llr.sv"
 "$S/qkd_native_attention_record.sv" "$D/ot_qwen_d2d_static.sv" "$D/ot_qwen_d2d_services.sv" "$D/ot_qwen_d2d_dies.sv"
 "$D/ot_qwen_d2d_dies_ovl.sv" "$D/ot_qwen_d2d_safe5.sv" "$D/ot_qwen_d2d_safe7.sv" "$D/ot_qwen_d2d_dies_ovl_sf7.sv"
 "$D/ot_qwen_d2d_safe_fo.sv" "$D/ot_qwen_d2d_sfm.sv" "$D/ot_qwen_d2d_sfm3.sv" "$D/ot_qwen_d2d_cal_seq.sv" "$D/ot_qwen_d2d_ovl_seq.sv"
 "$M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$M/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192.v"
 "$M/d2d_sram_1r1w_64x137_m1_r2c2_p288/d2d_sram_1r1w_64x137_m1_r2c2_p288.v"
 "physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv" "rtl/test/qwen_split/tb_d2d_ovl_mu_rel.sv")
mkdir -p "$OUT"; "$V" --version > "$OUT/verilator.txt"
sha256sum "${SRC[@]}" "$0" "$CR"/cal_*/ovl.json > "$OUT/source.sha256" || exit 2
want=("$@")
one() {
  local name=$1 exp=$2 cal=$CR/cal_$3 ovl=$4 o=$OUT/$1
  mkdir -p "$o"
  "$V" --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
     -DOT_MEM_NO_INIT -I"$cal" --top-module tb_d2d_ovl_mu_rel -GOVL=$ovl -GCALDIR="\"$cal\"" --Mdir "$o/obj" "${SRC[@]}" \
     > "$o/build.log" 2>&1 || { echo "$name expect=$exp got=BUILD_FAIL -> UNEXPECTED"; grep -m6 '%Error' "$o/build.log"; return; }
  "$o/obj/Vtb_d2d_ovl_mu_rel" > "$o/run.log" 2>&1
  rm -rf "$o/obj"
  local got=FAIL; grep -q '^D2DOVL_PASS' "$o/run.log" && got=PASS
  echo "$name expect=$exp got=$got -> $([ $got = $exp ] && echo OK || echo UNEXPECTED)"
  grep -E '^D2DOVL_(USER|MEAS|REL|ERR|PASS|FAIL)' "$o/run.log" | sed 's/^/    /'
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
