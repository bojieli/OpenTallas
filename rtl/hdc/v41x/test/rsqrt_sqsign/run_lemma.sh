#!/bin/bash
# LEC-EGN-1 11-03 lemma: the square ot_hdc_qmul_lat #(LM) with a = b never drives y[31] = 1 after the 64-edge reset
# window (free initial state of every flop, free x / v / rst_n after the window).  With it, ot_dsrom_rsqrt's m_hm
# input yy[k] equals {1'b0, yy[k][30:0]} on every reachable cycle, i.e. old and new rsqrt are equivalent.
# run_lemma.sh <outdir> [LM] [MUT]   MUT 1 = b = {~a[31], a[30:0]} (not a square: must FAIL).  Yosys + yosys-abc.
set -u; O=$1; LM=${2:-5}; M=${3:-0}; mkdir -p $O; O=$(cd $O && pwd)
B=$([ "$M" = 1 ] && echo "{~x[31], x[30:0]}" || echo "x")
cat > $O/lemma.sv <<V
module sq_lemma (input wire clk, input wire rst_in, input wire v, input wire [31:0] x, output wire bad);
    reg [6:0] cnt = 7'd0;
    always @(posedge clk) if (cnt != 7'd64) cnt <= cnt + 7'd1;
    wire done = (cnt == 7'd64);
    wire [31:0] y; wire f;
    ot_hdc_qmul_lat #($LM) u (clk, done ? rst_in : 1'b0, v, x, $B, y, f);
    assign bad = done && y[31];
endmodule
V
F="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
   rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv"
F=$(echo $F)
cat > $O/lemma.ys <<Y
read_slang --compat=vcs --ignore-assertions --top sq_lemma --single-unit -DSYNTHESIS $F $O/lemma.sv
hierarchy -check -top sq_lemma
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
setundef -zero
aigmap
write_aiger -zinit $O/lemma.aig
Y
yosys -q -l $O/yosys.log -s $O/lemma.ys > /dev/null 2>&1 || { echo "YOSYS_FAILED"; tail -n 15 $O/yosys.log; exit 3; }
# -zinit: every uninitialised flop gets a free initial-value input (free initial state)
yosys-abc -c "read_aiger $O/lemma.aig; print_stats; strash; pdr -T 1800" > $O/abc.log 2>&1
if grep -q "Property proved" $O/abc.log; then V=PASS; elif grep -qE "asserted" $O/abc.log; then V=FAIL; else V=UNDECIDED; fi
grep -m1 -E "Property proved|asserted" $O/abc.log
echo "LEMMA $V LM=$LM MUT=$M"
if [ "$M" = 0 ]; then [ $V = PASS ] && exit 0; exit 1; fi
[ $V = FAIL ] && exit 0; exit 1
