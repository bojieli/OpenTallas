#!/bin/bash
# slicertl_bench.sh <outdir> <part>   (cwd = repo root / staged archive; FLEET only via ot-run; Verilator 5.050)
# S81-SLICERTL (10-20): benches of the slice RTL changes the S81 slice parents need before they bind on the die.
#   c1k8       parameter-free ot_s81sl_slice_c1k8 (die top of the landed C1 parent) in the lp.py lockstep bench vs the
#              flat ot_s81sl_slice_c1x reference                                                   expect LP_LOCKSTEP PASS
#   c1k8_mut   same, wrapper mutated DLK0 1 -> 2 (wrong landed-leaf relay depth)                  expect LP_LOCKSTEP FAIL
#   n32a / n32h      ot_s81sl_lep_mu_{a,h}_n32 == ot_s81sl_lep_mu_{a,h} #(RX_SRAM/IN_PIPE/NATIVE32 1)  expect N32EQ PASS
#   n32a_mut / n32h_mut   reference = default-param top (the die source before)                     expect N32EQ FAIL
#   bind_c1k8  strict die_port_bind of ot_s81sl_slice_c1k8 and ot_s81sl_slice_c1x_k8_lp (no tied/open/undriven child pin)
# The regenerated lp.py benches (landed/*/..._lp_bench.sh), tools/s81_slice/pl_slice/pl_slice_bench.sh,
# tools/s81_slice/slice_eng_bench.sh and tools/s81_slice/lepmu_parent_checks.sh run as they are.
set -u; O=$(realpath -m $1); P=$2; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | head -1
L=rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8
VF="--binary -j ${J:-8} -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-WIDTH -O1"
c1k8() {   # $1 = 0 wrapper as committed | 1 wrapper DLK0 mutant
  local d=$O/c1k8_m$1; mkdir -p $d
  SRCS=$(sed -n 's/^SRCS="\(.*\)"$/\1/p' $L/ot_s81sl_slice_c1x_k8_lp_bench.sh | sed "s#$L/tb_ot_s81sl_slice_c1x_k8_lp.sv##")
  [ -n "$SRCS" ] || { echo "SETUP_FAILED no SRCS"; exit 4; }
  local W=$L/ot_s81sl_slice_c1k8.sv
  [ $1 = 1 ] && { sed 's/\.DLK0(1)/.DLK0(2)/' $W > $d/ot_s81sl_slice_c1k8_mut.sv; grep -q 'DLK0(2)' $d/ot_s81sl_slice_c1k8_mut.sv || exit 4; W=$d/ot_s81sl_slice_c1k8_mut.sv; }
  # the wrapper adds one level: the child-lockstep probes u_lp.<child> become u_lp.u_lp.<child>
  sed -E -e 's/ot_s81sl_slice_c1x_k8_lp #\([^)]*(\([^)]*\)[^)]*)*\) u_lp \(/ot_s81sl_slice_c1k8 u_lp (/' -e 's/\bu_lp\.u_/u_lp.u_lp.u_/g' $L/tb_ot_s81sl_slice_c1x_k8_lp.sv > $d/tb.sv
  grep -q 'ot_s81sl_slice_c1k8 u_lp (' $d/tb.sv || { echo "SETUP_FAILED tb rewrite"; exit 4; }
  $V $VF --top-module tb_ot_s81sl_slice_c1x_k8_lp -DDSFD_PQ_STATIC_X2 $SRCS $W $d/tb.sv -Mdir $d/obj > $d/build.log 2>&1 \
    && $d/obj/Vtb_ot_s81sl_slice_c1x_k8_lp > $d/run.log 2>&1
  r=$(grep -o 'LP_LOCKSTEP [A-Z]*.*' $d/run.log 2>/dev/null | head -1); echo "C1K8 MUT $1: ${r:-NO_RESULT (see $d/build.log)}"
  if [ $1 = 0 ]; then case "$r" in "LP_LOCKSTEP PASS"*) exit 0;; esac; else case "$r" in "LP_LOCKSTEP FAIL"*) exit 0;; esac; fi; exit 1
}
n32() {    # $1 H (0 a | 1 h), $2 MUT
  local d=$O/n32_h$1_m$2; mkdir -p $d
  local S="rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_1r1w.sv
    rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv
    physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
    physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v
    physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
    rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_n32.sv
    rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_lep_mu_n32_eq.sv"
  $V $VF --top-module tb_s81sl_lep_mu_n32_eq -GH=$1 -GMUT=$2 $S -Mdir $d/obj > $d/build.log 2>&1 && $d/obj/Vtb_s81sl_lep_mu_n32_eq > $d/run.log 2>&1
  r=$(grep -o 'N32EQ [A-Z]*.*' $d/run.log 2>/dev/null | head -1); echo "N32 H=$1 MUT $2: ${r:-NO_RESULT (see $d/build.log)}"; grep -m3 '%Error' $d/build.log
  if [ $2 = 0 ]; then case "$r" in "N32EQ PASS"*) exit 0;; esac; else case "$r" in "N32EQ FAIL"*) exit 0;; esac; fi; exit 1
}
bind_c1k8() {
  rc=0
  for top in ot_s81sl_slice_c1k8 ot_s81sl_slice_c1x_k8_lp; do
    f=$O/$top.v; src=$L/$top.sv
    if [ $top = ot_s81sl_slice_c1x_k8_lp ]; then
      # C1 has no band port: bi is unread and bo = 513'd0 (the die's mode_unused 'hb0' / spare-out rules own them, as for
      # ot_s81sl_slice HB 0).  Strip exactly those two ports and the constant so the check covers every CHILD pin.
      src=$O/c1x_k8_lp_noband.sv
      grep -v -E "^    input wire \[1103:0\] bi,$|^    output wire \[512:0\] bo,$|^    assign bo = 513'd0;$" $L/$top.sv > $src
      [ $(( $(wc -l < $L/$top.sv) - $(wc -l < $src) )) -eq 3 ] || { echo "SETUP_FAILED band strip"; exit 4; }
    fi
    python3 tools/s81_slice/bind_form.py $src $top $f || exit 3
    [ $top = ot_s81sl_slice_c1k8 ] && python3 tools/s81_slice/bind_form.py $L/ot_s81sl_slice_c1x_k8_lp.sv ot_s81sl_slice_c1x_k8_lp $O/lp_for_wrapper.v
    extra=""; [ $top = ot_s81sl_slice_c1k8 ] && extra="--rtl-file $O/lp_for_wrapper.v"
    python3 tools/die_port_bind.py $f --top $top --define DSFD_PQ_STATIC_X2 $extra \
      --rtl-file rtl/common/landed_parent/ot_pl_land.sv --rtl-file rtl/common/landed_parent/ot_pl_land_field_copies.sv --rtl-file rtl/common/landed_parent/ot_pl_land_reset_forest.sv --rtl-file rtl/common/landed_parent/ot_pl_land_kept_enable.sv \
      --rtl-file rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_glue.sv \
      --prefer rtl/hdc/v41/ot_hdc_fsqrt.sv --prefer rtl/hdc/ot_hdc_fp32_mul_lat.sv \
      --prefer-list $L/ot_s81sl_slice_c1x_k8_lp_bench.sh --out $O/bind_$top.json > $O/bind_$top.log 2>&1
    r=$?; echo "BIND $top exit $r"; tail -5 $O/bind_$top.log; [ $r -eq 0 ] || rc=1
  done
  echo "BIND_EXIT $rc"; exit $rc
}
case $P in
  c1k8) c1k8 0;; c1k8_mut) c1k8 1;;
  n32a) n32 0 0;; n32h) n32 1 0;; n32a_mut) n32 0 1;; n32h_mut) n32 1 1;;
  bind_c1k8) bind_c1k8;;
  *) echo "unknown part $P"; exit 2;;
esac
