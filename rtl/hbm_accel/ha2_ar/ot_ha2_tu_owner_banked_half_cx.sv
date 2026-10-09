`timescale 1ns/1ps
// HA2 TU owner reducer, banked, HALF-RATE shell (additive; ot_ha2_tu_owner_banked is unchanged).
//
// The unchanged banked reducer runs on a clock-gated half-rate clock (latch + AND ICG, enable = phase). Every
// crossing is registered and latency-insensitive:
//  * pins: every input is captured by a fast-clock flop; every output is launched by a fast-clock flop;
//  * peer flits p_*: per-port FIFO (depth FD) with a registered ready (p_r). The core sees p_v only while its own
//    registered p_r is high (the original contract), one item per half-rate edge;
//  * own partials h_*: per-injector FIFO with a CREDIT ready h_r (new: the original had no back-pressure; the sender
//    must stop on !h_r, ready deasserts with margin so FD absorbs the in-flight items);
//  * arm is a pulse: held sticky until the core edge samples it; the shell then holds all items for BLKN core edges
//    (the original drops arm-cycle items and the config follows pf/rank one edge behind);
//  * result/issue pulses are one core cycle (two fast cycles): the fast launch flop passes them in the second half
//    only, so the consumer sees one-fast-cycle pulses as before;
//  * dupe is sticky and includes any shell FIFO overflow (fail closed); quiet includes the FIFOs.
//  * H_CREDIT (credit-ready 2026-10-08, default 0 = the occupancy ready above): h_r[i] is a registered one-cycle
//    CREDIT-RETURN pulse, one per item popped from the injector FIFO; the sender (ot_ha2_truecredit_receiver_p
//    CREDIT=1, CRD<=FD) holds FD credits, so the FIFO cannot overflow (ovf stays fail-closed).
// Cost: throughput of the core halves (one flit per two fast cycles per port, 0.5 flit/cycle per injector), latency
// roughly doubles through the core; results/ordering/fault detection are transaction-exact vs the banked reducer.
// Opposite-phase landing successor. LANDING remains opt-in until exact gate and
// reviewed physical measurement qualify the actual clock crossing.
module ot_ha2_tu_owner_banked_half_cx #(
 parameter integer NC=8,PFMAX=384,LANES=16,BF16=1,INJ=2,NPT=8,LAT=7,
 parameter integer QD=6,QO=4,MUTANT=0,PQREG=0,FD=8,BLKN=3,H_CREDIT=0,LANDING=0,MUT_PHASE=0,
 parameter integer FW=32*LANES,PWT=FW+33
)(input wire clk,rst_n,active,arm,input wire [7:0] rank,input wire [15:0] pf,
 input wire [INJ-1:0] h_v,input wire [INJ*(32+FW)-1:0] h_d,output reg [INJ-1:0] h_r,
 input wire [NPT-1:0] p_v,input wire [NPT*PWT-1:0] p_flit,
 output reg [NPT-1:0] p_r,
 output reg r_v,output reg [15:0] r_m,output reg [FW-1:0] r_d,
 output reg dupe,output reg issue_o,output reg quiet);
 localparam integer HW=16+FW;
 // ---------------- phase + clock gate ----------------------------------------
 reg ph;
 always @(posedge clk or negedge rst_n)if(!rst_n)ph<=1'b0;else ph<=~ph;
 wire gclk;
 ot_ha2_hr_icg u_icg(.clk(clk),.en(ph),.gclk(gclk));
 // ---------------- fast pin capture ------------------------------------------
 reg act_f,arm_f;reg [7:0] rank_f;reg [15:0] pf_f;reg [INJ-1:0] hv_f;reg [NPT-1:0] pv_f;
 reg [INJ*HW-1:0] hd_f;reg [NPT*PWT-1:0] pd_f;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin act_f<=0;arm_f<=0;rank_f<=0;pf_f<=0;hv_f<=0;pv_f<=0;end
  else begin act_f<=active;arm_f<=arm;rank_f<=rank;pf_f<=pf;hv_f<=h_v;pv_f<=p_v;end
 always @(posedge clk)begin
  pd_f<=p_flit;
  for(integer i=0;i<INJ;i=i+1)hd_f[i*HW+:HW]<=h_d[i*(32+FW)+:HW];
 end
 // sticky arm, hold-off counter
 reg arm_s;reg [3:0] blk;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin arm_s<=0;blk<=0;end
  else begin
   arm_s<=arm_f||(arm_s&&!ph);
   if(ph&&arm_s)blk<=BLKN;else if(ph&&blk!=0)blk<=blk-1'b1;
  end
 wire hold=(blk!=0)||arm_s;
 // ---------------- FIFOs ------------------------------------------------------
 wire [NPT-1:0] core_pr;wire [INJ-1:0] hp_pop_unused;
 wire [NPT-1:0] p_head_v;wire [INJ-1:0] h_head_v;
 wire [NPT*PWT-1:0] p_head_d,p_fifo_d;wire [INJ*HW-1:0] h_head_d,h_fifo_d;
 wire core_act,core_arm;wire [7:0] core_rank;wire [15:0] core_pf;
 wire [NPT-1:0] p_nonempty;wire [INJ-1:0] h_nonempty;
 wire [NPT-1:0] p_ovf;wire [INJ-1:0] h_ovf;wire [NPT*4-1:0] p_cnt;wire [INJ*4-1:0] h_cnt;
 for(genvar p=0;p<NPT;p=p+1)begin:g_pf
  wire pop=ph&&p_head_v[p];
  ot_ha2_hr_fifo #(.W(PWT),.D(FD)) u(.clk(clk),.rst_n(rst_n),.wv(pv_f[p]),.wd(pd_f[p*PWT+:PWT]),.pop(pop),
   .hd(p_fifo_d[p*PWT+:PWT]),.nonempty(p_nonempty[p]),.cnt(p_cnt[p*4+:4]),.ovf(p_ovf[p]));

 end
 for(genvar i=0;i<INJ;i=i+1)begin:g_hf
  wire pop=ph&&h_head_v[i];
  ot_ha2_hr_fifo #(.W(HW),.D(FD)) u(.clk(clk),.rst_n(rst_n),.wv(hv_f[i]),.wd(hd_f[i*HW+:HW]),.pop(pop),
   .hd(h_fifo_d[i*HW+:HW]),.nonempty(h_nonempty[i]),.cnt(h_cnt[i*4+:4]),.ovf(h_ovf[i]));

 end
 // Complete FIFO heads are sampled on the intervening fast edge. Their
 // registered valid is both the next core offer and the fast FIFO pop decision;
 // the head remains stable across that consuming core edge. No duplicate state
 // checks or protection mirrors are introduced here.
 generate if(LANDING!=0)begin:g_landing
  wire headclk;
  ot_ha2_hr_icg u_head_icg(.clk(clk),.en(MUT_PHASE!=0?ph:!ph),.gclk(headclk));
  reg [NPT*PWT-1:0] pd;reg [INJ*HW-1:0] hd;
  reg [NPT-1:0] pv;reg [INJ-1:0] hv;
  reg act,arm_q;reg [7:0] rank_q;reg [15:0] pf_q;
  always @(posedge headclk)begin pd<=p_fifo_d;hd<=h_fifo_d;end
  always @(posedge headclk or negedge rst_n)
   if(!rst_n)begin pv<=0;hv<=0;act<=0;arm_q<=0;rank_q<=0;pf_q<=0;end
   else begin
    pv<=p_nonempty&core_pr&{NPT{!hold}};
    hv<=h_nonempty&{INJ{!hold}};
    act<=act_f;arm_q<=arm_s;rank_q<=rank_f;pf_q<=pf_f;
   end
  assign p_head_d=pd;assign h_head_d=hd;
  assign p_head_v=pv;assign h_head_v=hv;
  assign core_act=act;assign core_arm=arm_q;
  assign core_rank=rank_q;assign core_pf=pf_q;
 end else begin:g_bypass
  assign p_head_d=p_fifo_d;assign h_head_d=h_fifo_d;
  assign p_head_v=p_nonempty&core_pr&{NPT{!hold}};
  assign h_head_v=h_nonempty&{INJ{!hold}};
  assign core_act=act_f;assign core_arm=arm_s;
  assign core_rank=rank_f;assign core_pf=pf_f;
 end endgenerate
 // registered ready / credit toward the senders (margin for the in-flight items: pin flop, FIFO write, sender view)
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin p_r<=0;h_r<=0;end
  else begin
   for(integer p=0;p<NPT;p=p+1)p_r[p]<=p_cnt[p*4+:4]<=3;
   for(integer i=0;i<INJ;i=i+1)h_r[i]<=(H_CREDIT!=0)?(ph&&h_head_v[i]):(h_cnt[i*4+:4]<=3);
  end
 // ---------------- core --------------------------------------------------------
 wire c_rv,c_iss,c_dupe,c_q;wire [15:0] c_rm;wire [FW-1:0] c_rd;
 reg [INJ*(32+FW)-1:0] hd_core;
 always @*begin hd_core='0;for(integer i=0;i<INJ;i=i+1)hd_core[i*(32+FW)+:HW]=h_head_d[i*HW+:HW];end
 ot_ha2_tu_owner_banked #(.NC(NC),.PFMAX(PFMAX),.LANES(LANES),.BF16(BF16),.INJ(INJ),.NPT(NPT),.LAT(LAT),.QD(QD),.QO(QO),
  .MUTANT(MUTANT),.PQREG(PQREG)) u_core(
  .clk(gclk),.rst_n(rst_n),.active(core_act),.arm(core_arm),.rank(core_rank),.pf(core_pf),
  .h_v(h_head_v),.h_d(hd_core),.p_v(p_head_v),.p_flit(p_head_d),.p_r(core_pr),
  .r_v(c_rv),.r_m(c_rm),.r_d(c_rd),.dupe(c_dupe),.issue_o(c_iss),.quiet(c_q));
 // ---------------- fast output launch -------------------------------------------
 reg ovf_s;wire any_ovf=(|p_ovf)||(|h_ovf);
 wire fifos_empty=!(|p_nonempty)&&!(|h_nonempty)&&!(|p_head_v)&&!(|h_head_v);
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin r_v<=0;issue_o<=0;dupe<=0;quiet<=1;ovf_s<=0;end
  else begin
   r_v<=!ph&&c_rv;issue_o<=!ph&&c_iss;
   if(any_ovf)ovf_s<=1;
   dupe<=c_dupe||ovf_s||any_ovf;
   quiet<=c_q&&fifos_empty&&!arm_s&&!arm_f&&(blk==0)&&!(|pv_f)&&!(|hv_f);
  end
 always @(posedge clk)begin r_m<=c_rm;r_d<=c_rd;end
endmodule

