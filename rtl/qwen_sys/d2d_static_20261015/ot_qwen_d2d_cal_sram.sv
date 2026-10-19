`timescale 1ns/1ps
// Opt-in compatible SYSFACE table player. Integrator explicitly selects this
// module; legacy ot_qwen_d2d_cal remains unchanged. Two native 64x16 SRAMs,
// four stopped prefetch edges after the final cfg write; no execution stalls.
// Read-before-write SRAM; reads disabled on config writes (no collisions).
module ot_qwen_d2d_cal_sram #(
 parameter integer NE=32, AW=$clog2(NE), MUT=0
)(input wire ck,rst_n,cfg_we,input wire [AW:0] cfg_addr,
 input wire [31:0] cfg_data,input wire start,start_seg,halt,
 output reg ev_v,output reg [2:0] ev_port,output reg [3:0] ev_kind,
 output reg [4:0] ev_beat,output reg running,fault);
 initial if(NE>64 || NE<2 || (1<<AW)!=NE) $error("unsupported calendar shape");
 reg [AW-1:0] seg1;
 reg [31:0] cur,next_q,h00,h01,h10,h11;
 reg [13:0] cnt;reg [4:0] rep,bcur;reg [AW:0] ptr;
 reg [2:0] pf;reg cfg_recent;
 wire [31:0] mq;
 wire consume=running && cnt==1 && rep==0 && !cur[17];
 wire [AW-1:0] sb=start_seg ? seg1 : {AW{1'b0}};
 wire [AW-1:0] seq_addr=ptr[AW-1:0]+((consume && MUT!=4)?2:1);
 wire [AW-1:0] idle_addr=pf==0 ? {AW{1'b0}} : pf==1 ? {{(AW-1){1'b0}},1'b1} : pf==2 ? seg1 : seg1+1'b1;
 wire [AW-1:0] ra=start ? sb+2 : running ? seq_addr : idle_addr;
 wire rce=rst_n && !cfg_we && (start || running || pf<4);
 wire wce=cfg_we && !running && !cfg_addr[AW];
 wire [15:0] qlo,qhi;
 ot_sram_1r1w_64x16_m1 lo(.clk(ck),.r_ce_in(rce),.r_addr_in(6'(ra)),.rd_out(qlo),
  .w_ce_in(wce),.w_addr_in(6'(cfg_addr[AW-1:0])),.wd_in(cfg_data[15:0]),.w_mask_in(16'hffff));
 ot_sram_1r1w_64x16_m1 hi(.clk(ck),.r_ce_in(rce),.r_addr_in(6'(ra)),.rd_out(qhi),
  .w_ce_in(wce),.w_addr_in(6'(cfg_addr[AW-1:0])),.wd_in(cfg_data[31:16]),.w_mask_in(16'hffff));
 assign mq=MUT==1 ? {qlo,qhi} : {qhi,qlo};
 // Payload caches deliberately have no reset. pf certifies every head was read
 // from the current image; SRAM and cache contents never infer resettable FF RAM.
 always @(posedge ck) begin
  if(cfg_we && !running && cfg_addr[AW])seg1<=cfg_data[AW-1:0];
  if(!cfg_we && !running)case(pf)
   1:h00<=mq;2:h01<=mq;3:h10<=mq;4:h11<=mq;default:begin end
  endcase
 end
 wire ready_head=pf>=4;
 wire sel_seg=(MUT==3)?!start_seg:start_seg;
 wire [31:0] first=sel_seg?h10:h00;
 wire [31:0] second=sel_seg ? ((pf==4)?mq:h11) : h01;
 wire [31:0] nxt=next_q;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   pf<=0;cfg_recent<=0;running<=0;ev_v<=0;ev_port<=0;ev_kind<=0;ev_beat<=0;
   cur<=0;cnt<=0;ptr<=0;fault<=0;rep<=0;bcur<=0;
  end else begin
   cfg_recent<=cfg_we;ev_v<=0;
   if(cfg_we && !running)pf<=0;
   else if(start && ready_head)pf<=5;
   else if(!running && !start && pf<5)pf<=pf+1'b1;
   if(cfg_we && running)fault<=1;
   if(halt)running<=0;
   else if(start)begin
    if(running || cfg_we || cfg_recent || (!ready_head && MUT!=5))fault<=1;
    running<=1;cur<=(MUT==2)?second:first;cnt<=first[31:18];
    ptr<={1'b0,sb}+1'b1;rep<=first[4:0];bcur<=first[9:5];
    if(first[31:18]==0 || {1'b0,first[9:5]}+{1'b0,first[4:0]}>31)fault<=1;
   end else if(running)begin
    if(cnt==1)begin
     ev_v<=1;ev_port<=cur[16:14];ev_kind<=cur[13:10];ev_beat<=bcur;
     if(rep!=0)begin rep<=rep-1'b1;bcur<=bcur+1'b1;end
     else if(cur[17])running<=0;
     else begin
      if(ptr==NE || nxt[31:18]==0 || {1'b0,nxt[9:5]}+{1'b0,nxt[4:0]}>31)fault<=1;
      cur<=nxt;cnt<=nxt[31:18];ptr<=ptr+1'b1;rep<=nxt[4:0];bcur<=nxt[9:5];
     end
    end else cnt<=cnt-1'b1;
   end
  end
 end
 // Only this 32-bit lookahead payload advances on the exact entry boundary.
 always @(posedge ck)if(start)next_q<=second;else if(consume)next_q<=mq;
endmodule
