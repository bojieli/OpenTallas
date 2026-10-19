#!/usr/bin/env bash
# run_gunit_native_eq.sh <workdir> [mut]  (any cwd): S81-NATIVE3 equivalence bench of dsdv_gunit_l2/l3 (pin fixes) against
# the CLOSED views' RTL (L2 99ffdc846, L3 7205fead6).  No argument: must PASS.  'mut': L2 MUT 10 (raw hct_b into the
# S-side inject) must FAIL; 'mut3': L3 MUT 4 (route_scale skipped) must FAIL.  Exit 0 = expected verdict.
set -u
U=$(cd "$(dirname "$0")/.." && pwd); R=$(cd "$U/../../../.." && pwd); T=$1; M=${2:-}; mkdir -p "$T"
P=rtl/dsrom_sys/s81_dv/unit
git -C "$R" show 99ffdc846:$P/dsdv_gunit_l2.sv | sed 's/^module dsdv_gunit_l2 /module dsdv_gunit_l2_ref /; s/ot_dsdv_vstop #/ot_dsdv_vstop_ref #/' > "$T/l2_ref.sv"
git -C "$R" show 99ffdc846:$P/ot_dsdv_vstop.sv | sed 's/^module ot_dsdv_vstop /module ot_dsdv_vstop_ref /' > "$T/vstop_ref.sv"
git -C "$R" show 7205fead6:$P/dsdv_gunit_l3.sv | sed 's/^module dsdv_gunit_l3 /module dsdv_gunit_l3_ref /' > "$T/l3_ref.sv"
grep -q dsdv_gunit_l2_ref "$T/l2_ref.sv" && grep -q ot_dsdv_vstop_ref "$T/l2_ref.sv" && grep -q dsdv_gunit_l3_ref "$T/l3_ref.sv" || { echo "BENCH_SETUP_FAILED ref"; exit 4; }
SRC="rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv
 rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
 rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv rtl/lib/ot_rst_relay.sv $P/ot_dsdv_vstop.sv $P/dsdv_gunit_pass.sv $P/dsdv_gunit_l2.sv $P/dsdv_gunit_l3.sv
 $P/test/tb_gunit_native_eq.sv"
D=""; [ "$M" = mut ] && D="+define+MUT=10"; [ "$M" = mut3 ] && D="+define+MUT3"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
( cd "$T" && $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D --top-module tb_gunit_native_eq -Mdir "obj$M" \
   $(for f in $SRC; do echo "$R/$f"; done) l2_ref.sv vstop_ref.sv l3_ref.sv --build-jobs 6 > "build$M.log" 2>&1 ) || { echo BUILD_FAILED; tail -8 "$T/build$M.log"; exit 3; }
( cd "$T" && "./obj$M/Vtb_gunit_native_eq" > "run$M.log" 2>&1 ); grep -E "MISMATCH|^GUNITEQ|^PASS|^FAIL" "$T/run$M.log" | head -14
if [ -z "$M" ]; then grep -q '^PASS' "$T/run$M.log"; exit $?; fi
grep -q '^FAIL' "$T/run$M.log" && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
