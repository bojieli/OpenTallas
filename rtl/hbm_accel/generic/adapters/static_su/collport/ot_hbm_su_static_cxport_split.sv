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
// HBM-CXDL 10-18 (route hbm_su_cx_dl_1017-s2-761317600 NEEDS_RTL: FF hold -95.1, TT setup -166.7, 1,045 endpoints):
// classified NOT clock-tree skew (clk_s / clk_q leaf insertion differ ~47 ps at FF) but the 3:4 crossing INSIDE a
// two-root leaf: dl_slot (clk_s) -> dw_d (clk_q) is timed by ordinary related-clock STA at the VCO tick (setup 1q =
// 277.8 ps) and the coincident edge (hold 0), each less the distinct-entry reserve (setup 150 / hold 100); hold repair
// stalls because the same endpoints fail setup (tools/ref_tile/README: a 3:4 crossing with any logic cannot close
// natively in a leaf). Fix = the S81 x34 _s/_t precedent (ot_s81_vm_x34, closed 10-16) and RBH-SFUS bridge_release_s:
// ONE clock root per leaf. The stream leaf ot_hbm_su_static_cxport_dl_s holds the pin registers and TWO banks
// (one event per serial edge, events alternate banks); the serial leaf ot_hbm_su_static_cxport_dl_q reads the banks
// alternately (one toggle flop, R kept copies) and keeps the old mux-only zeroing and dw_* / fault registers.
// The bank -> dw arcs (and sfault_s -> sf_q) become parent-level 3:4 seam arcs with a calendar window (die STA owns
// them with the epoch multicycle): bank written at stream edge A (A mod 4 in {0,1,3}, A = 4k+{0,1,3} -> bank
// (3k + {0,1,2}) mod 2), read at serial edge n = ceil((3A+3)/4) => setup >= 3 quanta (833 ps); the bank is rewritten
// >= 3 quanta after its read (hold window >= 833 ps). Seam 2 x 524 + 2 x 2R + 1 = 1,065 b (the hub's 4 slots would be
// 2,129 b; slot 2 was never read). Same edges and outputs as before: lockstep vs the hub unchanged.
module ot_hbm_su_static_cxport_dl_s #(parameter integer QID=0, G=0, MUT=0, R=4)(
 input wire clk_s, rst_s_n,
 input wire del_valid,
 input wire [544:0] del_flit,
 input wire [39:0] del_obase,
 output reg [523:0] b0, b1,          // banks {nz 3, row 9, flit 512}
 output reg [2*R-1:0] v0, v1,        // bank lane code {vh x R, vl x R}
 output reg sfault_s
);
 reg [1:0] sp; reg wp;
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) begin sp<=2'd0; wp<=1'b0; end
  else begin sp<=sp+2'd1; if(sp!=2'd2) wp<=~wp; end
 wire [39:0] ob_s = del_obase;
 wire hi_s = (MUT==2) ? 1'b0 : ob_s[6];
 wire vh_s = del_valid && hi_s, vl_s = del_valid && !hi_s;
 wire [2:0] nz_s = {|{ob_s[3:0], ob_s[17:16]^2'(QID), !del_flit[544], ob_s[5:4]^2'(G)}, |ob_s[28:18], |ob_s[39:29]};
 always @(posedge clk_s) if(sp!=2'd2) begin
  if(wp) begin b1 <= {nz_s, ob_s[15:7], del_flit[511:0]}; v1 <= {{R{vh_s}}, {R{vl_s}}}; end
  else   begin b0 <= {nz_s, ob_s[15:7], del_flit[511:0]}; v0 <= {{R{vh_s}}, {R{vl_s}}}; end
 end
 always @(posedge clk_s or negedge rst_s_n) if(!rst_s_n) sfault_s<=1'b0; else if(sp==2'd2 && del_valid) sfault_s<=1'b1;
endmodule

module ot_hbm_su_static_cxport_dl_q #(parameter integer MUT=0, R=4)(
 input wire clk_q, rst_q_n,
 input wire [523:0] b0, b1,
 input wire [2*R-1:0] v0, v1,
 input wire sfault_s,
 output reg [1:0] dw_v,
 output reg [17:0] dw_row,
 output reg [1023:0] dw_d,
 output reg fault
);
 // read bank: serial edge n reads bank (n+1) mod 2 (n = 0 reads the unwritten bank 1, as the hub reads slot 3);
 // MUT 4: off by one event.  R kept copies: copy r selects data quarter r (<= ~262 loads each).
 (* keep = "true" *) reg [R-1:0] rp;
 always @(posedge clk_q or negedge rst_q_n)
  if(!rst_q_n) rp <= (MUT==4) ? {R{1'b0}} : {R{1'b1}}; else rp <= ~rp;
 wire [2*R-1:0] dv = rp[0] ? v1 : v0;
 wire vh = dv[R], vl = dv[0];
 wire [523:0] dlx;
 for(genvar r=0;r<R;r=r+1) begin : g_sel
  assign dlx[128*r +: 128] = rp[r] ? b1[128*r +: 128] : b0[128*r +: 128];
 end
 assign dlx[523:512] = rp[0] ? b1[523:512] : b0[523:512];
 wire dbad = (vh || vl) && (|dlx[523:521]);
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) dw_v<=2'd0; else dw_v <= {vh, vl};
 always @(posedge clk_q) begin
  dw_row <= {dlx[520:512] & {9{vh}}, dlx[520:512] & {9{vl}}};
  for(integer r=0;r<R;r=r+1) begin
   dw_d[512+128*r +: 128] <= dlx[128*r +: 128] & {128{dv[R+r]}};
   dw_d[128*r +: 128]     <= dlx[128*r +: 128] & {128{dv[r]}};
  end
 end
 reg sf_q;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) sf_q<=1'b0; else sf_q<=sfault_s;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) fault<=1'b0; else if(dbad||sf_q) fault<=1'b1;
endmodule

// composition with the old leaf ports (bench lockstep vs the hub; the die binds dl_s + dl_q as two abutted leaves)
module ot_hbm_su_static_cxport_dl #(parameter integer QID=0, G=0, MUT=0)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,
 input wire del_valid,
 input wire [544:0] del_flit,
 input wire [39:0] del_obase,
 output wire [1:0] dw_v,
 output wire [17:0] dw_row,
 output wire [1023:0] dw_d,
 output wire fault
);
 wire [523:0] b0, b1; wire [7:0] v0, v1; wire sf;
 ot_hbm_su_static_cxport_dl_s #(.QID(QID),.G(G),.MUT(MUT)) u_s(.clk_s(clk_s),.rst_s_n(rst_s_n),.del_valid(del_valid),
  .del_flit(del_flit),.del_obase(del_obase),.b0(b0),.b1(b1),.v0(v0),.v1(v1),.sfault_s(sf));
 ot_hbm_su_static_cxport_dl_q #(.MUT(MUT)) u_q(.clk_q(clk_q),.rst_q_n(rst_q_n),.b0(b0),.b1(b1),.v0(v0),.v1(v1),.sfault_s(sf),
  .dw_v(dw_v),.dw_row(dw_row),.dw_d(dw_d),.fault(fault));
endmodule

// ------------------------------------------------------------------------------------------------ inject leaf
// CX-IJ 10-18: same class as dl / rc (routes hbm_su_cx_{dl,rc}_1017-s2-761317600 NEEDS_RTL): the two-root ij leaf
// carried two 3:4 crossings inside one leaf (ijd_slot (clk_s) -> ipv / ipgb / ibad (clk_q), stream->serial; io_slot
// (clk_q) -> idl (clk_s), serial->stream, 3 x 1,024 b), which related-clock STA times at the VCO tick (setup 277.8 ps,
// coincident-edge hold) less the 150 / 100 distinct-entry reserve. Fix (dl / rc split, S81 x34 _s/_t precedent): ONE
// clock root per leaf. ot_hbm_su_static_cxport_ij_s (stream) keeps the request pipe, decode, sfault_s, idl / ins_coll /
// inj_d; it writes the decoded request into TWO banks jb0 / jb1 (events alternate, as dl_s) and reads the serial
// inject banks ob0 / ob1 alternately on its event edges (as rc_s reads cb). ot_hbm_su_static_cxport_ij_q (serial) keeps
// the inject pipe / one-hot select / iq / gather; it reads jb alternately (as dl_q) and writes ob alternately on every
// serial edge (as rc_q writes cb). Same calendar as dl / rc: every seam arc has >= 3 quanta (833 ps) both for setup and
// for rewrite-after-read; die STA owns the seam arcs with the epoch multicycle. Seam 2 x 32 + 2 x 1,024 + 2 = 2,114 b
// (the hub's slots were 4 x 32 + 3 x 1,024). Same edges and outputs (lockstep vs the hub).
module ot_hbm_su_static_cxport_ij_s #(
 parameter integer QID=0, B39_NOOP=0, INJ_RET=11, RQ=0, RQC=0, SD=0, MUT=0, R=8
)(
 input wire clk_s, rst_s_n,
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output reg [1023:0] inj_d,
 output reg [31:0] jb0, jb1,          // request banks {nz12, iv4, ig8, ib8}
 input wire [1023:0] ob0, ob1,        // serial inject banks
 output reg sfault_s, ins_coll
);
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
 // wp: bank of this event edge (write jb; ob read = ~wp); R kept copies (ob read select: 1,024 / R loads each)
 reg [1:0] sp; (* keep = "true" *) reg [R-1:0] wp;
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) begin sp<=2'd0; wp<={R{1'b0}}; end
  else begin sp<=sp+2'd1; if(sp!=2'd2) wp<=~wp; end
 reg [161:0] rqd [0:RQ-RQC];
 always @(posedge clk_s) begin
  rqd[0] <= {inj_rd, inj_addr};
  for(integer t=1;t<=RQ-RQC;t=t+1) rqd[t] <= rqd[t-1];
 end
 wire [161:0] rq_al = (RQ==RQC) ? {inj_rd, inj_addr} : rqd[(RQ>RQC)?RQ-RQC-1:0];
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
 always @(posedge clk_s) if(sp!=2'd2) begin
  if(wp[0]) jb1 <= {nz_s, iv_s, ig_s, ib_s}; else jb0 <= {nz_s, iv_s, ig_s, ib_s};
 end
 // event p reads the ob bank written at serial m = p-1 (bank (p+1) mod 2; p = 0 reads bank 1, as the hub's slot 2)
 wire [1023:0] ev_i;
 for(genvar r=0;r<R;r=r+1) begin : g_ob
  assign ev_i[(1024/R)*r +: (1024/R)] = wp[r] ? ob0[(1024/R)*r +: (1024/R)] : ob1[(1024/R)*r +: (1024/R)];
 end
 function automatic integer ins_of(input integer rp);
  integer ph, r; begin r=-1;
   for(ph=0;ph<4;ph=ph+1) if(ph!=2 && ((ph+lat_of(ph))%4)==rp) r=lat_of(ph)-LMIN;
   ins_of=r; end
 endfunction
 localparam integer I0=ins_of(0), I1=ins_of(1), I2=ins_of(2), I3=ins_of(3);
 initial if(I2>=0)$fatal(1,"cxport_ij: an inject event maps to stream phase 2");
 reg [1023:0] idl [0:K];
 integer ins;
 always @* ins = (sp==2'd0)?I0:(sp==2'd1)?I1:(sp==2'd3)?I3:-1;
 always @(posedge clk_s) begin
  for(integer t=0;t<=K;t=t+1) idl[t] <= (t==0) ? 1024'd0 : idl[t-1];
  if(ins>=0) idl[ins] <= ev_i;
 end
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) ins_coll<=1'b0; else if(ins>0 && (|idl[ins-1])) ins_coll<=1'b1;
 always @* inj_d = idl[K];
endmodule

module ot_hbm_su_static_cxport_ij_q #(parameter integer SD=0, MUT=0, R=8, SAFE_GATHER=0)(
 input wire clk_q, rst_q_n,
 input wire [31:0] jb0, jb1,
 input wire [1023:0] inj_q0, inj_q1, inj_q2, inj_q3,   // slice G port-5 data (hub inj_q[1024G +: 1024])
 output reg [1023:0] ob0, ob1,
 input wire sfault_s, ins_coll,
 output reg fault
);
 wire [4*1024-1:0] inj_q = {inj_q3, inj_q2, inj_q1, inj_q0};
 // rp: serial edge n reads jb bank (n+1) mod 2 (n = 0 reads the unwritten bank 1, as the hub reads slot 3) and writes
 // ob bank n mod 2; R kept copies (ob write enable 2,048 / R loads each). MUT 4: off by one event.
 (* keep = "true" *) localparam integer RN=SAFE_GATHER?64:R;
 (* keep="true" *) reg [RN-1:0] rp;
 always @(posedge clk_q or negedge rst_q_n)
  if(!rst_q_n) rp <= (MUT==4) ? {RN{1'b0}} : {RN{1'b1}}; else rp <= ~rp;
 wire [31:0] ijd = rp[0] ? jb1 : jb0;
 wire [3:0] iv = ijd[19:16]; wire [7:0] ig = ijd[15:8]; wire [7:0] ib = ijd[7:0];
 wire ibad = |{iv[3] && (|ijd[31:29]), iv[2] && (|ijd[28:26]), iv[1] && (|ijd[25:23]), iv[0] && (|ijd[22:20])};
 wire [3:0] ctl_v; wire [15:0] ctl_gb;
 generate if(SAFE_GATHER) begin:g_ctl_ring
  localparam integer D=4+SD, AW=$clog2(D);
  reg [19:0] mem[0:D-1]; reg [AW-1:0] wp; integer warm;
  wire [AW-1:0] ra = (wp >= D-2) ? wp-(D-2) : wp+2;
  always @(posedge clk_q or negedge rst_q_n)
   if(!rst_q_n) begin wp<=0; warm<=0; end
   else begin wp <= (wp==D-1)?0:wp+1'b1; if(warm<D)warm<=warm+1; end
  always @(posedge clk_q) mem[wp]<={iv,ig,ib};
  wire [AW-1:0] ra_test=(MUT==5)?((ra==D-1)?0:ra+1'b1):ra;
  assign ctl_v=(warm>=D-2)?mem[ra_test][19:16]:4'd0;
  assign ctl_gb=mem[ra_test][15:0];
 end else begin:g_ctl_legacy
  reg [3:0] ipv[0:3+SD]; reg [15:0] ipgb[0:3+SD];
  always @(posedge clk_q or negedge rst_q_n)
   if(!rst_q_n) begin for(integer t=0;t<=3+SD;t=t+1) ipv[t]<=0; end
   else begin ipv[0]<=iv; for(integer t=1;t<=3+SD;t=t+1) ipv[t]<=ipv[t-1]; end
  always @(posedge clk_q) begin ipgb[0]<={ig,ib}; for(integer t=1;t<=3+SD;t=t+1) ipgb[t]<=ipgb[t-1]; end
  assign ctl_v=(MUT==1)?ipv[1+SD]:ipv[2+SD];
  assign ctl_gb=(MUT==1)?ipgb[1+SD]:ipgb[2+SD];
 end endgenerate
 function automatic [63:0] ohdec(input [3:0] v, input [15:0] gb);
  integer kk; begin ohdec=64'd0;
   for(kk=0;kk<4;kk=kk+1) if(v[kk]) ohdec[16*kk + 4*gb[8+2*kk+:2] + gb[2*kk+:2]] = 1'b1; end
 endfunction
 wire [1023:0] iword;
 generate if(SAFE_GATHER) begin:g_safe_gather
  // Decode one existing edge earlier; stage one gathers four local sources,
  // stage two gathers four registered partials. No calendar edge added.
  for(genvar ch=0;ch<8;ch=ch+1) begin:g_chunk
   wire [63:0] oh;
   (* keep_hierarchy="yes" *) ot_hbm_cxijq_sel_copy #(.COPY_ID(ch)) u_sel(
    .clk(clk_q),.rst_n(rst_q_n),.d(ohdec(ctl_v,ctl_gb)),.q(oh));
   for(genvar k=0;k<4;k=k+1) begin:g_dst
    wire [31:0] part[0:3];
    for(genvar g=0;g<4;g=g+1) begin:g_src
     reg [31:0] pq;
     always @(posedge clk_q) pq <=
      (inj_q[256*(4*g)+32*ch+:32]&{32{oh[16*k+4*g]}}) |
      (inj_q[256*(4*g+1)+32*ch+:32]&{32{oh[16*k+4*g+1]}}) |
      (inj_q[256*(4*g+2)+32*ch+:32]&{32{oh[16*k+4*g+2]}}) |
      (inj_q[256*(4*g+3)+32*ch+:32]&{32{oh[16*k+4*g+3]}});
     assign part[g]=pq;
    end
    assign iword[256*k+32*ch+:32]=part[0]|part[1]|part[2]|((MUT==6)?32'd0:part[3]);
   end
  end
 end else begin:g_legacy_gather
  reg [63:0] ioh;
  always @(posedge clk_q or negedge rst_q_n)
   if(!rst_q_n)ioh<=0; else ioh<=ohdec(ctl_v,ctl_gb);
  reg [4095:0] iq; always @(posedge clk_q)iq<=inj_q;
  wire [4095:0] isrc=(MUT==1)?inj_q:iq;
  reg [1023:0] iw;
  always @* begin
   iw=0;
   for(integer k=0;k<4;k=k+1)for(integer j=0;j<16;j=j+1)
    iw[256*k+:256]=iw[256*k+:256]|(isrc[256*j+:256]&{256{ioh[16*k+j]}});
  end
  assign iword=iw;
 end endgenerate
 for(genvar r=0;r<RN;r=r+1) begin : g_ob
  always @(posedge clk_q)
   if(rp[r]) ob0[(1024/RN)*r +: (1024/RN)] <= iword[(1024/RN)*r +: (1024/RN)];
   else      ob1[(1024/RN)*r +: (1024/RN)] <= iword[(1024/RN)*r +: (1024/RN)];
 end
 reg sf_q;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) sf_q<=1'b0; else sf_q<=sfault_s||ins_coll;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) fault<=1'b0; else if(ibad||sf_q) fault<=1'b1;
endmodule

// composition with the old leaf ports (bench lockstep vs the hub; the die binds ij_s + ij_q as two abutted leaves)
module ot_hbm_su_static_cxport_ij #(
 parameter integer QID=0, B39_NOOP=0, INJ_RET=11, RQ=0, RQC=0, SD=0, MUT=0
)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,   // epoch reset per domain
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output wire [1023:0] inj_d,
 input wire [1023:0] inj_q0, inj_q1, inj_q2, inj_q3,
 output wire fault
);
 wire [31:0] jb0, jb1; wire [1023:0] ob0, ob1; wire sfs, icl;
 ot_hbm_su_static_cxport_ij_s #(.QID(QID),.B39_NOOP(B39_NOOP),.INJ_RET(INJ_RET),.RQ(RQ),.RQC(RQC),.SD(SD),.MUT(MUT)) u_s(
  .clk_s(clk_s),.rst_s_n(rst_s_n),.inj_rd(inj_rd),.inj_addr(inj_addr),.inj_d(inj_d),.jb0(jb0),.jb1(jb1),.ob0(ob0),.ob1(ob1),
  .sfault_s(sfs),.ins_coll(icl));
 ot_hbm_su_static_cxport_ij_q #(.SD(SD),.MUT(MUT)) u_q(.clk_q(clk_q),.rst_q_n(rst_q_n),.jb0(jb0),.jb1(jb1),
  .inj_q0(inj_q0),.inj_q1(inj_q1),.inj_q2(inj_q2),.inj_q3(inj_q3),.ob0(ob0),.ob1(ob1),.sfault_s(sfs),.ins_coll(icl),.fault(fault));
endmodule

// ------------------------------------------------------------------------------------------------ RED_CARRY + SFU operand
// rc SFU operand (d): the hub selects ro_slot[rslot] lane red_sel[3:0] (a 64:1 AND-OR) on the stream->serial crossing,
// which STA times at the 1-quantum edge pair (gate: sfu_x -277 ps). Here the crossing is mux-only: every serial edge
// registers the whole slot word (rq, 528 b) and the lane select is serial->serial on the NEXT edge. COMPILER: the
// SFU-source reducer command (red_sel / red_cmd osel=1, lane[6]=1) issues at E+1 instead of E = ceil((3A+3)/4); the
// operand, its ro_v check and the reducer timeline are otherwise unchanged (sfu_x at E+1 is the hub's sfu_x at E).
// HBM-CXDL 10-18 (route hbm_su_cx_rc_1017-s2-761317600 NEEDS_RTL: TT -173.4 / FF hold -77.9, 1,284 endpoints): same
// class as dl -- every failing arc is a 3:4 crossing inside the two-root leaf (ro_slot / rr_slot1 -> ro / rr_wv / rr_w*
// stream->serial, rc_slot -> pend / rc_d serial->stream), timed at the VCO tick less the 150 / 100 entry reserve.
// Fix: one root per leaf. ot_hbm_su_static_cxport_rc_s (stream) holds the ro / rr pin banks (2 each, events alternate)
// and reads the two serial rc banks alternately on its event edges; ot_hbm_su_static_cxport_rc_q (serial) holds the
// reducer carry, writes the rc banks alternately on every serial edge, reads the ro / rr banks alternately. Seam
// windows >= 3 quanta both ways (stream->serial as dl; serial m -> stream ceil((4m+3)/3): 3/5/4 q, rewrite >= 3 q after
// read). Same edges / outputs as before (lockstep vs the hub).
module ot_hbm_su_static_cxport_rc_s #(parameter integer MUT=0, R=4)(
 input wire clk_s, rst_s_n,
 output reg rc_v,
 output reg [2:0] rc_tag,
 output reg [255:0] rc_d,
 input wire rr_v,
 input wire [2:0] rr_tag,
 input wire [255:0] rr_d,
 input wire [15:0] ro_v,
 input wire [511:0] ro_x,
 output reg [527:0] ob0, ob1,        // ro banks {ro_v, ro_x}
 output reg [267:0] rb0, rb1,        // rr banks {v, tag3, onehot8, d256}
 input wire [260:0] cb0, cb1,        // serial rc banks
 output reg sfault_s, rc_coll
);
 reg [1:0] sp; (* keep = "true" *) reg [R-1:0] wp;   // wp: bank of this event edge (write ro/rr; rc read = ~wp)
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) begin sp<=2'd0; wp<={R{1'b0}}; end
  else begin sp<=sp+2'd1; if(sp!=2'd2) wp<=~wp; end
 wire s_ev = sp!=2'd2;
 always @(posedge clk_s) if(s_ev) begin
  if(wp[0]) begin ob1 <= {ro_v, ro_x}; rb1 <= {rr_v, rr_tag, 8'd1 << rr_tag, rr_d}; end
  else      begin ob0 <= {ro_v, ro_x}; rb0 <= {rr_v, rr_tag, 8'd1 << rr_tag, rr_d}; end
 end
 always @(posedge clk_s or negedge rst_s_n)
  if(!rst_s_n) sfault_s<=1'b0; else if(sp==2'd2 && (rr_v||(|ro_v))) sfault_s<=1'b1;
 // event p reads the rc bank written at serial m with p = ceil((4m+3)/3): p = 0 reads bank 1 (as the hub's slot 2)
 wire [260:0] cbx;
 for(genvar r=0;r<R;r=r+1) begin : g_cb
  localparam integer LO = (261*r)/R, HI = (261*(r+1))/R;
  assign cbx[HI-1:LO] = wp[r] ? cb0[HI-1:LO] : cb1[HI-1:LO];
 end
 wire [260:0] ev = s_ev ? cbx : 261'd0;
 reg [260:0] pend;
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
endmodule

module ot_hbm_su_static_cxport_rc_q #(parameter integer MUT=0, R=4)(
 input wire clk_q, rst_q_n,
 input wire red_sv,
 input wire [31:0] red_tag,
 input wire [31:0] red_x,
 output reg rr_wv,
 output reg [4:0] rr_wa,
 output reg [255:0] rr_wd,
 input wire [11:0] red_sel,
 output reg [31:0] sfu_x,
 input wire [527:0] ob0, ob1,
 input wire [267:0] rb0, rb1,
 output reg [260:0] cb0, cb1,
 input wire sfault_s, rc_coll,
 output reg fault
);
 // rp: serial edge n reads the ro / rr bank (n+1) mod 2 and writes rc bank n mod 2 (= ~rp); MUT 4: off by one event
 (* keep = "true" *) reg [R-1:0] rp;
 always @(posedge clk_q or negedge rst_q_n)
  if(!rst_q_n) rp <= (MUT==4) ? {R{1'b0}} : {R{1'b1}}; else rp <= ~rp;
 reg r_sv; reg [31:0] r_tag, r_x;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) r_sv<=1'b0; else r_sv<=red_sv;
 always @(posedge clk_q) begin r_tag<=red_tag; r_x<=red_x; end
 wire cw   = r_sv && r_tag[9];
 wire emit = r_sv && r_tag[13];
 reg [255:0] carry;
 reg [255:0] cvec;
 always @* begin cvec=carry; if(cw) cvec[32*r_tag[12:10]+:32]=r_x; end
 (* keep = "true" *) reg [1:0] crst_n;
 always @(posedge clk_q or negedge rst_q_n) if(!rst_q_n) crst_n<=2'b00; else crst_n<=2'b11;
 for(genvar h=0;h<2;h=h+1) begin : g_carry
  always @(posedge clk_q or negedge crst_n[h])
   if(!crst_n[h]) carry[128*h+:128]<=128'd0; else carry[128*h+:128] <= emit ? 128'd0 : cvec[128*h+:128];
 end
 always @(posedge clk_q)
  if(rp[0]) cb0 <= {emit, r_tag[17]&&(MUT!=3), r_tag[16:14], cvec};
  else      cb1 <= {emit, r_tag[17]&&(MUT!=3), r_tag[16:14], cvec};
 reg [7:0] tv; reg [4:0] tdst [0:7];
 wire [267:0] rr1;
 for(genvar r=0;r<R;r=r+1) begin : g_rr
  localparam integer LO = (268*r)/R, HI = (268*(r+1))/R;
  assign rr1[HI-1:LO] = rp[r] ? rb1[HI-1:LO] : rb0[HI-1:LO];
 end
 wire rrv = rr1[267]; wire [7:0] rroh = rr1[263:256]; wire [255:0] rr_dd = rr1[255:0];
 wire tvh = |(tv & rroh);
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
 reg [527:0] ro;
 for(genvar r=0;r<R;r=r+1) begin : g_ro
  always @(posedge clk_q) ro[132*r +: 132] <= rp[r] ? ob1[132*r +: 132] : ob0[132*r +: 132];
 end
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

// composition with the old leaf ports (bench lockstep vs the hub; the die binds rc_s + rc_q as two abutted leaves)
module ot_hbm_su_static_cxport_rc #(parameter integer MUT=0)(
 input wire clk_s, clk_q, rst_s_n, rst_q_n,
 output wire rc_v,
 output wire [2:0] rc_tag,
 output wire [255:0] rc_d,
 input wire rr_v,
 input wire [2:0] rr_tag,
 input wire [255:0] rr_d,
 input wire red_sv,
 input wire [31:0] red_tag,
 input wire [31:0] red_x,
 output wire rr_wv,
 output wire [4:0] rr_wa,
 output wire [255:0] rr_wd,
 input wire [15:0] ro_v,
 input wire [511:0] ro_x,
 input wire [11:0] red_sel,
 output wire [31:0] sfu_x,
 output wire fault
);
 wire [527:0] ob0, ob1; wire [267:0] rb0, rb1; wire [260:0] cb0, cb1; wire sfs, rcc;
 ot_hbm_su_static_cxport_rc_s #(.MUT(MUT)) u_s(.clk_s(clk_s),.rst_s_n(rst_s_n),.rc_v(rc_v),.rc_tag(rc_tag),.rc_d(rc_d),
  .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.ro_v(ro_v),.ro_x(ro_x),.ob0(ob0),.ob1(ob1),.rb0(rb0),.rb1(rb1),.cb0(cb0),.cb1(cb1),
  .sfault_s(sfs),.rc_coll(rcc));
 ot_hbm_su_static_cxport_rc_q #(.MUT(MUT)) u_q(.clk_q(clk_q),.rst_q_n(rst_q_n),.red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),
  .rr_wv(rr_wv),.rr_wa(rr_wa),.rr_wd(rr_wd),.red_sel(red_sel),.sfu_x(sfu_x),.ob0(ob0),.ob1(ob1),.rb0(rb0),.rb1(rb1),
  .cb0(cb0),.cb1(cb1),.sfault_s(sfs),.rc_coll(rcc),.fault(fault));
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

// Separate paramod per data region: preserving net aliases alone does not stop
// opt_merge from combining identical onehot flops (first census caught 256 loads).
(* keep_hierarchy="yes" *) module ot_hbm_cxijq_sel_copy #(parameter integer COPY_ID=0)(
 input wire clk,rst_n,input wire[63:0]d,output reg[63:0]q);
 (* keep="true" *) reg[3:0] reset_copy;
 always @(posedge clk or negedge rst_n)if(!rst_n)reset_copy<=0;else reset_copy<=4'hf;
 for(genvar x=0;x<64;x=x+1)begin:g_bit
  always @(posedge clk)q[x]<=reset_copy[x/16]?d[x]:1'b0;
 end
endmodule
