#!/bin/bash
# hcpl_bench.sh <outdir> [both|mut]  (cwd = repo root): the s81sl_hcpl kit's bench -- ot_dsrom_su_hcpost_lane_pr (ML 7 /
# AL 6) lockstep against the unchanged core lane (rtl/test/tb_hcpost_lane_pr.sv, random operands incl. specials).
#   both (default): the exact run must PASS and MUTANT 1 (c3 bypasses its pin flop) must FAIL -> "PASS hcpl", exit 0
#   mut           : MUTANT 1 alone, raw: prints the tb verdict line, exit 1 when it fails (an expect=fail bench)
# The golden hc_post arithmetic is covered by tools/s81_slice/beat_bench.sh.
set -u; O=$1; M=${2:-both}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/test/tb_hcpost_lane_pr.sv"
MS="0 1"; [ "$M" = mut ] && MS="1"
for m in $MS; do
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUTANT=$m --top-module tb_hcpost_lane_pr -Mdir $O/obj$m $S > $O/build$m.log 2>&1 || { echo "BUILD_FAILED $m"; tail -5 $O/build$m.log; exit 3; }
  $O/obj$m/Vtb_hcpost_lane_pr > $O/run$m.log 2>&1
done
if [ "$M" = mut ]; then grep -E "^(PASS|FAIL)_HCPOST_LANE_PR" $O/run1.log; grep -q "^PASS_HCPOST_LANE_PR" $O/run1.log && exit 0; exit 1; fi
grep -q PASS_HCPOST_LANE_PR $O/run0.log && ! grep -q PASS_HCPOST_LANE_PR $O/run1.log && { echo "PASS hcpl"; exit 0; }
echo "FAIL hcpl"; tail -2 $O/run0.log $O/run1.log; exit 1
