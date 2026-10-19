`timescale 1ns/1ps
// HBM-NEXT-UNITS-SUDMA 2026-10-19: DMA.KVWB_DS N-row record into the 256-slot window ring (CMTP rule R8 / R-POS) on the
// d4g die master ot_hgi_dma_back_static_vp4_banks (UNCHANGED: controller + 8 real landing banks) fed by 8 real static VM
// banks (ot_vms_bank_static).  Fork of tb_dma_back_rows (H-MTP2/sudma 10-16, ot_hgi_dma_back_static, iverilog).
// Mechanism (compile-time, no RTL delta): row r of the record (position POS_SLOT + r, VM copy VB + r * VS) lands in ring
// slot (s0 + r) mod 256, s0 = POS_SLOT mod 256 (8-bit ring index: the "+1 index bit" over the d4g 128-slot ring).  The
// existing move227 descriptor carries m rows at a dense HBM stride n * 4 B: one move of m = N rows when the rows do not
// cross slot 255; else the compiler splits the record into two moves (m1 = 256 - s0 rows at slot s0, then N - m1 rows at
// slot 0), the second commanded on the static calendar after the first releases the engine (first_drain + chunks + 2).
// Golden per row: HBM[HB0 + ((s0 + r) mod 256) * 2048 + 4 k] = VM[VB + r * VS + k], k < 512, computed here from the
// addresses.  Fixed timeline: every beat at drain_at(move) + K + ord / 8 (K learned on the first beat, then fixed).
// Measured per case: first command -> last WB beat (cycles).
// MUT (bench, compiler mutants): 1 ring index 7 b (slot mod 128, the d4g ring); 2 no wrap split (one move runs past
// slot 255); 3 per-position VM row stride dropped (VS = n).
module tb_hnx_dma_kvwb_ring;
parameter integer MUT=0;
localparam integer N=512, VS=1024, RING=256, ROWB=2048;
localparam integer RING_IX=(MUT==1)?128:RING;
localparam [31:0] HB0=32'h0080_0000;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg [31:0] cycle=0;always @(posedge clk)cycle<=cycle+1;
reg mv_v=0;reg [226:0] mv=0;reg [31:0] issue_at=0,drain_at=0;
wire mv_src,mv_done,mv_fault,quiet,busy;
wire [8*17-1:0] rq;wire [8*257-1:0] rr;wire [8*289-1:0] wd;
wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,wb_fill_start;wire [15:0] wb_reserve_epoch,wb_fill_epoch;
wire [11:0] wb_reserve_sectors;wire [31:0] wb_reserve_base;
reg [11:0] wa=0;
ot_hgi_dma_back_static_vp4_banks dut(.clk(clk),.clk_bank({8{clk}}),.rst_n(rst_n),.stk(2'd0),.cycle(cycle),.mv_v(mv_v),.mv(mv),
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
function automatic [255:0] pattern(input integer word);
  for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h9e3779b9*(word+k+1)^32'(word+k);
endfunction
function automatic [226:0] move(input integer n,input integer m,input integer vb,input integer vs,input integer hb);
  move={21'(n),20'(m),16'd1,32'(n*4),3'd0,37'(hb),3'd0,2'd0,16'd1,32'(vs),40'(vb),3'd0,2'd1};
endfunction
integer errors=0,beats=0,last_beat=0,r,k,b,i,K=-1,ncase=0;
integer vs_d,m1,nmv,mi,mj,t0,ord,slot,col,lane,rr_,chunks,ordm;
integer dr[0:1],mbase[0:1],mrows[0:1],mslot[0:1];
reg [288:0] beat;reg [31:0] adr;
integer res_c[0:31],res_r[0:31],res_s[0:31],res_mv[0:31];
reg [7:0] seen[0:4095];
integer ack_due[0:65535];
always @(posedge clk) wa<=12'(ack_due[cycle[15:0]]);
// one record: R rows, ring slot s0; VM rows VB + r * VS
task run(input integer R,input integer s0,input integer VB);
  begin
    for(i=0;i<4096;i=i+1)seen[i]=0;
    for(r=0;r<R;r=r+1)for(k=0;k<VS;k=k+8)begin
      @(negedge clk);for(b=0;b<8;b=b+1)dq[b]=0;
      dq[((VB+r*VS+k)>>3)&7]={1'b1,1'b0,2'd0,13'((VB+r*VS+k)>>3),pattern(VB+r*VS+k),8'hff};
    end
    @(negedge clk);for(b=0;b<8;b=b+1)dq[b]=0;repeat(12)@(negedge clk);
    vs_d=(MUT==3)?N:VS;
    // compiler: ring slot of row 0, split at the ring end (MUT 2: no split)
    m1=(MUT!=2&&s0%RING_IX+R>RING_IX)?RING_IX-s0%RING_IX:R;
    nmv=(m1<R)?2:1;
    mrows[0]=m1;mslot[0]=s0%RING_IX;mbase[0]=VB;mrows[1]=R-m1;mslot[1]=0;mbase[1]=VB+m1*VS;
    t0=cycle;beats=0;
    fork
      begin
        for(mi=0;mi<nmv;mi=mi+1)begin
          // the engine takes a move only when idle (busy clears at first_drain + chunks + 1): the split move's command
          // is on the calendar at first_drain + chunks + 2, 16 edges before its issue (the same lead as move 0)
          issue_at=(mi==0)?t0+16:dr[0]+mrows[0]*N/64+2+16;
          dr[mi]=issue_at+10;drain_at=dr[mi];
          while(cycle+16<issue_at)@(negedge clk);
          mv=move(N,mrows[mi],mbase[mi],vs_d,HB0+mslot[mi]*ROWB);mv_v=1;@(negedge clk);mv_v=0;
        end
      end
      begin
        while(cycle<t0+16+2000&&beats<R*N/8)begin
          @(posedge clk);#1;
          if(mv_fault)begin errors=errors+1;if(errors<6)$display("FAULT at %0d",cycle);end
          for(b=0;b<8;b=b+1)if(status[b]!==0)begin errors=errors+1;$display("VM bank status %0d",b);end
          for(lane=0;lane<8;lane=lane+1)begin
            beat=wd[lane*289+:289];
            if(beat[288])begin
              adr=beat[287:256];
              ord=int'(adr)-int'(HB0/32);slot=ord/(N/8);col=ord%(N/8);rr_=(slot-s0+4*RING)%RING;
              if(ord<0||slot>=RING||rr_>=R)begin errors=errors+1;if(errors<6)$display("BAD ADDRESS %h (slot %0d) lane %0d case%0d",adr,slot,lane,ncase);end
              else begin
                mj=(rr_<m1)?0:1; ordm=(rr_-((mj==0)?0:m1))*(N/8)+col;
                if(lane!=ord%8)begin errors=errors+1;if(errors<6)$display("LANE %0d ord %0d",lane,ord);end
                if(beat[255:0]!==pattern(VB+rr_*VS+col*8))begin errors=errors+1;if(errors<6)$display("PAYLOAD case%0d row %0d col %0d",ncase,rr_,col);end
                if(K<0)K=cycle-1-dr[mj]-ordm/8;
                if(cycle-1!=dr[mj]+K+ordm/8)begin errors=errors+1;if(errors<6)$display("TIMELINE case%0d row %0d at %0d",ncase,rr_,cycle);end
                if(seen[ord%4096])begin errors=errors+1;$display("DUP %0d",ord);end
                seen[ord%4096]=1;
              end
              beats=beats+1;last_beat=cycle;
              ack_due[(cycle+40)%65536]=ack_due[(cycle+40)%65536]+1;
            end
          end
        end
      end
    join
    if(beats!=R*N/8)begin errors=errors+1;$display("BEATS %0d expected %0d case%0d",beats,R*N/8,ncase);end
    res_c[ncase]=last_beat-t0;res_r[ncase]=R;res_s[ncase]=s0;res_mv[ncase]=nmv;ncase=ncase+1;
    repeat(80)@(negedge clk);
  end
endtask
initial begin
  for(i=0;i<65536;i=i+1)ack_due[i]=0;
  for(b=0;b<8;b=b+1)dq[b]=0;
  repeat(3)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  run(1,5,16384); run(2,5,16384); run(3,5,16384); run(4,5,16384); run(6,5,16384);   // N = 1 = the d4g KVWB_DS
  run(6,200,20480);                     // slots >= 128 (the +1 index bit)
  run(6,253,24576);                     // wrap: 3 + 3 rows, two moves
  run(4,255,16384);                     // wrap: 1 + 3
  run(1,255,20480);
  if(errors)$fatal(1,"KVWB_RING FAIL errors=%0d MUT=%0d",errors,MUT);
  $write("KVWB_RING PASS n=%0d ring=%0d vm_stride=%0d die master vp4_banks K=%0d; first command -> last WB beat:",N,RING,VS,K);
  for(i=0;i<ncase;i=i+1)$write(" R%0d@s%0d/%0dmv=%0d",res_r[i],res_s[i],res_mv[i],res_c[i]);
  $display("");$finish;
end
endmodule
