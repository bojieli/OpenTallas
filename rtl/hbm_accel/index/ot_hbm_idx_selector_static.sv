`default_nettype none
// Fixed compiler-issued 5/5/6-bit radix schedule, Q4xW16 production shape. No ready,
// replay, queue, credit or variable-length scan. Owns 12 real 256x256 SRAMs.
// Opcodes: 0idle,1clear frame,2ingest,3hist clear,4hist scan,5choose bin,
// 6compact scan,7flush partial,8emit line. Bins scanned 31..0,31..0,63..0 for passes 0..2. Ingest fuses pass0 histogram.
//
// PIPELINED SUCCESSOR (H-NETLIST/IDXP-SEL 2026-10-16; gate hidx_sel_pr REFUSE: 55-level SRAM->compare->serial
// compaction->buf_q path, 13,468-load reset). Same arithmetic and selection, every stage <= ~20 levels:
//   q domain (clk_q[q]):  S0 op edge t: SRAM read issued.  S1 (t+1): SRAM rd_out registered (rawr).
//     S2 (t+2): orderkey compare vs threshold (gt/eq per lane) + parallel prefix rank of tie lanes.
//     S3 (t+3): tie-budget recurrence -> choose mask -> selected_line/selected_v register (stream to the link).
//     S4 (t+4): parallel prefix of the choose mask -> constant-index (one-hot AND-OR) dense packing; count.
//     S5 (t+5): dense line rotated by fill (4-level barrel) OR-merged into buf_q; full line -> write register.
//     S6 (t+6): registered SRAM write (pack line or op7 flush line).
//   histogram (q): H1 lane bin/match register (from in_line on op2, from rawr on op4), H2 per-bin 16-lane popcount
//     register, H3 hist += count (clear op3 registered one edge, applied in H3).
//   choose (ctl, clk_ctl): A hist[q][addr] read register (q domain), B 4-way sum + prefix sums, C rank recurrence /
//     threshold / found, D tie split (pass 2).  op3's found-clear rides the same A/B pipe.
// Constant latency changes the IDX compiler schedules (tools/hbm_idx_static_calendar.py SEL_CORE table):
//   +2 edges on the selected stream (selected_v/selected_line) -> link;  +2 drain edges after every op4 scan before
//   the first op5 (4 instead of 2);  op7 >= last op6 + 6 (was +2), op8 >= op7 + 2 (unchanged);  out_v +1 edge.
//   op2 ingest -> op5 drain unchanged (2); op5 -> next op3/op4/op6 spacing unchanged (1 idle).
// Reset: rst_n drives only ot_rst_relay (2 sync + 5 region flops on clk_ctl); regions 0..3 = quadrant control,
// 4 = ctl. Datapath registers (lines, histogram, pipeline payload) have no reset: op1/op3 clear what is used.
module ot_hbm_idx_selector_static_core #(parameter integer MUT=0)(
 input wire clk_ctl,input wire [3:0] clk_q,input wire [11:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [2367:0] in_line,
 output reg [3:0] out_v,output reg [2367:0] out_line,
 output wire [15:0] threshold_observe,
 output reg [3:0] selected_v,output reg [2367:0] selected_line,
 output wire [55:0] selected_observe,
 output reg fault
);
 localparam integer EW=37,W=16,LW=592;
 function automatic [15:0] orderkey(input [15:0] x);
  orderkey=x[15]?~x:(x^16'h8000);
 endfunction
 function automatic [15:0] pmask(input [1:0] p);
  pmask=(p==0)?16'd0:((p==1)?16'hf800:16'hffc0);
 endfunction
 function automatic [3:0] pshift(input [1:0] p);
  pshift=(p==0)?4'd11:((p==1)?4'd6:4'd0);
 endfunction
 function automatic [15:0] pbins(input [1:0] p);
  pbins=(p==2)?16'd63:16'd31;
 endfunction
 wire [4:0] rr_n;
 ot_rst_relay #(.REGIONS(5),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rr_n));
 wire rc_n=rr_n[4];
 reg [15:0] threshold;
 reg [13:0] rank_left;
 reg found;
 reg [13:0] ties[0:3];
 reg [13:0] selected[0:3];
 reg [3:0] qfault;
 wire [13:0] hrd[0:3];
 assign threshold_observe=threshold;
 // ---------------- ctl: choose-bin pipeline (A: hist read in q domain, B: sums, C: recurrence, D: ties) -------------
 reg a_v,a_clr;reg [1:0] a_pass;reg [5:0] a_addr;
 reg b_v,b_clr;reg [1:0] b_pass;reg [5:0] b_addr;reg [15:0] b_all;reg [15:0] b_s[0:3];reg [13:0] b_h[0:3];
 reg d_go;reg [13:0] d_r;reg [15:0] d_s[0:3];reg [13:0] d_h[0:3];
 always @(posedge clk_ctl or negedge rc_n)begin
  if(!rc_n)begin
   threshold<=0;rank_left<=0;found<=0;fault<=0;a_v<=0;a_clr<=0;b_v<=0;b_clr<=0;d_go<=0;
   for(integer q=0;q<4;q=q+1)ties[q]<=0;
  end else begin
   if(|qfault)fault<=1;
   a_v<=op==5;a_clr<=op==3;
   b_v<=a_v;b_clr<=a_clr;
   d_go<=0;
   if(op==1)begin threshold<=0;rank_left<={4'b0,k};found<=0;if(k>512||k==0)fault<=1;end
   if(b_clr)found<=0;
   if(b_v&&!found)begin
    if({2'b0,rank_left}>b_all)rank_left<=rank_left-b_all[13:0];
    else begin
     threshold<=(threshold&pmask(b_pass))|(16'(b_addr)<<pshift(b_pass));found<=1;
     if(b_pass==2)d_go<=1;
    end
   end
   if(d_go)for(integer q=0;q<4;q=q+1)begin
    if({2'b0,d_r}<=d_s[q])ties[q]<=0;
    else if({2'b0,d_r}-d_s[q]>={2'b0,d_h[q]})ties[q]<=d_h[q];
    else ties[q]<=14'({2'b0,d_r}-d_s[q]);
   end
   if((op==1&&(a_v||b_v))||(op==5&&(a_clr||b_clr)))fault<=1;
  end
 end
 always @(posedge clk_ctl)begin
  a_pass<=pass;a_addr<=addr[5:0];
  b_pass<=a_pass;b_addr<=a_addr;
  for(integer q=0;q<4;q=q+1)b_h[q]<=hrd[q];
  b_s[0]<=16'd0;b_s[1]<=16'(hrd[0]);b_s[2]<=16'(hrd[0])+16'(hrd[1]);
  b_s[3]<=(16'(hrd[0])+16'(hrd[1]))+16'(hrd[2]);
  b_all<=(16'(hrd[0])+16'(hrd[1]))+(16'(hrd[2])+16'(hrd[3]));
  d_r<=rank_left;
  for(integer q=0;q<4;q=q+1)begin d_s[q]<=b_s[q];d_h[q]<=b_h[q];end
 end
 // ---------------- quadrants ----------------
 for(genvar q=0;q<4;q=q+1)begin:gq
  wire rq_n=rr_n[q];
  wire re=op==4||op==6||op==8;
  wire [767:0] raw;
  // S0->S1 control
  reg rv;reg [3:0] rop;reg [1:0] rpass;reg [7:0] raddr;
  // S1
  reg s1_v;reg [3:0] s1_op;reg [1:0] s1_pass;reg [7:0] s1_addr;reg [LW-1:0] rawr;
  // S2
  reg s2_v;reg [7:0] s2_addr;reg [LW-1:0] s2_line;reg [15:0] s2_gt,s2_eq;reg [4:0] s2_er[0:15];reg [4:0] s2_ecnt;
  // S3 (selected_line holds the lanes + choose mask)
  reg s3_v;reg [7:0] s3_addr;
  // S4
  reg s4_v;reg [7:0] s4_addr;reg [LW-1:0] dense;reg [4:0] dcnt;
  // S5 / S6
  reg [LW-1:0] buf_q;reg [3:0] fill;(* keep *) reg [3:0] fill_rep[0:7];reg [5:0] wp;
  reg wreq;reg [5:0] wa_r;reg [LW-1:0] wreg;
  reg [13:0] tie_rem;reg comp_started;reg [19:0] last_id;
  // histogram
  reg [15:0] h1_m;reg [5:0] h1_bin[0:15];reg h1_v;
  reg [4:0] h2_cnt[0:63];reg h2_v;(* keep *) reg [7:0] hclr;
  reg [13:0] hist[0:63];
  reg [13:0] hrd_q;
  assign hrd[q]=hrd_q;
  wire we=op==2||wreq;
  wire [7:0] wa=(op==2)?addr:{2'd0,wa_r};
  wire [LW-1:0] wd=(op==2)?in_line[q*LW+:LW]:wreg;
  wire [767:0] wide_wd={176'd0,wd};
  assign selected_observe[q*14+:14]=selected[q];
  for(genvar m=0;m<3;m=m+1)begin:gm
   ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk_mem[q*3+m]),.r_ce_in(re),.r_addr_in(addr),.rd_out(raw[m*256+:256]),
    .w_ce_in(we),.w_addr_in(wa),.wd_in(wide_wd[m*256+:256]),.w_mask_in({256{1'b1}}),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
  end
  // ---- S2 combinational: compare + tie-lane prefix rank ----
  reg [15:0] c_gt,c_eq;reg [4:0] c_er[0:15];reg [4:0] c_run;reg [15:0] c_ky;
  always @*begin
   c_run=0;
   for(integer l=0;l<W;l=l+1)begin
    c_ky=orderkey(rawr[l*EW+1+:16]);
    c_gt[l]=rawr[l*EW]&&(c_ky>threshold);
    c_eq[l]=rawr[l*EW]&&(c_ky==threshold);
    if(MUT==1)begin c_gt[l]=rawr[l*EW]&&(c_ky>=threshold);c_eq[l]=0;end
    c_er[l]=c_run;c_run=c_run+5'(c_eq[l]);
   end
  end
  // ---- S3 combinational: tie budget -> choose mask ----
  wire [13:0] tavail=comp_started?tie_rem:ties[q];
  reg [15:0] c_choose;
  always @*for(integer l=0;l<W;l=l+1)c_choose[l]=s2_gt[l]||(s2_eq[l]&&({9'd0,s2_er[l]}<tavail));
  wire [13:0] tuse=({9'd0,s2_ecnt}<tavail)?{9'd0,s2_ecnt}:tavail;
  // ---- S4 combinational: prefix positions + one-hot dense pack ----
  reg [4:0] c_pos[0:15];reg [4:0] c_cnt;reg [LW-1:0] c_dense;
  always @*begin
   c_cnt=0;c_dense=0;
   for(integer l=0;l<W;l=l+1)begin c_pos[l]=c_cnt;c_cnt=c_cnt+5'(selected_line[q*LW+l*EW]);end
   for(integer i=0;i<W;i=i+1)for(integer l=i;l<W;l=l+1)
    if(selected_line[q*LW+l*EW]&&c_pos[l]==5'(i))c_dense[i*EW+:EW]=selected_line[q*LW+l*EW+:EW];
  end
  // ---- S5 combinational: rotate dense by fill (replicated selects), merge ----
  reg [2*LW-1:0] c_merged;reg [2*LW-1:0] c_sh;
  always @*begin
   for(integer g=0;g<8;g=g+1)begin
    c_sh={{LW{1'b0}},dense}<<(fill_rep[g]*EW);
    c_merged[g*(2*LW/8)+:(2*LW/8)]=c_sh[g*(2*LW/8)+:(2*LW/8)];
   end
   c_merged=c_merged|{{LW{1'b0}},buf_q};
  end
  wire [4:0] nf={1'b0,fill}+dcnt;
  // ---- histogram H1 combinational ----
  wire h_ing=op==2;
  wire h_scan=s1_v&&s1_op==4;
  wire [1:0] h_pass=h_ing?2'd0:s1_pass;
  wire [LW-1:0] h_src=h_ing?in_line[q*LW+:LW]:rawr;
  reg [15:0] c_hm;reg [5:0] c_hb[0:15];reg [15:0] c_hk;
  always @*for(integer l=0;l<W;l=l+1)begin
   c_hk=orderkey(h_src[l*EW+1+:16]);
   c_hm[l]=(h_ing||h_scan)&&h_src[l*EW]&&((c_hk&pmask(h_pass))==(threshold&pmask(h_pass)));
   c_hb[l]=6'((c_hk>>pshift(h_pass))&pbins(h_pass));
  end
  reg [4:0] c_hc[0:63];
  always @*for(integer b=0;b<64;b=b+1)begin
   c_hc[b]=0;for(integer l=0;l<W;l=l+1)c_hc[b]=c_hc[b]+5'(h1_m[l]&&h1_bin[l]==6'(b));
  end
  // ---- control registers (reset, region q) ----
  always @(posedge clk_q[q] or negedge rq_n)begin
   if(!rq_n)begin
    rv<=0;s1_v<=0;s2_v<=0;s3_v<=0;s4_v<=0;wreq<=0;fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;
    qfault[q]<=0;out_v[q]<=0;selected_v[q]<=0;last_id<=0;h1_m<=0;h1_v<=0;h2_v<=0;hclr<=0;
    for(integer g=0;g<8;g=g+1)fill_rep[g]<=0;
   end else begin
    rv<=re;s1_v<=rv;
    s2_v<=s1_v&&s1_op==6;
    s3_v<=s2_v;selected_v[q]<=s2_v;
    s4_v<=s3_v;
    out_v[q]<=s1_v&&s1_op==8;
    h1_m<=c_hm;h1_v<=h_ing||h_scan;h2_v<=h1_v;hclr<={8{op==3}};
    wreq<=0;
    if(op==1)begin fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;last_id<=0;for(integer g=0;g<8;g=g+1)fill_rep[g]<=0;end
    // S2: source id order (compaction scan)
    if(s1_v&&s1_op==6)for(integer l=0;l<W;l=l+1)if(rawr[l*EW])begin
     if((s1_addr!=0||l!=0)&&rawr[l*EW+17+:20]<=last_id)qfault[q]<=1;
     last_id<=rawr[l*EW+17+:20];
    end
    // S3: tie recurrence
    if(s2_v)begin comp_started<=1;tie_rem<=tavail-tuse;end
    // S4: count
    if(s3_v)begin selected[q]<=selected[q]+14'(c_cnt);if(int'(selected[q])+int'(c_cnt)>512)qfault[q]<=1;end
    // S5: merge / pack write request
    if(s4_v)begin
     if(nf>=16)begin
      wreq<=1;wa_r<=wp;wp<=wp+1;fill<=4'(nf-16);for(integer g=0;g<8;g=g+1)fill_rep[g]<=4'(nf-16);
      if({2'd0,wp}>s4_addr)qfault[q]<=1; // never overwrite an unread source line
     end else begin fill<=nf[3:0];for(integer g=0;g<8;g=g+1)fill_rep[g]<=nf[3:0];end
    end
    // op7 flush (live edge): queue the partial line through the same write register
    if(op==7&&fill!=0)begin wreq<=1;wa_r<=wp;wp<=wp+1;fill<=0;for(integer g=0;g<8;g=g+1)fill_rep[g]<=0;end
    // schedule hazards the compiler must never issue
    if(op==2&&(rv&&rop==6||s1_v&&s1_op==6||s2_v||s3_v||s4_v||wreq))qfault[q]<=1;
    if(op==7&&(rv&&rop==6||s1_v&&s1_op==6||s2_v||s3_v||s4_v))qfault[q]<=1;
    if(op==3&&(rv&&rop==4||s1_v&&s1_op==4||h1_v||h2_v))qfault[q]<=1;
   end
  end
  // ---- datapath registers (no reset) ----
  always @(posedge clk_q[q])begin
   rop<=op;rpass<=pass;raddr<=addr;
   s1_op<=rop;s1_pass<=rpass;s1_addr<=raddr;rawr<=raw[LW-1:0];
   s2_addr<=s1_addr;s2_line<=rawr;s2_gt<=c_gt;s2_eq<=c_eq;s2_ecnt<=c_run;for(integer l=0;l<W;l=l+1)s2_er[l]<=c_er[l];
   s3_addr<=s2_addr;
   for(integer l=0;l<W;l=l+1)begin
    selected_line[q*LW+l*EW+:EW]<=s2_line[l*EW+:EW];selected_line[q*LW+l*EW]<=s2_v&&c_choose[l];
   end
   s4_addr<=s3_addr;dense<=c_dense;dcnt<=s3_v?c_cnt:5'd0;
   if(op==1)buf_q<=0;
   else if(op==7)buf_q<=0;
   else if(s4_v)buf_q<=(nf>=16)?c_merged[2*LW-1:LW]:c_merged[LW-1:0];
   if(op==7)wreg<=buf_q;
   else if(s4_v)wreg<=c_merged[LW-1:0];
   // emit (S2 from the registered read)
   if(s1_v&&s1_op==8)for(integer l=0;l<W;l=l+1)begin
    out_line[q*LW+l*EW+:EW]<=rawr[l*EW+:EW];
    out_line[q*LW+l*EW]<=((int'(s1_addr)*16+l)<int'(selected[q]));
    if(MUT==2&&s1_addr==0&&l==0)out_line[q*LW+l*EW+17+:20]<=rawr[l*EW+17+:20]^20'd1;
   end
   // histogram
   for(integer l=0;l<W;l=l+1)h1_bin[l]<=c_hb[l];
   for(integer b=0;b<64;b=b+1)h2_cnt[b]<=c_hc[b];
   for(integer b=0;b<64;b=b+1)hist[b]<=hclr[b/8]?14'd0:hist[b]+(h2_v?14'(h2_cnt[b]):14'd0);
   hrd_q<=hist[addr[5:0]];
  end
 end
endmodule
`default_nettype wire
`default_nettype none
// ---------------------------------------------------------------------------
// PIN-REGISTERED TILE (OWNER RULE 19:50 PT 10-15, H-NETLIST/idxreg 2026-10-16): the die
// master ot_hbm_idx_selector_static is this shell. Every data input and every output passes ONE kept
// flop at the pin (clocks pass through; rst_n enters the core's ot_rst_relay); the pipelined arithmetic/control is
// ot_hbm_idx_selector_static_core (core latencies: see its header). Latency: +1 edge on every input, +1 edge on every output; the IDX
// calendar compiler (tools/hbm_idx_static_calendar.py, PIN table) schedules them.
// Pin flops have no reset (as physical/common_flow/ot_pin_regs.tcl); the core's control registers are reset by region.
// One data clock for every pin flop: clk_ctl (the die's typed control clock, E face); the core's clk_q[q]
// quadrant roots and clk_mem[] SRAM entries are same-PLL phase-0 roots (related_same_frequency STA).
module ot_hbm_idx_selector_static #(parameter integer MUT=0)(
 input wire clk_ctl,input wire [3:0] clk_q,input wire [11:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [2367:0] in_line,
 output reg [3:0] out_v,output reg [2367:0] out_line,
 output reg [15:0] threshold_observe,
 output reg [3:0] selected_v,output reg [2367:0] selected_line,
 output reg [55:0] selected_observe,
 output reg fault
);
 // rst_n: the port drives only the core's ot_rst_relay (2 sync + 5 region flops on clk_ctl; async assert, 3-edge
 // release). No port net reaches a data pin or a region's flops directly (gate hidx_sel_pr: 13,468-load reset net).
 wire rst_core_n=rst_n;
 (* keep *) reg [3:0] op_r;(* keep *) reg [1:0] pass_r;(* keep *) reg [7:0] addr_r;(* keep *) reg [9:0] k_r;
 (* keep *) reg [2367:0] in_r;
 wire [3:0] c_out_v,c_sel_v;wire [2367:0] c_out_line,c_sel_line;wire [15:0] c_thr;wire [55:0] c_obs;wire c_fault;
 always @(posedge clk_ctl)begin
  op_r<=op;pass_r<=pass;addr_r<=addr;k_r<=k;in_r<=in_line;
  out_v<=c_out_v;out_line<=c_out_line;threshold_observe<=c_thr;
  selected_v<=c_sel_v;selected_line<=c_sel_line;selected_observe<=c_obs;fault<=c_fault;
 end
 ot_hbm_idx_selector_static_core #(.MUT(MUT)) core(.clk_ctl(clk_ctl),.clk_q(clk_q),.clk_mem(clk_mem),.rst_n(rst_core_n),
  .op(op_r),.pass(pass_r),.addr(addr_r),.k(k_r),.in_line(in_r),.out_v(c_out_v),.out_line(c_out_line),
  .threshold_observe(c_thr),.selected_v(c_sel_v),.selected_line(c_sel_line),.selected_observe(c_obs),.fault(c_fault));
endmodule
`default_nettype wire
