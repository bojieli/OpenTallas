#!/bin/bash
# el1014-qwen-kvsys-elements: hub-level equivalence of the die-leaf hub (qkd_ahub_core + 13 tiles) against hub_t.
#   run_qkd_ahub_d_eq.sh pos OUT   five die relay configurations (r3 = SI_RLY 1; r4 = the hp4 kit: SI_RLY 1, RA_RLY 1, PV_RLY 1 (core hd4 defaults), one clock ck + regional reset pipe) x three seeds x 6 layers, every mo / out word exact
#                                  -> prints "PASS qkd_ahub_d eq all" and exits 0
#   run_qkd_ahub_d_eq.sh neg OUT   TB_MUT (one pl_rz bit forced at the core) -> prints "FAIL qkd_ahub_d mutant detected"
#                                  and exits 1 when the mismatch is seen (the loop expects fail)
# Run from the source root.  Verilator 5 (VL env, default the fleet copy).
set -u
MODE=$1; OUT=$2
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
R=rtl
SRC="$R/test/nearhbm/tb_qkd_ahub_d_eq.sv $R/hdc/nearhbm/ot_qkd_ahub_core.sv $R/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_t.sv \
 $R/hdc/nearhbm/ot_nhb_tiles.sv $R/hdc/nearhbm/ot_qkh_recip_leaf.sv $R/lib/ot_rst_pipe.sv $R/lib/ot_rst_relay.sv \
 $R/hdc/ot_hdc_delay.sv $R/hdc/ot_hdc_fp32_add_lat_nr.sv $R/hdc/ot_hdc_fp32_add_lat.sv $R/hdc/ot_hdc_fp32_mul_lat.sv \
 $R/hdc/ot_hdc_prefix.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 $R/hdc/ot_hdc_sfu.sv $R/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv $R/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv $R/hdc/ot_hdc_fastfp.sv"
mkdir -p "$OUT"
build() {  # build TAG defines...
  local t=$1; shift
  $VL --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+QKH_RECIP_LEAF \
      "$@" --top-module tb_qkd_ahub_d_eq --Mdir "$OUT/$t" -o Vtb $SRC > "$OUT/$t.build.log" 2>&1 || { echo "BUILD_FAIL $t"; tail -n 5 "$OUT/$t.build.log"; exit 3; }
}
if [ "$MODE" = neg ]; then
  build mut +define+TB_MUT
  r=$("$OUT/mut/Vtb" +LAYERS=6 +SEED=1 2>&1 | grep -E '^AHUB|^PASS|^FAIL'); echo "$r"
  echo "$r" | grep -q '^FAIL' && { echo "FAIL qkd_ahub_d mutant detected"; exit 1; }
  echo "mutant NOT detected"; exit 0
fi
ok=1
build r0
build r1 +define+R_ZW=1 +define+R_ZR=1 +define+R_RA=1 +define+R_SR=1 +define+R_PV=1 +define+R_Y=1 +define+R_RX=2 +define+R_PI=1 +define+R_SI=1
build r2 +define+R_ZW=2 +define+R_ZR=1 +define+R_RA=0 +define+R_SR=2 +define+R_PV=1 +define+R_Y=2 +define+R_RX=3 +define+R_PI=3 +define+R_SI=2
build r3 +define+R_SI=1
build r4 +define+R_SI=1 +define+R_RA=1 +define+R_PV=1 +define+QKD_AHUB_ONE_CK
for t in r0 r1 r2 r3 r4; do for sd in 1 7 23; do
  r=$("$OUT/$t/Vtb" +LAYERS=6 +SEED=$sd 2>&1 | grep -E '^AHUB|^PASS|^FAIL' | tr '\n' ' '); echo "$t seed $sd: $r"
  echo "$r" | grep -q 'PASS ahub_d == hub_t' || ok=0
  echo "$r" | grep -q 'disagree' && ok=0
done; done
[ $ok = 1 ] && { echo "PASS qkd_ahub_d eq all"; exit 0; }
echo "FAIL qkd_ahub_d eq"; exit 1
