#!/bin/bash
# LEC-EGN-1 11-03: sequential equivalence of ot_dsrom_rsqrt before / after the square-sign fix (m_hm reads
# {1'b0, yy[k][30:0]}).  run_equiv.sh <outdir> [LM] [LA] [MUT]   (cwd = repo root; Yosys + yosys-abc, e.g. the
# openroad/orfs image).  OLD = ot_dsrom_rsqrt of git REF (default: the parent of the LEC-EGN-1 commit; OT_EQ_REF), NEW = the
# work tree module; MUT 1 = NEW with the m_hm sign input inverted ({~yy[k][31], ...}), MUT 2 = NEW with
# yy[k][0] dropped.  Miter: shared clk / v / x / rst_n; rst_n held low for the die reset contract (64 edges), then
# free; every cycle after the window y / vo / fault must match.  Latches start at 0 in both copies: the unit is a
# feed-forward pipeline of DEPTH = 1 + 3 (3 LM + LA) <= 64 stages, so after the 64-edge window no state bit depends on
# the initial state (free and zero initial states give the same reachable set).
# MUT 0 prints EQUIV PASS (exit 0); MUT 1/2 must print EQUIV FAIL (exit 0 = expected verdict for the control).
set -u; O=$1; LM=${2:-5}; LA=${3:-4}; M=${4:-0}; REF=${OT_EQ_REF:-$(git log -1 --format=%H --grep="^LEC-EGN-1: rsqrt m_hm" HEAD 2>/dev/null)~1}
mkdir -p $O; O=$(cd $O && pwd)
S=rtl/hdc/v41x/ot_dsrom_su_norm.sv
[ -s $O/su_norm_old.sv ] || git show $REF:$S > $O/su_norm_old.sv || exit 4
ext() { awk '/^module ot_dsrom_rsqrt #\(/{p=1} p{print} p&&/^endmodule/{exit}' "$1"; }
ext $O/su_norm_old.sv | sed 's/^module ot_dsrom_rsqrt /module ot_dsrom_rsqrt_old /' > $O/old.sv
ext $S | sed 's/^module ot_dsrom_rsqrt /module ot_dsrom_rsqrt_new /' > $O/new.sv
grep -q "{1'b0, yy\[k\]\[30:0\]}" $O/new.sv || { echo "NEW lacks the fix"; exit 4; }
case $M in
  1) sed -i "s/{1'b0, yy\[k\]\[30:0\]}/{~yy[k][31], yy[k][30:0]}/" $O/new.sv ;;
  2) sed -i "s/{1'b0, yy\[k\]\[30:0\]}/{1'b0, yy[k][30:1], 1'b0}/" $O/new.sv ;;
esac
cat > $O/miter.sv <<V
module eq_miter (input wire clk, input wire rst_in, input wire v, input wire [31:0] x, output wire bad);
    reg [6:0] cnt = 7'd0;
    always @(posedge clk) if (cnt != 7'd64) cnt <= cnt + 7'd1;
    wire done = (cnt == 7'd64);
    wire rn = done ? rst_in : 1'b0;
    wire [31:0] y0, y1; wire vo0, vo1, f0, f1;
    ot_dsrom_rsqrt_old #(.LM($LM), .LA($LA)) u_old (.clk(clk), .rst_n(rn), .v(v), .x(x), .y(y0), .vo(vo0), .fault(f0));
    ot_dsrom_rsqrt_new #(.LM($LM), .LA($LA)) u_new (.clk(clk), .rst_n(rn), .v(v), .x(x), .y(y1), .vo(vo1), .fault(f1));
    assign bad = done && ({y0, vo0, f0} != {y1, vo1, f1});
endmodule
V
# the rest of ot_dsrom_su_norm.sv minus ot_dsrom_rsqrt (qadd, helpers)
awk '/^module ot_dsrom_rsqrt #\(/{s=1} !s{print} s&&/^endmodule/{s=0}' $S > $O/su_norm_rest.sv
F="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
   rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv
   rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv
   rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
   rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/hdc/v41x/ot_dsrom_divc.sv"
F=$(echo $F)
cat > $O/eq.ys <<Y
read_slang --compat=vcs --ignore-assertions --top eq_miter --single-unit -DSYNTHESIS $F $O/su_norm_rest.sv $O/old.sv $O/new.sv $O/miter.sv
hierarchy -check -top eq_miter
proc
flatten
opt_clean
async2sync
memory -nomap
memory_map
techmap
opt -keepdc -fast
dffunmap
simplemap
opt_clean
check -assert
setundef -zero -init
aigmap
write_aiger -zinit $O/miter.aig
stat
Y
yosys -q -l $O/yosys.log -s $O/eq.ys > /dev/null 2>&1 || { echo "YOSYS_FAILED"; tail -n 15 $O/yosys.log; exit 3; }
# ABC: signal correspondence (the two copies merge everywhere but the m_hm sign cone), then unbounded pdr; if pdr runs
# out of time, BMC over B = 64 + DEPTH + 16 frames (DEPTH = 1 + 3 (3 LM + LA)) -- complete for these feed-forward
# pipelines, since every state bit is a function of the inputs of the last DEPTH cycles once the window has flushed.
B=${OT_EQ_BMC:-$((64 + 1 + 3 * (3 * LM + LA) + 16))}
yosys-abc -c "read_aiger $O/miter.aig; print_stats; strash; &get -n; &scorr; &put; print_stats; dc2; print_stats; write_aiger $O/miter_scorr.aig; pdr -T ${OT_EQ_PDR_T:-600}" > $O/abc.log 2>&1
if grep -q "Property proved" $O/abc.log; then V=PASS; grep -m1 "Property proved" $O/abc.log
elif grep -qE "was asserted|asserted in frame" $O/abc.log; then V=FAIL; grep -m1 -E "asserted" $O/abc.log
else
  yosys-abc -c "read_aiger $O/miter_scorr.aig; bmc3 -F $B -T ${OT_EQ_BMC_T:-7200}" > $O/abc_bmc.log 2>&1
  if grep -qE "was asserted|asserted in frame" $O/abc_bmc.log; then V=FAIL; grep -m1 -E "asserted" $O/abc_bmc.log
  elif grep -qE "No output asserted in $B frames" $O/abc_bmc.log && ! grep -q "Resource limit" $O/abc_bmc.log; then V=PASS; echo "BMC complete: $B frames"
  else V=UNDECIDED; tail -n 2 $O/abc_bmc.log; fi
fi
echo "EQUIV $V LM=$LM LA=$LA MUT=$M"
if [ "$M" = 0 ]; then [ $V = PASS ] && exit 0; exit 1; fi
[ $V = FAIL ] && exit 0; exit 1
