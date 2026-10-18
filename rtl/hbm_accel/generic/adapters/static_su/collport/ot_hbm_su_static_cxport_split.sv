`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SU COLL exchange port SPLIT (HBM-SU3 2026-10-17, coordinator 0dc: "cxport (13.2k pin bits on 264.6 um) is a hub:
// split it"). ot_hbm_su_static_cxport (one per quarter, sucx_<q>) becomes three placeable leaves per quarter, each with
// the same epoch counters (phase-zero release of rst_n = bridge_rst_n), the same pin slots and the same edges:
//   ot_hbm_su_static_cxport_dl #(G) x4  DELIVERY (c) of delivery lane G -> pgslice G (beside su_<q><G>):
//                                       del lane G (586 b stream) in, dw_v/dw_row/dw_d of slice G (1,044 b serial) out.
//                                       Calendar rule (already the compiler's construction, cxport (c)): lane j only
//                                       carries destinations with a[5:4] = j; a lane-j destination in another slice now
//                                       latches FAULT here (it was legal-but-unused in the hub).
//   ot_hbm_su_static_cxport_ij     x1  INJECT (a): inj_rd/inj_addr (stream) + the four slices' port-5 data inj_q (serial)
//                                       -> inj_d (stream), unchanged code and edges (INJ_RET, RQ, RQC, SD as the hub).
//   ot_hbm_su_static_cxport_rc     x1  RED_CARRY (b) + SFU reducer operand (d) (beside sucore_<q>): red_* / red_sel
//                                       (serial), rr_* / ro_* (stream) -> rr_w* / sfu_x (serial), rc_* (stream).
// Reset: each leaf takes the epoch reset (bridge_rst_n, released at stream E0-3q) once per clock domain (rst_s_n stream,
// rst_q_n serial; the die drives both from bridge_rst_n), so every pin has one clock domain.
// Faults: each leaf has its own sticky fault (same set edge as the hub for its causes); the hub's fault = OR of the six.
// ot_hbm_su_static_cxport_split = the composition with the hub's exact ports (bench lockstep vs the hub; H-NETLIST binds
// the six leaves directly). Pin bits: dl 1,634 (x4), ij 5,286, rc 1,451 + clocks/reset/fault (hub 13.2k on one tile).
// MUT (bench, must FAIL): 1 inject select one serial edge early; 2 delivery half bit ignored; 3 rc LATE ignored;
// 4 stream->serial slot map off by one phase (every leaf).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_cx_epoch #(parameter integer MUT=0)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,   // epoch reset per domain
 output reg [1:0] sp, output reg [1:0] sq, output wire [1:0] rslot, output wire s_ev, output wire [1:0] oslot_i
);
 always @(posedge clk_s or negedge rst_s_n) if(!rst_s_n) sp<=2'd0; else sp<=sp+2'd1;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) sq<=2'd0; else sq<=(sq==2'd2)?2'd0:sq+2'd1;
 assign rslot = ((sq==2'd1)?2'd0:(sq==2'd2)?2'd1:2'd3) + ((MUT==4)?2'd1:2'd0);
 assign s_ev = sp!=2'd2;
 assign oslot_i = (sp==2'd1)?2'd0:(sp==2'd3)?2'd1:2'd2;
endmodule

// ------------------------------------------------------------------------------------------------ delivery leaf, lane G
module ot_hbm_su_static_cxport_dl #(parameter integer QID=0, G=0, MUT=0)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,   // epoch reset per domain
 input wire del_valid,               // = hub del_valid[G]
 input wire [544:0] del_flit,        // = hub del_flit[545G +: 545]
 input wire [39:0] del_obase,        // = hub del_obase[40G +: 40]
 output reg [1:0] dw_v,              // = hub dw_v[2G +: 2]
 output reg [17:0] dw_row,           // = hub dw_row[18G +: 18]
 output reg [1023:0] dw_d,           // = hub dw_d[1024G +: 1024]
 output reg fault
);
 wire [1:0] sp, sq, rslot, oslot_i; wire s_ev;
 ot_hbm_su_cx_epoch #(.MUT(MUT)) u_ep(.clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_s_n),.rst_q_n(rst_q_n),.sp(sp),.sq(sq),.rslot(rslot),.s_ev(s_ev),.oslot_i(oslot_i));
 // PIN-FIRST SLOTS (HBM-SU6 10-17; gate bf7c343cb: del_valid / del_obase each drove ~1,048 decode gates straight from
 // the pin). The four phase slots ARE the pin registers: each holds the RAW lane {aperture partials, row, flit} plus R
 // kept copies of the 2-bit lane code {hi&v, !hi&v}; every pin feeds only its slot bits (<= 2 gate levels + the slot
 // enable). Half placement and valid zeroing moved to the serial side behind the 4:1 slot mux, one AND per bit, gated
 // by copy r of the lane code (<= ~131 loads per copy); the aperture check finishes there too (it feeds only FAULT).
 // Same edges as the hub (no added cycle): dw_* / fault at the same serial edge as before.
 localparam integer R=4;
 wire [39:0] ob_s = del_obase;
 wire hi_s = (MUT==2) ? 1'b0 : ob_s[6];
 wire vh_s = del_valid && hi_s, vl_s = del_valid && !hi_s;
 wire [2:0] nz_s = {|{ob_s[3:0], ob_s[17:16]^2'(QID), !del_flit[544], ob_s[5:4]^2'(G)}, |ob_s[28:18], |ob_s[39:29]};
 reg [523:0] dl_slot [0:3];                     // {nz 3, row 9, flit 512}
 (* keep = "true" *) reg [8*R-1:0] dv_slot;     // slot s: dv_slot[2R*s +: 2R] = {vh x R, vl x R}
 always @(posedge clk_s) begin
  dl_slot[sp] <= {nz_s, ob_s[15:7], del_flit[511:0]};
  for(integer s=0;s<4;s=s+1) if(sp==2'(s)) dv_slot[2*R*s +: 2*R] <= {{R{vh_s}}, {R{vl_s}}};
 end
 reg sfault_s;
 always @(posedge clk_s or negedge rst_s_n) if(!rst_s_n) sfault_s<=1'b0; else if(sp==2'd2 && del_valid) sfault_s<=1'b1;
 wire [523:0] dl = dl_slot[rslot];
 reg [2*R-1:0] dv;
 always @* case(rslot) 2'd0: dv=dv_slot[0+:2*R]; 2'd1: dv=dv_slot[2*R+:2*R]; 2'd2: dv=dv_slot[4*R+:2*R]; default: dv=dv_slot[6*R+:2*R]; endcase
 wire vh = dv[R], vl = dv[0];
 wire dbad = (vh || vl) && (|dl[523:521]);
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) dw_v<=2'd0; else dw_v <= {vh, vl};
 always @(posedge clk_q) begin
  dw_row <= {dl[520:512] & {9{vh}}, dl[520:512] & {9{vl}}};
  for(integer r=0;r<R;r=r+1) begin
   dw_d[512+128*r +: 128] <= dl[128*r +: 128] & {128{dv[R+r]}};
   dw_d[128*r +: 128]     <= dl[128*r +: 128] & {128{dv[r]}};
  end
 end
 reg sf_q;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) sf_q<=1'b0; else sf_q<=sfault_s;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) fault<=1'b0; else if(dbad||sf_q) fault<=1'b1;
endmodule

// ------------------------------------------------------------------------------------------------ inject leaf
module ot_hbm_su_static_cxport_ij #(
 parameter integer QID=0, B39_NOOP=0, INJ_RET=11, RQ=0, RQC=0, SD=0, MUT=0
)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,   // epoch reset per domain
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output reg [1023:0] inj_d,
 input wire [1023:0] inj_q0, inj_q1, inj_q2, inj_q3,   // slice G port-5 data (hub inj_q[1024G +: 1024])
 output reg fault
);
 wire [4*1024-1:0] inj_q = {inj_q3, inj_q2, inj_q1, inj_q0};
 function automatic integer lat_of(input integer ph);
  integer a,n,m,pp;
  begin a=40+ph; n=(3*a+3+3)/4; m=n+4+SD; pp=(4*m+3+2)/3; lat_of=pp-a; end
 endfunction
 localparam integer L0=lat_of(0), L1=lat_of(1), L3=lat_of(3);
 localparam integer LMAX=(L0>L1)?((L0>L3)?L0:L3):((L1>L3)?L1:L3);
 localparam integer LMIN=(L0<L1)?((L0<L3)?L0:L3):((L1<L3)?L1:L3);
 localparam integer X=INJ_RET-1-RQ-LMAX;
 localparam integer K=LMAX-LMIN+X;
 initial if(X<0)$fatal(1,"cxport_ij: INJ_RET must be >= 1+RQ+LMAX");
 initial if(RQC>RQ)$fatal(1,"cxport_ij: RQC must be <= RQ");
 wire [1:0] sp, sq, rslot, oslot_i; wire s_ev;
 ot_hbm_su_cx_epoch #(.MUT(MUT)) u_ep(.clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_s_n),.rst_q_n(rst_q_n),.sp(sp),.sq(sq),.rslot(rslot),.s_ev(s_ev),.oslot_i(oslot_i));
 reg sfault_s;
 reg [161:0] rqd [0:RQ-RQC];
 always @(posedge clk_s) begin
  rqd[0] <= {inj_rd, inj_addr};
  for(integer t=1;t<=RQ-RQC;t=t+1) rqd[t] <= rqd[t-1];
 end
 wire [161:0] rq_al = (RQ==RQC) ? {inj_rd, inj_addr} : rqd[(RQ>RQC)?RQ-RQC-1:0];
 // MUX-ONLY CROSSING: the request is decoded on the stream side; the slot holds {nz12, iv4, ig8, ib8} (HBM-SU6: the
 // aperture check is stored as three <=11-bit OR partials per request (<= 2 levels from inj_addr) and finished on the
 // serial side, where it feeds only FAULT -- same edge)
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) sfault_s<=1'b0; else if(sp==2'd2 && (|rq_al[161:160])) sfault_s<=1'b1;
 reg [3:0] iv_s; reg [7:0] ig_s; reg [7:0] ib_s; reg [11:0] nz_s;
 integer k;
 always @* begin
  iv_s=0; ig_s=0; ib_s=0; nz_s=0;
  for(k=0;k<4;k=k+1) begin : dec
   reg [39:0] a; reg [39:0] lo; reg v;
   a  = rq_al[40*k+:40];
   lo = rq_al[80*(k/2)+:40];
   v  = rq_al[160+(k/2)] && !(B39_NOOP!=0 && lo[39]);
   iv_s[k] = v;
   ig_s[2*k+:2] = a[5:4];
   ib_s[2*k+:2] = {a[6],a[3]};
   nz_s[3*k+:3] = {|{a[2:0], a[17:16]^2'(QID), a[39]}, |a[28:18], |a[38:29]};
  end
 end
 reg [31:0] ijd_slot [0:3];
 always @(posedge clk_s) ijd_slot[sp] <= {nz_s, iv_s, ig_s, ib_s};
 wire [31:0] ijd = ijd_slot[rslot];
 wire [3:0] iv = ijd[19:16]; wire [7:0] ig = ijd[15:8]; wire [7:0] ib = ijd[7:0];
 wire ibad = |{iv[3] && (|ijd[31:29]), iv[2] && (|ijd[28:26]), iv[1] && (|ijd[25:23]), iv[0] && (|ijd[22:20])};
 // inject pipe (HBM-SU6): only the 4 valid bits are reset; the g/b fields are datapath (no reset). The select is
 // registered ONE-HOT (64 b = lane k x source 4g+b) one edge ahead, from the pipe word it will equal: each one-hot bit
 // gates 256 data bits (the gate saw ip[3] g/b bits driving 4,096 mux loads and a runtime 1,024-b part-select).
 reg [3:0] ipv [0:3+SD]; reg [15:0] ipgb [0:3+SD];
 always @(posedge clk_q or negedge rst_q_n)
  if(!rst_q_n) begin for(integer t=0;t<=3+SD;t=t+1) ipv[t]<=4'd0; end
  else begin ipv[0]<=iv; for(integer t=1;t<=3+SD;t=t+1) ipv[t]<=ipv[t-1]; end
 always @(posedge clk_q) begin ipgb[0]<={ig,ib}; for(integer t=1;t<=3+SD;t=t+1) ipgb[t]<=ipgb[t-1]; end
 function automatic [63:0] ohdec(input [3:0] v, input [15:0] gb);
  integer kk; begin ohdec=64'd0;
   for(kk=0;kk<4;kk=kk+1) if(v[kk]) ohdec[16*kk + 4*gb[8+2*kk+:2] + gb[2*kk+:2]] = 1'b1; end
 endfunction
 reg [63:0] ioh;                                  // = ohdec(isel) of the hub's isel (ip[3+SD]; MUT 1: ip[2+SD])
 always @(posedge clk_q or negedge rst_q_n)
  if(!rst_q_n) ioh<=64'd0;
  else ioh <= (MUT==1) ? ohdec(ipv[1+SD], ipgb[1+SD]) : ohdec(ipv[2+SD], ipgb[2+SD]);
 reg [4*1024-1:0] iq;
 always @(posedge clk_q) iq <= inj_q;
 wire [4*1024-1:0] isrc = (MUT==1) ? inj_q : iq;
 reg [1023:0] iword;
 always @* begin
  iword = 1024'd0;
  for(k=0;k<4;k=k+1)
   for(integer j=0;j<16;j=j+1) iword[256*k+:256] = iword[256*k+:256] | (isrc[256*j+:256] & {256{ioh[16*k+j]}});
 end
 reg [1023:0] io_slot [0:2];
 always @(posedge clk_q) io_slot[sq] <= iword;
 function automatic integer ins_of(input integer rp);
  integer ph, r; begin r=-1;
   for(ph=0;ph<4;ph=ph+1) if(ph!=2 && ((ph+lat_of(ph))%4)==rp) r=lat_of(ph)-LMIN;
   ins_of=r; end
 endfunction
 localparam integer I0=ins_of(0), I1=ins_of(1), I2=ins_of(2), I3=ins_of(3);
 initial if(I2>=0)$fatal(1,"cxport_ij: an inject event maps to stream phase 2");
 reg [1023:0] idl [0:K];
 reg ins_coll;
 wire [1023:0] ev_i = io_slot[oslot_i];
 integer ins;
 always @* ins = (sp==2'd0)?I0:(sp==2'd1)?I1:(sp==2'd3)?I3:-1;
 always @(posedge clk_s) begin
  for(integer t=0;t<=K;t=t+1) idl[t] <= (t==0) ? 1024'd0 : idl[t-1];
  if(ins>=0) idl[ins] <= ev_i;
 end
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) ins_coll<=1'b0; else if(ins>0 && (|idl[ins-1])) ins_coll<=1'b1;
 always @* inj_d = idl[K];
 reg sf_q;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) sf_q<=1'b0; else sf_q<=sfault_s||ins_coll;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) fault<=1'b0; else if(ibad||sf_q) fault<=1'b1;
endmodule

// ------------------------------------------------------------------------------------------------ RED_CARRY + SFU operand
// rc SFU operand (d): the hub selects ro_slot[rslot] lane red_sel[3:0] (a 64:1 AND-OR) on the stream->serial crossing,
// which STA times at the 1-quantum edge pair (gate: sfu_x -277 ps). Here the crossing is mux-only: every serial edge
// registers the whole slot word (rq, 528 b) and the lane select is serial->serial on the NEXT edge. COMPILER: the
// SFU-source reducer command (red_sel / red_cmd osel=1, lane[6]=1) issues at E+1 instead of E = ceil((3A+3)/4); the
// operand, its ro_v check and the reducer timeline are otherwise unchanged (sfu_x at E+1 is the hub's sfu_x at E).
module ot_hbm_su_static_cxport_rc #(parameter integer MUT=0)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,   // epoch reset per domain
 output reg rc_v,
 output reg [2:0] rc_tag,
 output reg [255:0] rc_d,
 input wire rr_v,
 input wire [2:0] rr_tag,
 input wire [255:0] rr_d,
 input wire red_sv,
 input wire [31:0] red_tag,
 input wire [31:0] red_x,
 output reg rr_wv,
 output reg [4:0] rr_wa,
 output reg [255:0] rr_wd,
 input wire [15:0] ro_v,
 input wire [511:0] ro_x,
 input wire [11:0] red_sel,
 output reg [31:0] sfu_x,
 output reg fault
);
 wire [1:0] sp, sq, rslot, oslot_i; wire s_ev;
 ot_hbm_su_cx_epoch #(.MUT(MUT)) u_ep(.clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_s_n),.rst_q_n(rst_q_n),.sp(sp),.sq(sq),.rslot(rslot),.s_ev(s_ev),.oslot_i(oslot_i));
 reg sfault_s;
 reg [527:0] ro_slot [0:3];
 // MUX-ONLY CROSSING for rr: the tag is one-hot decoded on the stream side (slot {v, tag3, onehot8, d256})
 reg [267:0] rr_slot1 [0:3];
 always @(posedge clk_s) begin ro_slot[sp] <= {ro_v, ro_x}; rr_slot1[sp] <= {rr_v, rr_tag, 8'd1 << rr_tag, rr_d}; end
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) sfault_s<=1'b0; else if(sp==2'd2 && (rr_v||(|ro_v))) sfault_s<=1'b1;
 reg r_sv; reg [31:0] r_tag, r_x;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) r_sv<=1'b0; else r_sv<=red_sv;
 always @(posedge clk_q) begin r_tag<=red_tag; r_x<=red_x; end
 wire cw   = r_sv && r_tag[9];
 wire emit = r_sv && r_tag[13];
 reg [255:0] carry;
 reg [255:0] cvec;
 always @* begin cvec=carry; if(cw) cvec[32*r_tag[12:10]+:32]=r_x; end
 // carry reset (HBM-SU6: rst_q_n drove 271 flops): two kept regional copies released one serial edge after the port.
 // Exact: at that first edge r_sv is still 0 (it is reset by the port), so carry would have reloaded 0 anyway.
 (* keep = "true" *) reg [1:0] crst_n;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) crst_n<=2'b00; else crst_n<=2'b11;
 for(genvar h=0;h<2;h=h+1) begin : g_carry
  always @(posedge clk_q or negedge crst_n[h])
   if(!crst_n[h]) carry[128*h+:128]<=128'd0; else carry[128*h+:128] <= emit ? 128'd0 : cvec[128*h+:128];
 end
 reg [260:0] rc_slot [0:2];
 always @(posedge clk_q) rc_slot[sq] <= {emit, r_tag[17]&&(MUT!=3), r_tag[16:14], cvec};
 reg [7:0] tv; reg [4:0] tdst [0:7];
 wire [267:0] rr1 = rr_slot1[rslot];
 wire rrv = rr1[267]; wire [2:0] rrt = rr1[266:264]; wire [7:0] rroh = rr1[263:256]; wire [255:0] rr_dd = rr1[255:0];
 wire tvh = |(tv & rroh);                     // tv[rrt] as an AND-OR of the one-hot tag
 reg [4:0] tdh; integer u;
 always @* begin tdh = 5'd0; for(u=0;u<8;u=u+1) if(rroh[u]) tdh = tdh | tdst[u]; end
 reg rbad;
 always @(posedge clk_q or negedge rst_q_n)
  if(!rst_q_n) begin tv<=8'd0; rr_wv<=1'b0; rbad<=1'b0; end
  else begin
   rr_wv <= rrv && tvh;
   rbad  <= (rrv && !tvh) || (emit && r_tag[23] && tv[r_tag[16:14]] && !(rrv && rroh[r_tag[16:14]]));
   if(rrv) tv <= tv & ~rroh;
   if(emit && r_tag[23]) tv[r_tag[16:14]] <= 1'b1;
  end
 always @(posedge clk_q) begin
  rr_wa <= tdh; rr_wd <= rr_dd;
  if(emit && r_tag[23]) tdst[r_tag[16:14]] <= r_tag[22:18];
 end
 reg [260:0] pend; reg rc_coll;
 wire [260:0] ev = s_ev ? rc_slot[oslot_i] : 261'd0;
 // HBM-SU6: only pend's valid bit is reset (rst_s_n drove 265 flops); its payload is read only under pend[260]
 always @(posedge clk_s) pend[259:0] <= ev[259:0];
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) begin rc_v<=1'b0; pend[260]<=1'b0; rc_coll<=1'b0; end
  else begin
   pend[260] <= ev[260] && ev[259];
   rc_v <= (ev[260] && !ev[259]) || pend[260];
   if(ev[260] && !ev[259] && pend[260]) rc_coll<=1'b1;
  end
 always @(posedge clk_s)
  if(ev[260] && !ev[259]) begin rc_tag<=ev[258:256]; rc_d<=ev[255:0]; end
  else if(pend[260]) begin rc_tag<=pend[258:256]; rc_d<=pend[255:0]; end
 reg [527:0] ro;
 always @(posedge clk_q) ro <= ro_slot[rslot];          // mux-only crossing; lane select next serial edge
 // HBM-SU6: red_sel[3:0] (528 / 264 loads, a runtime 32-b part-select) is decoded once into a 16-b one-hot (each bit
 // gates 33 loads); the select stays combinational from the pin because sfu_x at this edge is the contract (a pin flop
 // would move the SFU operand to E+2: reducer timeline change, not taken here).
 wire [15:0] ro_oh = 16'd1 << red_sel[3:0];
 wire ro_mine = red_sel[11] && red_sel[7] && red_sel[6];
 wire ro_ext  = red_sel[10:8]==3'd0 || red_sel[10:8]==3'd1 || red_sel[10:8]==3'd3;
 wire ro_bad  = ro_mine && ro_ext && !(|(ro_oh & ro[527:512]));
 reg [31:0] sfu_n;
 always @* begin sfu_n = 32'd0; for(integer l=0;l<16;l=l+1) sfu_n = sfu_n | (ro[32*l+:32] & {32{ro_oh[l]}}); end
 always @(posedge clk_q) sfu_x <= sfu_n;
 reg sf_q;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) sf_q<=1'b0; else sf_q<=sfault_s||rc_coll;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) fault<=1'b0; else if(rbad||ro_bad||sf_q) fault<=1'b1;
endmodule

// ------------------------------------------------------------------------------------------------ composition (bench)
module ot_hbm_su_static_cxport_split #(
 parameter integer QID=0, B39_NOOP=0, INJ_RET=11, RQ=0, RQC=0, SD=0, MUT=0
)(
 input wire clk_s, clk_q, rst_n,
 input wire [1:0] inj_rd, input wire [159:0] inj_addr, output wire [1023:0] inj_d,
 input wire [3:0] del_valid, input wire [2179:0] del_flit, input wire [159:0] del_obase,
 output wire rc_v, output wire [2:0] rc_tag, output wire [255:0] rc_d,
 input wire rr_v, input wire [2:0] rr_tag, input wire [255:0] rr_d,
 input wire [4*1024-1:0] inj_q,
 output wire [4*2-1:0] dw_v, output wire [4*18-1:0] dw_row, output wire [4*1024-1:0] dw_d,
 input wire red_sv, input wire [31:0] red_tag, input wire [31:0] red_x,
 output wire rr_wv, output wire [4:0] rr_wa, output wire [255:0] rr_wd,
 input wire [15:0] ro_v, input wire [511:0] ro_x, input wire [11:0] red_sel, output wire [31:0] sfu_x,
 output wire fault
);
 wire [3:0] f_dl; wire f_ij, f_rc;
 for(genvar g=0;g<4;g=g+1)begin:g_dl
  ot_hbm_su_static_cxport_dl #(.QID(QID),.G(g),.MUT(MUT)) u_dl(.clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_n),.rst_q_n(rst_n),
   .del_valid(del_valid[g]),.del_flit(del_flit[545*g+:545]),.del_obase(del_obase[40*g+:40]),
   .dw_v(dw_v[2*g+:2]),.dw_row(dw_row[18*g+:18]),.dw_d(dw_d[1024*g+:1024]),.fault(f_dl[g]));
 end
 ot_hbm_su_static_cxport_ij #(.QID(QID),.B39_NOOP(B39_NOOP),.INJ_RET(INJ_RET),.RQ(RQ),.RQC(RQC),.SD(SD),.MUT(MUT)) u_ij(
  .clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_n),.rst_q_n(rst_n),.inj_rd(inj_rd),.inj_addr(inj_addr),.inj_d(inj_d),.inj_q0(inj_q[0+:1024]),.inj_q1(inj_q[1024+:1024]),.inj_q2(inj_q[2048+:1024]),.inj_q3(inj_q[3072+:1024]),.fault(f_ij));
 ot_hbm_su_static_cxport_rc #(.MUT(MUT)) u_rc(.clk_s(clk_s),.clk_q(clk_q),.rst_s_n(rst_n),.rst_q_n(rst_n),.rc_v(rc_v),.rc_tag(rc_tag),
  .rc_d(rc_d),.rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.rr_wv(rr_wv),
  .rr_wa(rr_wa),.rr_wd(rr_wd),.ro_v(ro_v),.ro_x(ro_x),.red_sel(red_sel),.sfu_x(sfu_x),.fault(f_rc));
 assign fault = (|f_dl) | f_ij | f_rc;
endmodule
`default_nettype wire
