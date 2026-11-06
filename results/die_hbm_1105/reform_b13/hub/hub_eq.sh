#!/bin/bash
# hub_eq.sh MUT : yosys equiv old vs new ot_vms_hub_static_pc (NC=0,CW=1), new with DMUT=$1
set -e
cd /srv/opentallas-scratch2/claude/hbm-reform-b13/hub
mkdir -p eq; cd eq
W=/srv/opentallas-scratch2/claude/hbm-reform-b13/wt
F=rtl/hbm_accel/cores_split/reform_1105s/glue/ot_vms_glue_pc.sv
ext() { awk '/^module ot_vms_hub_static_pc/{f=1} f{print} f&&/^endmodule/{exit}'; }
git -C $W show HEAD:$F | ext | sed 's/module ot_vms_hub_static_pc/module hub_gold/' > gold.sv
ext < $W/$F | sed 's/module ot_vms_hub_static_pc/module hub_gate/' > gate.sv
Y=$HOME/.local/opentallas-tools/bin/yosys
cat > eq_$1.ys <<YS
read_verilog -sv gold.sv
read_verilog -sv gate.sv
chparam -set NC 0 -set CW 1 -set DMUT 0 hub_gold
chparam -set NC 0 -set CW 1 -set DMUT $1 hub_gate
proc; memory; opt_clean
async2sync
equiv_make hub_gold hub_gate eqm
hierarchy -top eqm
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
YS
prlimit --as=30000000000 timeout 3000 $Y -q -l eq_$1.log eq_$1.ys && echo "EQ_MUT$1 EQUIVALENT" || { echo "EQ_MUT$1 NOT_PROVEN"; grep -i "unproven\|error\|Found" eq_$1.log | tail -5; }
