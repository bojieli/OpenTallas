`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_programme_store_r9 (SFU-STORE-9 2026-10-17): the r7c programme store rebuilt as a small top over FOUR
// hardened bank leaves (ot_hgi_sfu_store_leaf3_r9 x3 = programme stripes 0-2, 3-5 and IO stripes 0-2;
// ot_hgi_sfu_store_leaf2_r9 x1 = programme stripes 6-7). Structural fix for r7c4 native FAIL (capture 222.0 ps on
// cfg_we: one control pin broadcast to 22 SRAMs over 1 mm on one root): every top input pin feeds ONE plain flop;
// configuration reaches each leaf through ONE registered per-leaf hop (h_*), then the leaf's own pin flops; reset
// qualification is folded in front of the leaf pins; each leaf has its own clock root and stage-B reset relays.
// PRICED CYCLES vs r7c: io_word / compiler_control D = 4, status 2, reset release 4 edges -- unchanged.
// Configuration write path +1 edge (per-leaf hop): an SRAM row is written one edge later; writes still stream one per
// edge. Host contract: the first start (io_start_v) must be sampled >= 2 edges after the last configuration write
// (r7c: >= 1); the canonical programme load leaves 4. Programme load is once per calendar load, so the per-token cost
// is 0 cycles.
// Exactness notes: the leaves check W=222; the narrower stripes (programme stripe 7 W=188, IO stripe 2 W=27) get the
// remaining captured[221:W]==0 term here, exactly: a nonzero high field zeroes that stripe's word on the same edge and
// enters its fault on the same edge (nb_now gated by the delayed stripe reset) and stays sticky (nb_s). Ordinal
// agreement uses the leaf mismatch bits plus leaf-first-stripe ordinals (equivalent to every stripe vs stripe 0 under
// the valid-agreement term). The output gate by control_v is retimed (ungated relay, registered control_v at the
// output register): identical outputs on every edge.
module ot_hgi_sfu_programme_store_r9 #(
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
 output reg [470:0] io_word,
 output reg [1741:0] compiler_control,
 output reg fault
);
 initial if(PAGE_AW!=1)$fatal(1,"programme store r9: PAGE_AW=1 only (22 SRAMs)");
 // ---- top pin flops: pure (pin -> D), one copy each
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
 // ---- synchronous regional reset tree: 2-flop sync -> stage A (one relay per leaf + one for the top) -> stage B
 reg rs1,rs2;
 always @(posedge clk)begin rs1<=rst_n;rs2<=rs1;end
 (* keep = "true", dont_touch = "true" *) reg [3:0] ra_leaf;   // 0 P0, 1 P1, 2 P2, 3 IO -> leaf rst_a
 (* keep = "true", dont_touch = "true" *) reg ra_top;
 always @(posedge clk)begin ra_leaf<={4{rs2}};ra_top<=rs2;end
 (* keep = "true", dont_touch = "true" *) reg [3:0] rb;        // 0 status/pin, 1 IO calendar, 2 programme calendar, 3 leaf strobes
 (* keep = "true", dont_touch = "true" *) reg rbd1,rbd2;       // rb delayed 1 / 2 (pin-flop and strobe qualification)
 always @(posedge clk)begin rb<={4{ra_top}};rbd1<=rb[3];rbd2<=rbd1;end
 // ---- one registered configuration hop per leaf (+1 edge on the configuration-write path only)
 (* keep = "true", dont_touch = "true" *) reg [2:0] h_we;      // programme leaves 0..2
 (* keep = "true", dont_touch = "true" *) reg [2:0] h_st[0:2];
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] h_addr[0:2];
 (* keep = "true", dont_touch = "true" *) reg [255:0] h_data[0:2];
 (* keep = "true", dont_touch = "true" *) reg hio_we;
 (* keep = "true", dont_touch = "true" *) reg [1:0] hio_st;
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] hio_addr;
 (* keep = "true", dont_touch = "true" *) reg [255:0] hio_data;
 always @(posedge clk)begin
  for(integer l=0;l<3;l=l+1)begin h_we[l]<=p_cfg_we;h_st[l]<=p_cfg_stripe;h_addr[l]<=p_cfg_addr;h_data[l]<=p_cfg_data;end
  hio_we<=p_io_cfg_we;hio_st<=p_io_cfg_stripe;hio_addr<=p_io_cfg_addr;hio_data<=p_io_cfg_data;
 end
 wire wq=rbd1&rbd2;    // = the r7c pin-flop reset AND and stripe strobe reset, one edge later (uniform +1)
 wire [7:0] p_we;
 for(genvar s=0;s<8;s=s+1)begin:g_pwe
`ifdef OT_SFU_PSTORE9_MUT_CFGDROP
  assign p_we[s]=(s/3==1)?1'b0:(wq && h_we[s/3] && h_st[s/3]==s);   // MUTANT: leaf P1 configuration hop dropped
`else
  assign p_we[s]=wq && h_we[s/3] && h_st[s/3]==s;
`endif
 end
 wire [2:0] io_we;
 for(genvar s=0;s<3;s=s+1)begin:g_iowe
  assign io_we[s]=wq && hio_we && hio_st==s;
 end
 // ---- launch arguments, precomputed in front of the leaf pins (r7c computed them in front of the stripe registers)
 wire p_legal=p_start_limit>{1'b0,p_start_base} && p_start_limit<=(1<<AW) && p_start_loops!=0;
 wire [AW:0] p_span=p_start_limit-{1'b0,p_start_base};
 wire p_lone=p_start_loops==16'd1;
 wire io_legal=p_io_start_limit>{1'b0,p_io_start_base} && p_io_start_limit<=(1<<AW) && p_io_start_loops!=0;
 wire [AW:0] io_span=p_io_start_limit-{1'b0,p_io_start_base};
 wire io_lone=p_io_start_loops==16'd1;
 wire io_sv=rb[1] && rbd1 && p_io_start_v;      // r7c: rb(stripe) & r_io_start_v (= rb_pin delayed & pin)
 // ---- leaves
 wire [665:0] cal0,cal1,calio;
 wire [443:0] cal2;
 wire [2:0] v0,a0,d0,f0,v1,a1,d1,f1,vio,aio,dio,fio;
 wire [1:0] v2,a2,d2,f2;
 wire [31:0] o0,o1,o2,oio;
 wire [2:1] m0,m1,mio;
 wire m2;
 wire io470;
 wire p_sv=rb[2] && io470;                       // r7c: rb(stripe) & io[470]
 // r9c data-port split (lo = SRAM A-edge bits 0..135, hi = B-edge bits 136..255); MUT_SPLIT rotates leaf P0's high half
`ifdef OT_SFU_PSTORE9_MUT_SPLIT
 wire [119:0] p0_hi={h_data[0][136],h_data[0][255:137]};   // MUTANT: high-half bits misrouted by one
`else
 wire [119:0] p0_hi=h_data[0][255:136];
`endif
 ot_hgi_sfu_store_leaf3_r9 #(.PAGE_AW(PAGE_AW)) u_leaf_p0(.clk(clk),.rst_a(ra_leaf[0]),.in_we(p_we[2:0]),.in_addr(h_addr[0]),
  .in_data_lo(h_data[0][135:0]),.in_data_hi(p0_hi),.in_start_v(p_sv),.in_start_base(p_start_base),.in_legal(p_legal),.in_span(p_span),
  .in_loops(p_start_loops),.in_loops_one(p_lone),.out_cal0(cal0[0+:222]),.out_cal1(cal0[222+:222]),.out_cal2(cal0[444+:222]),.out_v(v0),.out_active(a0),.out_done(d0),
  .out_fault(f0),.out_ord(o0),.out_mm(m0));
 ot_hgi_sfu_store_leaf3_r9 #(.PAGE_AW(PAGE_AW)) u_leaf_p1(.clk(clk),.rst_a(ra_leaf[1]),.in_we(p_we[5:3]),.in_addr(h_addr[1]),
  .in_data_lo(h_data[1][135:0]),.in_data_hi(h_data[1][255:136]),.in_start_v(p_sv),.in_start_base(p_start_base),.in_legal(p_legal),.in_span(p_span),
  .in_loops(p_start_loops),.in_loops_one(p_lone),.out_cal0(cal1[0+:222]),.out_cal1(cal1[222+:222]),.out_cal2(cal1[444+:222]),.out_v(v1),.out_active(a1),.out_done(d1),
  .out_fault(f1),.out_ord(o1),.out_mm(m1));
 ot_hgi_sfu_store_leaf2_r9 #(.PAGE_AW(PAGE_AW)) u_leaf_p2(.clk(clk),.rst_a(ra_leaf[2]),.in_we(p_we[7:6]),.in_addr(h_addr[2]),
  .in_data_lo(h_data[2][135:0]),.in_data_hi(h_data[2][255:136]),.in_start_v(p_sv),.in_start_base(p_start_base),.in_legal(p_legal),.in_span(p_span),
  .in_loops(p_start_loops),.in_loops_one(p_lone),.out_cal0(cal2[0+:222]),.out_cal1(cal2[222+:222]),.out_v(v2),.out_active(a2),.out_done(d2),
  .out_fault(f2),.out_ord(o2),.out_mm(m2));
 ot_hgi_sfu_store_leaf3_r9 #(.PAGE_AW(PAGE_AW)) u_leaf_io(.clk(clk),.rst_a(ra_leaf[3]),.in_we(io_we),.in_addr(hio_addr),
  .in_data_lo(hio_data[135:0]),.in_data_hi(hio_data[255:136]),.in_start_v(io_sv),.in_start_base(p_io_start_base),.in_legal(io_legal),.in_span(io_span),
  .in_loops(p_io_start_loops),.in_loops_one(io_lone),.out_cal0(calio[0+:222]),.out_cal1(calio[222+:222]),.out_cal2(calio[444+:222]),.out_v(vio),.out_active(aio),.out_done(dio),
  .out_fault(fio),.out_ord(oio),.out_mm(mio));
 // ---- narrow-stripe W check (programme stripe 7: W=188; IO stripe 2: W=27)
 wire nb7_now=|cal2[222+188+:34];
 wire nbio_now=|calio[444+27+:195];
 reg nb7_s,nbio_s;
 always @(posedge clk)begin
  nb7_s<=rb[2] && ((rbd1 && nb7_now) || nb7_s);
  nbio_s<=rb[1] && ((rbd1 && nbio_now) || nbio_s);
 end
 // ---- calendar aggregation (as ot_hgi_sfu_calendar_paged_rc / ot_hgi_sfu_io_calendar_rc)
 wire [1741:0] pwords={nb7_now?188'd0:cal2[222+:188],cal2[0+:222],cal1,cal0};
 wire [470:0] iowords={nbio_now?27'd0:calio[444+:27],calio[0+:444]};
 wire [7:0] pv={v2,v1,v0},pa={a2,a1,a0},pd={d2,d1,d0};
 wire [7:0] pf={f2[1]|(rbd1&&nb7_now)|nb7_s,f2[0],f1,f0};
 wire [2:0] iof={fio[2]|(rbd1&&nbio_now)|nbio_s,fio[1:0]};
 wire p_cv=(&pv) && !(|pf);
 wire io_cv=(&vio) && !(|iof);
 assign io470=io_cv && iowords[470];
 wire [7:0] pmm={m2|(o2!=o0),o2!=o0,m1[2]|(o1!=o0),m1[1]|(o1!=o0),o1!=o0,m0[2],m0[1],1'b0};
 wire p_dis=(|pv && !(&pv)) || (|pd && !(&pd)) || (|pa && !(&pa)) || |(pv&pmm);
 wire io_dis=(|vio && !(&vio)) || (|dio && !(&dio)) || (|aio && !(&aio)) || |(vio[2:1]&mio);
 reg p_fault,io_fault;
 always @(posedge clk)begin
  if(!rb[2])p_fault<=0; else if(p_dis || |pf)p_fault<=1;
  if(!rb[1])io_fault<=0; else if(io_dis || |iof)io_fault<=1;
 end
 // ---- relay stage (ungated) + gated output registers (retimed control_v gate; identical outputs)
 reg [470:0] io_p;
 reg [1741:0] ctl_p;
 (* keep = "true", dont_touch = "true" *) reg [3:0] p_cv_d;
 (* keep = "true", dont_touch = "true" *) reg io_cv_d;
 always @(posedge clk)begin
  io_p<=iowords;ctl_p<=pwords;p_cv_d<={4{p_cv}};io_cv_d<=io_cv;
  io_word<=io_cv_d?io_p:471'd0;
`ifdef OT_SFU_PSTORE_MUT_FLIP
  compiler_control<={p_cv_d[3]?ctl_p[1741:1306]:436'd0,p_cv_d[2]?ctl_p[1305:871]:435'd0,
                     p_cv_d[1]?ctl_p[870:436]:435'd0,p_cv_d[0]?ctl_p[435:0]:436'd0}^1742'd1;   // bench negative control
`else
  compiler_control<={p_cv_d[3]?ctl_p[1741:1306]:436'd0,p_cv_d[2]?ctl_p[1305:871]:435'd0,
                     p_cv_d[1]?ctl_p[870:436]:435'd0,p_cv_d[0]?ctl_p[435:0]:436'd0};
`endif
 end
 always @(posedge clk)
  if(!rb[0])begin
   io_active<=0;io_done<=0;io_ordinal<=0;programme_active<=0;programme_done<=0;programme_ordinal<=0;fault<=0;
  end else begin
   io_active<=|aio;io_done<=&dio;io_ordinal<=oio;
   programme_active<=|pa;programme_done<=&pd;programme_ordinal<=o0;
   if(io_fault||p_fault)fault<=1;
  end
endmodule
`default_nettype wire
