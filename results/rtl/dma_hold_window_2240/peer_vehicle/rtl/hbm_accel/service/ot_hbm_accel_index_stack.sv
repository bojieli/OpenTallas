`timescale 1ps/1fs
// Hardware query-owner attachment to Cicero's existing round-robin scorer.
// Index top-512 is independent of the MoE router's top-six expert fetch.
module ot_hbm_accel_index_stack #(
 parameter ENABLE=0,STACK=0,NSL=4,NK=4,NB=4,IH=32,IW=20,K=512,
 FPL=7,FML=5,QL=5,NC=32,FA=7,LO=16,MACRO=0)(
 input wire clk,por_n,run_enable,
 input wire query_v,output wire query_r,input ot_hbm_r14_pkg::identity_t query_id,
 input wire ql_v,output wire ql_ready,input ot_hbm_r14_pkg::identity_t ql_owner,
 input wire[7:0] ql_head,input wire[NB*128-1:0] ql_codes,input wire[NB*8-1:0] ql_sc,input wire[15:0] ql_w,
 input wire k_valid,output wire k_ready,input ot_hbm_r14_pkg::identity_t k_owner,
 input wire k_last,input wire[IW-1:0] k_first,
 input wire[NSL*NK-1:0] k_kv,k_keep,k_ref,input wire[NSL*NK*NB*136-1:0] k_key,
 output wire c_valid,input wire c_ready,output wire c_last,
 output ot_hbm_r14_pkg::identity_t c_owner,output wire[LO-1:0] c_lv,
 output wire[LO*16-1:0] c_val,output wire[LO*IW-1:0] c_idx,
 output wire fault,output wire retained,
 output wire[31:0] st_folds,st_pass,st_stall);
 import ot_hbm_r14_pkg::*;import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign query_r=0;assign ql_ready=0;assign k_ready=0;assign c_valid=0;
  assign c_last=0;assign c_owner='0;assign c_lv=0;assign c_val=0;assign c_idx=0;
  assign fault=0;assign retained=0;assign st_folds=0;assign st_pass=0;assign st_stall=0;
 end else begin:on
  typedef struct packed{logic live,sticky,start_pending;identity_t id;} owner_t;
  owner_t o,n;reg[287:0] owner_seal;
  function automatic[287:0] seal(input owner_t raw);
   for(integer w=0;w<4;w=w+1)seal[w*72+:72]=encode64(64'(256'(raw)>>(w*64)));
  endfunction
  wire bad=owner_seal!=seal(o);
  wire scorer_fault,scorer_busy,qready,kready,cv,cl;
  wire qm=ql_owner==o.id,km=k_owner==o.id;
  assign fault=o.sticky||bad||scorer_fault;
  assign query_r=run_enable&&!o.live&&!fault;
  assign retained=o.live;
  assign ql_ready=qready&&o.live&&!o.start_pending&&qm&&!fault;
  assign k_ready=kready&&o.live&&!o.start_pending&&km&&!fault;
  assign c_valid=cv&&o.live&&!fault;assign c_last=cl;assign c_owner=o.id;
  ot_dsrom_edge_stack #(.NSL(NSL),.NK(NK),.NB(NB),.IH(IH),.IW(IW),.K(K),
   .FPL(FPL),.FML(FML),.QL(QL),.NC(NC),.FA(FA),.LO(LO),.MACRO(MACRO),.CONTIGUOUS(0)) scorer(
   .clk(clk),.rst_n(por_n),.stack_id(2'(STACK)),.start(o.start_pending&&!fault),
   .layout_n('0),.layout_installed(1'b0),
   .ql_v(ql_v&&o.live&&!o.start_pending&&qm&&!fault),.ql_ready(qready),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
   .k_valid(k_valid&&o.live&&!o.start_pending&&km&&!fault),.k_ready(kready),.k_last(k_last),.k_first(k_first),
   .k_kv(k_kv),.k_keep(k_keep),.k_ref(k_ref),.k_key(k_key),
   .c_valid(cv),.c_ready(c_ready&&c_valid),.c_last(cl),.c_lv(c_lv),.c_val(c_val),.c_idx(c_idx),
   .fault(scorer_fault),.busy(scorer_busy),.st_folds(st_folds),.st_pass(st_pass),.st_stall(st_stall));
  always @*begin
   n=o;
   if(o.start_pending&&!fault)n.start_pending=0;
   if(query_v&&query_r)begin
    if(query_id.stack!=2'(STACK))n.sticky=1;
    else begin n.live=1;n.id=query_id;n.start_pending=1;end
   end
   if(o.live&&((ql_v&&!qm)||(k_valid&&!km)))n.sticky=1;
   if(c_valid&&c_ready&&c_last)n.live=0;
   if(bad||scorer_fault)n.sticky=1;
  end
  always @(posedge clk or negedge por_n)
   if(!por_n)begin o<='0;owner_seal<=0;end
   else begin o<=n;owner_seal<=seal(n);end
 end endgenerate
endmodule
