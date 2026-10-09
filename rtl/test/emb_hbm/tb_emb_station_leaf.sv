`timescale 1ps/1fs
module tb_emb_station_leaf;
 parameter integer STAGES=17;
 reg clk=0,rst_n=0;always #416.666667 clk=~clk;
 reg [287:0] cmd_i=0;reg [259:0] ret_i=0;
 wire [287:0] cmd_o;wire [259:0] ret_o;
 reg [287:0] commands[0:255];reg [259:0] returns[0:255];
 integer i,j,at;
 ot_qfd_emb_station_pair #(.STAGES(STAGES)) dut(.*);
 initial begin
  repeat(4) @(negedge clk);
  if({cmd_o,ret_o}!==0)$fatal(1,"FAIL station resetzero");
  rst_n=1;
  for(i=0;i<256;i=i+1) begin
   @(negedge clk);
   for(j=0;j<288;j=j+1)cmd_i[j]=((i*13+j*17+j/7)%29)<15;
   for(j=0;j<260;j=j+1)ret_i[j]=((i*19+j*23+j/11)%31)<17;
   commands[i]=cmd_i;returns[i]=ret_i;
   @(posedge clk);#1;at=STAGES==0 ? i : i-STAGES+1;
   if(at<0) begin if({cmd_o,ret_o}!==0)$fatal(1,"FAIL station startup padding");end
   else if({cmd_o,ret_o} !== {commands[at],returns[at]})$fatal(1,"FAIL station all-packet bit/edge mapping");
  end
  @(negedge clk);rst_n=0;cmd_i=0;ret_i=0;#1;
  if({cmd_o,ret_o}!==0)$fatal(1,"FAIL station resetflush");
  $display("PASS station_leaf STAGES=%0d packets256 all548bits exact edge mapping resetzero resetflush core833.333334ps",STAGES);$finish;
 end
endmodule
