`timescale 1ns/1ps
// Two actual ot_hbm_idx_vm_static faces (INDEX operand face and a second client with the TOPK capture timing)
// share one 8-bank read group of real ot_vms_bank_static banks (24 SRAM macros) through the four bank-pair
// leaves. Owners change per bank per edge; each face must capture exactly its own sectors at n+8 with no fault;
// a deliberate double booking must fault in the share and reach neither face (both faces fault on the missing response).
module tb_idx_vm_share_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [135:0] slot_i=0,slot_t=0;reg [127:0] tag_i=0,tag_t=0;
 wire [135:0] rq_i,rq_t,vm_rq;wire [2055:0] rr_i,rr_t,vm_rr,res_i,res_t;wire [127:0] rtag_i,rtag_t;wire f_i,f_t,f_s;
 reg [8*281-1:0] wr=0;wire [143:0] status;
 ot_hbm_idx_vm_static face_i(.clk(clk),.rst_n(rst_n),.sid(2'd0),.read_slot(slot_i),.read_tag(tag_i),.vm_rq(rq_i),.vm_rr(rr_i),.result(res_i),.result_tag(rtag_i),.fault(f_i));
 ot_hbm_idx_vm_static face_t(.clk(clk),.rst_n(rst_n),.sid(2'd0),.read_slot(slot_t),.read_tag(tag_t),.vm_rq(rq_t),.vm_rr(rr_t),.result(res_t),.result_tag(rtag_t),.fault(f_t));
 ot_hbm_idx_vm_share_static #(.MUT(MUT)) share(.clk_pair({4{clk}}),.rst_n(rst_n),.index_rq(rq_i),.topk_rq(rq_t),.vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(rr_i),.topk_rr(rr_t),.fault(f_s));
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
 reg [256:0] ei[0:4095][0:7],et[0:4095][0:7];
 integer cycle=0,errors=0,ci=0,ct=0,coll=0;bit checking=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(checking)begin
   for(integer b=0;b<8;b=b+1)begin
    ei[cycle+8][b]={slot_i[b*17+16],pattern(int'(slot_i[b*17+3+:10])+128*int'(slot_i[b*17+15]),b)};
    et[cycle+8][b]={slot_t[b*17+16],pattern(int'(slot_t[b*17+3+:10])+128*int'(slot_t[b*17+15]),b)};
   end
   #1;
   for(integer b=0;b<8;b=b+1)begin
    if(res_i[b*257+256]!==ei[cycle][b][256]||res_t[b*257+256]!==et[cycle][b][256])errors++;
    if(ei[cycle][b][256])begin ci++;if(res_i[b*257+:256]!==ei[cycle][b][255:0])errors++;end
    if(et[cycle][b][256])begin ct++;if(res_t[b*257+:256]!==et[cycle][b][255:0])errors++;end
   end
   if(f_i||f_t||f_s||status!==144'd0)errors++;
  end
 end
 initial begin
  for(integer c=0;c<4096;c=c+1)for(integer b=0;b<8;b=b+1)begin ei[c][b]=0;et[c][b]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(integer row=0;row<256;row=row+1)begin
   @(negedge clk);
   for(integer b=0;b<8;b=b+1)wr[b*281+:281]={1'b1,1'(row/128),2'd0,10'(row%128),3'(b),pattern(row,b),8'hff};
  end
  @(negedge clk);wr=0;repeat(12)@(negedge clk);checking=1;
  for(integer c=0;c<1024;c=c+1)begin
   slot_i=0;slot_t=0;
   for(integer b=0;b<8;b=b+1)begin
    integer who;who=(c*7+b*3+(c/13))%3; // 0 idle, 1 INDEX, 2 TOPK, changing per bank per edge
    if(who==1)slot_i[b*17+:17]={1'b1,1'(c/8),2'd0,10'((c+b*13)%128),3'(b)};
    if(who==2)slot_t[b*17+:17]={1'b1,1'(c/5),2'd0,10'((c*3+b)%128),3'(b)};
    tag_i[b*16+:16]=16'(c*8+b);tag_t[b*16+:16]=16'(c*8+b+1);
   end
   @(negedge clk);
  end
  slot_i=0;slot_t=0;repeat(12)@(negedge clk);checking=0;
  // double booking: bank 3 on both clients -> share fault, no bank request
  slot_i[3*17+:17]={1'b1,1'b0,2'd0,10'd5,3'd3};slot_t[3*17+:17]={1'b1,1'b0,2'd0,10'd9,3'd3};
  @(negedge clk);slot_i=0;slot_t=0;repeat(12)@(negedge clk);
  if(!f_s)errors++;
  // neither client may receive a double-booked sector: both faces see their reserved response missing and fault
  if(!(f_i&&f_t))errors++;
  $display("IDX_VM_SHARE MUT%0d index_reads%0d topk_reads%0d errors%0d share_fault%0d SRAMs24 leaves4",MUT,ci,ct,errors,f_s);
  if(errors||ci<2000||ct<2000)$fatal(1,"static IDX read-group share");
  $finish;
 end
endmodule
