`timescale 1ps/1ps
module tb_xpos;
 reg clk=0; always #416.5 clk=~clk;
 reg rst_n=0,in_v=0,in_tree=0,in_final=0,in_err=0; reg [2:0] in_pos=0;reg[31:0] in_val=0;
 wire [1:0] ov,otree,oerr,fault;wire[2:0] opos[0:1];wire[31:0] oval[0:1];
 genvar g;generate for(g=0;g<2;g=g+1)begin:d
 ot_v41_segtree5 #(.NT(2),.LV(3),.QD(8),.EARLY(1),.KEEP_XPOS(g)) u(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_tree(in_tree),.in_pos(in_pos),.in_val(in_val),.in_final(in_final),.in_err(in_err),.ov(ov[g]),.otree(otree[g]),.opos(opos[g]),.oval(oval[g]),.oerr(oerr[g]),.fault(fault[g]));
 end endgenerate
 integer i,n=0,seed=1;reg[31:0] r=32'h593aba87;
 initial begin
  if($value$plusargs("seed=%d",seed))r=r^seed;
  for(i=0;i<12000;i=i+1)begin
   @(negedge clk);r=r^(r<<13);r=r^(r>>17);r=r^(r<<5);
   rst_n=(i%2048>=64);in_v=rst_n&&(i%17==0);in_tree=r[0];in_pos=r[4:2];in_val={r[31],8'h7e,r[22:0]};in_final=r[5];in_err=r[7:6]==3;
   @(posedge clk);#1;
   if(rst_n)begin
    if(ov[0]!==ov[1]||fault[0]!==fault[1])$fatal(1,"XPOS_BAD_VALID cyc=%0d",i);
    if(ov[0])begin
     n=n+1;if({otree[0],opos[0],oval[0],oerr[0]}!=={otree[1],opos[1],oval[1],oerr[1]})$fatal(1,"XPOS_BAD_PAYLOAD cyc=%0d pos=%h/%h",i,opos[0],opos[1]);
    end
   end
  end
  if(n<16)$fatal(1,"XPOS_VACUOUS n=%0d",n);
  $display("XPOS_PASS cycles=12000 outputs=%0d seed=%0d",n,seed);$finish;
 end
endmodule
