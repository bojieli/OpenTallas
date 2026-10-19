`timescale 1ns/1ps
module tb_kv_retirement_reset;
 parameter integer BAD_RELEASE=0;
 reg ck=0;always #5 ck=~ck;
 integer age=0;
 always @(negedge ck)age=age+1;
 // Fixture source clears at36, forwarding registers reset only at POR.
 // The delayed source reset leaves old health in flight after a sink clear.
 reg source_health=1;
 always @(posedge ck)if(age>=36)source_health<=0;
 wire [180:0] lane;
 assign lane[0]=source_health;
 for(genvar k=0;k<180;k=k+1)begin:g
   qkd_astk_fault_join f(.ck(ck),.rst_n(age>=2),.a(lane[k]),.b(1'b0),.q(lane[k+1]));
 end
 wire health;
 qkd_astk_fault_join sink(.ck(ck),.rst_n(age>=((BAD_RELEASE!=0)?128:220)),
                          .a(lane[180]),.b(health),.q(health));
 initial begin
   repeat(260)@(negedge ck);
   if(health)$fatal(1,"reset resurrection: sink release precedes source clear plus propagation");
   $display("PASS reset cohort fixture source_clear36 path180 sink_release220");
   $finish;
 end
endmodule
