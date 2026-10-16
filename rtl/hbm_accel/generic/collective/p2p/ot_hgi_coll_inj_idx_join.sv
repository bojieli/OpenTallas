`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_inj_idx_join (H-NETLIST/coll 2026-10-16): the SW COLL inject-source join. It closes
// IDX_TOPK_TX_INJECTION (hb_idx.tx_v/tx had no consumer) and COLL_INJECTION_READ_SERVICE for hb_coll_SW
// without changing the closed COLL master. It sits on hb_coll_SW.inj_d and serves each of the two inject lanes
// either from the SU quarter's answer (su_inj_d) or from an 8-flit staging register file of the actual INDEX
// TopK link frames (hb_idx.tx).
// The source is chosen per lane by the request address: addr_lo[39]=1 means IDX staging, 0 means SU. Bit 39 is
// reserved in the SU element address space.
// Static schedule, all fixed. There is no ready, credit, queue, arbitration or retry. Checks latch fault and
// never move an edge.
//   Request: COLL registers inj_rd/inj_idx/hgi_inj_addr at edge P (pins change after P). The join captures
//            them at P+1 (pin register) and delays them to P+INJLAT-3.
//   Staging: the IDX producer registers tx at T. The join captures it at T+1 (pin register) and writes
//            slot = flit16[2:0] at T+2. A request reading that flit needs P+INJLAT-2 >= T+3. Slots are
//            overwritten 16 edges later by the next-but-one emit (emits are 8 edges apart, 4 flits each).
//   Read:    at P+INJLAT-2, idx_q[j] <= staging[inj_idx[16j+:3]], src_q[j] <= addr_lo[39], and
//            su_q <= su_inj_d (SU pin register, sampled every edge). So the SU must have updated its inj_d
//            output register at P+INJLAT-3 (= P+9 for INJLAT 12).
//   Out:     at P+INJLAT-1, inj_d[512j+:512] <= src_q[j] ? idx_q[j] : su_q[j] (2:1 mux of registers), so
//            COLL samples it at P+INJLAT.
// IDX word: inj_d lane = tx data[511:0] = {ids U32 x8, scores FP32 x8} = {hi sector, lo sector}. COLL supplies the
// 33-bit header from its calendar (p_inj_meta). The join checks the provenance it can see. Fault on:
//   - IDX read of an empty slot, or a stored flit16 != requested inj_idx flit (stale or mis-scheduled read);
//   - IDX read whose addr_hi != addr_lo+8;
//   - partial IDX emit (tx_v not 0000/1111), header v=0 on a valid lane, or two valid flits on one slot;
//   - MUT bench mutants (must FAIL): 1 = output one edge early (no read stage); 2 = select inverted;
//     3 = slot index off by one; 4 = provenance check disabled.
module ot_hgi_coll_inj_idx_join #(
 parameter integer INJLAT=12, MUT=0
)(
 input wire clk, rst_n,
 input wire [1:0] inj_rd,
 input wire [31:0] inj_idx,
 input wire [159:0] inj_addr,
 input wire [1023:0] su_inj_d,
 input wire [3:0] idx_tx_v,
 input wire [2179:0] idx_tx,
 output reg [1023:0] inj_d,
 output reg fault
);
 localparam integer D=INJLAT-4;   // delay-line stages after the pin capture: pin P+1, dl[D-1] at P+INJLAT-3
 initial if(INJLAT<5)$fatal(1,"inj join needs INJLAT>=5");
 // ------------------------------------------------ pin registers
 reg [1:0] rq_rd; reg [31:0] rq_idx; reg [159:0] rq_addr;
 reg [3:0] tx_v_q; reg [2179:0] tx_q;
 reg [1023:0] su_q;
 always @(posedge clk) begin rq_idx<=inj_idx; rq_addr<=inj_addr; tx_q<=idx_tx; su_q<=su_inj_d; end
 // reset is captured on one flop (async assert, sync release); control flops reset from it
 reg rst_q;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_q<=1'b0; else rst_q<=1'b1;
 always @(posedge clk or negedge rst_q) if(!rst_q) begin rq_rd<=0; tx_v_q<=0; end else begin rq_rd<=inj_rd; tx_v_q<=idx_tx_v; end
 // ------------------------------------------------ request delay line (compact per-lane record)
 // rec = {rd, src_idx, hi_ok, flit16}
 wire [18:0] rec0 [0:1];
 for(genvar j=0;j<2;j=j+1)begin:g_rec
  wire [39:0] lo=rq_addr[80*j+:40], hi=rq_addr[80*j+40+:40];
  assign rec0[j]={rq_rd[j], lo[39], hi==lo+40'd8, rq_idx[16*j+:16]};
 end
 reg [37:0] dl [0:D-1];
 always @(posedge clk or negedge rst_q)
  if(!rst_q) begin for(integer k=0;k<D;k=k+1) dl[k]<=0; end
  else begin dl[0]<={rec0[1],rec0[0]}; for(integer k=1;k<D;k=k+1) dl[k]<=dl[k-1]; end
 wire [37:0] rd_rec = dl[D-1];
 // ------------------------------------------------ staging (8 flits)
 reg [511:0] st_d [0:7]; reg [15:0] st_f [0:7]; reg [7:0] st_v;
 reg stage_bad;
 always @* begin
  stage_bad = (tx_v_q!=4'b0000 && tx_v_q!=4'b1111);
  for(integer a=0;a<4;a=a+1) begin
   if(tx_v_q[a] && !tx_q[a*545+544]) stage_bad=1'b1;
   for(integer b=a+1;b<4;b=b+1)
    if(tx_v_q[a] && tx_v_q[b] && tx_q[a*545+512+:3]==tx_q[b*545+512+:3]) stage_bad=1'b1;
  end
 end
 always @(posedge clk) for(integer a=0;a<4;a=a+1) if(tx_v_q[a]) begin
  st_d[tx_q[a*545+512+:3]] <= tx_q[a*545+:512];
  st_f[tx_q[a*545+512+:3]] <= tx_q[a*545+512+:16];
 end
 always @(posedge clk or negedge rst_q)
  if(!rst_q) st_v<=0; else for(integer a=0;a<4;a=a+1) if(tx_v_q[a]) st_v[tx_q[a*545+512+:3]]<=1'b1;
 // ------------------------------------------------ read stage (P+INJLAT-2) and output (P+INJLAT-1)
 reg [511:0] idx_q [0:1]; reg [1:0] src_q;
 reg read_bad;
 always @* begin
  read_bad=1'b0;
  for(integer j=0;j<2;j=j+1) begin : g_chk
   reg [18:0] r; reg [2:0] s;
   r=rd_rec[19*j+:19]; s=r[2:0]+((MUT==3)?3'd1:3'd0);
   if(r[18] && r[17]) begin
    if(!r[16]) read_bad=1'b1;
    if(MUT!=4 && (!st_v[s] || st_f[s]!=r[15:0])) read_bad=1'b1;
   end
  end
 end
 always @(posedge clk) for(integer j=0;j<2;j=j+1) idx_q[j] <= st_d[rd_rec[19*j+:3]+((MUT==3)?3'd1:3'd0)];
 always @(posedge clk or negedge rst_q)
  if(!rst_q) src_q<=0; else for(integer j=0;j<2;j=j+1) src_q[j] <= rd_rec[19*j+17] ^ (MUT==2);
 always @(posedge clk)
  for(integer j=0;j<2;j=j+1)
   if(MUT==1) inj_d[512*j+:512] <= (rd_rec[19*j+17]) ? st_d[rd_rec[19*j+:3]] : su_inj_d[512*j+:512];
   else       inj_d[512*j+:512] <= src_q[j] ? idx_q[j] : su_q[512*j+:512];
 always @(posedge clk or negedge rst_q)
  if(!rst_q) fault<=1'b0; else if(stage_bad || read_bad) fault<=1'b1;
endmodule
`default_nettype wire
