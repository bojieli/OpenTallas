`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;reg rst=0;reg[1:0]d=0;reg[63:0]dd=0;
wire[43:0]r44;wire[51:0]r52;wire[1:0]oldq,newq,badq;wire[63:0]a,b;
qfd_dv_reset_tree #(.N(44)) o(ck,rst,r44);
qfd_dv_reset_tree #(.N(52)) n(ck,rst,r52);
qfd_dv_s8_pad #(.W(2),.D(55),.RST(1)) old(ck,r44[32],d,oldq);
qfd_dv_s8s_control55 next(ck,{r52[48:46],r52[32]},d,newq);
qfd_dv_s8s_control55 mut(ck,{r52[48],1'b0,r52[46],r52[32]},d,badq);
qfd_dv_s8s_selected_delay #(.D(55),.ENABLE_DELAY55(1)) da(ck,r44[30],r44[30],dd,a);
qfd_dv_s8s_selected_delay #(.D(55),.ENABLE_DELAY55(1)) db(ck,r52[30],r52[44],dd,b);
integer cy=0,checks=0,mutants=0;
initial begin
 for(cy=0;cy<700;cy++)begin
 @(negedge ck);rst=!(cy<8||(cy>=300&&cy<308));d=2'(cy)^2'(cy>>3)^2'b11;dd=64'h1234000000+64'(cy)*64'h100003;
 @(posedge ck);#0.001;
 if(cy>10)begin
  if(r44!==r52[43:0]||r52[51:44]!=={8{r44[32]}})$fatal(1,"RESET_EPOCH");
  if(oldq!==newq)$fatal(1,"CONTROL_EQ %0d",cy);
  checks+=2;
 end
 if(cy>100)begin if(a!==b)$fatal(1,"DATA_RESET_EQ %0d",cy);checks++;end
 if(oldq!==badq)mutants++;
 end
 if(mutants==0)$fatal(1,"FROZEN_RESET_NOT_CAUGHT");
 $display("STN55_RESET_FACTOR_PASS checks%0d frozen_mutant%0d old44_new52_sameepoch maxfanout28 datahelpers32",checks,mutants);$finish;
end
endmodule
