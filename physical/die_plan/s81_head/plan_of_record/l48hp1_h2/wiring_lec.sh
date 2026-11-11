#!/bin/bash
# HEAD-92/H2 wiring equivalence: ot_s81ph_coll_lane_safe4_hd (host_e params) original vs OT_HE_EPC (u_epc hard-core cut)
set -e
W=/w; Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
F="ot_rst_relay_tree3.sv ot_link_crc32.sv ot_s81ph_ckbuf.sv ot_sram_oldread_b64.sv ot_sram_showahead_b64.sv ot_link_credit_rx_b64.sv ot_link_credit_tx_rc.sv ot_s81ph_link_ep_safe4.sv ot_s81ph_link_gbx_safe3.sv ot_s81ph_coll_lane_safe4.sv ot_s81hd_util.sv ot_s81hd_lsc_parts.sv ot_s81hd_beat_link.sv ot_s81hd_best64.sv ot_s81hd_mesh_ep_core.sv"
D="-DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF"
mk() { # dir extra_defines extra_files out
  s=""; for f in $F $3; do s="$s $1/$f"; done
  $Y -q -l $W/$4.log -p "read_verilog -sv -lib $1/ot_sram_1r1w2c_256x64_m1_bb.v $1/ot_sram_1r1w2c_32x64_m1_bb.v; read_verilog -sv $D $2 $s; hierarchy -top ot_s81ph_coll_lane_safe4_hd -chparam CH_BOARD 700 -chparam TF_CLEANUP 1 -chparam REACH 2; proc; setattr -mod -unset keep_hierarchy *; flatten; attrmap -remove hdlname -remove src; memory; opt_clean; rename -top top_$4; hierarchy -top top_$4; write_rtlil $W/$4.il"
}
[ -s $W/gate.il ] || mk $W/a "" "" gold
[ -s $W/gate.il ] || mk $W/b "-DOT_HE_EPC" "ot_s81hd_he_epc.sv" gate
sed -i -e 's/\\rr\b/\\rr_epc_parent_tie/g' -e 's#\\u_epc\.u_ep\.#\\u_ep.#g' -e 's#\\u_epc\.u_rr\.#\\u_rr.#g' $W/gate.il
grep -c 'u_epc' $W/gate.il || true
$Y -l $W/equiv.log -p "read_verilog -sv -lib $W/a/ot_sram_1r1w2c_256x64_m1_bb.v $W/a/ot_sram_1r1w2c_32x64_m1_bb.v; read_rtlil $W/gold.il; read_rtlil $W/gate.il; async2sync; equiv_make top_gold top_gate eq; hierarchy -top eq; equiv_simple -seq 4; equiv_status -assert" > /dev/null
grep -E 'Found|unproven|proven' $W/equiv.log | tail -n 5
echo WEQ_DONE
