#!/bin/bash
# Formal equivalence: regrouped ot_qfd_tt_ctlm_static_parent (hr leaf + tree leaf) vs the original body
# (ot_qfd_tt_ctlm_static_parent_ref, byte copy of the pre-regrouping file). MUT=1 swaps two tree-return bits.
set -e
MUT=${1:-0}
P=physical/qwen_tt_static_cluster_1015
SRCS="$(sed "s@physical/asap7_memory_macros/[^ ]*_bb.v@@g" $P/srcs.txt) $P/sram_proof_stubs.v rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_hr.sv"
NEW=rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_parent.sv
if [ "$MUT" = 1 ]; then sed 's/\.rom_ret_i(rom_ret),/.rom_ret_i({rom_ret[94:2],rom_ret[0],rom_ret[1]}),/' $NEW > /tmp/eqv_mut_$$.sv; NEW=/tmp/eqv_mut_$$.sv; fi
yosys -q -p "read_verilog -defer -sv -DSYNTHESIS $P/icg_bb.v $SRCS $NEW $P/ot_qfd_tt_ctlm_static_parent_ref.sv;
 hierarchy -top ot_qfd_tt_ctlm_static_parent_ref; proc; flatten; opt_clean; rename ot_qfd_tt_ctlm_static_parent_ref gold; design -stash gold;
 read_verilog -defer -sv -DSYNTHESIS $P/icg_bb.v $SRCS $NEW;
 hierarchy -top ot_qfd_tt_ctlm_static_parent; proc; flatten; opt_clean; rename ot_qfd_tt_ctlm_static_parent gate; write_json /tmp/eq_gate_$$.json" && python3 $P/strip_prefix.py /tmp/eq_gate_$$.json /tmp/eq_gate2_$$.json gate && yosys -q -p "read_verilog -defer -sv -DSYNTHESIS $P/icg_bb.v $SRCS $P/ot_qfd_tt_ctlm_static_parent_ref.sv;
 hierarchy -top ot_qfd_tt_ctlm_static_parent_ref; proc; flatten; opt_clean; rename ot_qfd_tt_ctlm_static_parent_ref gold; design -stash gold;
 read_json /tmp/eq_gate2_$$.json; design -stash gate;
 design -copy-from gold -as gold gold; design -copy-from gate -as gate gate;
 equiv_make -inames gold gate equiv; hierarchy -top equiv; async2sync; equiv_simple -seq 5; equiv_induct -seq 5; equiv_status -assert" && echo "EQUIV_PASS MUT=$MUT" || { echo "EQUIV_FAIL MUT=$MUT"; exit 3; }
