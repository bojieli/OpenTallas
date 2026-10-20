`timescale 1ns/1ps
module tb;
reg clk=0,rst=0,v=0;always #5 clk=~clk;
reg[3:0] tree=0;reg[31:0] val=0;wire[1:0] ov,err,fault;wire[3:0] tag[0:1];wire[2:0] pos[0:1];wire[31:0] y[0:1];
old_tree #(.NT(16),.LV(5),.QD(8),.EARLY(0)) a(.clk(clk),.rst_pin(rst),.in_v(v),.in_tree(tree),.in_pos(0),.in_val(val),.in_final(1'b1),.in_err(1'b0),.ov(ov[0]),.otree(tag[0]),.opos(pos[0]),.oval(y[0]),.oerr(err[0]),.fault(fault[0]));
ot_v41_segtree5_rp #(.NT(16),.LV(5),.QD(8),.EARLY(0)) b(.clk(clk),.rst_pin(rst),.in_v(v),.in_vk({5{v}}),.in_tree(tree),.in_pos(0),.in_val(val),.in_final(1'b1),.in_err(1'b0),.ov(ov[1]),.otree(tag[1]),.opos(pos[1]),.oval(y[1]),.oerr(err[1]),.fault(fault[1]));
integer outputs=0,stored=0,cycles=0;reg[31:0] rng=32'h10202026;
always @(negedge clk) if(rst) begin
 cycles++;
 if(a.use_q && (a.qr+(a.use_q?1:0))%8 != a.qw) stored++;
 if(ov[0]!==ov[1] || fault[0]!==fault[1]) $fatal(1,"QUEUE_DIFF valid/fault cycles=%0d",cycles);
 if(ov[0]) begin
  outputs++;
  if({tag[0],pos[0],y[0],err[0]} !== {tag[1],pos[1],y[1],err[1]}) $fatal(1,"QUEUE_DIFF y=%h/%h tree=%h/%h stored=%0d",y[0],y[1],tag[0],tag[1],stored);
 end
end
initial begin
 repeat(4) @(negedge clk); rst=1;repeat(4) @(negedge clk);
 for(integer wave=0;wave<64;wave++) begin
  for(integer n=0;n<16;n++) begin
   @(negedge clk); v=0;
   while(a.qc>=6) @(negedge clk);
   v=1;tree=4'(n);rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};val=32'h3f800000| (rng&32'h0007ffff);
  end
  @(negedge clk);v=0;repeat(160) @(negedge clk);
 end
 repeat(200) @(negedge clk);
 if(outputs<400 || stored<100 || fault[0]) $fatal(1,"QUEUE_COVERAGE outputs=%0d stored=%0d fault=%b",outputs,stored,fault);
 $display("QUEUE_BURST PASS outputs=%0d stored=%0d cycles=%0d",outputs,stored,cycles);$finish;
end
endmodule
