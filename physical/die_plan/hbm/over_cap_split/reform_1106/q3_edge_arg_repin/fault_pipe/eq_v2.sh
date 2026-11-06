#!/bin/bash
# eq_v2.sh TAG MUT_FP: gold = _fp SEEN_DEFER=0 (v1, proven vs the original) with u.seen_q renamed u.seen (and u.seen -> u.seen_cur);
# gate = _fp SEEN_DEFER=1 (v2). Invariant: v2.seen == v1.seen_q. Run in the orfs container, /fv, /wt.
T=$1; MUT=$2; Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys; cd /fv
A=/wt/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_argmax_static.sv
B=/wt/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv
cat > /fv/wrap_v2.sv <<EOW
module eqtop #(parameter integer MUT_FP=0, SEEN_DEFER=0)(input wire clk,rst_n,start,input wire [7:0] cfg_g,cfg_gbase,cfg_rank,input wire [3:0] in_slot,in_v,
 input wire [2179:0] in_flit,input wire flush_slot,publish_slot,output wire out_v,output wire [544:0] out_flit,output wire fault);
 ot_hgi_coll_argmax_static_fp #(.MAX_GROUP(192),.MUT_FP(MUT_FP),.SEEN_DEFER(SEEN_DEFER)) u(.clk(clk),.rst_n(rst_n),.start(start),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),
  .cfg_rank(cfg_rank),.in_slot(in_slot),.in_v(in_v),.in_flit(in_flit),.flush_slot(flush_slot),.publish_slot(publish_slot),
  .out_v(out_v),.out_flit(out_flit),.fault(fault));
endmodule
EOW
$Y -q -p "read_verilog -sv $B $A /fv/wrap_v2.sv; hierarchy -top eqtop -chparam SEEN_DEFER 0; proc; flatten; opt_clean; write_verilog -noattr /fv/v1_flat_$T.v" || exit 3
sed 's/\\u\.seen /\\u.seen_cur /g; s/\\u\.seen_q /\\u.seen /g' /fv/v1_flat_$T.v > /fv/v1_flat_${T}_n.v
cat > /fv/eq_$T.ys <<EOT
read_verilog /fv/v1_flat_${T}_n.v
hierarchy -top eqtop
proc; async2sync; opt_clean; rename eqtop gold; design -stash gold
read_verilog -sv $B $A /fv/wrap_v2.sv
hierarchy -top eqtop -chparam SEEN_DEFER 1 -chparam MUT_FP $MUT
proc; flatten; async2sync; opt_clean; rename eqtop gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync; equiv_simple -seq 5; equiv_induct -seq 5; equiv_status -assert
EOT
$Y -q -l /fv/eq_$T.log -s /fv/eq_$T.ys > /dev/null 2>&1; echo "EQ $T rc $?"
grep -E "Found [0-9]+ .equiv|proven and|unproven|ERROR|Equivalence successfully" /fv/eq_$T.log | tail -n 5
