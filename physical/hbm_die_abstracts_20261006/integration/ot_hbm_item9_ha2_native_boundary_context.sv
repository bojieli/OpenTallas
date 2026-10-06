`timescale 1ps/1fs
`default_nettype none
// Original TU boundary cones only. RX/hub selectors and result FIFO writes
// are real; omitted TX/CDC/PHY/release logic stays explicit external inputs.
// Cached child map is renamed mechanically to ot_hbm_item9_ha2_cached_map.
// Conditional internal timing vehicle, NOT a whole-TU functional replacement.
module ot_hbm_item9_ha2_native_boundary_context #(parameter integer ENABLE=0,CALLER_ONLY=0)(
 input wire clk,rst_n,go,endpoint_rearm_ready,
 input wire [7:0] rank,input wire [15:0] pf,
 input wire [63:0] context_operation,input wire [31:0] context_phase,
 input wire [1023:0] inj_data,
 input wire [7:0] w2_v,input wire [4359:0] w2_d,
 input wire [7:0] qr_pop,
 output wire [1:0] inj_rd,output wire [31:0] inj_idx,
 output wire [7:0] rb_pop,output wire dq_own_pop,
 output wire r_v,output wire [15:0] r_m,output wire [511:0] r_d,
 output wire dupe,issue_o,owner_quiet,context_fault_o,
 output wire [2179:0] delivery_words,output wire [3:0] delivery_v,
 output wire [4359:0] qr_heads,output wire [7:0] qr_empty,qr_ovf,
 output wire [55:0] qr_counts,
 output wire [1:0] caller_h_v,output wire [1087:0] caller_h_d,
 output wire [7:0] caller_p_v,output wire [4359:0] caller_p_flit,
 output wire caller_active,caller_arm,output wire [7:0] caller_rank,
 output wire [15:0] caller_pf,
 input wire adapter_r_v,input wire [15:0] adapter_r_m,
 input wire [511:0] adapter_r_d,input wire adapter_dupe,adapter_issue,adapter_quiet
);
 generate if(!ENABLE)begin:off
  assign inj_rd=0;assign inj_idx=0;assign rb_pop=0;assign dq_own_pop=0;
  assign r_v=0;assign r_m=0;assign r_d=0;assign dupe=0;assign issue_o=0;
  assign owner_quiet=0;assign context_fault_o=0;
  assign delivery_words=0;assign delivery_v=0;
  assign qr_heads=0;assign qr_empty=0;assign qr_ovf=0;assign qr_counts=0;
  assign caller_h_v=0;assign caller_h_d=0;assign caller_p_v=0;assign caller_p_flit=0;
  assign caller_active=0;assign caller_arm=0;assign caller_rank=0;assign caller_pf=0;
 end else begin:g_on
  localparam integer NC=8,NOG=8,PFMAX=384,FW=512,PWT=545,INJ=2,NPT=8,DEL=4;
  reg context_bound,context_fault;
  reg [7:0] bound_rank;reg [15:0] bound_pf;
  reg [63:0] bound_operation;reg [31:0] bound_phase;
  wire [31:0] RANK={24'b0,context_bound?bound_rank:rank};
  wire [31:0] PF={16'b0,context_bound?bound_pf:pf};
  wire [31:0] OG=RANK/NC,J=RANK%NC,OF=PF/NC,ROF=OF/2;
  wire CONTRIB=RANK<NOG*NC;
  wire config_ok=pf>0&&pf<=PFMAX&&pf%NC==0&&!((pf/NC)&1)&&rank<96;
  wire arm=go&&endpoint_rearm_ready&&config_ok;
  wire invalid_partial;
  always @(posedge clk or negedge rst_n)if(!rst_n)begin
   context_bound<=0;context_fault<=0;bound_rank<=0;bound_pf<=0;
   bound_operation<=0;bound_phase<=0;
  end else begin
   if((go&&!arm)||invalid_partial)context_fault<=1;
   if(arm)begin context_bound<=1;bound_rank<=rank;bound_pf<=pf;
    bound_operation<=context_operation;bound_phase<=context_phase;end
   else if(context_bound&&!endpoint_rearm_ready&&
    (rank!=bound_rank||pf!=bound_pf||context_operation!=bound_operation||context_phase!=bound_phase))context_fault<=1;
  end
  assign context_fault_o=context_fault|(|rb_ovf)|dq_own_ovf|(|qr_ovf)|dupe;
  integer k;reg started;reg [31:0] r_idx;reg [1:0] r_rd;
  always @*begin
   r_idx=0;r_rd=0;
   for(integer i=0;i<2;i=i+1)if(CONTRIB&&started&&!context_fault&&k+i<PF)begin
    r_rd[i]=1;r_idx[16*i+:16]=16'(((J+1+32'((k+i)%NC))%NC)*OF+32'((k+i)/NC));
   end
  end
  assign inj_idx=r_idx;assign inj_rd=r_rd;
  always @(posedge clk or negedge rst_n)if(!rst_n)begin k<=0;started<=0;end
   else if(arm)begin started<=1;k<=0;end else if(|r_rd)k<=k+2;
  wire [1:0] h_v,hub_idle;wire [1087:0] h_d;
  for(genvar i=0;i<2;i=i+1)begin:g_hub
   ot_ha2_delay_quiet #(.W(544),.D(35)) u_h(.clk(clk),.rst_n(rst_n),
    .v_in(r_rd[i]),.d_in({16'(k+i),r_idx[i*16+:16],inj_data[i*512+:512]}),
    .quiet(hub_idle[i]),.v_out(h_v[i]),.d_out(h_d[i*544+:544]));
  end
  wire [7:0] rb_empty,rb_ovf;wire [544:0] rb_head[0:7];
  reg [7:0] pop;
  assign rb_pop=pop;
  for(genvar p=0;p<8;p=p+1)begin:g_rx
   wire [8:0] cnt;
   ot_ha2_fifo #(.W(545),.AW(8)) u_rb(.clk(clk),.rst_n(rst_n),
    .push(w2_v[p]),.din(w2_d[p*545+:545]),.pop(pop[p]),
    .empty(rb_empty[p]),.dout(rb_head[p]),.ovf(rb_ovf[p]),.count(cnt));
  end
  wire [7:0] partial_v,invalid_partial_port;wire [4359:0] partial_flit;
  for(genvar p=0;p<8;p=p+1)begin:g_owner_ports
   assign invalid_partial_port[p]=!rb_empty[p]&&!rb_head[p][544]&&
    (!context_bound||rb_head[p][536+:8]!=RANK[7:0]||rb_head[p][528+:8]>=NC||rb_head[p][512+:16]>=OF);
   assign partial_v[p]=pop[p]&&!rb_head[p][544];
   assign partial_flit[p*545+:545]=rb_head[p];
  end
  assign invalid_partial=|invalid_partial_port;
  assign caller_h_v=h_v;assign caller_h_d=h_d;
  assign caller_p_v=partial_v;assign caller_p_flit=partial_flit;
  assign caller_active=context_bound&&CONTRIB&&!context_fault;
  assign caller_arm=arm;assign caller_rank=RANK[7:0];assign caller_pf=PF[15:0];
  if(CALLER_ONLY)begin:measurement_cut
   // Literal real child result boundary exposed for caller-only mapping.
   // No register, queue or scalar load substitutes for the child.
   assign r_v=adapter_r_v;assign r_m=adapter_r_m;assign r_d=adapter_r_d;
   assign dupe=adapter_dupe;assign issue_o=adapter_issue;assign owner_quiet=adapter_quiet;
  end else begin:linked_child
  ot_hbm_item9_ha2_cached_map u_owner(.clk(clk),.rst_n(rst_n),
   .active(context_bound&&CONTRIB&&!context_fault),.arm(arm),.rank(RANK[7:0]),.pf(PF[15:0]),
   .h_v(h_v),.h_d(h_d),.p_v(partial_v),.p_flit(partial_flit),
   .r_v(r_v),.r_m(r_m),.r_d(r_d),.dupe(dupe),.issue_o(issue_o),.quiet(owner_quiet));
  end
  wire [15:0] my_gi=16'((OG*NC+J)*ROF+{16'b0,r_m});
  wire [544:0] res_flit={1'b1,8'hFF,8'(OG),my_gi,r_d};
  wire dq_own_empty,dq_own_ovf;wire [544:0] dq_own_head;
  reg own_pop;wire [6:0] dc0;assign dq_own_pop=own_pop;
  ot_ha2_fifo #(.W(545),.AW(6)) u_dqo(.clk(clk),.rst_n(rst_n),
   .push(r_v),.din(res_flit),.pop(own_pop),.empty(dq_own_empty),
   .dout(dq_own_head),.ovf(dq_own_ovf),.count(dc0));
  integer rcnt,drot;reg [3:0] dv;reg [544:0] dfl[0:3];
  // Literal original dispatch. Kind=1 heads go to delivery, not reducer slots.
  always @*begin:dispatch
   integer n,src;pop=0;own_pop=0;dv=0;
   for(integer i=0;i<4;i=i+1)dfl[i]=0;
   for(integer p=0;p<8;p=p+1)
    if(!rb_empty[p]&&!rb_head[p][544]&&!invalid_partial_port[p])pop[p]=1;
   n=0;
   for(integer i=0;i<9;i=i+1)begin
    src=(drot+i)%9;
    if(n<4)begin
     if(src==8)begin
      if(!dq_own_empty)begin own_pop=1;dv[n]=1;dfl[n]=dq_own_head;n=n+1;end
     end else if(!rb_empty[src]&&rb_head[src][544])begin
      pop[src]=1;dv[n]=1;dfl[n]=rb_head[src];n=n+1;
     end
    end
   end
  end
  assign delivery_v=dv;
  for(genvar i=0;i<4;i=i+1)assign delivery_words[i*545+:545]=dfl[i];
  always @(posedge clk or negedge rst_n)if(!rst_n)begin drot<=0;rcnt<=0;end
   else begin drot<=(drot+1)%9;if(arm)rcnt<=0;else if(r_v)rcnt<=rcnt+1;end
  // The original qr write/load destinations are retained, not a scalar load.
  // qr_pop comes from the real TX credit/partial-first arbiter outside this cut.
  for(genvar p=0;p<8;p=p+1)begin:g_txq
   wire [6:0] cnt;wire empty,ovf;wire [544:0] head;
   (* keep *) ot_ha2_fifo #(.W(545),.AW(6)) u_qr(.clk(clk),.rst_n(rst_n),
    .push(r_v&&rcnt%8==p),.din((r_v&&rcnt%8==p)?res_flit:545'b0),
    .pop(qr_pop[p]),.empty(empty),.dout(head),.ovf(ovf),.count(cnt));
   assign qr_heads[p*545+:545]=head;assign qr_empty[p]=empty;
   assign qr_ovf[p]=ovf;assign qr_counts[p*7+:7]=cnt;
  end
 end endgenerate
endmodule
`default_nettype wire
