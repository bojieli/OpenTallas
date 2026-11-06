#!/bin/bash
# DIE-HEAD-71: beat_tx main (gold) vs branch HOLD_REAL 1 (gate), IDLE_ZERO 1 (the hd_ctl configuration).
# Unbounded proof: k-induction on a wrapper whose property ok = outputs equal AND the inductive invariant
#   control state equal (owe nxt oq_v oq_b fault oq_p);
#   seen (a word has started since reset) -> gold hold[W-P-1:0] == gate hold and gold pad hold[NP-P-1:W-P] == 0;
#   !seen -> owe == 0 (so no hold bit, real or pad, can reach oq_p before the first word).
# Base: init undef everywhere, rn = 0 in step 1 (control reset only, data registers stay X); the property is
# checked from step 2 (-seq 1: step 1 is the reset step, where oq_p is the power-up X in both).
set -u
OLD=$1; NEW=$2; OUT=$3; mkdir -p $OUT; cd $OUT
Y=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}
rc=0
for pt in "b97 97 2 62 1" "h553 553 3 273 2"; do set -- $pt; n=$1 W=$2 N=$3 P=$4 BW=$5
NP=$((N*P)); HW=$((W-P)); GH=$((NP-P))
cat > wrap_$n.v <<V
module wrap(input ck, input rn, input v, input [$((W-1)):0] d, output ok, output [$((P+BW)):0] o_a);
  wire [$((P+BW)):0] o_b; wire f_a, f_b;
  wire [$((GH-1)):0] h_a; wire [$((HW-1)):0] h_b;
  wire [$((BW-1)):0] owe_a, owe_b, nxt_a, nxt_b; wire [$((P-1)):0] p_a, p_b;
  bt_old ua(.ck(ck), .rn(rn), .v(v), .d(d), .o(o_a), .fault(f_a), .\\g_multi.hold (h_a), .owe(owe_a), .nxt(nxt_a), .oq_p(p_a));
  bt_new ub(.ck(ck), .rn(rn), .v(v), .d(d), .o(o_b), .fault(f_b), .\\g_multi.hold (h_b), .owe(owe_b), .nxt(nxt_b), .oq_p(p_b));
  reg seen;
  always @(posedge ck or negedge rn) if (!rn) seen <= 1'b0; else if (v && owe_a == 0) seen <= 1'b1;
  assign ok = (o_a == o_b) && (f_a == f_b) && (owe_a == owe_b) && (nxt_a == nxt_b) && (p_a == p_b)
            && (!seen || (h_a[$((HW-1)):0] == h_b && h_a[$((GH-1)):$HW] == 0)) && (seen || owe_a == 0);
endmodule
V
cat > eq2_$n.ys <<Y
read_verilog -sv $OLD
chparam -set W $W -set N $N -set P $P -set IDLE_ZERO 1 ot_s81hd_beat_tx
hierarchy -top ot_s81hd_beat_tx
proc; opt_clean; rename ot_s81hd_beat_tx bt_old
expose bt_old/w:g_multi.hold bt_old/w:owe bt_old/w:nxt bt_old/w:oq_p
design -stash g
read_verilog -sv $NEW
chparam -set W $W -set N $N -set P $P -set IDLE_ZERO 1 -set HOLD_REAL 1 ot_s81hd_beat_tx
hierarchy -top ot_s81hd_beat_tx
proc; opt_clean; rename ot_s81hd_beat_tx bt_new
expose bt_new/w:g_multi.hold bt_new/w:owe bt_new/w:nxt bt_new/w:oq_p
design -stash h
design -copy-from g -as bt_old bt_old
design -copy-from h -as bt_new bt_new
read_verilog -sv wrap_$n.v
hierarchy -top wrap
proc; flatten; opt_clean
async2sync
select -assert-count 1 wrap/w:ok
# widths: gold hold NP-P = $GH, gate hold W-P = $HW
sat -tempinduct -prove ok 1 -set-init-undef -set-def-inputs -set-at 1 rn 0 -seq 1 -maxsteps 8 -verify wrap
Y
echo "== $n (W $W N $N P $P: gold hold $GH, gate hold $HW)"; $Y -q -l eq2_$n.log eq2_$n.ys > /dev/null 2>&1; r=$?; echo "rc=$r"; [ $r = 0 ] || rc=1
grep -E "Induction step proven|SUCCESS|failed|ERROR" eq2_$n.log | tail -3
done
echo "EQBT2 rc=$rc"; exit $rc
