`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_su_static_cxport (H-NETLIST/suport 2026-10-16): the SU quarter's COLL exchange port, one per quarter (sucx_<q>).
// It is the stream(1.2 GHz)/serial(0.9 GHz) boundary of the three COLL<->SU joins, so the 3:4 crossing stays inside
// the SU. Every pin is registered: stream inputs land in phase-indexed pin slots, serial inputs in pin registers, and
// every output is a register.
//
// Common epoch (as ot_hbm_su_multirate_bridge): quantum 2500/9 ps, stream edge p at 3p, serial edge n at 4n, both counted
// from the phase-zero release of rst_n (bridge_rst_n); the first edge of each clock after release is p=0 / n=0.
// Stream -> serial: a value captured at stream edge A (A mod 4 in {0,1,3}) is read at serial edge n = ceil((3A+3)/4)
//   (A=4k -> n=3k+1, 4k+1 -> 3k+2, 4k+3 -> 3k+3; setup 4/5/6 quanta). Stream phase A mod 4 == 2 is IDLE for every
//   SU-bound stream input (a valid there latches FAULT). Slots are overwritten 12 quanta later (>= 6 quanta after use).
// Serial -> stream: a value written at serial edge m is registered at stream edge p = ceil((4m+3)/3)
//   (m=3k -> 4k+1, 3k+1 -> 4k+3, 3k+2 -> 4k+4; setup 3/5/4 quanta); stream phase 2 carries no serial event.
//
// (a) INJECT (COLL_INJECTION_READ_SERVICE). COLL registers inj_rd[1:0] / inj_addr[159:0] at P; the four pgslices and
//   this leaf capture them at A = P+1+RQ. Sector address (each 40-b half, SU aperture): a[6:0] quarter lane (a[2:0]=0),
//   a[15:7] store row, a[17:16] = QID, a[38:18] = 0, a[39]: B39_NOOP (SW) = IDX staging select -> no SU read, lane data 0;
//   else must be 0. Sector -> store group g = a[6:3] -> pgslice G = g[2:1] (a[5:4]), VM port h = g[0] (a[3]),
//   half hi = g[3] (a[6]); banks = quarter lanes 8g..8g+7 = slice-local banks 8h+16hi..+7 (port 5), row a[15:7].
//   Edges: pgslice bank port 5 samples at serial n (from its own slot), bank read_data at n+2, inj_q pin register here
//   at n+3+SD, sector select into the serial->stream slot at n+4+SD, stream read register at A+LAT(A mod 4)
//   (LAT = 8 for SD=0 on every phase; SD not a multiple of 3 makes LAT phase dependent and the stream line inserts each
//   event at the stage that equalises it to LMAX), then extra registers: inj_d updates at P+INJ_RET for every phase,
//   with A = P+1+RQ and INJ_RET >= 1+RQ+LMAX (SD=0: 9+RQ). lane j: inj_d[512j+:512] = {sector(hi), sector(lo)}.
// (c) DELIVERY (COLL_DELIVERY_TO_VM_SU). del_valid/del_flit/del_obase registered by COLL at P, captured here at A.
//   Lane j writes the 16 words del_flit[545j+:512] at word address del_obase[40j+:40] (exact destination: the flit
//   index is NOT added): a[3:0]=0, a[17:16]=QID, a[39:18]=0, flit bit 544 = 1; pgslice G = a[5:4], half a[6]
//   (16 banks), row a[15:7]. Serial edge n registers dw_* for each slice; the bank write pins sample at n+1, commit n+2.
//   Conflict-free rule (FAULT here, and in the pgslice against fill / lane writes): the valid lanes of one stream edge
//   hit distinct (G, half). Calendar construction: lane j only carries destinations with a[5:4] = j.
// (b) RED_CARRY (COLL_REDUCTION_RETURN). Source = this quarter's reducer scalars (qcore red_sv/red_tag/red_x, captured
//   at serial s). red_tag ABI (bits [31:9] were 0): [9] CW: carry word [12:10] <= red_x; [13] EMIT: the 8 carry words
//   (this edge's CW included) leave as rc_d (word k = fold lane k), rc_tag = [16:14], then the carry words clear;
//   [17] LATE: one more stream edge; [23] RR_EN with [22:18] = {RF row2, RF sector3} where the rr of that rc_tag is
//   written. EMIT at serial s+1 = m -> rc_v one-edge pulse registered at stream p(m) (+1 if LATE); COLL samples it
//   unregistered at E_lp, so the compiler issues the reducer command such that p = E_lp-1-R (phases 1,3,0 direct,
//   phase 2 with LATE). rc_v is 0 on every other edge. rr_v/rr_tag/rr_d: COLL one-edge pulse at E_rr, captured at
//   A = E_rr+1+R (A mod 4 != 2), serial n: rr_wv/rr_wa/rr_wd registered -> qcore RF bank pins n+1, commit n+2.
// (d) SFU_RESULT: ro_v/ro_x of the stream SFU core cross into the serial reducer operand sfu_x (see section below).
// Faults (sticky, never stall): SU-bound valid at stream phase 2; inject/delivery address outside the aperture;
// delivery header v=0; two delivery lanes on one (G, half); rr for a tag with no recorded destination; EMIT for a tag
// still outstanding; two rc events for one stream edge; SFU reducer operand from a lane without ro_v.
// MUT (bench, must FAIL): 1 inject select one serial edge early (no pin register); 2 delivery half bit ignored;
// 3 rc LATE ignored; 4 stream->serial slot map off by one phase.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_cxport #(
 parameter integer QID=0,
 parameter integer B39_NOOP=0,      // 1 on SW: inject addr_lo[39]=1 is an IDX-staging read (no SU read)
 parameter integer INJ_RET=11,      // inj_d register update edge after the COLL request edge P
 parameter integer RQ=0,            // stream relay stages COLL -> each pgslice on the request path (padded equal)
 parameter integer RQC=0,           // stream relay stages COLL -> this leaf on the request path (<= RQ)
 parameter integer SD=0,            // serial relay stages pgslice inj_q -> this leaf (padded equal over the 4 slices)
 parameter integer MUT=0
)(
 input wire clk_s,                  // stream 1.2 GHz
 input wire clk_q,                  // serial 0.9 GHz, phase-zero related 3:4
 input wire rst_n,                  // phase-zero epoch reset (bridge_rst_n)
 // ---- COLL (stream)
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output reg [1023:0] inj_d,
 input wire [3:0] del_valid,
 input wire [2179:0] del_flit,
 input wire [159:0] del_obase,
 output reg rc_v,
 output reg [2:0] rc_tag,
 output reg [255:0] rc_d,
 input wire rr_v,
 input wire [2:0] rr_tag,
 input wire [255:0] rr_d,
 // ---- SU (serial)
 input wire [4*1024-1:0] inj_q,     // slice G bank port-5 data, inj_q[1024G + 32n +: 32] = slice-local bank n
 output reg [4*2-1:0] dw_v,         // slice G half hi: dw_v[2G+hi]
 output reg [4*18-1:0] dw_row,      // dw_row[18G+9hi +: 9]
 output reg [4*1024-1:0] dw_d,      // dw_d[1024G+512hi +: 512], word w -> slice-local bank 16hi+w
 input wire red_sv,
 input wire [31:0] red_tag,
 input wire [31:0] red_x,
 output reg rr_wv,
 output reg [4:0] rr_wa,            // {row2, sector3}
 output reg [255:0] rr_wd,
 // ---- SFU core reducer operand (ro_* stream from sfucore_<q>, red_sel serial from the SU programme)
 input wire [15:0] ro_v,
 input wire [511:0] ro_x,
 input wire [11:0] red_sel,         // {v, op3, osel, lane7}: SFU source when osel && lane[6]; SFU lane = lane[3:0]
 output reg [31:0] sfu_x,           // registered at the reducer command edge E (as a pgslice slice_x)
 output reg fault
);
 // stream latency A -> slot read register, per stream phase of A (0,1,3)
 function automatic integer lat_of(input integer ph);
  integer a,n,m,pp;
  begin a=40+ph; n=(3*a+3+3)/4; m=n+4+SD; pp=(4*m+3+2)/3; lat_of=pp-a; end
 endfunction
 localparam integer L0=lat_of(0), L1=lat_of(1), L3=lat_of(3);
 localparam integer LMAX=(L0>L1)?((L0>L3)?L0:L3):((L1>L3)?L1:L3);
 localparam integer LMIN=(L0<L1)?((L0<L3)?L0:L3):((L1<L3)?L1:L3);
 localparam integer X=INJ_RET-1-RQ-LMAX;
 localparam integer K=LMAX-LMIN+X;
 initial if(X<0)$fatal(1,"cxport: INJ_RET must be >= 1+RQ+LMAX");
 initial if(RQC>RQ)$fatal(1,"cxport: RQC must be <= RQ");
 // ------------------------------------------------------------------ epoch counters
 reg [1:0] sp;                       // stream phase of the current stream edge
 reg [1:0] sq;                       // serial phase (n mod 3) of the current serial edge
 always @(posedge clk_s or negedge rst_n) if(!rst_n) sp<=2'd0; else sp<=sp+2'd1;
 always @(posedge clk_q or negedge rst_n) if(!rst_n) sq<=2'd0; else sq<=(sq==2'd2)?2'd0:sq+2'd1;
 // stream slot index read by serial phase: n%3=1 -> A%4=0, 2 -> 1, 0 -> 3
 function automatic [1:0] s2q_slot(input [1:0] q);
  s2q_slot = (q==2'd1)?2'd0:(q==2'd2)?2'd1:2'd3;
 endfunction
 wire [1:0] rslot = s2q_slot(sq) + ((MUT==4)?2'd1:2'd0);
 // serial slot index read by stream phase: p%4=1 -> m%3=0, 3 -> 1, 0 -> 2; phase 2 none
 wire s_ev = sp!=2'd2;
 wire [1:0] oslot_i = (sp==2'd1)?2'd0:(sp==2'd3)?2'd1:2'd2;
 reg sfault_s;                       // stream-side sticky fault
 // ------------------------------------------------------------------ stream pin slots
 reg [161:0] ij_slot [0:3];
 reg [2343:0] dl_slot [0:3];
 reg [259:0] rr_slot [0:3];
 reg [527:0] ro_slot [0:3];
 reg [161:0] rqd [0:RQ-RQC];
 always @(posedge clk_s) begin
  rqd[0] <= {inj_rd, inj_addr};
  for(integer t=1;t<=RQ-RQC;t=t+1) rqd[t] <= rqd[t-1];
 end
 wire [161:0] rq_al = (RQ==RQC) ? {inj_rd, inj_addr} : rqd[(RQ>RQC)?RQ-RQC-1:0];
 always @(posedge clk_s) begin
  ro_slot[sp] <= {ro_v, ro_x};
  ij_slot[sp] <= rq_al;
  dl_slot[sp] <= {del_valid, del_flit, del_obase};
  rr_slot[sp] <= {rr_v, rr_tag, rr_d};
 end
 always @(posedge clk_s or negedge rst_n)
  if(!rst_n) sfault_s<=1'b0;
  else if(sp==2'd2 && ((|rq_al[161:160])||(|del_valid)||rr_v||(|ro_v))) sfault_s<=1'b1;
 // ------------------------------------------------------------------ (a) inject: serial request decode
 wire [161:0] ij = ij_slot[rslot];
 // per lane-sector k = 2j+s: {v, G2, n0 4 (=8h+16hi -> bank base/8: {hi,h})}
 reg [3:0] iv; reg [7:0] ig; reg [7:0] ib; reg ibad;
 integer k;
 always @* begin
  iv=0; ig=0; ib=0; ibad=0;
  for(k=0;k<4;k=k+1) begin : dec
   reg [39:0] a; reg [39:0] lo; reg v;
   a  = ij[40*k+:40];
   lo = ij[80*(k/2)+:40];
   v  = ij[160+(k/2)] && !(B39_NOOP!=0 && lo[39]);
   iv[k] = v;
   ig[2*k+:2] = a[5:4];
   ib[2*k+:2] = {a[6],a[3]};
   if(v && (a[2:0]!=3'd0 || a[17:16]!=2'(QID) || a[38:18]!=21'd0 || a[39])) ibad=1'b1;
  end
 end
 reg [19:0] ip [0:3+SD];
 always @(posedge clk_q or negedge rst_n)
  if(!rst_n) begin for(integer t=0;t<=3+SD;t=t+1) ip[t]<=20'd0; end
  else begin ip[0]<={iv,ig,ib}; for(integer t=1;t<=3+SD;t=t+1) ip[t]<=ip[t-1]; end
 // pin register of the four slices' port-5 data (bank read_data registered at n+2, captured here at n+3+SD)
 reg [4*1024-1:0] iq;
 always @(posedge clk_q) iq <= inj_q;
 wire [19:0] isel = (MUT==1) ? ip[2+SD] : ip[3+SD];
 wire [4*1024-1:0] isrc = (MUT==1) ? inj_q : iq;
 reg [1023:0] iword;
 always @* begin
  for(k=0;k<4;k=k+1) begin : sel
   reg [1:0] g; reg [1:0] b;
   g = isel[8+2*k+:2]; b = isel[2*k+:2];
   iword[256*k+:256] = isel[16+k] ? isrc[1024*g + 256*b +: 256] : 256'd0;
  end
 end
 // serial -> stream slot (written at n+4)
 reg [1023:0] io_slot [0:2];
 always @(posedge clk_q) io_slot[sq] <= iword;
 // stream: the slot read at p = A+LAT(ph) enters stage k = LAT(ph)-LMIN of a K+1 stage line, so it leaves at
 // A+LMAX+X = P+INJ_RET for every phase. The read phase rp = (ph+LAT(ph)) mod 4 identifies ph (solved at elaboration).
 function automatic integer ins_of(input integer rp);
  integer ph, r; begin r=-1;
   for(ph=0;ph<4;ph=ph+1) if(ph!=2 && ((ph+lat_of(ph))%4)==rp) r=lat_of(ph)-LMIN;
   ins_of=r; end
 endfunction
 localparam integer I0=ins_of(0), I1=ins_of(1), I2=ins_of(2), I3=ins_of(3);
 initial if(I2>=0)$fatal(1,"cxport: an inject event maps to stream phase 2");
 reg [1023:0] idl [0:K];
 reg ins_coll;
 wire [1023:0] ev_i = io_slot[oslot_i];
 integer ins;
 always @* ins = (sp==2'd0)?I0:(sp==2'd1)?I1:(sp==2'd3)?I3:-1;
 always @(posedge clk_s) begin
  for(integer t=0;t<=K;t=t+1) idl[t] <= (t==0) ? 1024'd0 : idl[t-1];
  if(ins>=0) idl[ins] <= ev_i;
 end
 always @(posedge clk_s or negedge rst_n)
  if(!rst_n) ins_coll<=1'b0;
  else if(ins>0 && (|idl[ins-1])) ins_coll<=1'b1;
 always @* inj_d = idl[K];
 // ------------------------------------------------------------------ (c) delivery
 wire [2343:0] dl = dl_slot[rslot];
 reg [4*2-1:0] dv_n; reg [4*18-1:0] dr_n; reg [4*1024-1:0] dd_n; reg dbad;
 always @* begin
  dv_n=0; dr_n=0; dd_n=0; dbad=0;
  for(k=0;k<4;k=k+1) begin : dk
   reg [39:0] ob; reg [544:0] f; reg vv; reg [2:0] slot;
   vv = dl[2340+k]; ob = dl[40*k+:40]; f = dl[160+545*k+:545];
   slot = {(MUT==2)?1'b0:ob[6], ob[5:4]};
   if(vv) begin
    if(ob[3:0]!=4'd0 || ob[17:16]!=2'(QID) || ob[39:18]!=22'd0 || !f[544]) dbad=1'b1;
    if(dv_n[{slot[1:0],slot[2]}]) dbad=1'b1;
    dv_n[{slot[1:0],slot[2]}] = 1'b1;
    dr_n[18*slot[1:0]+9*slot[2]+:9] = ob[15:7];
    dd_n[1024*slot[1:0]+512*slot[2]+:512] = f[511:0];
   end
  end
 end
 always @(posedge clk_q or negedge rst_n) if(!rst_n) dw_v<=0; else dw_v<=dv_n;
 always @(posedge clk_q) begin dw_row<=dr_n; dw_d<=dd_n; end
 // ------------------------------------------------------------------ (b) RED_CARRY
 reg r_sv; reg [31:0] r_tag, r_x;
 always @(posedge clk_q or negedge rst_n) if(!rst_n) r_sv<=1'b0; else r_sv<=red_sv;
 always @(posedge clk_q) begin r_tag<=red_tag; r_x<=red_x; end
 wire cw   = r_sv && r_tag[9];
 wire emit = r_sv && r_tag[13];
 reg [255:0] carry;
 reg [255:0] cvec;
 always @* begin cvec=carry; if(cw) cvec[32*r_tag[12:10]+:32]=r_x; end
 always @(posedge clk_q or negedge rst_n)
  if(!rst_n) carry<=256'd0; else carry <= emit ? 256'd0 : cvec;
 reg [260:0] rc_slot [0:2];           // {v, late, tag3, d256}
 always @(posedge clk_q) rc_slot[sq] <= {emit, r_tag[17]&&(MUT!=3), r_tag[16:14], cvec};
 // rr destination table
 reg [7:0] tv; reg [4:0] tdst [0:7];
 wire [259:0] rr = rr_slot[rslot];
 wire rrv = rr[259]; wire [2:0] rrt = rr[258:256];
 reg rbad;
 always @(posedge clk_q or negedge rst_n)
  if(!rst_n) begin tv<=8'd0; rr_wv<=1'b0; rbad<=1'b0; end
  else begin
   rr_wv <= rrv && tv[rrt];
   rbad  <= (rrv && !tv[rrt]) || (emit && r_tag[23] && tv[r_tag[16:14]] && !(rrv && rrt==r_tag[16:14]));
   if(rrv) tv[rrt] <= 1'b0;
   if(emit && r_tag[23]) tv[r_tag[16:14]] <= 1'b1;
  end
 always @(posedge clk_q) begin
  rr_wa <= tdst[rrt]; rr_wd <= rr[255:0];
  if(emit && r_tag[23]) tdst[r_tag[16:14]] <= r_tag[22:18];
 end
 // stream: rc pulse
 reg [260:0] pend; reg rc_coll;
 wire [260:0] ev = s_ev ? rc_slot[oslot_i] : 261'd0;
 always @(posedge clk_s or negedge rst_n)
  if(!rst_n) begin rc_v<=1'b0; pend<=261'd0; rc_coll<=1'b0; end
  else begin
   pend <= (ev[260] && ev[259]) ? ev : 261'd0;
   rc_v <= (ev[260] && !ev[259]) || pend[260];
   if(ev[260] && !ev[259] && pend[260]) rc_coll<=1'b1;
  end
 always @(posedge clk_s)
  if(ev[260] && !ev[259]) begin rc_tag<=ev[258:256]; rc_d<=ev[255:0]; end
  else if(pend[260]) begin rc_tag<=pend[258:256]; rc_d<=pend[255:0]; end
 // ------------------------------------------------------------------ (d) SFU ro -> reducer operand
 // sfucore registers ro_v/ro_x at stream edge T; captured here at A=T+1(+R); the compiler emits the SFU-source red_cmd at
 // the serial edge E = ceil((3A+3)/4) (A mod 4 != 2) and sfu_x is registered at E like a slice's slice_x.
 wire [527:0] ro = ro_slot[rslot];
 wire ro_mine = red_sel[11] && red_sel[7] && red_sel[6];
 wire ro_ext  = red_sel[10:8]==3'd0 || red_sel[10:8]==3'd1 || red_sel[10:8]==3'd3;
 wire ro_bad  = ro_mine && ro_ext && !ro[512+red_sel[3:0]];
 always @(posedge clk_q) sfu_x <= ro[32*red_sel[3:0]+:32];
 // ------------------------------------------------------------------ sticky fault (serial)
 reg sf_q;
 always @(posedge clk_q or negedge rst_n) if(!rst_n) sf_q<=1'b0; else sf_q<=sfault_s||rc_coll||ins_coll;
 always @(posedge clk_q or negedge rst_n)
  if(!rst_n) fault<=1'b0;
  else if(ibad||dbad||rbad||ro_bad||sf_q) fault<=1'b1;
endmodule
`default_nettype wire
