`timescale 1ns/1ps
module tb_qkd_astk_phys;
reg ck=0; always #5 ck=~ck;
reg rn=0;reg [650:0] d=0;
wire [650:0] q,refq;
qkd_astk_delay #(.W(651),.D(3)) dut(ck,rn,d,q);
ot_hdc_delay #(.W(651),.D(3),.RESET(1)) ref_(ck,rn,d,refq);
reg a=0,b=0;wire f;reg expected=0;
qkd_astk_fault_join fj(ck,rn,a,b,f);
integer i;
initial begin
 #1;rn=1;#1;rn=0;#1;
 for(i=0;i<2000;i=i+1) begin
  @(negedge ck);rn=(i%97!=0);d={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};a=$random;b=$random;
  @(posedge ck);expected=rn ? (a|b):0;#1;
  if(q!==refq || f!==expected) begin $display("FAIL ASTK physical relay cycle=%0d",i);$fatal;end
 end
 $display("PASS ASTK physical relay 2000 words reset + RL3 + fault edge");$finish;
end
endmodule
