// Reference: qkd_ctrl_pc_cdc_child exactly as CLOSED in cdc_s7b (claude/qkvctrl-split-1016 71d281424, main c39b4cded),
// renamed. Golden for tb_cdc_idle_export_equiv (cdc_s7c single idle_core export flop must match it bit for bit).
module qkd_ctrl_pc_cdc_child_s7b_ref #(
    parameter integer WDONE = 17,
    parameter integer PROFILE = 0,
    parameter integer EVMUT = 0,
    parameter integer STRAP_CDC = 0,
    parameter integer DRAIN_PIPE = 0
) (
    input  wire         pll_hbm,
    input  wire         hrst,
    input  wire         ck,
    input  wire         rsi,
    input  wire [4:0]   pc,
    input  wire [4:0]   pc_q,                          // sched hclk strap register
    input  wire [287:0] es,
    output wire [260:0] er,
    input wire [1:0] cfg_stack,
    input wire [317:0] es_context,
    input wire es_expected_valid,input wire [60:0] es_expected_identity,
    input wire [28:0] es_expected_address,input wire [4:0] es_expected_pc,input wire [1:0] es_expected_stack,
    output wire completion_v,completion_we,completion_fault,
    output wire idle_core,output reg drain_fault_core,
    input  wire         s_cr,                          // sched u_ctl credit register
    input  wire         p_em_v,                        // port child embedding return
    input  wire [257:0] p_em_d,
    output reg          c_v,                           // -> sched (registered)
    output reg  [286:0] c_d,
    output reg  [61:0]  c_context,
    output wire         f_ecdc,
    input  wire         col_v, col_we, col_sr          // sched po[28] / po[29] / physical_col_sr registers
);
    wire hclk = pll_hbm;
    (* keep *) reg hr_q;
    (* keep *) reg rs_q;
    always @(posedge hclk) hr_q <= hrst;
    always @(posedge ck)   rs_q <= rsi;
    wire h_rn = hr_q;
    // pin registers (flop-first): u_ctl credit and the embedding return beat
    (* keep *) reg s_cr_q, em_v_q;
    (* keep *) reg [257:0] em_d_q;
    always @(posedge hclk or negedge h_rn) if(!h_rn)begin s_cr_q<=1'b0;em_v_q<=1'b0;end else begin s_cr_q<=s_cr;em_v_q<=p_em_v;end
    always @(posedge hclk) em_d_q<=p_em_d;
    // ---- embedding static port crossing (strip engine on the core clock) ---------------------------------------------
    (* keep *) reg         es_v_q;
    (* keep *) reg [286:0] es_d_q;
    (* keep *) reg [317:0] es_context_q;
    (* keep *) reg es_expected_q;
    (* keep *) reg [60:0] es_expected_identity_q;
    (* keep *) reg [28:0] es_expected_address_q;
    (* keep *) reg [4:0] es_expected_pc_q,pc_core_q;
    (* keep *) reg [4:0] pc_core_meta;
    (* keep *) reg [1:0] stack_q,es_expected_stack_q;
    reg native_intake_fault;
    always @(posedge ck)begin
      es_context_q<=es_context;es_expected_identity_q<=es_expected_identity;
      es_expected_address_q<=es_expected_address;es_expected_pc_q<=es_expected_pc;
      es_expected_stack_q<=es_expected_stack;stack_q<=cfg_stack;
      pc_core_meta<=pc_q;pc_core_q<=(STRAP_CDC!=0)?pc_core_meta:pc;
    end
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin es_expected_q<=0;native_intake_fault<=0;end
      else begin
        es_expected_q<=es_expected_valid;
        if(PROFILE==0 && ((es_v_q&&es_context_q[317])!=es_expected_q))native_intake_fault<=1;
        if(es_v_q&&es_context_q[317] && (es_context_q[316:256]!=es_expected_identity_q ||
          es_context_q[255:0]!={256{1'b1}} || !es_d_q[286] || !es_d_q[285] ||
          {es_d_q[274:256],es_d_q[284:280],es_d_q[279:275]}!=es_expected_address_q ||
          pc_core_q!=es_expected_pc_q || stack_q!=es_expected_stack_q))native_intake_fault<=1;
      end
    always @(posedge ck or negedge rs_q) if (!rs_q) es_v_q <= 1'b0; else es_v_q <= es[0];
    always @(posedge ck) es_d_q <= es[287:1];
    wire         e_v, s_credit, f_core;
    wire [257:0] e_d;
    wire         c_v_w;
    wire [286:0] c_d_w;
    wire [61:0]  c_context_w;
    ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ecdc (
        .clk(ck), .rst_n(rs_q), .hclk(hclk), .hrst_n(h_rn), .s_v(es_v_q), .s_d(es_d_q),.s_context(es_context_q[317:256]), .c_v(c_v_w), .c_d(c_d_w),.c_context(c_context_w),
        .h_credit(s_cr_q), .s_credit(s_credit), .h_v(em_v_q), .h_d(em_d_q), .e_v(e_v), .e_d(e_d),
        .fault_core(f_core), .fault_hbm(f_ecdc));
    // down-FIFO output registers (the FIFO read mux never reaches a pin)
    always @(posedge hclk or negedge h_rn) if(!h_rn) c_v<=1'b0; else c_v<=c_v_w;
    always @(posedge hclk) begin c_d<=c_d_w; c_context<=c_context_w; end
    reg          er_v, er_cr, er_f;
    reg  [257:0] er_d;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin er_v <= 1'b0; er_cr <= 1'b0; er_f <= 1'b0; end
        else begin er_v <= e_v; er_cr <= s_credit; er_f <= f_core | native_intake_fault; end
    always @(posedge ck) er_d <= e_d;
    assign er = {er_f, er_cr, er_d, er_v};
    qkd_ctrl_static_commit #(.WDONE(WDONE),.MUT(EVMUT)) u_static_commit(
        .hclk(hclk),.hrst_n(h_rn),.ck(ck),.rst_n(rs_q),
        .col_v(col_v),.col_we(col_we),.col_sr(col_sr),
        .completion_v(completion_v),.completion_we(completion_we),.fault(completion_fault));
    // ---- actual outstanding work observations (not execution/admission gates) ----
    reg [15:0] drain_desc,drain_reads,drain_credits;
    wire dc_push=es_v_q,dc_pop=completion_v;
    wire dr_push=es_v_q&&!es_d_q[285],dr_pop=e_v;
    wire dq_push=es_v_q,dq_pop=s_credit;
    wire core_drain_activity_q=es_v_q||completion_v||e_v||er_v||s_credit||er_cr;   // all but the raw es[0] pin
    wire core_drain_activity=core_drain_activity_q;
    reg idle_core_r;
    (* keep *) reg es0_idle_q;
    always @(posedge ck or negedge rs_q) if(!rs_q) es0_idle_q<=1'b0; else es0_idle_q<=es[0];
    assign idle_core=idle_core_r&&!es0_idle_q;
    reg core_debt_zero_q;reg [1:0] core_quiet_q;
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin core_debt_zero_q<=0;core_quiet_q<=0;end
      else begin
        core_debt_zero_q<=drain_desc==0&&drain_reads==0&&drain_credits==0;
        core_quiet_q<={core_quiet_q[0],!core_drain_activity};
      end
    always @(posedge ck or negedge rs_q)
      if(!rs_q)begin
        drain_desc<=0;drain_reads<=0;drain_credits<=0;
        drain_fault_core<=0;idle_core_r<=0;
      end else begin
        case({dc_push,dc_pop})
          2'b10:drain_desc<=drain_desc+16'd1;
          2'b01:drain_desc<=drain_desc-16'd1;
          default:;
        endcase
        case({dr_push,dr_pop})
          2'b10:drain_reads<=drain_reads+16'd1;
          2'b01:drain_reads<=drain_reads-16'd1;
          default:;
        endcase
        case({dq_push,dq_pop})
          2'b10:drain_credits<=drain_credits+16'd1;
          2'b01:drain_credits<=drain_credits-16'd1;
          default:;
        endcase
        if((dc_pop&&!dc_push&&drain_desc==0)||
           (dr_pop&&!dr_push&&drain_reads==0)||
           (dq_pop&&!dq_push&&drain_credits==0)||
           (dc_push&&!dc_pop&&drain_desc==16'hffff)||
           (dr_push&&!dr_pop&&drain_reads==16'hffff)||
           (dq_push&&!dq_pop&&drain_credits==16'hffff))drain_fault_core<=1;
        if(DRAIN_PIPE!=0)idle_core_r<=core_debt_zero_q&&(&core_quiet_q)&&!core_drain_activity_q&&
          !drain_fault_core&&!completion_fault&&!f_core&&!native_intake_fault;
        else idle_core_r<=drain_desc==0&&drain_reads==0&&drain_credits==0&&
          !es_v_q&&!completion_v&&!e_v&&!er_v&&!s_credit&&!er_cr&&
          !drain_fault_core&&!completion_fault&&!f_core&&!native_intake_fault;
      end
endmodule
