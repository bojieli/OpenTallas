#!/bin/bash
# HBM-HUB-RTL-1 11-11 (tag hbm-hub-gather-phase): reader at the padded hub round trip (GATHER_PHASE 174 ne / 161 nw).
# Run from the repo root: bash rtl/hbm_accel/generic/peers/static_hc/run_gather_phase.sh OUT [BASE_REF]
#   BASE_REF (default origin/main) supplies the pre-fix sources for the negative controls.
# 1 sim  tb_hgi_hc_gather_phase: RP 23 (unpadded reference) / 174 / 161, NPOS 1 and 3: PASS vs the token lowering
#        schedule (gather_period max(24,RP+1)); MIX logs diffed: padded == reference shifted (RP-23)*(1+pos) edges,
#        same data/pos/row (EQ_CYCLE_SHIFTED); RP 23 MIX log of the pre-fix reader == fixed reader (unchanged logic).
# 2 neg  VMLAT=RP+1 (late return) FAIL; PERIOD override RP+2 FAIL; pre-fix reader at RP 174 aborts ($fatal).
# 3 lint yosys read_verilog -defer -sv + hierarchy -check (rtl_lint form) of ot_hbm_hc_q_static GATHER_PHASE 174/161:
#        pre-fix rtl/ q_static (no GATHER_PERIOD) + fixed reader PASS; fixed q_static + fixed reader PASS;
#        pre-fix rtl/ q_static + pre-fix bundle reader (the failing kit mix) FAIL with the $fatal (negative control).
# 4 YC1  no 8'(...) cast in a concat member of either ot_hgi_dma_back_static_vp4_banks.sv copy; yosys parses both.
# 5 regression rtl/test/tb_hbm_hc_q_static (MUT 0 PASS, 1..4 FAIL) with the fixed reader + q_static.
set -u
O=$(realpath -m "${1:?OUT}"); REF=${2:-origin/main}; mkdir -p $O/old; rc=0
cat > $O/sram_bb.v <<'BB'
(* blackbox *)
module ot_sram_1r1w_1024x256_m2_r2c2 (input wire clk, input wire r_ce_in, input wire [9:0] r_addr_in, output wire [255:0] rd_out,
    input wire w_ce_in, input wire [9:0] w_addr_in, input wire [255:0] wd_in, input wire [255:0] w_mask_in,
    input wire [1:0] rr_en, input wire [17:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
endmodule
BB
YOSYS=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
H=rtl/hbm_accel/generic/peers/static_hc; BH=physical/die_plan/hbm/bind/r18h5_bundle/$H
TB=$H/tb_hgi_hc_gather_phase.sv
git show $REF:$H/ot_hgi_hc_gathered_mix_reader_static.sv > $O/old/rtl_reader.sv
git show $REF:$BH/ot_hgi_hc_gathered_mix_reader_static.sv > $O/old/bundle_reader.sv
git show $REF:$H/ot_hbm_hc_q_static.sv > $O/old/rtl_q_static.sv
ok(){ echo "OK   $*"; }; bad(){ echo "BAD  $*"; rc=1; }
sim(){ # name reader params...
  local n=$1 r=$2; shift 2; local P=""; for p in "$@"; do P="$P -P tb_hgi_hc_gather_phase.$p"; done
  iverilog -g2012 $P -o $O/$n.vvp $TB $r > $O/$n.comp 2>&1 || { echo "COMPILE_FAIL" > $O/$n.log; return; }
  vvp -n $O/$n.vvp > $O/$n.log 2>&1; grep -h "MIX " $O/$n.log > $O/$n.mix; }
R=$H/ot_hgi_hc_gathered_mix_reader_static.sv
for c in "ref3 RP=23 VMLAT=23 NPOS=3" "ref1 RP=23 VMLAT=23 NPOS=1" "ne3 RP=174 VMLAT=174 NPOS=3" "ne1 RP=174 VMLAT=174 NPOS=1" \
         "nw3 RP=161 VMLAT=161 NPOS=3" "nw8 RP=161 VMLAT=161 NPOS=8" "p51 RP=51 VMLAT=51 NPOS=2"; do
  set -- $c; n=$1; shift; sim $n $R "$@"
  grep -q "TB_GATHER_PHASE PASS" $O/$n.log && ok "sim $n $(grep -h TB_GATHER_PHASE $O/$n.log)" || bad "sim $n $(tail -2 $O/$n.log)"
done
# EQ_CYCLE_SHIFTED: padded MIX == reference MIX with dt + (RP-23)*(1+pos), identical pos/row/data
eqs(){ awk -v S=$3 '{split($2,a,"=");split($3,p,"=");a[2]+=S*(1+p[2]);print "MIX dt="a[2],$3,$4,$5}' $O/$1.mix > $O/$2.shift
       cmp -s $O/$2.shift $O/$2.mix && [ -s $O/$2.mix ]; }
eqs ref3 ne3 151 && ok "EQ_CYCLE_SHIFTED ne3 == ref3 +151*(1+pos) ($(wc -l < $O/ne3.mix) mixes)" || bad "EQ_CYCLE_SHIFTED ne3"
eqs ref1 ne1 151 && ok "EQ_CYCLE_SHIFTED ne1 == ref1 +151 ($(wc -l < $O/ne1.mix) mixes)" || bad "EQ_CYCLE_SHIFTED ne1"
eqs ref3 nw3 138 && ok "EQ_CYCLE_SHIFTED nw3 == ref3 +138*(1+pos) ($(wc -l < $O/nw3.mix) mixes)" || bad "EQ_CYCLE_SHIFTED nw3"
sim old_ref3 $O/old/rtl_reader.sv RP=23 VMLAT=23 NPOS=3
cmp -s $O/old_ref3.mix $O/ref3.mix && [ -s $O/ref3.mix ] && ok "RP 23: pre-fix reader MIX log == fixed reader (bit-identical)" || bad "RP 23 drift vs pre-fix"
# negative controls
sim neg_late $R RP=174 VMLAT=175 NPOS=3
grep -q "TB_GATHER_PHASE FAIL" $O/neg_late.log && ok "neg late return: $(grep -h TB_GATHER_PHASE $O/neg_late.log)" || bad "neg late return not caught"
sim neg_per $R RP=174 VMLAT=174 NPOS=3 PER_OVR=176
grep -q "TB_GATHER_PHASE FAIL" $O/neg_per.log && ok "neg PERIOD 176: $(grep -h TB_GATHER_PHASE $O/neg_per.log)" || bad "neg PERIOD not caught"
sim neg_old $O/old/rtl_reader.sv RP=174 VMLAT=174 NPOS=3
grep -q "RESP_PHASE must lie" $O/neg_old.log && ! grep -q PASS $O/neg_old.log && ok "neg pre-fix reader RP 174: $(grep -h -m1 'RESP_PHASE' $O/neg_old.log)" || bad "neg pre-fix reader did not abort"
# yosys rtl_lint form
DEPS="$H/ot_hgi_hc_residual_vm_static.sv $H/ot_hgi_hc_result_vm_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv"
lint(){ # name qstatic reader gp
  { echo "verilog_defines -DSYNTHESIS"
    echo "read_verilog -lib -sv $O/sram_bb.v"   # interface-only macro, as the kit reads its liberty
    for s in $DEPS $2 $3; do echo "read_verilog -defer -sv -noautowire $s"; done
    echo "hierarchy -check -top ot_hbm_hc_q_static -chparam GATHER_PHASE $4 -chparam RD_CAPTURE $4 -chparam DONE_LAT $(($4-4)) -chparam XW_BEATS 4"
    echo "proc"; echo "opt_clean"; echo "check -assert"; } > $O/lint_$1.ys
  $YOSYS -q -s $O/lint_$1.ys > $O/lint_$1.log 2>&1; }
for gp in 174 161; do
  lint mix$gp $O/old/rtl_q_static.sv $R $gp && ok "lint pre-fix rtl q_static + fixed reader GATHER_PHASE $gp" || bad "lint mix$gp $(grep -m1 ERROR $O/lint_mix$gp.log)"
  lint fix$gp $H/ot_hbm_hc_q_static.sv $R $gp && ok "lint fixed q_static + fixed reader GATHER_PHASE $gp" || bad "lint fix$gp $(grep -m1 ERROR $O/lint_fix$gp.log)"
  lint bfix$gp $BH/ot_hbm_hc_q_static.sv $BH/ot_hgi_hc_gathered_mix_reader_static.sv $gp && ok "lint bundle q_static + bundle reader GATHER_PHASE $gp" || bad "lint bfix$gp $(grep -m1 ERROR $O/lint_bfix$gp.log)"
  lint neg$gp $O/old/rtl_q_static.sv $O/old/bundle_reader.sv $gp && bad "neg lint (kit mix) passed GATHER_PHASE $gp" || ok "neg lint pre-fix kit mix GATHER_PHASE $gp: $(grep -m1 ERROR $O/lint_neg$gp.log)"
done
lint fix23 $H/ot_hbm_hc_q_static.sv $R 23 && ok "lint fixed q_static default-range GATHER_PHASE 23" || bad "lint fix23"
# YC1
for f in rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv; do
  if grep -nE "[0-9]+'\(&" $f; then bad "YC1 cast left in $f"; else ok "YC1 no N'(&x) cast: $f"; fi
  $YOSYS -q -p "read_verilog -defer -sv -noautowire $f" > $O/yc1_parse.log 2>&1 && ok "yosys parse $f" || bad "yosys parse $f"
done
# regression: the shipped q_static bench with the fixed sources
OUT=$O/qbench bash $H/run_hc_q_static.sh > $O/qbench.log 2>&1 && ok "$(tail -1 $O/qbench.log): $(grep -h TB_HBM $O/qbench.log | tr '\n' ' ')" || bad "q_static bench $(tail -3 $O/qbench.log)"
[ $rc = 0 ] && echo "GATHER_PHASE CHECK PASS" || echo "GATHER_PHASE CHECK FAIL"
exit $rc
