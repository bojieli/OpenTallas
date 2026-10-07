`timescale 1ns/1ps
// HA2 TU owner reducer, BANKED structural successor (additive, default-off at
// the caller; ot_ha2_tu_owner_adapter_item9_cuts and every earlier reducer are
// unchanged).
//
// Why: the original keeps the operand store as an NC x OFMX x FW flop array
// (8 x 48 x 512 = 196,608 flops at the DS TP-96 shape) written by INJ+NP = 10
// dynamically indexed ports. Every port data bit fans out to 384 entries and
// every entry carries a 10:1 write mux: the routed block was 355k um2 of cells
// (CTS setup TNS -105.6 us, 46,252 violating endpoints, ha2red_sr1_r4) and the
// item9 read-select cut never left ABC (20 h). The function is unchanged; the
// structure is replaced:
//  * every input pin is captured by a flop (P stage) with no logic before it;
//  * each column's operands live in one 1R1W 64x512 SRAM macro (one write and
//    one read per column per cycle);
//  * a per-port queue (depth QD) plus a REGISTERED ready (p_r) lets the caller
//    keep the item in its receive FIFO when a column is contended; own partials
//    (no backpressure, at most one per cycle to column J in the native caller)
//    use an own queue with fail-closed overflow;
//  * the port->column crossbar is split: port side H (head + registered grant),
//    column side W (one-hot OR), macro side W2 (write registers at the macro);
//  * the slot directory (pres, dupe check) is updated at W, the read-ready map
//    (prdy) when the macro write happens, so an issue never reads before write;
//  * the read address is a kept per-macro register, the macro output is captured
//    at the macro pin (RQ) and staged once more (RQ2) before the adder tree.
// Semantics: results (r_m, r_d) are bit-identical and in the same order as the
// original for legal traffic; latency grows by the pipeline (measured by the
// bench). Duplicate/out-of-range/foreign flits raise the sticky dupe as before;
// a duplicate is never written (the original could overwrite when two writers
// hit one slot on the same edge; this form flags it). Faults are detected a few
// edges later than in the original; no data is ever overwritten, so a result
// emitted before dupe rises is still the exact sum of a complete slot.
module ot_ha2_tu_owner_banked #(
 parameter integer NC=8,PFMAX=384,LANES=16,BF16=1,INJ=2,NPT=8,LAT=7,
 parameter integer QD=6,QO=4,MUTANT=0,PQREG=0,
 parameter integer FW=32*LANES,PWT=FW+33
)(input wire clk,rst_n,active,arm,input wire [7:0] rank,input wire [15:0] pf,
 input wire [INJ-1:0] h_v,input wire [INJ*(32+FW)-1:0] h_d,
 input wire [NPT-1:0] p_v,input wire [NPT*PWT-1:0] p_flit,
 output reg [NPT-1:0] p_r,
 output reg r_v,output reg [15:0] r_m,output reg [FW-1:0] r_d,
 output reg dupe,output reg issue_o,output reg quiet);
 localparam integer LV=$clog2(NC);
 localparam integer OFMX=PFMAX/NC;
 localparam integer FLW=$clog2(OFMX);
 localparam integer PCW=$clog2(OFMX+1);
 localparam integer NS=(FW+63)/64;           // 64-bit slices (arbiter/grant copies)
 localparam integer QW=$clog2(QD);
 initial if((1<<LV)!=NC || OFMX>64 || FW>512)$fatal(1,"banked HA2: NC power of two, OFMX<=64, FW<=512");
 // ---------------- P: pin capture --------------------------------------------
 reg act_p,arm_p;reg [7:0] rank_p;reg [15:0] pf_p;
 reg [INJ-1:0] hv_p;reg [INJ*(16+FW)-1:0] hd_p;
 reg [NPT-1:0] pv_p;reg [NPT*PWT-1:0] pd_p;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin act_p<=0;arm_p<=0;hv_p<=0;pv_p<=0;rank_p<=0;pf_p<=0;end
  else begin act_p<=active;arm_p<=arm;hv_p<=h_v;pv_p<=p_v;rank_p<=rank;pf_p<=pf;end
 always @(posedge clk)begin
  pd_p<=p_flit;
  for(integer i=0;i<INJ;i=i+1)hd_p[i*(16+FW)+:16+FW]<=h_d[i*(32+FW)+:16+FW];
 end
 // ---------------- configuration (registered once more; static per arm) ------
 reg [LV-1:0] J_q;reg [NC-1:0] Jhot_q;reg [15:0] OF_q,base_q,limit_q,PF_q;reg ok_q;
 wire [15:0] of_c=pf_p>>LV;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin J_q<=0;Jhot_q<=1;OF_q<=0;base_q<=0;limit_q<=0;PF_q<=0;ok_q<=0;end
  else begin
   J_q<=rank_p[LV-1:0];Jhot_q<={{(NC-1){1'b0}},1'b1}<<rank_p[LV-1:0];
   OF_q<=of_c;PF_q<=pf_p;
   base_q<=16'(rank_p[LV-1:0])*of_c;limit_q<=16'(rank_p[LV-1:0])*of_c+of_c;
   ok_q<=pf_p>0&&pf_p<=PFMAX&&pf_p[LV-1:0]==0&&(!BF16||!of_c[0]);
  end
 // The configuration follows pf/rank one edge behind P; P items in the edge
 // that applies arm are dropped (as the original drops arm-cycle writes), and
 // the parent holds rank/pf static while bound, so items use the bound config.
 wire run=act_p&&ok_q&&!arm_p;
 // ---------------- P checks, queue pushes --------------------------------------
 reg  [NPT-1:0] cnt_hi;                       // ready bound per port
 wire [NPT-1:0] pq_push,pq_bad;
 wire [INJ-1:0] oq_push;wire [INJ-1:0] oq_bad;
 wire [FLW-1:0] own_fl[0:INJ-1];
 for(genvar i=0;i<INJ;i=i+1)begin:g_own
  wire [15:0] f=hd_p[i*(16+FW)+FW+:16];
  wire [15:0] rel=f-base_q;
  assign oq_bad[i]=run&&hv_p[i]&&f>=PF_q;
  assign oq_push[i]=run&&hv_p[i]&&f<PF_q&&f>=base_q&&f<limit_q;
  assign own_fl[i]=rel[FLW-1:0];
 end
 wire [NPT-1:0] id_bad;
 for(genvar p=0;p<NPT;p=p+1)begin:g_peer_chk
  wire [7:0] c=pd_p[p*PWT+FW+16+:8];wire [15:0] fl=pd_p[p*PWT+FW+:16];
  wire ident=pd_p[p*PWT+FW+24+:8]==rank_p&&!pd_p[p*PWT+PWT-1];
  assign id_bad[p]=pv_p[p]&&!ident;
  assign pq_bad[p]=run&&pv_p[p]&&ident&&(c>=NC||fl>=OF_q);
  assign pq_push[p]=run&&pv_p[p]&&ident&&c<NC&&fl<OF_q;
 end
 // ---------------- peer queues (circular, registered one-hot read pointer) ---
 localparam integer EW=FLW+NC+FW;            // {fl, column one-hot, data}
 reg [EW-1:0] pq[0:NPT-1][0:QD-1];
 reg [QD-1:0] prp[0:NPT-1],pwp[0:NPT-1];     // one-hot pointers
 reg [QW:0] pcnt[0:NPT-1];
 wire [NPT-1:0] pdeq;
 wire [EW-1:0] phead[0:NPT-1];
 wire [NPT-1:0] pne;
 wire [NPT-1:0] povf;
 for(genvar p=0;p<NPT;p=p+1)begin:g_pq
  reg [EW-1:0] h;
  always @*begin h='0;for(integer e=0;e<QD;e=e+1)if(prp[p][e])h=h|pq[p][e];end
  assign phead[p]=h;
  assign pne[p]=pcnt[p]!=0;
  // PQREG=1: the peer push is a registered decision. Stage A (pin flops + identity/range checks) registers the
  // push strobe (one kept copy per 64-bit slice of the entry) and the new entry; stage B writes the entry and
  // moves the pointer/count with those registers only, so the 526-bit write-enable fanout starts at a flop.
  // Cost: +1 edge from pin to queue; the registered ready counts the push in flight.
  localparam integer NSL=(EW+63)/64;
  reg pushq;reg [EW-1:0] newq;wire [NSL-1:0] ens;
  wire pushB=PQREG?pushq:pq_push[p];
  assign povf[p]=pushB&&pcnt[p]==QD&&!pdeq[p];
  wire [7:0] c=pd_p[p*PWT+FW+16+:8];
  wire [NC-1:0] chot={{(NC-1){1'b0}},1'b1}<<c[LV-1:0];
  wire [EW-1:0] newd={pd_p[p*PWT+FW+:FLW],chot,pd_p[p*PWT+:FW]};
  if(PQREG)begin:g_pqreg
   always @(posedge clk or negedge rst_n)if(!rst_n)pushq<=0;else pushq<=pq_push[p]&&!arm_p;
   always @(posedge clk)newq<=newd;
   for(genvar sl=0;sl<NSL;sl=sl+1)begin:g_sl
    ot_ha2_bk_kreg #(.W(1)) u_en(.clk(clk),.rst_n(rst_n),.d(pq_push[p]&&!arm_p),.q(ens[sl]));
   end
   always @(posedge clk)
    for(integer e=0;e<QD;e=e+1)
     for(integer sl=0;sl<NSL;sl=sl+1)
      if(ens[sl]&&pwp[p][e])
       for(integer b=sl*64;b<sl*64+64&&b<EW;b=b+1)pq[p][e][b]<=newq[b];
  end else begin:g_pqplain
   always @(posedge clk)
    for(integer e=0;e<QD;e=e+1)if(pq_push[p]&&pwp[p][e])
     pq[p][e]<=newd;
  end
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin prp[p]<=1;pwp[p]<=1;pcnt[p]<=0;end
   else if(arm_p)begin prp[p]<=1;pwp[p]<=1;pcnt[p]<=0;end
   else begin
    if(pushB&&!povf[p])pwp[p]<={pwp[p][QD-2:0],pwp[p][QD-1]};
    if(pdeq[p])prp[p]<={prp[p][QD-2:0],prp[p][QD-1]};
    pcnt[p]<=pcnt[p]+(pushB&&!povf[p])-pdeq[p];
   end
  // Registered ready: with pops at t-1 and t not yet seen, the queue plus the P
  // seat can hold two more items than this bound admits.
  always @(posedge clk or negedge rst_n)
   if(!rst_n)p_r[p]<=0;
   else p_r[p]<=({1'b0,pcnt[p]}+pv_p[p]+(PQREG?pushq:1'b0)+2)<=QD;
 end
 // ---------------- own queue (up to INJ pushes per edge) ----------------------
 localparam integer OW=FLW+FW;
 localparam integer QOW=$clog2(QO);
 reg [OW-1:0] oq[0:QO-1];
 reg [QOW-1:0] orp,owp;reg [QOW:0] ocnt;
 wire odeq;
 wire [OW-1:0] ohead=oq[orp];
 wire one=ocnt!=0;
 integer npush;
 always @*begin npush=0;for(integer i=0;i<INJ;i=i+1)npush=npush+oq_push[i];end
 wire oovf=({1'b0,ocnt}+npush-odeq)>QO;
 always @(posedge clk)begin:own_write
  integer k;k=0;
  if(!oovf)for(integer i=0;i<INJ;i=i+1)if(oq_push[i])begin
   oq[QOW'(owp+k)]<={own_fl[i],hd_p[i*(16+FW)+:FW]};k=k+1;end
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin orp<=0;owp<=0;ocnt<=0;end
  else if(arm_p)begin orp<=0;owp<=0;ocnt<=0;end
  else begin
   if(!oovf)owp<=owp+QOW'(npush);
   if(odeq)orp<=orp+1'b1;
   ocnt<=ocnt+(oovf?0:npush)-odeq;
  end
 // ---------------- arbitration (stage A) -> H (port side) ---------------------
 // Requesters: own (index NPT) to column J; peer p to its head's column.
 // Own first, then the lowest peer. One grant per column, one column per port.
 wire [NPT:0] req[0:NC-1];
 for(genvar c=0;c<NC;c=c+1)begin:g_req
  for(genvar p=0;p<NPT;p=p+1)begin:g_rp
   assign req[c][p]=pne[p]&&phead[p][FW+c];
  end
  assign req[c][NPT]=one&&Jhot_q[c];
 end
 // Reference arbiter (drives dequeue); the per-slice kept copies below select
 // data with identical inputs, so they agree by construction.
 wire [NPT:0] gnt[0:NC-1];
 for(genvar c=0;c<NC;c=c+1)begin:g_arb
  ot_ha2_bk_arb #(.N(NPT+1)) u_arb(.req({req[c][NPT-1:0],req[c][NPT]}),.gnt({gnt[c][NPT-1:0],gnt[c][NPT]}));
 end
 // (own is bit 0 of the arbiter input: highest priority)
 for(genvar p=0;p<NPT;p=p+1)begin:g_deq
  reg any;
  always @*begin any=0;for(integer c=0;c<NC;c=c+1)any=any|gnt[c][p];end
  assign pdeq[p]=any&&!arm_p;
 end
 wire gnt_own_any;
 reg goa;always @*begin goa=0;for(integer c=0;c<NC;c=c+1)goa=goa|gnt[c][NPT];end
 assign gnt_own_any=goa;
 assign odeq=gnt_own_any&&!arm_p;
 // H: port-side head registers + registered grants (kept copies per slice).
 reg [FW-1:0] H[0:NPT];reg [FLW-1:0] Hfl[0:NPT];
 always @(posedge clk)begin
  for(integer p=0;p<NPT;p=p+1)begin H[p]<=phead[p][FW-1:0];Hfl[p]<=phead[p][FW+NC+:FLW];end
  H[NPT]<=ohead[FW-1:0];Hfl[NPT]<=ohead[FW+:FLW];
 end
 wire [NPT:0] gq[0:NC-1][0:NS];               // slice NS = fl/valid copy
 for(genvar c=0;c<NC;c=c+1)begin:g_gq
  for(genvar s=0;s<=NS;s=s+1)begin:g_s
   ot_ha2_bk_kreg #(.W(NPT+1)) u_g(.clk(clk),.rst_n(rst_n),.d(arm_p?{(NPT+1){1'b0}}:gnt[c]),.q(gq[c][s]));
  end
 end
 // ---------------- W: column side one-hot OR ----------------------------------
 reg [NC-1:0] Wv;reg [FW-1:0] Wd[0:NC-1];reg [FLW-1:0] Wfl[0:NC-1];
 for(genvar c=0;c<NC;c=c+1)begin:g_w
  wire [FW-1:0] d;reg [FLW-1:0] f;
  for(genvar s=0;s<NS;s=s+1)begin:g_sl
   localparam integer LO=s*64,SW=(LO+64>FW)?FW-LO:64;
   reg [SW-1:0] x;
   always @*begin x='0;for(integer p=0;p<=NPT;p=p+1)if(gq[c][s][p])x=x|H[p][LO+:SW];end
   assign d[LO+:SW]=x;
  end
  always @*begin f='0;for(integer p=0;p<=NPT;p=p+1)if(gq[c][NS][p])f=f|Hfl[p];end
  always @(posedge clk)begin Wd[c]<=d;Wfl[c]<=f;end
  always @(posedge clk or negedge rst_n)if(!rst_n)Wv[c]<=0;else Wv[c]<=(|gq[c][NS])&&!arm_p;
 end
 // ---------------- slot directory: dupe check at W -----------------------------
 reg [OFMX-1:0] pres[0:NC-1],prdy[0:NC-1];
 reg [PCW-1:0] rptr;
 wire [NC-1:0] wdup,wok;
 for(genvar c=0;c<NC;c=c+1)begin:g_dir
  assign wdup[c]=Wv[c]&&(MUTANT==2?1'b0:pres[c][Wfl[c]]);
  assign wok[c]=Wv[c]&&!wdup[c];
 end
 // W2: macro write registers (kept per macro, at the macro pins).
 reg [NC-1:0] W2v;reg [FW-1:0] W2d[0:NC-1];reg [FLW-1:0] W2fl[0:NC-1];
 always @(posedge clk)for(integer c=0;c<NC;c=c+1)begin W2d[c]<=Wd[c];W2fl[c]<=Wfl[c];end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)W2v<=0;else W2v<=arm_p?{NC{1'b0}}:wok;
 // ---------------- issue (one-cycle loop: prdy/rptr/issue stay together) -----
 reg [NC-1:0] col;
 always @*for(integer c=0;c<NC;c=c+1)col[c]=({1'b0,rptr}<OF_q)?prdy[c][rptr]:1'b0;
 wire issue=act_p&&ok_q&&!dupe&&(&col)&&!arm_p;
 reg [PCW-1:0] pending;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   for(integer c=0;c<NC;c=c+1)begin pres[c]<=0;prdy[c]<=0;end
   rptr<=0;pending<=0;
  end else if(arm_p)begin
   for(integer c=0;c<NC;c=c+1)begin pres[c]<=0;prdy[c]<=0;end
   rptr<=0;pending<=0;
  end else begin
   for(integer c=0;c<NC;c=c+1)begin
    if(wok[c])pres[c][Wfl[c]]<=1'b1;
    if(W2v[c])prdy[c][W2fl[c]]<=1'b1;
   end
   if(issue)begin
    for(integer c=0;c<NC;c=c+1)begin pres[c][rptr]<=1'b0;prdy[c][rptr]<=1'b0;end
    rptr<=rptr+1'b1;
   end
   pending<=pending+(issue?1:0)-(r_v?(BF16?2:1):0);
  end
 // ---------------- read: kept address per macro -> macro -> RQ -> RQ2 --------
 wire [NC-1:0] rce;wire [6*NC-1:0] ra;
 for(genvar c=0;c<NC;c=c+1)begin:g_ra
  ot_ha2_bk_kreg #(.W(7)) u_ra(.clk(clk),.rst_n(rst_n),
   .d({issue,6'(rptr)+((MUTANT==1&&c==3&&rptr==2)?6'd1:6'd0)}),.q({rce[c],ra[6*c+:6]}));
 end
 wire [511:0] mq[0:NC-1];
 reg [FW-1:0] RQ[0:NC-1],RQ2[0:NC-1];
 for(genvar c=0;c<NC;c=c+1)begin:g_mem
  wire [511:0] wd512=512'(W2d[c]);
  ot_sram_1r1w_64x512_m1_r2c2 u_col(.clk(clk),.r_ce_in(rce[c]),.r_addr_in(ra[6*c+:6]),.rd_out(mq[c]),
   .w_ce_in(W2v[c]),.w_addr_in(6'(W2fl[c])),.wd_in(wd512),.w_mask_in({512{1'b1}}),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
  always @(posedge clk)begin RQ[c]<=mq[c][FW-1:0];RQ2[c]<=RQ[c];end
 end
 // issue -> (ra) -> macro -> RQ -> RQ2: the tree sees issue delayed by 4 edges.
 reg [3:0] tv;reg [15:0] ti[0:3];
 always @(posedge clk or negedge rst_n)
  if(!rst_n)tv<=0;else tv<={tv[2:0],issue};
 always @(posedge clk)begin ti[0]<=16'(rptr);for(integer k=1;k<4;k=k+1)ti[k]<=ti[k-1];end
 wire t_v=tv[3];wire [15:0] t_i=ti[3];
 // ---------------- adder tree (unchanged arithmetic) ---------------------------
 wire [FW-1:0] lvl[0:LV][0:NC-1];
 wire [LV:0] lvv;
 for(genvar c=0;c<NC;c=c+1)begin:g_l0 assign lvl[0][c]=RQ2[c];end
 assign lvv[0]=t_v;
 for(genvar l=1;l<=LV;l=l+1)begin:g_lv
  localparam integer NN=NC>>l;
  wire [NN*LANES-1:0] vv;
  /* verilator lint_off UNUSEDSIGNAL */
  wire [NN*2*LANES-1:0] ee;
  /* verilator lint_on UNUSEDSIGNAL */
  for(genvar i=0;i<NN;i=i+1)begin:g_n
   for(genvar ln=0;ln<LANES;ln=ln+1)begin:g_ln
    ot_hdc_fp32_add_lat #(.LAT(LAT)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(lvv[l-1]),
     .a(lvl[l-1][2*i][32*ln+:32]),.b(lvl[l-1][2*i+1][32*ln+:32]),
     .y(lvl[l][i][32*ln+:32]),.err(ee[(i*LANES+ln)*2+:2]),.valid_out(vv[i*LANES+ln]));
   end
  end
  assign lvv[l]=vv[0];
 end
 wire ti_v;wire [15:0] ti_d;
 ot_ha2_delay #(.W(16),.D(LAT*LV)) u_tidx(.clk(clk),.rst_n(rst_n),.v_in(t_v),.d_in(t_i),
  .v_out(ti_v),.d_out(ti_d));
 function automatic [15:0] bf16(input [31:0] b);
  reg [32:0] s;s={1'b0,b}+33'h7FFF+{32'b0,b[16]};bf16=s[31:16];
 endfunction
 reg [FW-1:0] hold;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)r_v<=1'b0;
  else begin
   r_v<=1'b0;
   if(lvv[LV])begin
    if(BF16)begin
     if(!ti_d[0])for(integer ln=0;ln<LANES;ln=ln+1)hold[16*ln+:16]<=bf16(lvl[LV][0][32*ln+:32]);
     else begin
      r_v<=1'b1;r_m<=ti_d>>1;
      for(integer ln=0;ln<LANES;ln=ln+1)begin
       r_d[16*ln+:16]<=hold[16*ln+:16];
       r_d[16*(LANES+ln)+:16]<=bf16(lvl[LV][0][32*ln+:32]);
      end
     end
    end else begin r_v<=1'b1;r_m<=ti_d;r_d<=lvl[LV][0];end
   end
  end
 // ---------------- sticky fault, status outputs (all from flops) -------------
 wire any_bad=(|id_bad)||(act_p&&!ok_q&&!arm_p)||(|oq_bad)||(|pq_bad)||(|povf)||oovf||(|wdup);
 reg busy_q;
 reg qe;always @*begin qe=1;for(integer p=0;p<NPT;p=p+1)qe=qe&&!pne[p];end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin dupe<=0;issue_o<=0;quiet<=1;busy_q<=0;end
  else begin
   if(any_bad)dupe<=1'b1;
   issue_o<=issue;
   busy_q<=(|pv_p)||(|hv_p)||!qe||one||(|Wv)||(|W2v)||(|tv)||lvv[LV]||ti_v;
   quiet<=pending==0&&(!act_p||{1'b0,rptr}>=OF_q)&&!busy_q&&!(|pv_p)&&!(|hv_p)&&qe&&!one&&!(|Wv)&&!(|W2v);
  end
endmodule

// Fixed-priority one-hot arbiter (bit 0 highest). Kept hierarchy.
(* keep_hierarchy="yes" *)
module ot_ha2_bk_arb #(parameter integer N=9)(input wire [N-1:0] req,output wire [N-1:0] gnt);
 assign gnt=req&(~req+1'b1);
endmodule
(* keep_hierarchy="yes" *)
module ot_ha2_bk_kreg #(parameter integer W=1)(input wire clk,rst_n,input wire [W-1:0] d,output reg [W-1:0] q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<='0;else q<=d;
endmodule
