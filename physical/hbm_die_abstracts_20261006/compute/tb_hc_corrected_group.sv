`timescale 1ps/1fs
// Real minimum group, four real m6/a5 arithmetic lanes; no quarter/stub.
module tb_hc_corrected_group;
 reg clk=0,rst_n=0,in_v=0;always #416.666667 clk=~clk;
 reg [159:0] d=0;reg [511:0] c;reg [127:0] p;
 wire out_v,fault;wire [127:0] o;
 ot_dsrom_su_hcpost_group #(.WIN(0),.WOUT(0),.ML(6),.AL(5)) dut(
  .clk(clk),.rst_n(rst_n),.in_v(in_v),.r(d[127:0]),.y(d[159:128]),
  .c(c),.p(p),.out_v(out_v),.o(o),.fault(fault));
 reg [159:0] reqs[0:31];reg [127:0] exps[0:31];
 reg [639:0] cfg[0:0];string dir;
 integer sent=0,received=0,cycles=0,k;
 always @(posedge clk)begin
  if(rst_n)begin
   cycles=cycles+1;
   if(in_v)sent=sent+1;
   #1;
   if(fault)$fatal(1,"HC_GROUP_UNEXPECTED_FAULT");
   if(out_v)begin
    if(received>=sent||o!==exps[received])
     $fatal(1,"HC_GROUP_GOLDEN_FAIL beat=%0d got=%h exp=%h",received,o,exps[received]);
    received=received+1;
   end
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR_REQUIRED");
  $readmemh({dir,"/group_req.mem"},reqs);$readmemh({dir,"/group_exp.mem"},exps);
  $readmemh({dir,"/group_cfg.mem"},cfg);{p,c}=cfg[0];
  repeat(3)@(negedge clk);rst_n=1;
  // Consecutive real beats followed by bubbles expose data/valid phase errors.
  // comb/post remain the same real operation configuration throughout.
  for(k=0;k<32;k=k+1)begin
   @(negedge clk);in_v=1;d=reqs[k];
   if(k%5==4)begin @(negedge clk);in_v=0;d=0;end
  end
  @(negedge clk);in_v=0;d=0;
  repeat(6+4*5+1+8)@(negedge clk);
  if(received!=32||sent!=32)$fatal(1,"HC_GROUP_COMPLETION_FAIL sent=%0d received=%0d",sent,received);
  $display("HC_CORRECTED_GROUP_GOLDEN_PASS beats=%0d words=%0d cycles=%0d",received,received*4,cycles);
  $finish;
 end
endmodule
