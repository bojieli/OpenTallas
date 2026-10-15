`timescale 1ns/1ps
module tb_idx_vm_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [135:0] read_slot=0;reg [127:0] read_tag=0;
 wire [135:0] vm_rq;wire [2055:0] vm_rr,result;wire [127:0] result_tag;wire fault;
 reg [8*281-1:0] wr=0;wire [143:0] status;
 ot_hbm_idx_vm_static #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.sid(2'd0),.*);
 for(genvar b=0;b<8;b=b+1)begin:bank
  wire done,dqd,kqd,xd,x2d;wire [275:0] eg;wire[265:0] pr;
  ot_vms_bank_static #(.RG(1),.WG(1)) mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(vm_rq[b*17+16]),.rslot(1'b0),.wslot_v(wr[b*281+280]),.wslot(3'd0),
   .rq(vm_rq[b*17+:17]),.rr(vm_rr[b*257+:257]),.wq(wr[b*281+:281]),.wq_done(done),
   .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),
   .xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[b*18+:18]));
 end
 function automatic [255:0] pattern(input integer row,input integer b);
 for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h9e3779b9*(row*64+b*8+k+1);
 endfunction
 reg [2055:0] expected[0:2047];reg[127:0] etag[0:2047];
 integer cycle=0,errors=0,checks=0;bit checking=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(checking) begin
   for(integer b=0;b<8;b=b+1)begin
    expected[cycle+8][b*257+:257]={read_slot[b*17+16],pattern(int'(read_slot[b*17+3+:10])+128*int'(read_slot[b*17+15]),b)};
    etag[cycle+8][b*16+:16]=read_tag[b*16+:16];
   end
   #1;
   for(integer b=0;b<8;b=b+1)begin
    if(result[b*257+256]!==expected[cycle][b*257+256])errors++;
    if(expected[cycle][b*257+256])begin
     checks++;
     if(result[b*257+:256]!==expected[cycle][b*257+:256]||result_tag[b*16+:16]!==etag[cycle][b*16+:16])errors++;
    end
   end
   if(fault || status!==144'd0)errors++;
  end
 end
 initial begin
  for(integer c=0;c<2048;c=c+1)begin expected[c]=0;etag[c]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(integer row=0;row<256;row=row+1)begin
   @(negedge clk);
   for(integer b=0;b<8;b=b+1)wr[b*281+:281]={1'b1,1'(row/128),2'd0,10'(row%128),3'(b),pattern(row,b),8'hff};
  end
  @(negedge clk);wr=0;repeat(12)@(negedge clk);checking=1;
  for(integer c=0;c<512;c=c+1)begin
   for(integer b=0;b<8;b=b+1)begin
    read_slot[b*17+:17]={(c%17!=0),1'(c/8),2'd0,10'((c+b*13)%128),3'(b)};
    read_tag[b*16+:16]=16'(c*8+b);
   end
   @(negedge clk);
  end
  read_slot=0;repeat(12)@(negedge clk);
  $display("IDX_STATIC_VM MUT%0d checks%0d errors%0d fault%0d real_SRAMs24",MUT,checks,errors,fault);
  if(errors||checks!=3848)$fatal(1,"exact fixed-slot IDX VM gate");
  $finish;
 end
endmodule
