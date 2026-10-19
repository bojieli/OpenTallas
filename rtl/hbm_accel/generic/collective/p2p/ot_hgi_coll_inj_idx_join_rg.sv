`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_inj_idx_join_rg (HBM-TILES-B 10-17): successor of ot_hgi_coll_inj_idx_join with IDENTICAL edges and
// faults (lockstep + the original bench/mutants), restructured after its pre-route gate (hcoll_inj_idx_join, HBM-C):
// TT clock insertion 396 ps on one 9,926-sink root, and the dl[D-1] slot select broadcast drove 4,208 / 4,180 loads.
//  - TWO REGIONAL ROOTS: region r (clk_r<r>) owns data bits [256r+:256] of every 512-bit word (both inject lanes, the
//    8-flit staging file, the SU word, the output). Data never crosses regions; each region captures the small control
//    (request, tx_v, flit slots) itself, so the only shared pins are the ~270 control bits (fan-out 2 at the pin).
//    The die drives clk_r0/clk_r1 from one regional source (neighbour-relative, phase-aligned like any tile root pair).
//  - REPLICATED SELECTS: per 32-bit group (8 per region), kept copies of the read slot / source select (loaded with
//    dl[D-2], so they equal dl[D-1]) and of tx_v / the write slots: every copy drives <= ~256 loads.
//  - Reset: one async-assert/sync-release capture per region (rst_q<r>); fault logic lives in region 0 only.
// PORTS are split by region so every data pin belongs to one root (die contract: bit-range edges):
//   idx_tx_r<r>[a*256+:256]   = idx_tx[a*545+256r+:256]     (flit a data half r)
//   idx_tx_h[a*33+:33]        = idx_tx[a*545+512+:33]       (flit a header, shared control)
//   su_inj_d_r<r>[j*256+:256] = su_inj_d[512j+256r+:256],  inj_d_r<r>[j*256+:256] = inj_d[512j+256r+:256]
// Control pins are REPLICATED per region (die fans the producer register out to both pins; each root captures only its
// own pins): region 1 uses rst_n_r1, inj_rd_r1, inj_idx_r1, inj_addr_r1, idx_tx_v_r1, idx_tx_h_r1.
// ot_hgi_coll_inj_idx_join_rg_flat (below) restores the original port shape for benches. MUT 1..4 as the original.
module ot_hgi_coll_inj_idx_join_rg #(
 parameter integer INJLAT=12, MUT=0
)(
 input wire clk_r0, clk_r1, rst_n, rst_n_r1,
 input wire [1:0] inj_rd, inj_rd_r1,
 input wire [31:0] inj_idx, inj_idx_r1,
 input wire [159:0] inj_addr, inj_addr_r1,
 input wire [511:0] su_inj_d_r0, su_inj_d_r1,
 input wire [3:0] idx_tx_v, idx_tx_v_r1,
 input wire [131:0] idx_tx_h, idx_tx_h_r1,
 input wire [1023:0] idx_tx_r0, idx_tx_r1,
 output wire [511:0] inj_d_r0, inj_d_r1,
 output wire fault
);
 // flat views (wiring only)
 wire [1023:0] su_inj_d, inj_d; wire [2179:0] idx_tx, idx_tx1;
 for(genvar j=0;j<2;j=j+1)begin:g_flat
  assign su_inj_d[512*j+:256]=su_inj_d_r0[256*j+:256]; assign su_inj_d[512*j+256+:256]=su_inj_d_r1[256*j+:256];
  assign inj_d_r0[256*j+:256]=inj_d[512*j+:256];       assign inj_d_r1[256*j+:256]=inj_d[512*j+256+:256];
 end
 for(genvar a=0;a<4;a=a+1)begin:g_tx
  assign idx_tx[a*545+:256]=idx_tx_r0[a*256+:256]; assign idx_tx[a*545+256+:256]=idx_tx_r1[a*256+:256];
  assign idx_tx[a*545+512+:33]=idx_tx_h[a*33+:33];
  assign idx_tx1[a*545+:512]=512'd0; assign idx_tx1[a*545+512+:33]=idx_tx_h_r1[a*33+:33];   // region-1 header view
 end
 localparam integer D=INJLAT-4;
 localparam integer GB=32, NG=256/GB;
 initial if(INJLAT<6)$fatal(1,"inj join rg needs INJLAT>=6 (select replicas load from dl[D-2])");
 wire [1:0] fault_r;
 assign fault=fault_r[0];
 for(genvar r=0;r<2;r=r+1)begin:g_reg
  wire ck = r ? clk_r1 : clk_r0;
  wire rn = r ? rst_n_r1 : rst_n;
  wire [1:0] p_rd = r ? inj_rd_r1 : inj_rd; wire [31:0] p_idx = r ? inj_idx_r1 : inj_idx;
  wire [159:0] p_addr = r ? inj_addr_r1 : inj_addr; wire [3:0] p_txv = r ? idx_tx_v_r1 : idx_tx_v;
  wire [2179:0] p_tx = r ? idx_tx1 : idx_tx;      // header bits only are read through p_tx
  // ---------------- reset capture (async assert, sync release), one per region
  reg rst_q;
  always @(posedge ck or negedge rn) if(!rn) rst_q<=1'b0; else rst_q<=1'b1;
  // ---------------- control pin registers (region copy)
  reg [1:0] rq_rd; reg [31:0] rq_idx; reg [159:0] rq_addr;
  reg [3:0] tx_v_q; reg [16:0] tx_h [0:3];       // {v544, flit16}
  always @(posedge ck) begin rq_idx<=p_idx; rq_addr<=p_addr;
   for(integer a=0;a<4;a=a+1) tx_h[a]<={p_tx[a*545+544],p_tx[a*545+512+:16]}; end
  always @(posedge ck or negedge rst_q) if(!rst_q) begin rq_rd<=0; tx_v_q<=0; end else begin rq_rd<=p_rd; tx_v_q<=p_txv; end
  // ---------------- request delay line (region copy)
  wire [18:0] rec0 [0:1];
  for(genvar j=0;j<2;j=j+1)begin:g_rec
   wire [39:0] lo=rq_addr[80*j+:40], hi=rq_addr[80*j+40+:40];
   assign rec0[j]={rq_rd[j], lo[39], hi==lo+40'd8, rq_idx[16*j+:16]};
  end
  reg [37:0] dl [0:D-1];
  always @(posedge ck or negedge rst_q)
   if(!rst_q) begin for(integer k=0;k<D;k=k+1) dl[k]<=0; end
   else begin dl[0]<={rec0[1],rec0[0]}; for(integer k=1;k<D;k=k+1) dl[k]<=dl[k-1]; end
  wire [37:0] rd_rec = dl[D-1];
  wire [37:0] pre_rec = dl[D-2];
  // ---------------- data pin registers (this region's half)
  reg [255:0] tx_d [0:3]; reg [255:0] su_q [0:1];
  always @(posedge ck) begin
   for(integer a=0;a<4;a=a+1) tx_d[a]<=r ? idx_tx_r1[a*256+:256] : idx_tx_r0[a*256+:256];
   for(integer j=0;j<2;j=j+1) su_q[j]<=su_inj_d[512*j+256*r+:256];
  end
  // ---------------- per 32-bit group: replicated selects, staging slice, read, output
  for(genvar g=0;g<NG;g=g+1)begin:g_grp
   (* keep = "true", dont_touch = "true" *) reg [3:0] gv;          // copy of tx_v_q
   (* keep = "true", dont_touch = "true" *) reg [11:0] gs;         // copies of the 4 write slots
   (* keep = "true", dont_touch = "true" *) reg [3:0] rsel [0:1];  // copy of dl[D-1] {src, slot} per lane
   (* keep = "true", dont_touch = "true" *) reg [1:0] srcq;        // copy of src_q
   always @(posedge ck) for(integer a=0;a<4;a=a+1) gs[a*3+:3]<=p_tx[a*545+512+:3];
   always @(posedge ck or negedge rst_q) if(!rst_q) gv<=0; else gv<=p_txv;
   always @(posedge ck or negedge rst_q)
    if(!rst_q) begin rsel[0]<=0; rsel[1]<=0; srcq<=0; end
    else for(integer j=0;j<2;j=j+1) begin
     rsel[j]<={pre_rec[19*j+17],pre_rec[19*j+:3]};
     srcq[j]<=rsel[j][3]^(MUT==2);
    end
   reg [GB-1:0] st [0:7];
   always @(posedge ck) for(integer a=0;a<4;a=a+1) if(gv[a]) st[gs[a*3+:3]] <= tx_d[a][g*GB+:GB];
   reg [GB-1:0] iq [0:1];
   always @(posedge ck) for(integer j=0;j<2;j=j+1) iq[j] <= st[rsel[j][2:0]+((MUT==3)?3'd1:3'd0)];
   reg [GB-1:0] o [0:1];
   always @(posedge ck)
    for(integer j=0;j<2;j=j+1)
     if(MUT==1) o[j] <= rsel[j][3] ? st[rsel[j][2:0]] : su_inj_d[512*j+256*r+g*GB+:GB];
     else       o[j] <= srcq[j] ? iq[j] : su_q[j][g*GB+:GB];
   for(genvar j=0;j<2;j=j+1)begin:g_o assign inj_d[512*j+256*r+g*GB+:GB]=o[j]; end
  end
  // ---------------- checks (region 0 only; identical to the original)
  if(r==0)begin:g_chk
   reg [15:0] st_f [0:7]; reg [7:0] st_v; reg flt;
   reg stage_bad, read_bad;
   always @* begin
    stage_bad = (tx_v_q!=4'b0000 && tx_v_q!=4'b1111);
    for(integer a=0;a<4;a=a+1) begin
     if(tx_v_q[a] && !tx_h[a][16]) stage_bad=1'b1;
     for(integer b=a+1;b<4;b=b+1)
      if(tx_v_q[a] && tx_v_q[b] && tx_h[a][2:0]==tx_h[b][2:0]) stage_bad=1'b1;
    end
   end
   always @(posedge ck) for(integer a=0;a<4;a=a+1) if(tx_v_q[a]) st_f[tx_h[a][2:0]] <= tx_h[a][15:0];
   always @(posedge ck or negedge rst_q)
    if(!rst_q) st_v<=0; else for(integer a=0;a<4;a=a+1) if(tx_v_q[a]) st_v[tx_h[a][2:0]]<=1'b1;
   always @* begin
    read_bad=1'b0;
    for(integer j=0;j<2;j=j+1) begin : g_c
     reg [18:0] rr; reg [2:0] s;
     rr=rd_rec[19*j+:19]; s=rr[2:0]+((MUT==3)?3'd1:3'd0);
     if(rr[18] && rr[17]) begin
      if(!rr[16]) read_bad=1'b1;
      if(MUT!=4 && (!st_v[s] || st_f[s]!=rr[15:0])) read_bad=1'b1;
     end
    end
   end
   always @(posedge ck or negedge rst_q) if(!rst_q) flt<=1'b0; else if(stage_bad || read_bad) flt<=1'b1;
   assign fault_r[r]=flt;
  end else begin:g_nochk
   assign fault_r[r]=1'b0;
  end
 end
endmodule

// Bench-only flat-port view (original port shape + two roots). Not a hardened master.
module ot_hgi_coll_inj_idx_join_rg_flat #(parameter integer INJLAT=12, MUT=0)(
 input wire clk_r0, clk_r1, rst_n, input wire [1:0] inj_rd, input wire [31:0] inj_idx, input wire [159:0] inj_addr,
 input wire [1023:0] su_inj_d, input wire [3:0] idx_tx_v, input wire [2179:0] idx_tx, output wire [1023:0] inj_d, output wire fault);
 wire [511:0] s0,s1,o0,o1; wire [1023:0] t0,t1; wire [131:0] h;
 for(genvar j=0;j<2;j=j+1)begin:g_j
  assign s0[256*j+:256]=su_inj_d[512*j+:256]; assign s1[256*j+:256]=su_inj_d[512*j+256+:256];
  assign inj_d[512*j+:256]=o0[256*j+:256];    assign inj_d[512*j+256+:256]=o1[256*j+:256];
 end
 for(genvar a=0;a<4;a=a+1)begin:g_a
  assign t0[a*256+:256]=idx_tx[a*545+:256]; assign t1[a*256+:256]=idx_tx[a*545+256+:256]; assign h[a*33+:33]=idx_tx[a*545+512+:33];
 end
 ot_hgi_coll_inj_idx_join_rg #(.INJLAT(INJLAT),.MUT(MUT)) u(.clk_r0(clk_r0),.clk_r1(clk_r1),.rst_n(rst_n),.inj_rd(inj_rd),
  .inj_idx(inj_idx),.inj_addr(inj_addr),.su_inj_d_r0(s0),.su_inj_d_r1(s1),.idx_tx_v(idx_tx_v),.idx_tx_h(h),.idx_tx_r0(t0),
  .rst_n_r1(rst_n),.inj_rd_r1(inj_rd),.inj_idx_r1(inj_idx),.inj_addr_r1(inj_addr),.idx_tx_v_r1(idx_tx_v),.idx_tx_h_r1(h),
  .idx_tx_r1(t1),.inj_d_r0(o0),.inj_d_r1(o1),.fault(fault));
endmodule
`default_nettype wire
