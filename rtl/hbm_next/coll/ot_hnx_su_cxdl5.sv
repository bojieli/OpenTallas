`timescale 1ps/1ps
`default_nettype none
// HBM-NEXT-UNITS-COLL 2026-10-19: L = 5 COLL delivery lanes landing on the UNCHANGED SU slices (next-release die, P = 4).
//
// Decision (SU landing of the 5th lane, results/arch/hbm_next_1019/units/coll/README.md): no 5th SU slice, no new RF
// write port. Every SU slice already has TWO independent delivery write groups (pgslice: dw_v[HI] writes banks
// 16HI..16HI+15 at row dw_row[9HI+:9]; dw_v = 2'b11 writes both in one serial edge), and a d4g lane uses at most ONE of
// them per serial edge (a lane carries one 64-B flit a serial edge: 3 stream events per 4 stream edges = 3 serial
// edges). Lane 4 therefore lands in the FREE half of whichever slice its flit addresses (ob[5:4]), in the same serial
// edge as that slice's own lane. The compiler's static calendar picks, for every lane-4 flit, an edge where the own
// lane's flit (if any) is in the other half; a same-half collision is a compile error and latches FAULT here (no
// arbitration, no backpressure).
//
// Lane 4 travels as a neighbour chain along the quadrant's SU band: tap s (beside slice s) registers the stream for
// tap s + 1 (one stream edge a hop, fixed latency) and keeps the flits with ob[5:4] == s in its own bank pair. The tap
// is the d4g stream leaf ot_hbm_su_static_cxport_dl_s with the slice filter in front and the forward register added.
// The serial leaf ot_hnx_su_cxdl_q2 is the d4g ot_hbm_su_static_cxport_dl_q with a second bank pair (lane 4): per half,
// own | lane 4 (AND-OR, exact d4g output when lane 4 is idle).
// Calendar mapping (both bank pairs share the epoch: event k of a stream leaf is read at the same serial edge as event k
// of every other leaf of the quadrant): a lane-4 flit emitted at stream edge A reaches tap s at A + s, must not land on
// stream phase 2 there ((A + s) mod 4 != 2) and is written together with the own lane's event of the same index.
// Wires a quadrant: lane-4 stream 586 b into tap 0, 3 neighbour hops of 586 b, 1,065-b seam tap -> serial leaf per slice
// (abutted, as dl_s -> dl_q); the slice's dw face (1,044 b) is unchanged.
// MUT (bench, must FAIL): 11 same-half collision not checked; 12 tap ignores the slice filter; 13 lane-4 halves swapped.

module ot_hnx_su_cxdl_tap_s #(parameter integer QID=0, S=0, MUT=0, R=4)(
 input wire clk_s, rst_s_n,
 input wire x_valid,                 // lane-4 stream at this tap
 input wire [544:0] x_flit,
 input wire [39:0] x_obase,
 output reg y_valid,                 // forwarded to tap S+1 (registered hop)
 output reg [544:0] y_flit,
 output reg [39:0] y_obase,
 output wire [523:0] b0, b1,         // bank pair as dl_s {nz 3, row 9, flit 512}
 output wire [2*R-1:0] v0, v1,
 output wire sfault_s
);
 wire mine = x_valid && ((MUT==12) ? 1'b1 : (x_obase[5:4] == 2'(S)));
 ot_hbm_su_static_cxport_dl_s #(.QID(QID),.G(S),.MUT(0),.R(R)) u_s(.clk_s(clk_s),.rst_s_n(rst_s_n),.del_valid(mine),
  .del_flit(x_flit),.del_obase(x_obase),.b0(b0),.b1(b1),.v0(v0),.v1(v1),.sfault_s(sfault_s));
 always @(posedge clk_s) begin y_flit <= x_flit; y_obase <= x_obase; end
 always @(posedge clk_s or negedge rst_s_n) if(!rst_s_n) y_valid <= 1'b0; else y_valid <= x_valid;
endmodule

module ot_hnx_su_cxdl_q2 #(parameter integer MUT=0, R=4)(
 input wire clk_q, rst_q_n,
 input wire [523:0] b0, b1,          // own lane (dl_s G)
 input wire [2*R-1:0] v0, v1,
 input wire sfault_s,
 input wire [523:0] c0, c1,          // lane 4 (tap G)
 input wire [2*R-1:0] u0, u1,
 input wire tfault_s,
 output reg [1:0] dw_v,
 output reg [17:0] dw_row,
 output reg [1023:0] dw_d,
 output reg fault
);
 (* keep = "true" *) reg [R-1:0] rp;
 always @(posedge clk_q or negedge rst_q_n)
  if(!rst_q_n) rp <= {R{1'b1}}; else rp <= ~rp;
 wire [2*R-1:0] dv = rp[0] ? v1 : v0;
 wire [2*R-1:0] du0 = rp[0] ? u1 : u0;
 wire [2*R-1:0] du = (MUT==13) ? {du0[R-1:0], du0[2*R-1:R]} : du0;
 wire vh = dv[R], vl = dv[0], wh = du[R], wl = du[0];
 wire [523:0] dlx, elx;
 for(genvar r=0;r<R;r=r+1) begin : g_sel
  assign dlx[128*r +: 128] = rp[r] ? b1[128*r +: 128] : b0[128*r +: 128];
  assign elx[128*r +: 128] = rp[r] ? c1[128*r +: 128] : c0[128*r +: 128];
 end
 assign dlx[523:512] = rp[0] ? b1[523:512] : b0[523:512];
 assign elx[523:512] = rp[0] ? c1[523:512] : c0[523:512];
 wire dbad = (vh || vl) && (|dlx[523:521]);
 wire ebad = (wh || wl) && (|elx[523:521]);
 wire coll = (MUT==11) ? 1'b0 : ((vh && wh) || (vl && wl));
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) dw_v<=2'd0; else dw_v <= {vh | wh, vl | wl};
 always @(posedge clk_q) begin
  dw_row <= {(dlx[520:512] & {9{vh}}) | (elx[520:512] & {9{wh}}), (dlx[520:512] & {9{vl}}) | (elx[520:512] & {9{wl}})};
  for(integer r=0;r<R;r=r+1) begin
   dw_d[512+128*r +: 128] <= (dlx[128*r +: 128] & {128{dv[R+r]}}) | (elx[128*r +: 128] & {128{du[R+r]}});
   dw_d[128*r +: 128]     <= (dlx[128*r +: 128] & {128{dv[r]}})   | (elx[128*r +: 128] & {128{du[r]}});
  end
 end
 reg sf_q, tf_q;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) begin sf_q<=1'b0; tf_q<=1'b0; end else begin sf_q<=sfault_s; tf_q<=tfault_s; end
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) fault<=1'b0; else if(dbad||ebad||coll||sf_q||tf_q) fault<=1'b1;
endmodule

// One quadrant's delivery landing at L = 5: lanes 0..3 as d4g (dl_s G unchanged), lane 4 through the tap chain.
module ot_hnx_su_cxdl5 #(parameter integer QID=0, MUT=0)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,
 input wire [4:0] del_valid,
 input wire [5*545-1:0] del_flit,
 input wire [5*40-1:0] del_obase,
 output wire [7:0] dw_v,
 output wire [71:0] dw_row,
 output wire [4095:0] dw_d,
 output wire [3:0] fault
);
 wire xv[0:4]; wire [544:0] xf[0:4]; wire [39:0] xo[0:4];
 assign xv[0] = del_valid[4]; assign xf[0] = del_flit[4*545 +: 545]; assign xo[0] = del_obase[4*40 +: 40];
 for(genvar g=0; g<4; g=g+1) begin : g_sl
  wire [523:0] b0, b1, c0, c1; wire [7:0] v0, v1, u0, u1; wire sf, tf;
  ot_hbm_su_static_cxport_dl_s #(.QID(QID),.G(g),.MUT(0)) u_s(.clk_s(clk_s),.rst_s_n(rst_s_n),.del_valid(del_valid[g]),
   .del_flit(del_flit[545*g +: 545]),.del_obase(del_obase[40*g +: 40]),.b0(b0),.b1(b1),.v0(v0),.v1(v1),.sfault_s(sf));
  ot_hnx_su_cxdl_tap_s #(.QID(QID),.S(g),.MUT(MUT)) u_t(.clk_s(clk_s),.rst_s_n(rst_s_n),.x_valid(xv[g]),.x_flit(xf[g]),
   .x_obase(xo[g]),.y_valid(xv[g+1]),.y_flit(xf[g+1]),.y_obase(xo[g+1]),.b0(c0),.b1(c1),.v0(u0),.v1(u1),.sfault_s(tf));
  ot_hnx_su_cxdl_q2 #(.MUT(MUT)) u_q(.clk_q(clk_q),.rst_q_n(rst_q_n),.b0(b0),.b1(b1),.v0(v0),.v1(v1),.sfault_s(sf),
   .c0(c0),.c1(c1),.u0(u0),.u1(u1),.tfault_s(tf),.dw_v(dw_v[2*g +: 2]),.dw_row(dw_row[18*g +: 18]),
   .dw_d(dw_d[1024*g +: 1024]),.fault(fault[g]));
 end
endmodule
`default_nettype wire
