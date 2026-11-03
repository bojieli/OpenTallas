`timescale 1ns/1fs
module tb_projection;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,q_v=0;reg[7:0]q_idx=0;reg[31:0]q_d=0;reg[135:0]obs136=0;
 wire[143:0]gold_obs={obs136[135:49], 2'b00, obs136[48:38], 2'b00, obs136[37:27], 2'b00, obs136[26:16], 2'b00, obs136[15:0]};
 wire gv,cv;wire[7:0]gi,ci;wire[31:0]gd,cd;
 ot_hbm_obs_leaf #(.N(144),.LID(0),.SYNC_MASK(512'd0),.MUT(0)) g(
 .clk(clk),.rst_n(rst_n),.obs(gold_obs),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),.r_v(gv),.r_idx(gi),.r_d(gd));
 ot_hbm_obs_leaf_fc136 #(.LID(0),.SYNC_MASK(512'd0)) c(
 .clk(clk),.rst_n(rst_n),.obs(obs136),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),.r_v(cv),.r_idx(ci),.r_d(cd));
 integer checked=0,cycles=0,i,j,logical_bit;
 always @(posedge clk)begin
  #0.000001;
  if(cycles>=6)begin
   if({gv,gi,gd}!=={cv,ci,cd})$fatal(1,"OBS136_PROJECTION_MISMATCH cycle=%0d gold=%h candidate=%h",cycles,{gv,gi,gd},{cv,ci,cd});
   checked=checked+1;
  end
  cycles=cycles+1;
 end
 function integer old_index(input integer physical);
  begin
   if(physical<16)old_index=physical;
   else if(physical<27)old_index=physical+2;
   else if(physical<38)old_index=physical+4;
   else if(physical<49)old_index=physical+6;
   else old_index=physical+8;
  end
 endfunction
 initial begin
  repeat(6)@(negedge clk);rst_n=1;
  // Every retained input is exercised at its OLD logical debug-word index.
  for(i=0;i<136;i=i+1)begin
   @(negedge clk);obs136=136'd1<<i;q_v=1;q_d=0;
   logical_bit=old_index(i);q_idx=logical_bit/32;
   repeat(8)@(negedge clk);
   obs136=0;q_idx=16|(logical_bit/32); // sticky read and same-bank clear
   repeat(8)@(negedge clk);
  end
  // Live/sticky/padded words, nonmatching LID, passthrough data and q bubbles.
  for(i=0;i<1024;i=i+1)begin
   @(negedge clk);obs136={$random,$random,$random,$random,$random};
   q_idx=i%256;q_v=(i%7!=0);q_d=$random;
   if(i==333 || i==777)begin
    #0.1;rst_n=0;repeat(5)@(negedge clk);rst_n=1;
   end
  end
  q_v=0;obs136=0;repeat(10)@(negedge clk);
  $display("OBS136_LOCKSTEP_PASS checked=%0d retained136 oldlogical144 allquerybytes sticky_clear warmreset no_added_cycles",checked);
  $finish;
 end
endmodule
