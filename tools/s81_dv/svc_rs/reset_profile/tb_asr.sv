`timescale 1ns/1ps
module tb_asr;
 reg clk=0;always #5 clk=~clk;
 reg raw=0;wire rn;wire[511:0]leaf;
 dsdv_svc_rs_rl ref_rl(.ck(clk),.rst(raw),.sid(4'd0),.rn(rn));
 ot_s81svc_reset_rl2_n32 dut(.clk(clk),.pre({512{raw}}),.reset_leaf(leaf));
 integer checks=0,errors=0;reg[31:0]rng=32'h4329ac;
 task check;begin #0.001;checks++;if(leaf!=={512{rn}})errors++;end endtask
 always@(posedge clk)check();
 always@(negedge raw)begin check();if(leaf!==512'd0)$fatal(1,"async assertion late");end
 initial begin
  #0.7;raw=1;#2.1;raw=0;#18.3;raw=1;
  for(integer i=0;i<1200;i++)begin
   #3.7;rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);raw=rng[0];check();
  end
  #30; $display("RESET_ASR_ACTUAL checks=%0d leaves=512 errors=%0d",checks,errors);
  if(checks<1500||errors)$fatal(1,"actual controller ASR mismatch");$finish;
 end
endmodule
