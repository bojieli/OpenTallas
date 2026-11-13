`timescale 1ns/1ps
// KV-PVFIN-1 2026-11-13 (R-CAP-3.3, DIE-KV-100 06:13 ASK / kv3_hub_C split): qkd_pv_fin_s cut into 2 LANE-SLICED hard cores.
//
// qkd_pv_fin_s8 = one slice: NL (8) of the 16 fp32 lanes of qkd_pv_fin_s, with the WHOLE control (calendar, slot checks,
// sticky fault) of qkd_pv_fin_s replicated in each slice, so the two slices step in lock-step on the same pins.
// qkd_pv_fin_s2x8 = the drop-in pair with the exact port list of qkd_pv_fin_s: slice lo = lanes 0..7 (data bits
// [255:0]), slice hi = lanes 8..15 ([511:256]); out_valid = lo & hi, fault = lo | hi, out_beat / out_epoch = lo's.
// IN_STAGE 1 (the kit form; R-RTL-6 parameter, default 0) = +1 ADDED CYCLE (declared, results/kv-pvfin-1/latency_rows.json):
// every input lands in a flop at the pin (stage i), then
// the pin registers of qkd_pv_fin_s (stage q); every output is a flop; beat b leaves PRODUCT_AGE + 2 + b edges after the
// start pin edge (qkd_pv_fin_s: + 1 + b), and fault / out_valid / out_beat / out_epoch / out_data are those of
// qkd_pv_fin_s one edge later.  The inside is re-timed (R-RTL-5 (1) restructure + (2) retime) and (3) one input stage
// was added because the calendar decode cannot sit behind the 487 ps link-budget input delay.  The unsliced pvfin_h3 build (epyc7 kvhubc-core1, 11-12) failed setup at -381 ps on
// out_epoch[3] (placement -448 ps: ep -> 16-b compare -> OR trees -> bad -> 1,145 ps of enable fan-out) and on ~20k
// endpoints (the sbuf write enables behind the window compares), because every slot of the static calendar was a
// combinational 16-bit window compare of age + 1 against adder-derived ages, re-evaluated each cycle and ANDed into
// `bad`, the state enables and the 16,384 sbuf enables.  Here:
//   * the calendar is decoded from the stage-i cal flops into registers (cq_*: the same values qkd_pv_fin_s derives
//     from cal_q every cycle), and latched at the accepted start edge (window / end / beat-offset registers);
//   * every slot (p0, p1, r, add, sum, mul, product) is a FLAG register kept equal to active && win(n, X) by its
//     set (n + 1 == X) / clear (n + 1 == X + 32) edges, so `bad`, the state enables and the sbuf write enable start at
//     flops (no adder, no magnitude compare in the cycle);
//   * the beat indices n - P0, n - P1, n - PRODUCT_AGE and the sbuf write / read pointers are 5-bit counters equal to
//     5'(n - X) (the only 5 bits qkd_pv_fin_s uses);
//   * the 32:1 sbuf read and the reciprocal-head select move one edge earlier into the multiplier operand registers
//     (rd_q / rzh_q) with a write-through bypass for the beat written at the same edge (MUL_AGE = SUM_AGE + 1 when
//     R <= LASTP), so the multiplier inputs are flops instead of a 32:1 mux behind a 512-load pointer.
// Equivalence (lock-step at the declared +1 edge, every reset): rtl/test/qwen_split/tb_qkd_pv_fin_s2x8.sv runs
// qkd_pv_fin_s2x8 against the unsliced qkd_pv_fin_s on the same pins (healthy commands in the three STRETCH regimes, random calendars incl.
// unmeetable ones, off-slot / wrong-beat / wrong-epoch / missing inputs, starts while active, NaN / overflow operands,
// warm resets): out_valid and fault equal at every edge; out_beat / out_epoch equal at every edge outside a fault (until
// the next reset), out_data at every edge outside a fault (until the next product beat; it has no reset in either design),
// and all of them on every out_valid beat.  After a fault raised by ONE slice's own lanes (fp err / unit valid) the other
// slice's payload registers may still move with out_valid low (qkd_pv_fin_s holds them): the payload is qualified by
// out_valid, which is identical.  MUT (bench negative controls, as qkd_pv_fin_s): 1 head index (b + 1) / 8, 2 pair-0
// operand one tap late, 3 R left out of the join age.
module qkd_pv_fin_s8 #(
 parameter integer ADD_LAT=7,
 parameter integer MUL_LAT=6,
 parameter integer SKEW=2,
 parameter integer MUT=0,
 parameter integer NL=8,
 parameter integer IN_STAGE=0
)(
 input wire ck,rst_n,
 input wire start,input wire [15:0] epoch,input wire [47:0] cal,
 input wire p0_valid,input wire [4:0] p0_beat,input wire [15:0] p0_epoch,input wire [32*NL-1:0] p0_data,
 input wire p1_valid,input wire [4:0] p1_beat,input wire [15:0] p1_epoch,input wire [32*NL-1:0] p1_data,
 input wire rz_valid,input wire [15:0] rz_epoch,input wire [127:0] rz,
 output reg out_valid,output reg [4:0] out_beat,output reg [15:0] out_epoch,output reg [32*NL-1:0] out_data,
 output reg fault
);
 localparam integer DW=32*NL;
 // ---------------- pin registers (as qkd_pv_fin_s) ----------------
 // stage i (IN_STAGE 1: +1 cycle): EVERY input lands in a flop at the pin.  The s8c build (52cf3da09d) decoded the
 // calendar from the raw cal pins (c0 > c1 -> max -> + ADD/MUL ages -> 17-bit compare) behind the 487 ps link-budget input
 // delay: post-CTS setup -304 ps at cq_bad / cq_em.  Now cq_* = f(cal_i), flop to flop, and the whole command (beats,
 // epochs, reciprocals, start) is uniformly one edge later than qkd_pv_fin_s.
 // IN_STAGE (R-RTL-6 parameter, default 0 = the 0-cycle form, flop for flop): the hub_C kit / plan type set IN_STAGE 1.
 wire start_i,p0_valid_i,p1_valid_i,rz_valid_i;wire [15:0] epoch_i,p0_epoch_i,p1_epoch_i,rz_epoch_i;wire [47:0] cal_i;
 wire [4:0] p0_beat_i,p1_beat_i;wire [DW-1:0] p0_data_i,p1_data_i;wire [127:0] rz_i;
 generate if(IN_STAGE!=0)begin:g_in
  reg sv,v0,v1,vr;reg [15:0] e,e0,e1,er;reg [47:0] c;reg [4:0] b0,b1;reg [DW-1:0] d0,d1;reg [127:0] r;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin sv<=0;v0<=0;v1<=0;vr<=0;end
   else begin sv<=start;v0<=p0_valid;v1<=p1_valid;vr<=rz_valid;end
  always @(posedge ck)begin e<=epoch;c<=cal;b0<=p0_beat;b1<=p1_beat;e0<=p0_epoch;e1<=p1_epoch;er<=rz_epoch;
   d0<=p0_data;d1<=p1_data;r<=rz;end
  assign start_i=sv,p0_valid_i=v0,p1_valid_i=v1,rz_valid_i=vr,epoch_i=e,cal_i=c,p0_beat_i=b0,p1_beat_i=b1;
  assign p0_epoch_i=e0,p1_epoch_i=e1,rz_epoch_i=er,p1_data_i=d1,rz_i=r;
`ifdef OT_PVFIN_S8_MUTANT_ROWSHORT
  assign p0_data_i=p0_data;                 // R-RTL-6 mutant: pair-0 data not moved with its valid / beat (a row short)
`else
  assign p0_data_i=d0;
`endif
 end else begin:g_in0
  assign start_i=start,p0_valid_i=p0_valid,p1_valid_i=p1_valid,rz_valid_i=rz_valid,epoch_i=epoch,cal_i=cal;
  assign p0_beat_i=p0_beat,p1_beat_i=p1_beat,p0_epoch_i=p0_epoch,p1_epoch_i=p1_epoch,rz_epoch_i=rz_epoch;
  assign p0_data_i=p0_data,p1_data_i=p1_data,rz_i=rz;
 end endgenerate
 // stage q (the pin registers of qkd_pv_fin_s)
 reg start_q,p0v_q,p1v_q,rzv_q;reg [15:0] epoch_q,p0e_q,p1e_q,rze_q;reg [4:0] p0b_q,p1b_q;reg [127:0] rz_q;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin start_q<=0;p0v_q<=0;p1v_q<=0;rzv_q<=0;end
  else begin start_q<=start_i;p0v_q<=p0_valid_i;p1v_q<=p1_valid_i;rzv_q<=rz_valid_i;end
 always @(posedge ck)begin epoch_q<=epoch_i;p0b_q<=p0_beat_i;p1b_q<=p1_beat_i;p0e_q<=p0_epoch_i;p1e_q<=p1_epoch_i;
  rze_q<=rz_epoch_i;rz_q<=rz_i;end
 // ---------------- calendar decode: cq_* = f(cal_q) of qkd_pv_fin_s, registered from the stage-i cal flops ----------------
 wire [15:0] c0=cal_i[15:0],c1=cal_i[31:16],cr=cal_i[47:32];
 wire g01=c0>c1;
 wire [15:0] lp=g01?c0:c1;                                       // LASTP of the new command
 wire lp_gt_r=g01?(c0>cr):(c1>cr);
 wire [15:0] cl=(MUT==3||lp_gt_r)?lp:cr;                          // max(P0, P1, R)
 wire [15:0] csk=g01?(c0-c1):(c1-c0);
 wire cbad=(c0<16'd1)||(c1<16'd1)||(cr<16'd1)||(csk>16'(SKEW))||({1'b0,cl}+17'd64+17'(ADD_LAT+MUL_LAT)>17'hffff);
 wire [15:0] d0=lp-c0,d1=lp-c1;
 wire [15:0] d0m=(MUT==2&&d0<SKEW)?d0+16'd1:d0;
 wire [15:0] xadd=lp+16'd1,xsum=lp+16'd1+16'(ADD_LAT),xmul=cl+16'(ADD_LAT+2),xprod=cl+16'(ADD_LAT+2+MUL_LAT);
 function automatic win(input [15:0] x,input [15:0] lo);win=(x>=lo)&&(x<lo+16'd32);endfunction
 // per window X: g = X - 1 (set when n == g), e = X + 31 (clear when n == e), i = win(1, X) (flag on the start edge)
 reg cq_bad;reg [7:0] cq_s0,cq_s1;
 reg [15:0] cq_g0,cq_e0,cq_g1,cq_e1,cq_gr,cq_ga,cq_ea,cq_gs,cq_es,cq_gm,cq_em,cq_gp,cq_ep;
 reg cq_i0,cq_i1,cq_ir,cq_ia,cq_is,cq_im,cq_ip;
 reg [4:0] cq_b0,cq_b1,cq_bs,cq_bq,cq_bp;
 always @(posedge ck)begin
  cq_bad<=cbad;cq_s0<=d0m[7:0]+8'd1;cq_s1<=d1[7:0]+8'd1;
  cq_g0<=c0-16'd1;cq_e0<=c0+16'd31;cq_i0<=win(16'd1,c0);
  cq_g1<=c1-16'd1;cq_e1<=c1+16'd31;cq_i1<=win(16'd1,c1);
  cq_gr<=cr-16'd1;cq_ir<=(cr==16'd1);
  cq_ga<=xadd-16'd1;cq_ea<=xadd+16'd31;cq_ia<=win(16'd1,xadd);
  cq_gs<=xsum-16'd1;cq_es<=xsum+16'd31;cq_is<=win(16'd1,xsum);
  cq_gm<=xmul-16'd1;cq_em<=xmul+16'd31;cq_im<=win(16'd1,xmul);
  cq_gp<=xprod-16'd1;cq_ep<=xprod+16'd31;cq_ip<=win(16'd1,xprod);
  cq_b0<=5'(16'd1-c0);cq_b1<=5'(16'd1-c1);cq_bs<=5'(16'd1-xsum);cq_bq<=5'(16'd2-xmul);cq_bp<=5'(16'd1-xprod);
 end
 // ---------------- command state ----------------
 // n = age + 1 of qkd_pv_fin_s; the window registers hold the latched calendar; f_* = active && win(n, X)
 reg active;reg [15:0] n,ep;
 reg [15:0] g0,e0,g1,e1,gr,ga,ea,gs,es,gm,em,gp,epd;
 reg f_p0,f_p1,f_r,f_add,f_sum,f_mul,f_prod;
 reg [4:0] b_p0,b_p1,b_sum,b_q,b_prod;                            // 5'(n - P0), 5'(n - P1), wptr, rptr + 1, 5'(n - PRODUCT_AGE)
 reg [7:0] s0,s1;                                                  // operand tap index (D0m + 1, D1 + 1)
 // ---------------- operand lines, sum buffer, multiplier operand registers ----------------
 reg [DW-1:0] t0[0:SKEW+1],t1[0:SKEW+1];
 integer k;
 always @(posedge ck)begin
  t0[0]<=p0_data_i;t1[0]<=p1_data_i;
  for(k=1;k<=SKEW+1;k=k+1)begin t0[k]<=t0[k-1];t1[k]<=t1[k-1];end
 end
 wire [DW-1:0] opa=t0[s0],opb=t1[s1];
 // sbuf is a FLAT vector, never an array: yosys memory_dff folded rd_q into a sync read port of an inferred sbuf memory and
 // memory_map then registered the ADDRESS (b_q) and put the 32:1 x 256-bit mux AFTER the flop, in front of the multiplier
 // S1 logic (s8a post-place WC -480 ps, b_q copy -> sbuf mux -> u_mul a_n -> u_c1).  A flat vector keeps rd_q a data register.
 reg [32*DW-1:0] sbuf;reg [127:0] rzr;
 reg [DW-1:0] rd_q;reg [31:0] rzh_q;                               // = sbuf[rptr] / rzh of qkd_pv_fin_s, one edge early
 wire [DW-1:0] sum,product;wire [NL-1:0] av,mv;wire [2*NL-1:0] ae,me;
 genvar l;
 generate for(l=0;l<NL;l=l+1)begin:g_lane
  ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add(.clk(ck),.rst_n(rst_n),.valid_in(f_add&&!fault),
   .a(opa[32*l+:32]),.b(opb[32*l+:32]),.y(sum[32*l+:32]),.err(ae[2*l+:2]),.valid_out(av[l]));
  ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_mul(.clk(ck),.rst_n(rst_n),.valid_in(f_mul&&!fault),
   .a(rd_q[32*l+:32]),.b(rzh_q),.y(product[32*l+:32]),.err(me[2*l+:2]),.valid_out(mv[l]));
 end endgenerate
 wire bad=(p0v_q!=f_p0)||(p1v_q!=f_p1)||(rzv_q!=f_r)||
          (f_p0&&(p0b_q!=b_p0||p0e_q!=ep))||(f_p1&&(p1b_q!=b_p1||p1e_q!=ep))||(f_r&&rze_q!=ep)||
          (av!={NL{f_sum}})||(mv!={NL{f_prod}})||(f_sum&&|ae)||(f_prod&&|me);
 // next flag on a healthy step: win(n + 1, X) = (win(n, X) && n + 1 != X + 32) || n + 1 == X  (no wrap: the start
 // check bounds every accepted window end by 0xffff - 30; n + 1 <= PRODUCT_AGE + 32)
 wire last=(n==epd);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin active<=0;n<=16'd1;ep<=0;fault<=0;out_valid<=0;out_beat<=0;out_epoch<=0;
   {f_p0,f_p1,f_r,f_add,f_sum,f_mul,f_prod}<=7'd0;
   // the reset calendar of qkd_pv_fin_s (P0 = P1 = R = MUL_AGE = 0xffff, n = 1)
   b_p0<=5'(16'd1-16'hffff);b_p1<=5'(16'd1-16'hffff);b_sum<=0;b_q<=5'd1;b_prod<=5'(16'd1-(16'hffff+16'(MUL_LAT)));
   s0<=(MUT==2&&SKEW>0)?8'd2:8'd1;s1<=8'd1;
   g0<=0;e0<=0;g1<=0;e1<=0;gr<=0;ga<=0;ea<=0;gs<=0;es<=0;gm<=0;em<=0;gp<=0;epd<=0;
  end else begin
   out_valid<=0;
   if(start_q)begin
    if(active||cq_bad)begin fault<=1;active<=0;{f_p0,f_p1,f_r,f_add,f_sum,f_mul,f_prod}<=7'd0;end
    else begin
     active<=1;n<=16'd1;ep<=epoch_q;
     g0<=cq_g0;e0<=cq_e0;g1<=cq_g1;e1<=cq_e1;gr<=cq_gr;ga<=cq_ga;ea<=cq_ea;gs<=cq_gs;es<=cq_es;gm<=cq_gm;em<=cq_em;
     gp<=cq_gp;epd<=cq_ep;s0<=cq_s0;s1<=cq_s1;
     {f_p0,f_p1,f_r,f_add,f_sum,f_mul,f_prod}<={cq_i0,cq_i1,cq_ir,cq_ia,cq_is,cq_im,cq_ip};
     b_p0<=cq_b0;b_p1<=cq_b1;b_sum<=cq_bs;b_q<=cq_bq;b_prod<=cq_bp;
    end
   end else if(active&&!fault)begin
    n<=n+16'd1;b_p0<=b_p0+5'd1;b_p1<=b_p1+5'd1;b_sum<=b_sum+5'd1;b_q<=b_q+5'd1;b_prod<=b_prod+5'd1;
    if(bad||last)begin
     if(bad)fault<=1;
     active<=0;{f_p0,f_p1,f_r,f_add,f_sum,f_mul,f_prod}<=7'd0;
    end
    if(!bad)begin
     if(f_prod)out_valid<=1;
     if(!last)begin
      f_p0<=(f_p0&&n!=e0)||n==g0;f_p1<=(f_p1&&n!=e1)||n==g1;f_r<=(n==gr);
      f_add<=(f_add&&n!=ea)||n==ga;f_sum<=(f_sum&&n!=es)||n==gs;
      f_mul<=(f_mul&&n!=em)||n==gm;f_prod<=(f_prod&&n!=epd)||n==gp;
     end
    end
   end else if(!active&&(p0v_q||p1v_q||rzv_q))fault<=1;
   // payload regs: enable = f_prod && active && !fault && !start_q (no `bad`): on a bad product edge they move with
   // out_valid low and fault rising; out_beat / out_epoch are qualified by out_valid (qkd_pv_fin_s holds them there)
   if(!start_q&&active&&!fault&&f_prod)begin out_beat<=b_prod;out_epoch<=ep;end
  end
 end
 // sum buffer write (beat order), operand prefetch for the next edge, reciprocal, product
 wire [2:0] hb=(MUT==1)?3'(({1'b0,b_q}+6'd1)>>3):3'(b_q>>3);
 wire [127:0] rzn=f_r?rz_q:rzr;                                    // rzr after this edge
 always @(posedge ck)begin
  if(f_r)rzr<=rz_q;
  if(f_sum)sbuf[DW*b_sum+:DW]<=sum;
  rd_q<=(f_sum&&b_sum==b_q)?sum:sbuf[DW*b_q+:DW];
  rzh_q<=(hb==3'd0)?rzn[31:0]:(hb==3'd1)?rzn[63:32]:(hb==3'd2)?rzn[95:64]:rzn[127:96];
  if(f_prod)out_data<=product;
 end
endmodule

// Drop-in pair: the qkd_pv_fin_s port list, two qkd_pv_fin_s8 slices (lanes 0..7 / 8..15).
module qkd_pv_fin_s2x8 #(
 parameter integer ADD_LAT=7,
 parameter integer MUL_LAT=6,
 parameter integer SKEW=2,
 parameter integer MUT=0,
 parameter integer IN_STAGE=0
)(
 input wire ck,rst_n,
 input wire start,input wire [15:0] epoch,input wire [47:0] cal,
 input wire p0_valid,input wire [4:0] p0_beat,input wire [15:0] p0_epoch,input wire [511:0] p0_data,
 input wire p1_valid,input wire [4:0] p1_beat,input wire [15:0] p1_epoch,input wire [511:0] p1_data,
 input wire rz_valid,input wire [15:0] rz_epoch,input wire [127:0] rz,
 output wire out_valid,output wire [4:0] out_beat,output wire [15:0] out_epoch,output wire [511:0] out_data,
 output wire fault
);
 wire [1:0] ov,fl;wire [4:0] ob[0:1];wire [15:0] oe[0:1];wire [255:0] od[0:1];
 genvar s;
 generate for(s=0;s<2;s=s+1)begin:g_sl
`ifdef OT_PVFIN_S2X8_MUTANT_LANESWAP
  localparam integer LO=256*(1-s);                                // MUTANT: the slices take each other's lanes
`else
  localparam integer LO=256*s;
`endif
  qkd_pv_fin_s8 #(.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT),.SKEW(SKEW),.MUT(MUT),.NL(8),.IN_STAGE(IN_STAGE)) u_sl(.ck(ck),.rst_n(rst_n),
   .start(start),.epoch(epoch),.cal(cal),
   .p0_valid(p0_valid),.p0_beat(p0_beat),.p0_epoch(p0_epoch),.p0_data(p0_data[LO+:256]),
   .p1_valid(p1_valid),.p1_beat(p1_beat),.p1_epoch(p1_epoch),.p1_data(p1_data[LO+:256]),
   .rz_valid(rz_valid),.rz_epoch(rz_epoch),.rz(rz),
   .out_valid(ov[s]),.out_beat(ob[s]),.out_epoch(oe[s]),.out_data(od[s]),.fault(fl[s]));
 end endgenerate
 assign out_valid=&ov,fault=|fl,out_beat=ob[0],out_epoch=oe[0],out_data={od[1],od[0]};
endmodule
