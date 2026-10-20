`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_programme_store_r11 (HBM-ELEMOWN3/SFUPS 2026-10-19): r10 (11 one-stripe leaves, same leaf master, same pins,
// same floorplan 1080 x 950.4) with every head leg that the r10 cluster gate measured above the 405 um reach rule
// replaced by a FORWARDED MULTI-STAGE RELAY sized from the floorplan distances, one kept copy per destination leaf/site.
// Why: the r10 --cts gate (ref_gate/hbm_sfu_programme_store_r10_cl-20261018-180939) never closed post-GRT repair_timing:
// SS WNS -256 ps on pr_base[0][4]/D, 468 endpoints. The r10 per-row relay pr_* took the launch arguments from the E-face
// start pins (y 891..949) and fed THREE leaves 830 um apart in one row: ~1.5 mm of wire over two cycles. The same reach
// defect exists on the reset tree (rs2 -> ra_leaf), the config chain heads (P6 / IO0 direct, P3 one relay ~1 mm), the
// write strobes (we0 -> depth-0 leaves ~0.9 mm), the row status pre-combine (P2 vs P0 ordinal compare ~700 um) and the
// leaf -> S-face output registers (cal3 -> compiler_control pins ~1.3 mm in one cycle).
// Structure (floorplan distances along std-cell channels, stage spacing <= ~390 um; generator
// physical/ref_tile/hbm_sfu_programme_store_r11_cl/relay_place_gen.py places every stage FIRM at its channel point):
//   KR=3  reset: rs2 -> 3 relays -> per-leaf ra (at the leaf) / per-site ra,rb,rbd1 (at the site). Uniform +3 release.
//   KI=2  IO launch (io_sv + args, stage 1 beside the io_start pins) -> IO0/IO1/IO2: equal depth (lockstep).
//   KL=4  programme launch: args stage 1 beside the start pins, sv from p_sv_q (centre, beside the IO leaves) -> the 8
//         programme leaves, equal depth (lockstep; the r10 rowskew mutant becomes MUT_ROWSKEW: row R3 one stage short).
//   KC    configuration chain-head data relays: P0 1, P3 3, P6 4, IO0 2 (= KI, so an IO write keeps its edge vs the IO
//         start); each leaf's write strobe is a per-leaf relay of depth(l) = KC(chain) + 2 x chain position.
//   KS=2  status: per-leaf raw status relays -> one combine point beside the S-face status pins (r7c agreement exactly),
//         then KO-KS=2 pad stages so IO status keeps the io_word shift.
//   KO=4  outputs: leaf out_cal -> 3 relays -> the S-face pin registers (o_io / o_ctl as r10).
// PRICED CYCLES vs r7c (same IO image): IO side +KI+KO = +6 (io_word, IO status, IO fault); programme side
// +KI+1+KL+KO = +11 (compiler_control, programme status, programme fault). COMPILE SCHEDULE: arith_start (io_word[470]) is
// placed ARITH_START_ADVANCE_R11 = 1+KL = 5 IO rows earlier (tools/hbm_static/make_qswiglu_io_calendar.py -> io_store_r11.hex)
// so compiler_control lands with io_word: the whole store is r7c + 6 edges (D = 10, status DS = 8; r10 D = 5, DS = 3).
// The start-to-first-word latency is +5 edges vs r10 per SFU invocation; the static schedule issues io_start_v 5 edges
// earlier (the store holds no state the previous invocation needs once its calendars are done: done/status are
// compared at their shifted edge), so the per-token cost is 0 when the start lead slot is free, else <= 5 edges per
// invocation. Host contracts: first configuration write >= 4+KR = 7 edges after rst_n release (was 4: reset +3, once per
// power-up); io_start_v >= 4 idle edges after the last configuration write (unchanged: every chain head relay is
// matched by a later start, see depth()).
// Exactness: same r7c functions as r10 (narrow-W checks, all-stripe agreement on the r7c expression, sticky faults,
// per-leaf own-status output gate of decision B), each computed at the site that consumes it with site-local reset
// copies of equal depth (a uniform time shift is exact). Benches: tb_sfu_store_r11_lockstep (r7c vs r11, every output
// every edge, ISHIFT=6 / PSHIFT=11) + tb_hgi_sfu_split_equiv STORE11=1 (D=10, DS=8, io_store_r11.hex).
module ot_hgi_sfu_programme_store_r11 #(
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
 output wire programme_active,programme_done,
 output wire [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output wire io_active,io_done,
 output wire [31:0] io_ordinal,
 output wire [470:0] io_word,
 output wire [1741:0] compiler_control,
 output wire fault
);
 initial if(PAGE_AW!=1)$fatal(1,"programme store r11: PAGE_AW=1 only (2048-row stripes)");
 localparam integer NL=11;                       // leaves 0..7 = programme stripes, 8..10 = IO stripes 0..2
 localparam integer KR=3, KI=2, KL=4, KS=2, KO=4, KP=KO-KS;
 localparam integer KC0=1, KC3=3, KC6=4, KCIO=KI;
 localparam integer CW=AW+256;                   // configuration chain bundle {addr, data}
 localparam integer LW=1+AW+1+(AW+1)+16+1;       // launch bundle {sv, base, legal, span, loops, lone}
 localparam integer SW=1+1+1+1+32+2;             // status bundle {v, a, d, f, ord, hz}
 function automatic integer pred(input integer l);
  case(l) 1:pred=0; 2:pred=1; 4:pred=3; 5:pred=4; 7:pred=6; 9:pred=8; 10:pred=9; default:pred=-1; endcase
 endfunction
 // write-strobe depth = chain-head data relay + 2 edges per leaf chain hop (r10n2 leaf)
 function automatic integer depth(input integer l);
  case(l) 0:depth=KC0; 1:depth=KC0+2; 2:depth=KC0+4; 3:depth=KC3; 4:depth=KC3+2; 5:depth=KC3+4;
   6:depth=KC6; 7:depth=KC6+2; 8:depth=KCIO; 9:depth=KCIO+2; default:depth=KCIO+4; endcase
 endfunction
 function automatic integer sdepth(input integer l);   // strobe relay length actually built (mutant: P4 one hop early)
`ifdef OT_SFU_PSTORE11_MUT_CHAIN
  sdepth=(l==4)?depth(4)-2:depth(l);
`else
  sdepth=depth(l);
`endif
 endfunction
 function automatic integer owid(input integer l);     // calendar bits of leaf l that reach a pin
  owid=(l==7)?188:(l==10)?27:222;
 endfunction
 // ---- head pin flops: pure (pin -> D), one copy each (anchored at their pins by io_flop_at_pins)
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
 // ---- reset: 2-flop sync at the rst_n pin, then one KR-stage relay per leaf / per site (kept copies, placed)
 reg rs1,rs2;
 always @(posedge clk)begin rs1<=rst_n;rs2<=rs1;end
 wire [NL-1:0] ra_leaf;
 for(genvar l=0;l<NL;l=l+1)begin:g_rl
  (* keep = "true", dont_touch = "true" *) reg [KR-1:0] q;
  (* keep = "true", dont_touch = "true" *) reg ra;
  always @(posedge clk)begin q<={q[KR-2:0],rs2};ra<=q[KR-1];end
  assign ra_leaf[l]=ra;
 end
 // sites: 0 CFG strobes, 1 IOCFG strobes, 2 IOL io launch, 3 PSV programme start, 4 N7 (P7 own gate), 5 N10 (IO2 own
 // gate), 6 ST status combine (relay KR+KS: it sees the leaf status KS edges late, so its reset is KS edges later too)
 localparam integer NS=7, S_CFG=0, S_IOCFG=1, S_IOL=2, S_PSV=3, S_N7=4, S_N10=5, S_ST=6;
 wire [NS-1:0] rb_s,rbd1_s;
 for(genvar s=0;s<NS;s=s+1)begin:g_rs
  localparam integer K=(s==S_ST)?KR+KS:KR;
  (* keep = "true", dont_touch = "true" *) reg [K-1:0] q;
  (* keep = "true", dont_touch = "true" *) reg ra,rb,rbd1;
  always @(posedge clk)begin q<={q[K-2:0],rs2};ra<=q[K-1];rb<=ra;rbd1<=rb;end
  assign rb_s[s]=rb;
  assign rbd1_s[s]=rbd1;
 end
 // ---- leaves' raw outputs
 wire [221:0] cal[0:NL-1];
 wire [NL-1:0] lv,la,ld,lf,b26;
 wire [1:0] hz[0:NL-1];
 wire [31:0] ord[0:NL-1];
 wire [AW-1:0] c_addr[0:NL-1];
 wire [255:0] c_data[0:NL-1];
 // ---- narrow-W sticky checks, one copy per consuming site (same recurrence, site-local reset: exact time shift)
 //  N7: P7's own output gate; N10: IO2's own output gate; PSV: the all-IO agreement for the programme start
 reg nb7_n7,nbio_n10,nbio_psv;
 always @(posedge clk)begin
  nb7_n7<=rb_s[S_N7] && ((rbd1_s[S_N7] && hz[7][1]) || nb7_n7);
  nbio_n10<=rb_s[S_N10] && ((rbd1_s[S_N10] && hz[10][0]) || nbio_n10);
  nbio_psv<=rb_s[S_PSV] && ((rbd1_s[S_PSV] && hz[10][0]) || nbio_psv);
 end
 // ---- decision B: each leaf gates its outputs on its OWN stripe status (local)
 wire [NL-1:0] own_cv;
 for(genvar l=0;l<NL;l=l+1)begin:g_cv
  if(l==7)begin:g7 assign own_cv[l]=lv[l] && !(lf[l] || (rbd1_s[S_N7] && hz[7][1]) || nb7_n7); end
  else if(l==10)begin:g10 assign own_cv[l]=lv[l] && !(lf[l] || (rbd1_s[S_N10] && hz[10][0]) || nbio_n10); end
  else begin:gx assign own_cv[l]=lv[l] && !lf[l]; end
 end
 // ---- programme start (site PSV, beside the IO leaves' S faces): registered, as r10 decision B
 wire io_cv_psv=(&lv[10:8]) && !(lf[8] || lf[9] || lf[10] || (rbd1_s[S_PSV] && hz[10][0]) || nbio_psv);
 reg p_sv_q;
`ifdef OT_SFU_PSTORE11_MUT_NOSHIFT
 always @(*)p_sv_q=rb_s[S_PSV] && io_cv_psv && b26[10];   // MUTANT: combinational programme start (must mismatch)
`else
 always @(posedge clk)p_sv_q<=rb_s[S_PSV] && io_cv_psv && b26[10];
`endif
 // ---- launch bundles: precomputed at the start pins (stage 1 beside them), then forwarded
 wire p_legal=p_start_limit>{1'b0,p_start_base} && p_start_limit<=(1<<AW) && p_start_loops!=0;
 wire [AW:0] p_span=p_start_limit-{1'b0,p_start_base};
 wire p_lone=p_start_loops==16'd1;
 wire io_legal=p_io_start_limit>{1'b0,p_io_start_base} && p_io_start_limit<=(1<<AW) && p_io_start_loops!=0;
 wire [AW:0] io_span=p_io_start_limit-{1'b0,p_io_start_base};
 wire io_lone=p_io_start_loops==16'd1;
 wire io_sv=rb_s[S_IOL] && rbd1_s[S_IOL] && p_io_start_v;   // r7c: rb(stripe) & r_io_start_v
 wire [LW-2:0] p_args={p_start_base,p_legal,p_span,p_start_loops,p_lone};
 wire [LW-1:0] io_bundle={io_sv,p_io_start_base,io_legal,io_span,p_io_start_loops,io_lone};
 wire [LW-1:0] lb[0:NL-1];                       // launch bundle at each leaf's pins
 for(genvar l=0;l<8;l=l+1)begin:g_pl             // programme leaves: KL stages for args (from the pins) and sv (from p_sv_q)
  (* keep = "true", dont_touch = "true" *) reg [KL*(LW-1)-1:0] a;
  (* keep = "true", dont_touch = "true" *) reg [KL-1:0] v;
  always @(posedge clk)begin a<={a[(KL-1)*(LW-1)-1:0],p_args};v<={v[KL-2:0],p_sv_q};end
`ifdef OT_SFU_PSTORE11_MUT_ROWSKEW
  // MUTANT: row R3 (P3..P5) takes its programme start one relay stage early
  assign lb[l]={(l>=3 && l<=5)?v[KL-2]:v[KL-1],a[KL*(LW-1)-1-:(LW-1)]};
`else
  assign lb[l]={v[KL-1],a[KL*(LW-1)-1-:(LW-1)]};
`endif
 end
 for(genvar i=0;i<3;i=i+1)begin:g_il             // IO leaves: KI stages, stage 1 beside the io_start pins
  (* keep = "true", dont_touch = "true" *) reg [KI*LW-1:0] a;
  always @(posedge clk)a<={a[(KI-1)*LW-1:0],io_bundle};
`ifdef OT_SFU_PSTORE11_MUT_IOSKEW
  // MUTANT: IO2 takes the IO launch one relay stage early (IO stripes out of lockstep)
  assign lb[8+i]=(i==2)?a[(KI-1)*LW-1-:LW]:a[KI*LW-1-:LW];
`else
  assign lb[8+i]=a[KI*LW-1-:LW];
`endif
 end
 // ---- configuration chain heads: P0 (KC0), P3 (KC3), P6 (KC6), IO0 (KCIO) data relays
 wire [CW-1:0] ch[0:3];
 for(genvar c=0;c<4;c=c+1)begin:g_cd
  localparam integer K=(c==0)?KC0:(c==1)?KC3:(c==2)?KC6:KCIO;
  wire [CW-1:0] src=(c==3)?{p_io_cfg_addr,p_io_cfg_data}:{p_cfg_addr,p_cfg_data};
  (* keep = "true", dont_touch = "true" *) reg [K*CW-1:0] q;
  if(K==1)begin:g1 always @(posedge clk)q<=src; end
  else begin:gk always @(posedge clk)q<={q[(K-1)*CW-1:0],src}; end
  assign ch[c]=q[K*CW-1-:CW];
 end
 // ---- write strobes: r7c we_q[s] = rb(stripe) & r_cfg_we (site-local reset copies), then one relay per leaf
 wire [NL-1:0] we0,leaf_we;
 for(genvar s=0;s<8;s=s+1)begin:g_pwe
  assign we0[s]=rbd1_s[S_CFG] && rb_s[S_CFG] && p_cfg_we && p_cfg_stripe==s;
 end
 for(genvar s=0;s<3;s=s+1)begin:g_iowe
  assign we0[8+s]=rbd1_s[S_IOCFG] && rb_s[S_IOCFG] && p_io_cfg_we && p_io_cfg_stripe==s;
 end
 for(genvar l=0;l<NL;l=l+1)begin:g_we
  localparam integer K=sdepth(l);
  (* keep = "true", dont_touch = "true" *) reg [K-1:0] q;
  if(K==1)begin:g1 always @(posedge clk)q<=we0[l]; end
  else begin:gk always @(posedge clk)q<={q[K-2:0],we0[l]}; end
  assign leaf_we[l]=q[K-1];
 end
 // ---- leaves
 for(genvar l=0;l<NL;l=l+1)begin:g_leaf
  localparam integer PR=pred(l);
  wire [CW-1:0] cin;
  if(l==0)begin:g_h0 assign cin=ch[0]; end
  else if(l==3)begin:g_h3 assign cin=ch[1]; end
  else if(l==6)begin:g_h6 assign cin=ch[2]; end
  else if(l==8)begin:g_h8 assign cin=ch[3]; end
  else begin:g_chain assign cin={c_addr[PR],c_data[PR]}; end
  ot_hgi_sfu_store_stripe_leaf_r10 u_leaf(   // no #(): hard child (default AW=11 = PAGE_AW 1)
   .clk(clk),.rst_a(ra_leaf[l]),.in_we(leaf_we[l]),
   .in_addr(cin[CW-1-:AW]),.in_data(cin[255:0]),.out_addr(c_addr[l]),.out_data(c_data[l]),
   .in_start_v(lb[l][LW-1]),.in_start_base(lb[l][LW-2-:AW]),.in_legal(lb[l][LW-2-AW]),
   .in_span(lb[l][LW-3-AW-:AW+1]),.in_loops(lb[l][16:1]),.in_loops_one(lb[l][0]),
   .in_cv(own_cv[l]),.out_cal(cal[l]),.out_v(lv[l]),.out_active(la[l]),.out_done(ld[l]),.out_fault(lf[l]),
   .out_ord(ord[l]),.out_hz(hz[l]),.out_b26(b26[l]));
 end
 // ---- status: per-leaf raw relays (KS) to the combine point beside the S-face status pins
 wire [NL-1:0] sv,sa,sd,sf;
 wire [31:0] so[0:NL-1];
 wire [1:0] sh[0:NL-1];
 for(genvar l=0;l<NL;l=l+1)begin:g_st
  (* keep = "true", dont_touch = "true" *) reg [KS*SW-1:0] q;
  always @(posedge clk)q<={q[(KS-1)*SW-1:0],lv[l],la[l],ld[l],lf[l],ord[l],hz[l]};
  assign {sv[l],sa[l],sd[l],sf[l],so[l],sh[l]}=q[KS*SW-1-:SW];
 end
 // narrow-W checks at ST (reset copy KS edges later = the relayed leaf time)
 reg nb7_st,nbio_st;
 always @(posedge clk)begin
  nb7_st<=rb_s[S_ST] && ((rbd1_s[S_ST] && sh[7][1]) || nb7_st);
  nbio_st<=rb_s[S_ST] && ((rbd1_s[S_ST] && sh[10][0]) || nbio_st);
 end
 wire [7:0] pv=sv[7:0],pa=sa[7:0],pd=sd[7:0];
 wire [7:0] pf={sf[7]|(rbd1_s[S_ST]&&sh[7][1])|nb7_st,sf[6:0]};
 wire [2:0] vio=sv[10:8],aio=sa[10:8],dio=sd[10:8];
 wire [2:0] iof={sf[10]|(rbd1_s[S_ST]&&sh[10][0])|nbio_st,sf[9:8]};
 // r7c ot_hgi_sfu_calendar_paged_rc / ot_hgi_sfu_io_calendar_rc agreement, on the relayed status
 reg p_dis,io_dis;
 always @(*)begin
  p_dis=(|pv && !(&pv)) || (|pd && !(&pd)) || (|pa && !(&pa));
  for(integer s=1;s<8;s=s+1)if(pv[s] && so[s]!=so[0])p_dis=1;
  io_dis=(|vio && !(&vio)) || (|dio && !(&dio)) || (|aio && !(&aio));
  for(integer s=1;s<3;s=s+1)if(vio[s] && so[8+s]!=so[8])io_dis=1;
 end
 reg p_fault,io_fault;
 always @(posedge clk)begin
  if(!rb_s[S_ST])p_fault<=0; else if(p_dis || |pf)p_fault<=1;
  if(!rb_s[S_ST])io_fault<=0; else if(io_dis || |iof)io_fault<=1;
 end
 reg c_ia,c_id,c_pa,c_pd,c_f;
 reg [31:0] c_io_o,c_po;
 always @(posedge clk)
  if(!rb_s[S_ST])begin
   c_ia<=0;c_id<=0;c_io_o<=0;c_pa<=0;c_pd<=0;c_po<=0;c_f<=0;
  end else begin
   c_ia<=|aio;c_id<=&dio;c_io_o<=so[8];
   c_pa<=|pa;c_pd<=&pd;c_po<=so[0];
   if(io_fault||p_fault)c_f<=1;
  end
 // KP pad stages (pure delay; the last is the S-face pin register) so the status keeps the io_word shift
 localparam integer TW=1+1+32+1+1+32+1;
 (* keep = "true", dont_touch = "true" *) reg [KP*TW-1:0] st_pad;
 always @(posedge clk)st_pad<={st_pad[(KP-1)*TW-1:0],c_ia,c_id,c_io_o,c_pa,c_pd,c_po,c_f};
 assign {io_active,io_done,io_ordinal,programme_active,programme_done,programme_ordinal,fault}=st_pad[KP*TW-1-:TW];
 // ---- outputs: per-leaf calendar relays (KO-1 stages, placed toward the pins) + the pin registers
 wire [221:0] oc[0:NL-1];
 for(genvar l=0;l<NL;l=l+1)begin:g_oc
  localparam integer W=owid(l);
  (* keep = "true", dont_touch = "true" *) reg [(KO-1)*W-1:0] q;
  always @(posedge clk)q<={q[(KO-2)*W-1:0],cal[l][W-1:0]};
  assign oc[l]=222'(q[(KO-1)*W-1-:W]);
 end
 reg [470:0] o_io;
 reg [1741:0] o_ctl;
 always @(posedge clk)begin
  o_io<={oc[10][26:0],oc[9],oc[8]};
  o_ctl<={oc[7][187:0],oc[6],oc[5],oc[4],oc[3],oc[2],oc[1],oc[0]};
 end
 assign io_word=o_io;
`ifdef OT_SFU_PSTORE_MUT_FLIP
 `define OT_SFU_PSTORE11_FLIP
`endif
`ifdef OT_SFU_PSTORE11_MUT_FLIP
 `define OT_SFU_PSTORE11_FLIP
`endif
`ifdef OT_SFU_PSTORE11_FLIP
 assign compiler_control=o_ctl^1742'd1;   // bench negative control
`else
 assign compiler_control=o_ctl;
`endif
endmodule
`default_nettype wire
