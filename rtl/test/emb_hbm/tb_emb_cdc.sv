`timescale 1ps/1fs
module tb_emb_cdc;
 parameter integer NEG=0;
 reg clk=0,hclk=0,rst_n=0,hrst_n=0;
 always #416.666667 clk=~clk;
 always #512 hclk=~hclk;
 reg s_v=0; reg [286:0] s_d=0;
 wire c_v,e_v,s_credit,fc,fh;wire [286:0] c_d;wire [257:0] e_d;
 reg h_v=0,h_credit=0;reg [257:0] h_d=0;
 integer issued=0,received=0,credits=0,commands=0,errors=0;
 reg [286:0] expected[0:255];
 ot_qfd_emb_cdc #(.ENABLE(1)) dut(
  .clk(clk),.rst_n(rst_n),.hclk(hclk),.hrst_n(hrst_n),
  .s_v(s_v),.s_d(s_d),.c_v(c_v),.c_d(c_d),
  .h_credit(h_credit),.s_credit(s_credit),.h_v(h_v),.h_d(h_d),
  .e_v(e_v),.e_d(e_d),.fault_core(fc),.fault_hbm(fh));
 always @(posedge hclk) if(hrst_n) begin
  h_v<=c_v;h_credit<=c_v;
  if(c_v) begin
   if(c_d!==expected[commands]) errors=errors+1;
   commands=commands+1;
   h_d<=c_d[257:0] ^ (NEG==1 ? 258'd1 : 258'd0);
  end
 end
 always @(posedge clk) if(rst_n) begin
  if(e_v) begin
   if(e_d!==expected[received][257:0]) errors=errors+1;
   received=received+1;
  end
  if(s_credit) credits=credits+1;
 end
 integer i,j;
 initial begin
  repeat(4) @(negedge clk);rst_n=1;hrst_n=1;
  repeat(20) @(negedge clk);
  for(i=0;i<256;i=i+1) begin
   for(j=0;j<287;j=j+1) expected[i][j]=((i*17+j*13+j/7)%23)<11;
   s_d=expected[i];s_v=1;issued=issued+1;
   @(negedge clk);s_v=0;
   // One transaction remains outstanding; input credit and reply both retire.
   wait(credits==issued && received==issued);
   repeat(i%5+1) @(negedge clk);
  end
  if(commands!=256 || received!=256 || credits!=256 || errors || fc || fh)
   $fatal(1,"FAIL emb_cdc cmd=%0d rsp=%0d cr=%0d errors=%0d faults=%b%b",commands,received,credits,errors,fc,fh);
  $display("PASS emb_cdc commands=256 responses=256 credits=256 clocks=833.333334ps/1024ps");
  $finish;
 end
endmodule
