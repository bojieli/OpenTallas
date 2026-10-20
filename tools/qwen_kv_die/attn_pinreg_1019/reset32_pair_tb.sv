`timescale 1ns/1ps
// The exact native primitive model, not a replacement RTL flop.
module reset32_pair_tb;
 reg clk=0,d=0,rst=1;
 wire a,b;
 integer checks=0, opposite_initial=0;
 DFFASRHQNx1_ASAP7_75t_R original(.CLK(clk),.D(d),.QN(a),.RESETN(rst),.SETN(1'b1));
 DFFASRHQNx1_ASAP7_75t_R copy(.CLK(clk),.D(d),.QN(b),.RESETN(rst),.SETN(1'b1));
 task automatic equal_q(input integer reason);
   if (a !== b || !((a===1'b0)||(a===1'b1)) || !((b===1'b0)||(b===1'b1))) begin
     $display("RESET32_PAIR_FAIL reason=%0d a=%b b=%b",reason,a,b);$fatal(1);
   end
   checks++;
 endtask
 initial begin
  // Exhaust every independent binary power-up state of each master/copy pair.
  // Copies may differ before the first real clock or asynchronous assertion.
  for (int phase=0;phase<16;phase++) begin
   for (int seed=0;seed<4;seed++) begin
    for (int datum=0;datum<2;datum++) begin
     clk=0;rst=1;d=datum;#0.003;
     original.IQN=seed[0];copy.IQN=seed[1];#0.001;
     if(a!==b)opposite_initial++;
     // A real first edge converges independent states with unchanged inputs.
     clk=1;#0.001;equal_q(1);
     if(a!==~d)$fatal(1,"first real edge value");
     clk=0;#0.002;
     original.IQN=seed[0];copy.IQN=seed[1];#0.001;
     // Asynchronous assertion works with a stopped clock, at every phase.
     #(0.001*phase);rst=0;#0.001;equal_q(2);
     if(a!==1'b1)$fatal(1,"actual asynchronous assertion value");
     d=~d;#0.003;equal_q(3);
     rst=1;#0.001;equal_q(4);
     if(a!==1'b1)$fatal(1,"release changed state before capture");
     clk=1;#0.001;equal_q(5);
     if(a!==~d)$fatal(1,"post-release capture value");
     clk=0;#0.003;
    end
   end
  end
  if(opposite_initial!=64)$fatal(1,"independent initial-state coverage");
  $display("RESET32_PAIR_PASS checks=%0d opposite_initial=%0d phases=16 all_pair_initial_states=4",checks,opposite_initial);
  $finish;
 end
endmodule
