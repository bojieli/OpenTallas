`timescale 1ns/1ps
module nk_reset_counterexample;
 reg ck=0,rst_n=0,valid_in=0;
 always #5 ck=~ck;
 reg reset_q;always @(posedge ck) reset_q<=rst_n;
 wire [3:0] rn;
 // Exact signed-node reset relay parameters; input assertion is synchronous.
 ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(ck,reset_q,rn);
 // Exact signed-node t_vout_q reset/capture cone.
 reg node_v;always @(posedge ck or negedge rn[1]) if(!rn[1])node_v<=0;else node_v<=valid_in;
 reg original,candidate;
 always @(posedge ck)begin original<=reset_q?node_v:1'b0;candidate<=node_v;end
 integer differing=0;reg armed=0;
 always @(negedge ck)if(armed && original!==candidate)begin
  differing=differing+1;$display("NK_RESET_DIFFERENCE t=%0t reset_q=%b rn=%b node_v=%b old=%b drop=%b",$time,reset_q,rn,node_v,original,candidate);
 end
 initial begin
  repeat(5)@(negedge ck);rst_n=1;
  repeat(8)@(negedge ck);valid_in=1;
  repeat(5)@(negedge ck);armed=1;rst_n=0;
  repeat(5)@(negedge ck);
  if(differing==0)$fatal(1,"expected unsafe NK clamp-removal counterexample missing");
  $display("PASS_UNSAFE_CANDIDATE_CAUGHT diffs=%0d no_adoption",differing);$finish;
 end
endmodule
