`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_programme_store_r10 (SFU-PS-FUND 2026-10-17): the SFU programme store as ELEVEN identical one-stripe spine
// leaves (ot_hgi_sfu_store_stripe_leaf_r10: programme stripes P0..P7, IO stripes IO0..IO2) plus a thin head (this
// module's own logic: host pin flops, launch precompute, reset tree, per-leaf write strobes, all-stripe agreement /
// control_v / fault / status). Design decision: claude-takeover lanes/SFU-PS-FUND.md.
// Differences from r9 (bench-proven top): (1) one stripe per leaf, one master; (2) configuration reaches the leaves by
// four neighbour CHAINS through the leaves' own pin flops (P0>P1>P2, P3>P4>P5, P6>P7, IO0>IO1>IO2) instead of a
// per-leaf registered hop: no 256-bit hop registers in the head; (3) the relay and the control_v-gated output
// registers live in each leaf's S band, so the head holds no 2,213-bit register mass; (4) chain depth 0 leaves see
// configuration on the r7c edge (no +1 hop).
// PRICED CYCLES vs r7c: SUPERSEDED by RELAYS (SFU-PS-4) below: D = 5, status 3 (r7c + 1 edge everywhere, with the
// compile schedule's ARITH_START_ADVANCE_R10 = 2); reset release 4 edges unchanged.
// r10n2 (KH-NATIVE3 10-17): each leaf chain hop is 2 edges (leaf in-face pin flop -> out-face fwd flop, native capture
// fix); write strobe depths 0..5 (see depth()). A write lands depth+1 edges after the head pin flop; the deepest IO leaf
// (IO2, depth 4) meets the unchanged host contract (io_start_v >= 4 idle edges after the last write) with 0 edges slack.
// Configuration write path: chain depth k (0..2) lands k edges after r7c. Host contract: the first start
// (io_start_v) must be sampled >= 4 edges after the last configuration write (r7c >= 1, r9 >= 2); programme load is
// once per calendar load, so the per-token cost is 0 cycles.
// Exactness (before decision B): identical to r9/r7c on every edge (narrow-W check, ordinal agreement vs stripe 0, valid/active/done
// agreement, sticky faults, control_v gate); bench = tb_sfu_store_r10_lockstep (r7c vs r10, every output every edge)
// + the canonical tb_hgi_sfu_split_equiv with STORE10=1.
// DECISION B (coordinator 10-17 ~20:40, SFU-PS-3; leaf RTL unchanged): the r7c all-stripe agreement was leaf -> head ->
// leaf COMBINATIONAL (up to ~1.58 mm in one cycle in any 11-leaf floorplan). Two changes remove every cross-leaf
// one-cycle path:
//  (1) each leaf gates its outputs on its OWN stripe status: in_cv[l] = calendar_v[l] & !fault[l] (stripe 7 / IO 2 also
//      include their own narrow-W check). Exact in legal operation (all stripes lockstep); on a fault the faulting
//      stripe's outputs are zeroed locally and the sticky store fault still raises `fault` (the host must not launch
//      again); the not-yet-faulted stripes' words are not zeroed (fault-mode exception of the lockstep bench).
//  (2) the programme start is REGISTERED in the head: p_sv_q <= rb & io_cv & IO2.calendar[26] -> the programme calendar
//      starts ONE edge later than r7c relative to the IO calendar. compiler_control and programme_active/done/ordinal
//      are r7c + 1 edge for the same IO image. COMPILE SCHEDULE: the HBM compiler places arith_start (io_word[470])
//      ONE IO row earlier (ARITH_START_ADVANCE=1, tools/hbm_static/make_qswiglu_io_calendar.py io_store_r10.hex) so the
//      core sees compiler_control on the r7c edge; io_word itself is unchanged (the core ignores bit 470).
// Remaining head paths are single registered legs: leaf status -> head flop (agreement/fault/status), head flop -> leaf pin.
// RELAYS (SFU-PS-4, coordinator 10-17 0dh++++; the decision-B cluster gate measured head->far leaf -770, leaf->head
// -777, leaf->S face -483 ps): every cross-leaf leg is now ONE short registered hop through a per-row relay.
// Rows (S->N): R0 = P2 P1 P0 | R1 = P6 head IO0 | R2 = P7 IO2 IO1 | R3 = P5 P4 P3.
//  (a) programme start/launch args: one relay copy per row (pr_*), +1 edge -> the programme calendar starts 2 edges
//      after IO2 bit 26 (B +1, relay +1). IO leaves (all three touch the head cell) take the launch from the head.
//  (b) configuration chain heads P0 (R0) and P3 (R3) are fed through a per-row relay (cr_*), strobes +1 (chain
//      depths P0/P3 1, P1/P4 2, P2/P5 3); P6 / IO0 (beside the head) unchanged. Host contract unchanged: io_start_v
//      >= 4 edges after the last write (the programme start is >= 3 edges after the IO start).
//  (c) status: a per-row pre-combine register (sp_* programme rows R0..R3, si_* IO rows R1..R2: valid/active/done
//      all+any, fault any, ordinal of the row representative, row-internal ordinal mismatch) -> the head computes the
//      r7c agreement / fault / status on the pre-combined rows, one edge later (exact: every input and the reset
//      qualifier delayed together). The programme START (io_cv & IO2 bit 26 -> p_sv_q) and each leaf's own gate stay
//      on the raw leaf outputs (IO leaves / own leaf: short).
//  (d) outputs: io_word and compiler_control are re-registered (o_io/o_ctl, placed per row between the leaf S band
//      and the S face): +1 edge.
// PRICED CYCLES vs r7c (same IO image): io_word +1 (D = 5), IO status +1, compiler_control / programme status +3,
// IO fault +1, programme fault +3. COMPILE SCHEDULE: arith_start (io_word[470]) is placed ARITH_START_ADVANCE_R10=2
// IO rows earlier (tools/hbm_static/make_qswiglu_io_calendar.py io_store_r10.hex) -> compiler_control and programme
// status land with io_word: the whole store is r7c + 1 edge (D = 5, status 3), 0 cycles/token (once per invocation).
module ot_hgi_sfu_programme_store_r10 #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW
)(
 input wire clk,rst_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output reg programme_active,programme_done,
 output reg [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output reg io_active,io_done,
 output reg [31:0] io_ordinal,
 output wire [470:0] io_word,
 output wire [1741:0] compiler_control,
 output reg fault
);
 initial if(PAGE_AW!=1)$fatal(1,"programme store r10: PAGE_AW=1 only (2048-row stripes)");
 localparam integer NL=11;                       // leaves 0..7 = programme stripes, 8..10 = IO stripes 0..2
 // chain predecessor (-1 = chain head fed by the head's pin flops) and depth
 function automatic integer pred(input integer l);
  case(l) 1:pred=0; 2:pred=1; 4:pred=3; 5:pred=4; 7:pred=6; 9:pred=8; 10:pred=9; default:pred=-1; endcase
 endfunction
 function automatic integer depth(input integer l);
`ifdef OT_SFU_PSTORE10N2_MUT_DEPTH1
  // MUTANT: r10n chain depths (1 edge per leaf hop) with the r10n2 leaf (2 edges per hop)
  case(l) 0,3,7,9:depth=1; 1,4,10:depth=2; 2,5:depth=3; default:depth=0; endcase
`else
  // r10n2 (KH-NATIVE3 10-17): leaf chain hop = 2 edges (in-face pin flop + out-face fwd flop); row relay = 1 edge.
  // depth = relay (P0/P3 rows: 1) + 2 x chain position: P0/P3 1, P1/P4 3, P2/P5 5; P6 0, P7 2; IO0 0, IO1 2, IO2 4.
  case(l) 0,3:depth=1; 7,9:depth=2; 1,4:depth=3; 10:depth=4; 2,5:depth=5; default:depth=0; endcase
`endif
 endfunction
 // ---- head pin flops: pure (pin -> D), one copy each
 reg p_cfg_we,p_io_cfg_we,p_io_start_v;
 reg [2:0] p_cfg_stripe;
 reg [1:0] p_io_cfg_stripe;
 reg [AW-1:0] p_cfg_addr,p_io_cfg_addr,p_start_base,p_io_start_base;
 reg [255:0] p_cfg_data,p_io_cfg_data;
 reg [AW:0] p_start_limit,p_io_start_limit;
 reg [15:0] p_start_loops,p_io_start_loops;
 always @(posedge clk)begin
  p_cfg_we<=cfg_we;p_io_cfg_we<=io_cfg_we;p_io_start_v<=io_start_v;
  p_cfg_stripe<=cfg_stripe;p_cfg_addr<=cfg_addr;p_cfg_data<=cfg_data;
  p_start_base<=start_base;p_start_limit<=start_limit;p_start_loops<=start_loops;
  p_io_cfg_stripe<=io_cfg_stripe;p_io_cfg_addr<=io_cfg_addr;p_io_cfg_data<=io_cfg_data;
  p_io_start_base<=io_start_base;p_io_start_limit<=io_start_limit;p_io_start_loops<=io_start_loops;
 end
 // ---- synchronous regional reset tree: 2-flop sync -> stage A (one relay per leaf + one for the head) -> stage B
 reg rs1,rs2;
 always @(posedge clk)begin rs1<=rst_n;rs2<=rs1;end
 (* keep = "true", dont_touch = "true" *) reg [NL-1:0] ra_leaf;
 (* keep = "true", dont_touch = "true" *) reg ra_top;
 always @(posedge clk)begin ra_leaf<={NL{rs2}};ra_top<=rs2;end
 (* keep = "true", dont_touch = "true" *) reg [3:0] rb;     // 0 status, 1 IO agreement, 2 programme agreement, 3 strobes
 (* keep = "true", dont_touch = "true" *) reg rbd1;         // rb delayed 1 (= r7c pin-flop reset qualification)
 always @(posedge clk)begin rb<={4{ra_top}};rbd1<=rb[3];end
 // ---- per-leaf write strobes: r7c we_q[s] = rb(stripe) & r_cfg_we (pin flop reset by rb_pin one edge earlier)
 wire [NL-1:0] we0;
 for(genvar s=0;s<8;s=s+1)begin:g_pwe
  assign we0[s]=rbd1 && rb[3] && p_cfg_we && p_cfg_stripe==s;
 end
 for(genvar s=0;s<3;s=s+1)begin:g_iowe
  assign we0[8+s]=rbd1 && rb[3] && p_io_cfg_we && p_io_cfg_stripe==s;
 end
 // chain-depth delay of each strobe (depth 0 leaves sample we0 directly)
 (* keep = "true", dont_touch = "true" *) reg [NL-1:0] we_d1,we_d2,we_d3,we_d4,we_d5;
 always @(posedge clk)begin we_d1<=we0;we_d2<=we_d1;we_d3<=we_d2;we_d4<=we_d3;we_d5<=we_d4;end
 wire [NL-1:0] leaf_we;
 for(genvar l=0;l<NL;l=l+1)begin:g_wed
`ifdef OT_SFU_PSTORE10_MUT_CHAIN
  // MUTANT: chain depth ignored for leaf 4 (P4 strobe one edge early -> writes the P3 row's data)
  assign leaf_we[l]=(l==4)?we0[l]:(depth(l)==0)?we0[l]:(depth(l)==1)?we_d1[l]:(depth(l)==2)?we_d2[l]:(depth(l)==3)?we_d3[l]:(depth(l)==4)?we_d4[l]:we_d5[l];
`else
  assign leaf_we[l]=(depth(l)==0)?we0[l]:(depth(l)==1)?we_d1[l]:(depth(l)==2)?we_d2[l]:(depth(l)==3)?we_d3[l]:(depth(l)==4)?we_d4[l]:we_d5[l];
`endif
 end
 // ---- launch arguments, precomputed in front of the leaf pins (as r9)
 wire p_legal=p_start_limit>{1'b0,p_start_base} && p_start_limit<=(1<<AW) && p_start_loops!=0;
 wire [AW:0] p_span=p_start_limit-{1'b0,p_start_base};
 wire p_lone=p_start_loops==16'd1;
 wire io_legal=p_io_start_limit>{1'b0,p_io_start_base} && p_io_start_limit<=(1<<AW) && p_io_start_loops!=0;
 wire [AW:0] io_span=p_io_start_limit-{1'b0,p_io_start_base};
 wire io_lone=p_io_start_loops==16'd1;
 wire io_sv=rb[1] && rbd1 && p_io_start_v;      // r7c: rb(stripe) & r_io_start_v
 // ---- per-row relays (SFU-PS-4): programme launch (a) and configuration chain heads P0 / P3 (b); one copy per row
 function automatic integer rowof(input integer l);
  case(l) 0,1,2:rowof=0; 6,8:rowof=1; 7,9,10:rowof=2; default:rowof=3; endcase
 endfunction
 wire p_sv;
 (* keep = "true", dont_touch = "true" *) reg [3:0] pr_sv,pr_legal,pr_lone;
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] pr_base[0:3];
 (* keep = "true", dont_touch = "true" *) reg [AW:0] pr_span[0:3];
 (* keep = "true", dont_touch = "true" *) reg [15:0] pr_loops[0:3];
 for(genvar r=0;r<4;r=r+1)begin:g_prow
  always @(posedge clk)begin
   pr_sv[r]<=p_sv;pr_legal[r]<=p_legal;pr_lone[r]<=p_lone;
   pr_base[r]<=p_start_base;pr_span[r]<=p_span;pr_loops[r]<=p_start_loops;
  end
 end
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] cr_addr0,cr_addr3;
 (* keep = "true", dont_touch = "true" *) reg [255:0] cr_data0,cr_data3;
 always @(posedge clk)begin cr_addr0<=p_cfg_addr;cr_data0<=p_cfg_data;cr_addr3<=p_cfg_addr;cr_data3<=p_cfg_data;end
 // ---- leaves
 wire [AW-1:0] c_addr[0:NL-1];
 wire [255:0] c_data[0:NL-1];
 wire [221:0] cal[0:NL-1];
 wire [NL-1:0] lv,la,ld,lf,b26;
 wire [1:0] hz[0:NL-1];
 wire [31:0] ord[0:NL-1];
 wire [NL-1:0] own_cv;                          // decision B: per-leaf output gate = its own stripe status
 wire io_cv;
 reg p_sv_q;
 for(genvar l=0;l<NL;l=l+1)begin:g_leaf
  localparam integer PR=pred(l);
  wire io=(l>=8);
  wire [AW-1:0] a_in;
  wire [255:0] d_in;
  localparam integer RW=rowof(l);
  if(l==0)begin:g_cr0
   assign a_in=cr_addr0;
   assign d_in=cr_data0;
  end else if(l==3)begin:g_cr3
   assign a_in=cr_addr3;
   assign d_in=cr_data3;
  end else if(PR<0)begin:g_head
   assign a_in=(l>=8)?p_io_cfg_addr:p_cfg_addr;
   assign d_in=(l>=8)?p_io_cfg_data:p_cfg_data;
  end else begin:g_chain
   assign a_in=c_addr[PR];
   assign d_in=c_data[PR];
  end
  ot_hgi_sfu_store_stripe_leaf_r10 u_leaf(   // no #(): hard child (default AW=11 = PAGE_AW 1)
  .clk(clk),.rst_a(ra_leaf[l]),.in_we(leaf_we[l]),
   .in_addr(a_in),.in_data(d_in),.out_addr(c_addr[l]),.out_data(c_data[l]),
`ifdef OT_SFU_PSTORE10C_MUT_ROWSKEW
   // MUTANT: row R3 (P3..P5) takes the programme start from the head, bypassing its row relay -> one edge early
   .in_start_v((l>=8)?io_sv:(RW==3)?p_sv:pr_sv[RW]),
`else
   .in_start_v((l>=8)?io_sv:pr_sv[RW]),
`endif
   .in_start_base((l>=8)?p_io_start_base:pr_base[RW]),.in_legal((l>=8)?io_legal:pr_legal[RW]),
   .in_span((l>=8)?io_span:pr_span[RW]),.in_loops((l>=8)?p_io_start_loops:pr_loops[RW]),.in_loops_one((l>=8)?io_lone:pr_lone[RW]),
   .in_cv(own_cv[l]),.out_cal(cal[l]),.out_v(lv[l]),.out_active(la[l]),.out_done(ld[l]),.out_fault(lf[l]),
   .out_ord(ord[l]),.out_hz(hz[l]),.out_b26(b26[l]));
 end
 // ---- narrow-stripe W check (programme stripe 7: W=188; IO stripe 2: W=27), exactly as r9
 wire nb7_now=hz[7][1];
 wire nbio_now=hz[10][0];
 reg nb7_s,nbio_s;
 always @(posedge clk)begin
  nb7_s<=rb[2] && ((rbd1 && nb7_now) || nb7_s);
  nbio_s<=rb[1] && ((rbd1 && nbio_now) || nbio_s);
 end
 // ---- calendar agreement (as ot_hgi_sfu_calendar_paged_rc / ot_hgi_sfu_io_calendar_rc)
 wire [7:0] pv=lv[7:0],pa=la[7:0],pd=ld[7:0];
 wire [7:0] pf={lf[7]|(rbd1&&nb7_now)|nb7_s,lf[6:0]};
 wire [2:0] vio=lv[10:8],aio=la[10:8],dio=ld[10:8];
 wire [2:0] iof={lf[10]|(rbd1&&nbio_now)|nbio_s,lf[9:8]};
 assign own_cv[7:0]=pv & ~pf;                     // decision B: no cross-leaf AND on the output gate
 assign own_cv[10:8]=vio & ~iof;
 assign io_cv=(&vio) && !(|iof);                  // all-IO agreement: only into the registered programme start
`ifdef OT_SFU_PSTORE10B_MUT_NOSHIFT
 // MUTANT: programme start left combinational (r7c timing) -> must mismatch the +1 lockstep
 always @(*)p_sv_q=rb[2] && io_cv && b26[10];
`else
 always @(posedge clk)p_sv_q<=rb[2] && io_cv && b26[10];   // r7c: rb(stripe) & io[470], +1 edge (decision B)
`endif
 assign p_sv=p_sv_q;
 // ---- (c) per-row status pre-combine (registered beside each row), then the r7c agreement on the rows, one edge later
 localparam [7:0] PM0=8'b0000_0111, PM1=8'b0100_0000, PM2=8'b1000_0000, PM3=8'b0011_1000;   // programme rows
 localparam integer PREP0=0, PREP1=6, PREP2=7, PREP3=3;                                    // row representatives
 function automatic [7:0] pmask(input integer r);
  case(r) 0:pmask=PM0; 1:pmask=PM1; 2:pmask=PM2; default:pmask=PM3; endcase
 endfunction
 function automatic integer prep(input integer r);
  case(r) 0:prep=PREP0; 1:prep=PREP1; 2:prep=PREP2; default:prep=PREP3; endcase
 endfunction
 (* keep = "true", dont_touch = "true" *) reg [3:0] sp_vall,sp_vany,sp_aall,sp_aany,sp_dall,sp_dany,sp_f,sp_mm;
 (* keep = "true", dont_touch = "true" *) reg [31:0] sp_ord[0:3];
 for(genvar r=0;r<4;r=r+1)begin:g_sp
  localparam [7:0] M=pmask(r);
  localparam integer RP=prep(r);
  wire [7:0] mm;
  for(genvar s=0;s<8;s=s+1)begin:g_m assign mm[s]=M[s] && ord[s]!=ord[RP]; end
  always @(posedge clk)begin
   sp_vall[r]<=&(pv|~M);sp_vany[r]<=|(pv&M);sp_aall[r]<=&(pa|~M);sp_aany[r]<=|(pa&M);
   sp_dall[r]<=&(pd|~M);sp_dany[r]<=|(pd&M);sp_f[r]<=|(pf&M);sp_mm[r]<=|mm;sp_ord[r]<=ord[RP];
  end
 end
 // IO rows: R1 = IO0 (leaf 8), R2 = IO2 + IO1 (leaves 10, 9; representative IO1)
 (* keep = "true", dont_touch = "true" *) reg [1:0] si_vall,si_vany,si_aall,si_aany,si_dall,si_dany,si_f;
 (* keep = "true", dont_touch = "true" *) reg si_mm;
 (* keep = "true", dont_touch = "true" *) reg [31:0] si_ord[0:1];
 always @(posedge clk)begin
  si_vall[0]<=vio[0];si_vany[0]<=vio[0];si_aall[0]<=aio[0];si_aany[0]<=aio[0];si_dall[0]<=dio[0];si_dany[0]<=dio[0];
  si_f[0]<=iof[0];si_ord[0]<=ord[8];
  si_vall[1]<=&vio[2:1];si_vany[1]<=|vio[2:1];si_aall[1]<=&aio[2:1];si_aany[1]<=|aio[2:1];si_dall[1]<=&dio[2:1];
  si_dany[1]<=|dio[2:1];si_f[1]<=|iof[2:1];si_mm<=ord[10]!=ord[9];si_ord[1]<=ord[9];
 end
 (* keep = "true", dont_touch = "true" *) reg [2:0] rb_d;        // rb[2:0] delayed with the pre-combined status
 always @(posedge clk)rb_d<=rb[2:0];
 // r7c: p_dis = (|pv&&!&pv) || (|pd&&!&pd) || (|pa&&!&pa) || |(pv & (ord[s]!=ord[0])); the last term equals
 // &pv && (any ordinal differs) whenever the first is false, and "any differs" = a row-internal mismatch or a row
 // representative != row R0's (= P0).
 wire p_omm=(|sp_mm) || sp_ord[1]!=sp_ord[0] || sp_ord[2]!=sp_ord[0] || sp_ord[3]!=sp_ord[0];
 wire p_dis=(|sp_vany && !(&sp_vall)) || (|sp_dany && !(&sp_dall)) || (|sp_aany && !(&sp_aall)) || (&sp_vall && p_omm);
 wire io_omm=si_mm || si_ord[1]!=si_ord[0];
 wire io_dis=(|si_vany && !(&si_vall)) || (|si_dany && !(&si_dall)) || (|si_aany && !(&si_aall)) || (&si_vall && io_omm);
 reg p_fault,io_fault;
 always @(posedge clk)begin
  if(!rb_d[2])p_fault<=0; else if(p_dis || |sp_f)p_fault<=1;
  if(!rb_d[1])io_fault<=0; else if(io_dis || |si_f)io_fault<=1;
 end
 // ---- (d) outputs: re-registered after the leaf output registers (+1 edge, per-row relay toward the S face)
 reg [470:0] o_io;
 reg [1741:0] o_ctl;
 always @(posedge clk)begin
  o_io<={cal[10][26:0],cal[9],cal[8]};
  o_ctl<={cal[7][187:0],cal[6],cal[5],cal[4],cal[3],cal[2],cal[1],cal[0]};
 end
 assign io_word=o_io;
`ifdef OT_SFU_PSTORE_MUT_FLIP
 `define OT_SFU_PSTORE10_FLIP
`endif
`ifdef OT_SFU_PSTORE10_MUT_FLIP
 `define OT_SFU_PSTORE10_FLIP
`endif
`ifdef OT_SFU_PSTORE10_FLIP
 assign compiler_control=o_ctl^1742'd1;   // bench negative control
`else
 assign compiler_control=o_ctl;
`endif
 always @(posedge clk)
  if(!rb_d[0])begin
   io_active<=0;io_done<=0;io_ordinal<=0;programme_active<=0;programme_done<=0;programme_ordinal<=0;fault<=0;
  end else begin
   io_active<=|si_aany;io_done<=&si_dall;io_ordinal<=si_ord[0];
   programme_active<=|sp_aany;programme_done<=&sp_dall;programme_ordinal<=sp_ord[0];
   if(io_fault||p_fault)fault<=1;
  end
endmodule
`default_nettype wire
