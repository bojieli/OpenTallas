`timescale 1ps/1fs
module tb_qfd_native_cmd_plain;
 parameter integer MUT_DRAIN=0;
 reg clk=0;always #512 clk=~clk;
 reg rst_n=0,desc_v=0,go_v=0,wr_v=0,window_retired=0,write_quiet=1,transport_quiet=1,cmd_credit_return=0;
 reg [18:0] desc_row=0;reg [10:0] desc_n=1024;reg [4:0] wr_bank=0,wr_col=0;reg [2:0] read_release=0;
 wire desc_take,go_take,wr_take,cmd_v,fault;wire[31:0]cmd;wire[2:0]read_credit;
 ot_qfd_native_cmd_plain #(.ENABLE(1),.MUT_SKIP_DRAIN(MUT_DRAIN)) dut(.*);
 reg [31:0] expected[0:2047];integer sent=0,received=0,checks=0;reg monitor=1;reg[2:0]previous_read=0;
 always @(posedge clk)begin
  if(rst_n&&monitor)begin
   if(desc_take)begin expected[sent]={2'd0,desc_n,desc_row};sent=sent+1;end
   if(go_take)begin expected[sent]=32'h40000000;sent=sent+1;end
   if(wr_take)begin expected[sent]={2'd2,20'd0,wr_col,wr_bank};sent=sent+1;end
   if(cmd_v)begin
    if(received>=sent||cmd!==expected[received])$fatal(1,"native command ordering %0d cmd%h want%h",received,cmd,expected[received]);
    received=received+1;checks=checks+1;
   end
   if(read_credit!==previous_read)$fatal(1,"read recycle capture expected%0d got%0d",previous_read,read_credit);
   previous_read=read_release;
   if(fault)$fatal(1,"unexpected native provider fault");
  end
 end
 task step;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin
  monitor=0;rst_n=0;desc_v=0;go_v=0;wr_v=0;window_retired=0;cmd_credit_return=0;read_release=0;
  repeat(2)step;rst_n=1;sent=0;received=0;previous_read=0;monitor=1;
 end endtask
 integer i;
 initial begin
  reset;
  // Simultaneous pulse acceptance, DESC precedes GO on native FIFO.
  desc_row=19'h5317;desc_v=1;go_v=1;step;desc_v=0;go_v=0;
  repeat(4)step;
  if(received!=2)$fatal(1,"DESC/GO missing");
  // Eight prepaid native slots must stop sender when native FIFO never pops.
  wr_v=1;
  for(i=0;i<20;i=i+1)begin wr_bank=i;wr_col=31-i;step;end
  if(received!=8||dut.credits!=0||wr_take)$fatal(1,"native FIFO overrun prepaid8 received%0d",received);
  // Return one actual credit per native pop; exercise full WR field range.
  cmd_credit_return=1;
  for(i=0;i<64;i=i+1)begin wr_bank=i;wr_col=31-i;read_release=i%8;step;end
  wr_v=0;read_release=0;repeat(5)step;cmd_credit_return=0;repeat(3)step;
  // Causal window fence: retirement alone cannot replace context.
  window_retired=1;step;window_retired=0;write_quiet=0;desc_v=1;desc_row=19'h7123;
  repeat(4)begin #1;if(desc_take)$fatal(1,"descriptor crossed live writes");step;end
  write_quiet=1;transport_quiet=0;
  repeat(4)begin #1;if(desc_take)$fatal(1,"descriptor crossed transport tail");step;end
  transport_quiet=1;step;desc_v=0;go_v=1;step;go_v=0;repeat(5)step;
  if(received!=sent)$fatal(1,"pending native command lost");
  $display("PASS nativecmd positive commands%0d full32bank/col, finite8slots, DESC/GO pulse order, causal fence, readcredits",checks);
  reset;monitor=0;desc_v=1;desc_n=0;step;if(!fault||cmd_v||desc_take)$fatal(1,"zero descriptor escaped");
  reset;monitor=0;desc_n=1025;desc_v=1;step;if(!fault)$fatal(1,"oversized descriptor escaped");
  reset;monitor=0;desc_v=0;go_v=1;step;if(!fault)$fatal(1,"GO without descriptor escaped");
  reset;monitor=0;go_v=0;cmd_credit_return=1;step;if(!fault)$fatal(1,"duplicate native credit escaped");
  reset;monitor=0;window_retired=1;step;if(!fault)$fatal(1,"retirement without issued GO escaped");
  $display("PASS nativecmd negatives zero/oversizedDESC orphanGO duplicatecredit premature-retire failclosed");$finish;
 end
endmodule
