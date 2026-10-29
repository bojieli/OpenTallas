`default_nettype none
// Opt-in IDXQ calendar graft onto actual source-bound AM root (sha25605f5acd8).
// TOPK/share service tail is byte-identical, including RSTL/FAN32, VM_RT/CR_RT.
// FAN32 controls retained service only: new CW2 calendar is NOT physically qualified.
// New multirow control and selector paths require independent physical closure.
module ot_hnx_idxq_rootctl_static_am #(parameter integer K=8,S=4,CW=2, parameter integer AMMUT = 0, parameter integer SEL_LAT = 4,
 parameter integer VM_RT = 0, parameter integer CR_RT = 0, parameter integer RSTL = 0, parameter integer FAN32 = 0)(
 input wire clk,input wire rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[4:0]n_rows,input wire[11:0]row_pitch,
 output reg[4*S-1:0]sel_op,output reg[2*S-1:0]sel_pass,output reg[8*S-1:0]sel_addr,
 output reg lin_clear,link_flush,link_emit,output reg[3:0]link_group,output reg link_clear,
 output reg[4:0]lin_row,lout_row,
 input wire[4*S-1:0]selected_v,output reg[S-1:0]ingest_v,
 input wire[3:0]tree_ev,                 // ev of the 4 quadrant lists at the tree root (quadrant 0 = list 0)
 input wire[3:0]qfault,input wire[S-1:0]sf,input wire lf,
 output reg done,output reg fault,
 // TOPK
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output reg[337:0]cq,output reg[1:0]cq_seq,input wire[273:0]cr,
 output reg topk_busy,topk_done,topk_fault,
 // VM read group 4 share (index face = quadrant 0's operand reader)
 input wire[135:0]index_rq,output wire[2055:0]index_rr,
 input wire[135:0]argmax_rq,output wire[263:0]argmax_m,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output reg share_fault
);
 localparam [1:0] SID = 2'd0;
 wire [2:0] rst_c;
 generate if (RSTL != 0) begin : g_rstl
  assign rst_c = {3{rst_n}};                 // landed + regionally copied by the kit (see RSTL above)
 end else begin : g_relay
  ot_rst_relay #(.REGIONS(3),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_c));
 end endgenerate
 (* keep *) reg pw_r,st_r;(* keep *) reg[7:0]pa_r;(* keep *) reg[255:0]pd_r;(* keep *) reg[11:0]ln_r;
 (* keep *) reg[3:0]qf_r;reg[4:0]nr_r;reg[11:0]pi_r;
 always @(posedge clk)begin pw_r<=program_we;pa_r<=program_addr;pd_r<=program_data;st_r<=start;ln_r<=length;qf_r<=qfault;nr_r<=n_rows;pi_r<=row_pitch;end
 wire calendar_fault,done_u,rs,ow,oq,qe,kv,pv,lc,lf_u,le;
 wire[6:0]oi;wire[4:0]qh,kr,lr,er;wire[7:0]ki,pi;wire[3:0]eg;
 wire[4*S-1:0]sop;wire[2*S-1:0]sps;wire[8*S-1:0]sad;
 ot_hnx_idxn_calendar #(.K(K),.S(S),.CW(CW)) calendar(.clk(clk),.clk_mem(clk),.rst_n(rst_c[0]),
  .program_we(pw_r),.program_addr(pa_r),.program_data(pd_r),.start(st_r),.length(ln_r),.n_rows(nr_r),.pitch(pi_r),
  .row_start(rs),.opr_weight(ow),.opr_query(oq),.opr_index(oi),.qem_v(qe),.qem_head(qh),
  .key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),.sel_op(sop),.sel_pass(sps),.sel_addr(sad),
  .lin_clear(lc),.lin_flush(lf_u),.lin_row(lr),.lout_emit(le),.lout_group(eg),.lout_row(er),.done(done_u),.fault(calendar_fault));
 always @(posedge clk or negedge rst_c[0])
  if(!rst_c[0])begin sel_op<=0;lin_clear<=0;link_flush<=0;link_emit<=0;link_clear<=0;done<=0;end
  else begin sel_op<=sop;lin_clear<=lc;link_flush<=lf_u;link_emit<=le;link_clear<=st_r;done<=done_u;end
 always @(posedge clk)begin sel_pass<=sps;sel_addr<=sad;lin_row<=lr;link_group<=eg;lout_row<=er;end
 // One independent prediction/check per selector; retains actual SEL_LAT contract.
 localparam integer SL = (AMMUT == 6) ? SEL_LAT - 1 : SEL_LAT;
 initial if(SL<2 || S!=4 || K!=8)$fatal(1,"IDXQ root requires SL>=2/S4/K8");
 reg[4*S-1:0]so_d[0:SL-2];reg ingest_fault;
 always @(posedge clk or negedge rst_c[0])
  if(!rst_c[0])begin ingest_v<=0;ingest_fault<=0;for(integer d=0;d<SL-1;d=d+1)so_d[d]<=0;end
  else begin
   so_d[0]<=sel_op;for(integer d=1;d<SL-1;d=d+1)so_d[d]<=so_d[d-1];
   for(integer j=0;j<S;j=j+1)begin
    ingest_v[j]<=so_d[SL-2][j*4+:4]==4'd6;
    if(selected_v[j*4+:4]!={4{ingest_v[j]}})ingest_fault<=1;
   end
  end
 reg parent_calendar_fault,agree_fault;
 always @(posedge clk or negedge rst_c[0])begin
  if(!rst_c[0])begin parent_calendar_fault<=0;agree_fault<=0;fault<=0;end
  else begin
   for(integer j=0;j<S;j=j+1)if(sel_op[j*4+:4]==2&&tree_ev[0]!=1'b1)parent_calendar_fault<=1;
   if(tree_ev!={4{tree_ev[0]}})agree_fault<=1;
   fault<=calendar_fault|(|qf_r)|(|sf)|lf|parent_calendar_fault|agree_fault|ingest_fault;
  end
 end
 // TOPK command pin registers (+1 on the TOPK timeline; no reset: data pin flops, go is reset)
 (* keep *) reg tk_go_r;(* keep *) reg[3:0]tk_k_r;(* keep *) reg tk_ord_r,tk_am_r,tk_om_r,tk_hr_r;
 (* keep *) reg[19:0]tk_n_r,tk_m_r;(* keep *) reg[17:0]tk_ab_r,tk_as_r,tk_ob_r,tk_os_r,tk_rb_r,tk_rs_r;
 always @(posedge clk or negedge rst_c[1]) if(!rst_c[1]) tk_go_r<=0; else tk_go_r<=topk_go;
 always @(posedge clk)begin
  tk_k_r<=topk_k;tk_ord_r<=topk_order;tk_n_r<=topk_n;tk_m_r<=topk_m;tk_am_r<=topk_a_mirror;tk_ab_r<=topk_a_base;
  tk_as_r<=topk_a_str;tk_om_r<=topk_o_mirror;tk_ob_r<=topk_o_base;tk_os_r<=topk_o_str;tk_hr_r<=topk_has_r;
  tk_rb_r<=topk_r_base;tk_rs_r<=topk_r_str;
 end
 wire[135:0]topk_rq;wire[2055:0]topk_rr;wire[337:0]tk_cq;wire[1:0]tk_cqs;wire tk_busy,tk_done,tk_fault;
 generate if (FAN32 != 0) begin : g_tk32
  localparam integer NGO = 12;
  wire [NGO-1:0] go_c;   // kept copies of the go pin register tk_go_r (same D, same reset)
  for (genvar c = 0; c < NGO; c = c + 1) begin : g_go
   ot_hbm_idx_kreg #(.W(1)) u(.clk(clk),.rst_n(rst_c[1]),.d(topk_go),.q(go_c[c]));   // reset-free: settles in reset
  end
  ot_hbm_idx_topk_static_f32 #(.ACK(13 + CR_RT),.RT_EXTRA(((AMMUT == 5) ? 0 : 1) + VM_RT),.NGO(NGO)) topk(.clk(clk),.rst_n(rst_c[1]),.sid(SID),
   .go(tk_go_r),.go_c(go_c),
   .k(tk_k_r),.order(tk_ord_r),.n(tk_n_r),.m(tk_m_r),.a_mirror(tk_am_r),.a_base(tk_ab_r),.a_str(tk_as_r),.o_mirror(tk_om_r),
   .o_base(tk_ob_r),.o_str(tk_os_r),.has_r(tk_hr_r),.r_base(tk_rb_r),.r_str(tk_rs_r),
   .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(tk_cq),.cq_seq(tk_cqs),.cr(cr),.busy(tk_busy),.done(tk_done),.fault(tk_fault));
 end else begin : g_tk
  ot_hbm_idx_topk_static #(.ACK(13 + CR_RT),.RT_EXTRA(((AMMUT == 5) ? 0 : 1) + VM_RT),.RSPLIT((RSTL != 0) ? 1 : 0)) topk(.clk(clk),.rst_n(rst_c[1]),.sid(SID),.go(tk_go_r),
   .k(tk_k_r),.order(tk_ord_r),.n(tk_n_r),.m(tk_m_r),.a_mirror(tk_am_r),.a_base(tk_ab_r),.a_str(tk_as_r),.o_mirror(tk_om_r),
   .o_base(tk_ob_r),.o_str(tk_os_r),.has_r(tk_hr_r),.r_base(tk_rb_r),.r_str(tk_rs_r),
   .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(tk_cq),.cq_seq(tk_cqs),.cr(cr),.busy(tk_busy),.done(tk_done),.fault(tk_fault));
 end endgenerate
 // TOPK output pin registers (+1): the hub sees cq one edge later, so the engine's cr check runs at ACK 13
 always @(posedge clk or negedge rst_c[1])
  if(!rst_c[1])begin cq[337]<=0;topk_busy<=0;topk_done<=0;topk_fault<=0;end
  else begin cq[337]<=tk_cq[337];topk_busy<=tk_busy;topk_done<=tk_done;topk_fault<=tk_fault;end
 always @(posedge clk)begin cq[336:0]<=tk_cq[336:0];cq_seq<=tk_cqs;end
 // share: INDEX / ARGMAX request pin registers here, vm_rr pin registers in the leaves
 (* keep *) reg[135:0]irq_r,arq_r;
 always @(posedge clk)begin irq_r<=index_rq;arq_r<=argmax_rq;end
 wire share_f;
 ot_hbm_idx_vm_share_static_amr #(.MUT((AMMUT == 7) ? 1 : 0),.AMMUT((AMMUT >= 1 && AMMUT <= 4) ? AMMUT : 0),.VM_RT(VM_RT),.F32(FAN32)) share(.clk(clk),
  .rst_n(rst_c[2]),.index_rq(irq_r),.topk_rq(topk_rq),.argmax_rq(arq_r),.vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(index_rr),
  .topk_rr(topk_rr),.argmax_m(argmax_m),.fault(share_f));
 always @(posedge clk or negedge rst_c[2]) if(!rst_c[2]) share_fault<=0; else share_fault<=share_f;
endmodule
`default_nettype wire
