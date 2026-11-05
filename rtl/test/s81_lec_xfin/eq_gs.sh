#!/bin/bash
# yosys equiv: eng_finish with the ga1-1 chain (OT_S81DV_EF_GSCHAIN) vs the log-depth OR prefix; both NOWINQ (0-cycle)
# usage: eq_gs.sh KITRTL OUT [MUT]
KR=$1; O=$2; MUT=$3; mkdir -p $O; cd $O
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=$(ls $HOME/.local/opentallas-tools/yosys-0.68/*/yosys 2>/dev/null | head -1)
S=$(ls $KR/*.sv | grep -v ot_s81dv_norm.sv | tr '\n' ' ')
awk '/^module ot_s81dv_eng_finish/{p=1} p{print} p&&/^endmodule/{exit}' $KR/ot_s81dv_norm.sv > ef.sv
cp ef.sv ef_gate.sv
[ -n "$MUT" ] && sed -i 's/gl < LG8; gl = gl + 1/gl < LG8 - 1; gl = gl + 1/; s/gpo\[LG8\]\[NG8-2:0\]/gpo[LG8-1][NG8-2:0]/' ef_gate.sv
sed -i 's/module ot_s81dv_eng_finish/module gate_ef/' ef_gate.sv
sed 's/module ot_s81dv_eng_finish/module gold_ef/' ef.sv > ef_gold.sv
cat > eq.ys <<EOT
read_verilog -sv -DSYNTHESIS -DOT_S81DV_EF_NOWINQ -DOT_S81DV_EF_GSCHAIN ef_gold.sv $S
hierarchy -top gold_ef; proc; flatten; memory; async2sync; opt_clean; design -stash g
read_verilog -sv -DSYNTHESIS -DOT_S81DV_EF_NOWINQ ef_gate.sv $S
hierarchy -top gate_ef; proc; flatten; memory; async2sync; opt_clean; design -stash t
design -copy-from g -as gold gold_ef; design -copy-from t -as gate gate_ef
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
EOT
$Y -q -l eq.log eq.ys > /dev/null 2>&1; rc=$?
grep -E "Found [0-9]+ \\\$equiv|Of those|unproven|Equivalence successfully" eq.log | tail -4; echo "EQ_GS rc=$rc mut=${MUT:-0}"
