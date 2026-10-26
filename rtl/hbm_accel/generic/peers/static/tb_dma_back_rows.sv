`timescale 1ns/1ps
// H-MTP2/sudma 2026-10-16: DMA.KVWB_DS as a P-row record on the ACTUAL static VM->HBM store engine
// ot_hgi_dma_back_static (unchanged; 8 real ot_vms_bank_static banks / 24 VM macros + 8 real landing macros).
// No new hardware: the existing move227 descriptor already carries m rows (m <= 128 chunks / lane, n % 64 == 0 words,
// VM row stride >= n, dense HBM stride n*4 B): a P-row window-row append is ONE move with m = P, rows into P
// consecutive ring slots (dense, no ring wrap; a wrap is split by the compiler into two moves).  Per row r:
// HBM[HB + r*n*4 + k*4] = VM[VB + r*VS + k], k < n.  Golden computed here from the addresses; fixed timeline checked:
// chunk i (64 words) issued at issue_at + i, landed at +9, WB beat at drain_at + 2 + i on lane = sector % 8.
// MUT (bench): 1 engine wrong destination sector (ot_hgi_dma_back_static MUT 1); 3 descriptor VM row stride = n
// (the per-position row stride dropped: rows read contiguous VM, not the position copies).
module tb_dma_back_rows;
parameter integer MUT=0;
parameter integer N=512;           // KVWB_DS window row: 512 FP32 (2,048 B)
parameter integer VS=1024;         // VM per-position row stride (words, 64-aligned, >= N)
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg [31:0] cycle=0;always @(posedge clk)cycle<=cycle+1;
reg mv_v=0;reg [226:0] mv=0;reg [31:0] issue_at=0,drain_at=0;
wire mv_src,mv_done,mv_fault,quiet,busy;
wire [8*17-1:0] rq;wire [8*257-1:0] rr;wire [8*289-1:0] wd;
wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,wb_fill_start;wire [15:0] wb_reserve_epoch,wb_fill_epoch;
wire [11:0] wb_reserve_sectors;wire [31:0] wb_reserve_base;
reg [11:0] wa=0;
ot_hgi_dma_back_static #(.STK(0),.MUT(MUT==1?1:0)) dut(.clk(clk),.rst_n(rst_n),.cycle(cycle),.mv_v(mv_v),.mv(mv),
  .issue_at(issue_at),.drain_at(drain_at),.mv_wb_bank(1'b0),.mv_wb_epoch(16'd0),.mv_src(mv_src),.mv_done(mv_done),
  .mv_fault(mv_fault),.quiet(quiet),.busy(busy),.rq(rq),.rr(rr),.wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),
  .wb_fill_bank(wb_fill_bank),.wb_reserve_epoch(wb_reserve_epoch),.wb_fill_epoch(wb_fill_epoch),
  .wb_reserve_sectors(wb_reserve_sectors),.wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),.wb_ready(1'b1),
  .wd(wd),.wa(wa));
reg [280:0] dq[0:7];wire [17:0] status[0:7];
for(genvar b=0;b<8;b=b+1)begin:B
  wire [513:0] responses;
  ot_vms_bank_static #(.RG(2),.WG(2)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
  .rslot_v(rq[b*17+16]),.rslot(2'd0),.wslot_v(dq[b][280]),.wslot(3'd6),
  .rq({17'd0,rq[b*17+:17]}),.rr(responses),.wq(562'd0),.wq_done(),.dq(dq[b]),.dq_done(),.kq(281'd0),.kq_done(),
  .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b]));
  assign rr[b*257+:257]=responses[256:0];
end
function automatic [255:0] pattern(input integer word);   // VM sector content, distinct per word
  for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h9e3779b9*(word+k+1)^32'(word+k);
endfunction
function automatic [226:0] move(input integer n,input integer m,input integer vb,input integer vs,input integer hb);
  // {n21, m20, 16'd1, hbm_stride32, 3'd0, hbm_byte37, fmt3, 2'd0, 16'd1, vm_stride32, vm_base40, fmt3, 2'd1}
  move={21'(n),20'(m),16'd1,32'(n*4),3'd0,37'(hb),3'd0,2'd0,16'd1,32'(vs),40'(vb),3'd0,2'd1};
endfunction
integer errors=0,beats=0,last_beat=0,src_at=0,done_at=0,t0=0,r,k,b,i;
integer res_rows[0:15],res_beat[0:15],res_src[0:15],res_done[0:15];
reg [7:0] seen[0:1023];
integer ack_due[0:65535];
always @(posedge clk) wa<=12'(ack_due[cycle[15:0]]);
task automatic run(input integer R,input integer VB,input integer HB);
  integer vs_d,ii,ord,row,col,lane;reg [288:0] beat;reg [31:0] adr;reg [255:0] exp_;
  begin
    for(ii=0;ii<1024;ii=ii+1)seen[ii]=0;
    // preload the P position rows (and their neighbours, so a dropped stride reads wrong data, not X)
    for(r=0;r<R;r=r+1)for(k=0;k<VS;k=k+8)begin
      @(negedge clk);for(b=0;b<8;b=b+1)dq[b]=0;
      dq[((VB+r*VS+k)>>3)&7]={1'b1,1'b0,2'd0,13'((VB+r*VS+k)>>3),pattern(VB+r*VS+k),8'hff};
    end
    @(negedge clk);for(b=0;b<8;b=b+1)dq[b]=0;repeat(12)@(negedge clk);
    vs_d=(MUT==3)?N:VS;
    t0=cycle;issue_at=t0+16;drain_at=issue_at+10;mv=move(N,R,VB,vs_d,HB);mv_v=1;@(negedge clk);mv_v=0;
    beats=0;src_at=-1;done_at=-1;
    while(done_at<0&&cycle<t0+2000)begin
      @(posedge clk);#1;
      if(mv_fault)begin errors=errors+1;$display("FAULT at %0d",cycle);end
      for(b=0;b<8;b=b+1)if(status[b]!==0)begin errors=errors+1;$display("VM bank status %0d",b);end
      if(mv_src&&src_at<0)src_at=cycle;
      if(mv_done)done_at=cycle;
      for(lane=0;lane<8;lane=lane+1)begin
        beat=wd[lane*289+:289];
        if(beat[288])begin
          adr=beat[287:256];ord=int'(adr)-HB/32;row=ord/(N/8);col=ord%(N/8);
          if(ord<0||ord>=R*N/8||lane!=ord%8)begin errors=errors+1;if(errors<6)$display("BAD ADDRESS %h lane %0d",adr,lane);end
          else begin
            exp_=pattern(VB+row*VS+col*8);
            if(beat[255:0]!==exp_)begin errors=errors+1;if(errors<6)$display("PAYLOAD row %0d col %0d",row,col);end
            if(cycle-1!=drain_at+2+ord/8)begin errors=errors+1;if(errors<6)$display("TIMELINE ord %0d at %0d",ord,cycle);end
            if(seen[ord])begin errors=errors+1;$display("DUP %0d",ord);end
            seen[ord]=1;
          end
          beats=beats+1;last_beat=cycle;
          ack_due[(cycle+40)%65536]=ack_due[(cycle+40)%65536]+1;   // modelled PHY posted-ack latency (fence only)
        end
      end
    end
    if(beats!=R*N/8)begin errors=errors+1;$display("BEATS %0d expected %0d",beats,R*N/8);end
    if(done_at<0)begin errors=errors+1;$display("NO DONE");end
    res_rows[R]=R;res_beat[R]=last_beat-t0;res_src[R]=src_at-t0;res_done[R]=done_at-t0;
    repeat(8)@(negedge clk);
  end
endtask
initial begin
  for(i=0;i<65536;i=i+1)ack_due[i]=0;
  for(b=0;b<8;b=b+1)dq[b]=0;
  repeat(3)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
  for(i=1;i<=8;i=i+1)res_beat[i]=-1;
  run(1,16384,32'h0040_0000);
  run(6,16384,32'h0040_0000+8192);
  run(2,4096,32'h0050_0000);
  run(8,24576,32'h0060_0000);
  if(errors)$fatal(1,"DMA_ROWS FAIL errors=%0d",errors);
  $write("DMA_ROWS PASS n=%0d vm_stride=%0d actual VM banks=8 macros=24 landing=8; first command -> last WB beat / mv_src / mv_done(+40 modelled ack):",N,VS);
  for(i=1;i<=8;i=i+1)if(res_beat[i]>=0)$write(" R%0d=%0d/%0d/%0d",i,res_beat[i],res_src[i],res_done[i]);
  $display("");$finish;
end
endmodule
