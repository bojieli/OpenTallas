`timescale 1ns/1ps
module path #(parameter MUT=0)(input wire clk, serial, rst_n,
 input wire[16:0] rq, input wire[280:0] wq,
 output wire[256:0] result, output wire done, fault);
 wire[16:0] nrq; wire[280:0] nwq; wire[256:0] rr; wire wd;
 wire[256:0] bank_rr; wire bank_done;
 reg[297:0] reqpipe[0:4]; reg[257:0] retpipe[0:5];
 wire request_clock = MUT ? serial : clk;
 always @(posedge request_clock) begin
  reqpipe[0]<={nwq,nrq};
  for(integer j=1;j<5;j=j+1)reqpipe[j]<=reqpipe[j-1];
 end
 always @(posedge clk)begin
  retpipe[0]<={bank_done,bank_rr};
  for(integer j=1;j<6;j=j+1)retpipe[j]<=retpipe[j-1];
 end
 assign {wd,rr}=retpipe[5];
 ot_hbm_vm_lg_static_bank #(.READ_RETURN(22),.WRITE_RETURN(19),.LOCAL_SPLIT(1)) tap(
  .clk(clk),.rst_n(rst_n),.rret(5'd0),.wret(5'd0),
  .local_rq(rq),.far_rq(17'd0),.local_wq(wq),.far_wq(281'd0),
  .local_read(1'b1),.local_write(1'b1),.near_rq(nrq),.near_wq(nwq),
  .near_rr(rr),.near_w_done(wd),.local_rr(result),.far_rr(),
  .local_w_done(done),.far_w_done(),.fault(fault));
 hfd_vms_bank_native_q0_faces bank(
 .clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
 .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),
 .rq0(reqpipe[4][16:0]),.rr0(bank_rr),.wq0(reqpipe[4][297:17]),.wq_done0(bank_done),
 .rq1(17'd0),.rq2(17'd0),.rq3(17'd0),.rq4(17'd0),.wq1(281'd0),
 .rslot_v(1'b1),.rslot(3'd0),.wslot_v(1'b1),.wslot(3'd0),
 .dq(281'd0),.kq(281'd0),.xq(276'd0),.xq2(276'd0),.pq(285'd0));
endmodule
module tb;
 reg clk=0,serial=0,rst_n=0; always #6 clk=~clk; always #8 serial=~serial;
 reg[16:0] rq=0; reg[280:0] wq=0;
 wire[256:0] good,bad;wire gd,bd,gf,bf;
 path fixed_path(clk,serial,rst_n,rq,wq,good,gd,gf);
 path #(.MUT(1)) wrong_clock(clk,serial,rst_n,rq,wq,bad,bd,bf);
 localparam[255:0] DATA={8{32'h3f800123}};
 integer reads=0,writes=0;
 reg[22:0] read_due=0;reg[19:0] write_due=0;
 always @(posedge clk)begin
  if(!rst_n)begin read_due<=0;write_due<=0;end
  else begin read_due<={read_due[21:0],rq[16]};write_due<={write_due[18:0],wq[280]};end
 end
 always @(negedge clk)if(rst_n)begin
  if(good[256]!==read_due[22]||gd!==write_due[19])$fatal(1,"golden valid calendar mismatch");
  if(good[256])begin
   if(good[255:0]!==DATA)$fatal(1,"payload mismatch %h",good[255:0]);
   reads=reads+1;
  end
  if(gd)writes=writes+1;
  if(gf)$fatal(1,"corrected stream path faulted");
 end
 initial begin
  repeat(12)@(negedge clk);rst_n=1;
  repeat(12)@(negedge clk);
  for(integer i=0;i<8;i=i+1)begin
   wq={1'b1,16'd0,DATA,8'hff};@(negedge clk);wq=0;
   repeat(45)@(negedge clk);
   rq={1'b1,16'd0};@(negedge clk);rq=0;
   repeat(45+i)@(negedge clk);
  end
  if(reads!=8||writes!=8)$fatal(1,"missing returns r=%0d w=%0d",reads,writes);
  if(!bf)$fatal(1,"wrong-clock mutant escaped");
  $display("SU_BANK_CLOCK_MITER PASS reads=%0d writes=%0d mutant=CAUGHT",reads,writes);$finish;
 end
endmodule
