`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// TW3-PGSTREAM 2026-10-19 (coordinator 10-19: the pg_stream 3:4 bridge FAILS inside one tile, gate hbm_su_pg_stream_1019
// cross_clock TT setup -126.9 ps rr_slot -> serial_rr): ot_hbm_su_multirate_bridge split into two ONE-ROOT halves with a
// 2-bank seam (HBM-CXDL dl_s/dl_q, S81 x34_s/_t precedent). Same edges, same outputs as ot_hbm_su_multirate_bridge
// (READ_RETURN / WRITE_RETURN form of HBM-BANKLAT-SU) on every serial and stream edge; lockstep tb_hbm_su_pg_stream_split.
//   _q (serial_clk): serial event n (serial edge n) writes request bank n mod 2 (rq_b<b>/wq_b<b>), the old 4-slot write;
//                    reads the return banks one (ST) serial edge(s) EARLY into a staging register, so serial_rr /
//                    serial_done keep the old n+SRD / n+SWD edges.
//   _s (stream_clk): the old stream block (phase, warm, active, pipes, fault check) reading request bank n mod 2 at the
//                    old launch edge and writing return bank n mod 2 at the old capture edge.
// Seam calendar (quanta q = 277.8 ps, serial edge n at 4n, stream edge j at 3j, common epoch; checked in the bench):
//   request bank n:  written 4n, read at stream 4n+{6,5,4} (n mod 3 = 0,1,2); rewritten 4n+8
//                    => setup >= 4q, rewrite-after-read >= 2q.
//   return bank n:   written 3(j_n+RP) = 4n+6-(n mod 3)+3RP; staged read 4(n+D-ST); rewritten (source n+2)
//                    => with X = 4(D-ST)-3RP in [8,10]: setup >= X-6, rewrite-after-read >= 12-X
//                    10/7 and 18/15: read X=8 (setup 2q, hold 4q), done X=9 (3q / 3q).
//   ST = floor((4D-3RP-8)/4) is derived; a round trip with X = 11 (RP = 3 mod 4) would leave a 1q window -> $fatal.
// The seam arcs are die-level 3:4 arcs (die STA owns them with the epoch windows above; the halves abut).
// Seam bits per bridge: 2 x (RQ+WQ) out of _q + 2 x (RR+1) out of _s = 1,112 b (the one-tile bridge held 4 slots).
// MUT (bench, must FAIL): _q 1 = return staging bank parity flipped, 3 = staging removed (read at the output edge: hold
//                         0 / -1 q, caught by the bench window checker), 6 = request write bank flipped;
//                         _s 2 = launch bank flipped; 12 (HBM-PGSTREAM-B seam-window mutant) = request bank read one
//                         stream edge EARLY into a pre-stage and launched from it at the old edge: same data on the same
//                         edges, but setup 4q -> 1q (below the declared seam window; caught only by the window checker).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_multirate_bridge_q #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,
 parameter integer READ_RETURN=10,WRITE_RETURN=7,
 parameter integer MUT=0
)(input wire serial_clk,rst_n,
 input wire [RQ_BITS-1:0] serial_rq,input wire [WQ_BITS-1:0] serial_wq,
 output reg [RR_BITS-1:0] serial_rr,output reg serial_done,
 output reg [RQ_BITS-1:0] rq_b0,rq_b1,output reg [WQ_BITS-1:0] wq_b0,wq_b1,
 input wire [RR_BITS-1:0] rr_b0,rr_b1,input wire dn_b0,dn_b1);
 localparam integer SRD=(3*READ_RETURN+18+3)/4, SWD=(3*WRITE_RETURN+18+3)/4;
 localparam integer RP=READ_RETURN+2, WP=WRITE_RETURN+2;
 localparam integer XR0=4*SRD-3*RP, XW0=4*SWD-3*WP;
 localparam integer STR0=(XR0-8)/4, STW0=(XW0-8)/4;
 localparam integer STR=(MUT==3)?0:STR0, STW=(MUT==3)?0:STW0;
 localparam integer WW=$clog2(SRD+1)>$clog2(SWD+1)?$clog2(SRD+1):$clog2(SWD+1);
`ifndef SYNTHESIS
 initial begin
  if(READ_RETURN<10||WRITE_RETURN<7||WRITE_RETURN>READ_RETURN)$fatal(1,"bridge_q: LG round trip below the 10/7 contract");
  if(XR0<8||XW0<8||XR0-4*STR0>10||XW0-4*STW0>10)$fatal(1,"bridge_q: 2-bank seam window < 2q (XR=%0d XW=%0d)",XR0,XW0);
 end
`endif
 reg [1:0] cnt;                 // serial event n mod 4 (= the old serial_slot)
 reg [WW-1:0] warm;
 // staging: at serial edge e the return source n = e+ST-D sits in bank (n mod 2)
 wire rsel = 1'(cnt+2'(STR)-2'(SRD)) ^ (MUT==1);
 wire dsel = 1'(cnt+2'(STW)-2'(SWD)) ^ (MUT==1);
 wire [RR_BITS-1:0] rr_pick = rsel ? rr_b1 : rr_b0;
 wire dn_pick = dsel ? dn_b1 : dn_b0;
 wire [RR_BITS-1:0] rr_st; wire dn_st;
 if(STR>0)begin:g_rst
  reg [RR_BITS-1:0] p [0:STR-1];
  always @(posedge serial_clk) begin p[0]<=rr_pick; for(integer i=1;i<STR;i=i+1)p[i]<=p[i-1]; end
  assign rr_st=p[STR-1];
 end else begin:g_rst0
  assign rr_st=rr_pick;
 end
 if(STW>0)begin:g_dst
  reg p [0:STW-1];
  always @(posedge serial_clk) begin p[0]<=dn_pick; for(integer i=1;i<STW;i=i+1)p[i]<=p[i-1]; end
  assign dn_st=p[STW-1];
 end else begin:g_dst0
  assign dn_st=dn_pick;
 end
 wire wb = cnt[0] ^ (MUT==6);
 // outputs: no reset (warm is reset, so they read 0 from the first edge of the reset until the warm count; the async
 // reset of these 258 b x 2 data flops was the bridge_rst_n high-fanout textbook WARN of hbm_su_pg_stream_1019)
 always @(posedge serial_clk) begin
  serial_rr <= warm>=WW'(SRD) ? rr_st : '0;
  serial_done <= warm>=WW'(SWD) ? dn_st : 1'b0;
 end
 // request banks: no reset (every bank is written by its event before the first active stream read, j >= 2 reads n >= 0)
 always @(posedge serial_clk)
  if(wb)begin rq_b1<=serial_rq;wq_b1<=serial_wq;end else begin rq_b0<=serial_rq;wq_b0<=serial_wq;end
 always @(posedge serial_clk or negedge rst_n)begin
  if(!rst_n)begin
   cnt<=0;warm<=0;
  end else begin
   cnt<=cnt+1'b1;
   if(warm<WW'(SRD>SWD?SRD:SWD))warm<=warm+1'b1;
  end
 end
endmodule

module ot_hbm_su_multirate_bridge_s #(
 parameter integer RQ_BITS=17,WQ_BITS=281,RR_BITS=257,
 parameter integer READ_RETURN=10,WRITE_RETURN=7,
 parameter integer MUT=0
)(input wire stream_clk,rst_n,
 input wire [RQ_BITS-1:0] rq_b0,rq_b1,input wire [WQ_BITS-1:0] wq_b0,wq_b1,
 output reg [RR_BITS-1:0] rr_b0,rr_b1,output reg dn_b0,dn_b1,
 output reg [RQ_BITS-1:0] stream_rq,output reg [WQ_BITS-1:0] stream_wq,
 input wire [RR_BITS-1:0] stream_rr,input wire stream_done,
 output reg fault);
 localparam integer RP=READ_RETURN+2, WP=WRITE_RETURN+2;
 reg [3:0] phase;
 reg [4:0] stream_warm;
 reg [RP-1:0] active_pipe,read_pipe;
 reg [WP-1:0] write_pipe;
 // the old bridge's event map (request-register event j -> serial source n mod 4)
 function automatic [1:0] slot_for_phase(input [3:0] p);
  reg [3:0] n;
  begin
   n=3*{2'b0,p[3:2]};
   if(p[1:0]==3)n=n+1;
   if(p[1:0]==0)n=n-1;
   slot_for_phase=n[1:0];
  end
 endfunction
 wire active=phase[1:0]!=1 && stream_warm>=2;
 wire [1:0] lslot=slot_for_phase(phase), rslot=slot_for_phase(phase-4'(RP)), dslot=slot_for_phase(phase-4'(WP));
 wire lsel=lslot[0] ^ (MUT==2);
 wire rsel=rslot[0];
 wire dsel=dslot[0];
 wire [RQ_BITS-1:0] rq_sel = lsel ? rq_b1 : rq_b0;
 wire [WQ_BITS-1:0] wq_sel = lsel ? wq_b1 : wq_b0;
 // MUT 12 only: pre-stage read one stream edge early (the bank of the NEXT phase); unused (removed) otherwise
 wire [1:0] nslot=slot_for_phase(phase+4'd1);
 wire nsel=nslot[0];
 reg [RQ_BITS-1:0] rq_pre; reg [WQ_BITS-1:0] wq_pre;
 always @(posedge stream_clk) begin rq_pre <= nsel ? rq_b1 : rq_b0; wq_pre <= nsel ? wq_b1 : wq_b0; end
 wire [RQ_BITS-1:0] rq_pick = (MUT==12) ? rq_pre : rq_sel;
 wire [WQ_BITS-1:0] wq_pick = (MUT==12) ? wq_pre : wq_sel;
 // bench window checker: where the request bank is actually read (stream edge, bank)
 wire rd_v = (MUT==12) ? (phase[1:0]!=2'd0 && stream_warm>=1) : active;
 wire rd_b = (MUT==12) ? nsel : lsel;
 // launch registers: no reset (active is 0 while stream_warm is reset)
 always @(posedge stream_clk) begin
  stream_rq<=active ? rq_pick : '0;
  stream_wq<=active ? wq_pick : '0;
 end
 // return banks: no reset (serial reads are gated by its warm count until source 0 has been captured)
 always @(posedge stream_clk)begin
  if(active_pipe[RP-1])begin if(rsel)rr_b1<=stream_rr; else rr_b0<=stream_rr; end
  if(active_pipe[WP-1])begin if(dsel)dn_b1<=stream_done; else dn_b0<=stream_done; end
 end
 always @(posedge stream_clk or negedge rst_n)begin
  if(!rst_n)begin
   phase<=0;stream_warm<=0;
   active_pipe<=0;read_pipe<=0;write_pipe<=0;fault<=0;
  end else begin
   phase<=phase+1'b1;if(stream_warm<16)stream_warm<=stream_warm+1'b1;
   active_pipe<={active_pipe[RP-2:0],active};
   read_pipe<={read_pipe[RP-2:0],active && rq_pick[RQ_BITS-1]};
   write_pipe<={write_pipe[WP-2:0],active && wq_pick[WQ_BITS-1]};
   if(stream_rr[RR_BITS-1]!==read_pipe[RP-1] || stream_done!==write_pipe[WP-1])fault<=1;
  end
 end
endmodule
`default_nettype wire
