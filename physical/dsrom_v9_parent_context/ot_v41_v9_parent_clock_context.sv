`timescale 1ns/1ps
// Source register projection, NOT a reduced q-element or a full field.
// v9 f284118df broadcast/loader/root captures; QX10 0032b7355
// g_qb/g_ir/g_qz_cg/g_mz/g_qo and o_* register edges. Remaining engine
// cones are explicit clock-related terminals. The entire Z18 frame is reserved.
module ot_v41_v9_parent_clock_context (
    input wire clk, rst_n,
    input wire [1629:0] broadcast_source,
    input wire [47:0] cfg_rom_q,
    input wire walk_busy, drain_gt1, qz_en_r, qz_ext_lo,
    input wire [1:0] tree_valid, tree_idle,
    input wire [123:0] tree_payload,
    input wire busy_source, frontend_fault_source,
    input wire [1:0] bank_fault_source,
    input wire root_v, root_e,
    input wire [15:0] root_row, root_bf,
    input wire [2:0] root_pos,
    input wire [31:0] root_fp32,
    output wire [1629:0] f_bus,
    output wire [53:0] engine_cfg,
    output wire [7:0] engine_cdec,
    output wire [2:0] engine_go,
    output wire [548:0] engine_xs,
    output wire engine_clk,
    output wire [7:0] engine_reset_n,
    output wire node_v, node_e,
    output wire [31:0] node_t, node_d,
    output wire busy, fault,
    output wire [66:0] captured_root
);
    wire cfg_go, go, go_bf, xs_v, xb_v;
    wire [5:0] cfg_ph;
    wire [2:0] cfg_np, xs_b, xs_pos, xb_pos, xb_b;
    wire [1:0] go_tag, xs_sv;
    wire [7:0] xs_p;
    wire [255:0] xs_q0, xs_q1;
    wire [9:0] xs_e0, xs_e1;
    wire [3:0] xb_sv;
    wire [31:0] xb_u;
    wire [1023:0] xb_d;
    // Literal v9 BW1630, BST2+RPT1. All source broadcast bits retained.
    wire [1629:0] bc;
    if (1) begin : u_sp
        if (1) begin : g_bst
            ot_hdc_delay #(.W(1630), .D(3), .RESET(1)) u_bst
                (.clk(clk), .rst_n(rst_n), .d(broadcast_source), .q(bc));
        end
    end
    assign f_bus=bc;
    assign {cfg_go,cfg_ph,cfg_np,go,go_bf,go_tag,xs_v,xs_p,xs_b,xs_sv,xs_q0,xs_e0,xs_q1,
            xs_e1,xs_pos,xb_pos,xb_v,xb_b,xb_sv,xb_u,xb_d}=bc;
    wire c_v, go_load, ld_busy, ld_fault;
    wire go_pin=go_load && !go_bf; // actual Q-only field-pair admission
    wire [4:0] c_a;
    wire [47:0] c_d;
    wire [10:0] cm_a;
    // Full source loader including finite state, class-valid admission and faults.
    // PQ0 is the baseline join; no unsupported PQ identity semantics invented.
    ot_v41_pair_pq_ld #(.PHW(6), .PQ(0)) u_ld (.clk(clk), .rst_n(rst_n),
        .cfg_go(cfg_go), .cfg_ph(cfg_ph), .cfg_np(cfg_np), .go(go),
        .e_sh_free(1'b1), .e_bank_free(1'b1), .cm_a(cm_a), .cm_q(cfg_rom_q),
        .c_v(c_v), .c_a(c_a), .c_d(c_d), .go_e(go_load), .ld_busy(ld_busy), .fault(ld_fault));
    wire [1:0] pv, perr;
    wire [63:0] pval;
    wire [31:0] prow;
    wire [9:0] pseg, pnseg;
    wire [5:0] ppos;
    wire q_fault;
    wire [1:0] bkf;
    if (1) begin : g_qx
        wire gclk, rst_q;
        if (1) begin : g_qb
            (* keep *) reg rst_reg;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) rst_reg<=0; else rst_reg<=1;
            assign rst_q=rst_reg;
            reg b_go,b_cfg_v,b_go_bf;
            reg [7:0] b_cdec;
            reg [4:0] b_cfg_a;
            reg [47:0] b_cfg_d;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) b_cdec<=0;
                else for (integer c=0;c<8;c=c+1) b_cdec[c]<=c_v && c_a==5'(8+c);
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin b_go<=0;b_cfg_v<=0;end
                else begin b_go<=go_pin;b_cfg_v<=c_v;end
            always @(posedge clk) begin b_cfg_a<=c_a;b_cfg_d<=c_d;b_go_bf<=go_bf;end
            if (1) begin : g_bx
                reg b_xs_v;
                reg [7:0] b_xs_p;
                reg [2:0] b_xs_b,b_xs_pos;
                reg [1:0] b_xs_sv;
                reg [255:0] b_xs_q0,b_xs_q1;
                reg [9:0] b_xs_e0,b_xs_e1;
                always @(posedge gclk or negedge rst_n)
                    if (!rst_n) b_xs_v<=0; else b_xs_v<=xs_v;
                always @(posedge gclk) begin
                    b_xs_p<=xs_p;b_xs_b<=xs_b;b_xs_sv<=xs_sv;b_xs_q0<=xs_q0;b_xs_e0<=xs_e0;
                    b_xs_q1<=xs_q1;b_xs_e1<=xs_e1;b_xs_pos<=xs_pos;
                end
                // Cut at the actual QPIPE XS boundary. The FAST g_ir XS
                // stage remains in the source-qualified engine dependency.
                assign engine_xs={b_xs_v,b_xs_p,b_xs_b,b_xs_sv,b_xs_q0,b_xs_e0,b_xs_q1,b_xs_e1,b_xs_pos};
            end
            // Config writes bypass FAST r_cfg_* in the actual selected source.
            assign engine_cfg={b_cfg_v,b_cfg_a,b_cfg_d};
            assign engine_cdec=b_cdec;
        end
        if (1) begin : g_ir
            wire gn,gw,gm;
            ot_v41_kreg #(.W(1),.AR(1)) u_gn(.clk(clk),.arst_n(rst_q),.d(g_qb.b_go),.q(gn));
            ot_v41_kreg #(.W(1),.AR(1)) u_gw(.clk(clk),.arst_n(rst_q),.d(g_qb.b_go),.q(gw));
            ot_v41_kreg #(.W(1),.AR(1)) u_gm(.clk(clk),.arst_n(rst_q),.d(g_qb.b_go),.q(gm));
            reg r_go;
            always @(posedge clk or negedge rst_q) if (!rst_q) r_go<=0;else r_go<=g_qb.b_go;
            assign engine_go={gn,gw,gm};
        end
        wire z_q;
        if (1) begin : g_qz_cg
            wire en_r_d=g_qb.b_go || g_ir.r_go || walk_busy || drain_gt1;
            wire z_d=go_pin || (rst_q && (en_r_d || g_qb.b_go || qz_en_r || qz_ext_lo));
            ot_v41_kreg #(.W(1),.AR(1),.RV(1'b1)) u_z(.clk(clk),.arst_n(rst_n),.d(z_d),.q(z_q));
        end
        if (1) begin : g_cg
            ot_hdc_cg u_cg(.clk(clk),.en(z_q),.gclk(gclk));
        end
        assign engine_clk=gclk;
        for (genvar m=0;m<2;m=m+1) begin : g_mac
            wire rs,rsc,rsp,rst;
            if (1) begin : g_mz
                ot_v41_kreg #(.W(1),.AR(1)) u_rs(.clk(clk),.arst_n(rst_n),.d(1'b1),.q(rs));
                ot_v41_kreg #(.W(1),.AR(1)) u_rsc(.clk(clk),.arst_n(rst_n),.d(1'b1),.q(rsc));
                ot_v41_kreg #(.W(1),.AR(1)) u_rsp(.clk(clk),.arst_n(rst_n),.d(1'b1),.q(rsp));
                ot_v41_kreg #(.W(1),.AR(1)) u_rst(.clk(clk),.arst_n(rst_n),.d(1'b1),.q(rst));
            end
            assign engine_reset_n[4*m+:4]={rst,rsp,rsc,rs};
            reg o_v,o_err;
            reg [31:0] o_val;
            reg [15:0] o_row;
            reg [4:0] o_seg,o_n;
            reg [2:0] o_pos;
            always @(posedge gclk or negedge rst)
                if (!rst) o_v<=0;else o_v<=tree_valid[m] && !tree_idle[m];
            // The terminal is the real remaining tree/config-mux output cone;
            // no arithmetic, identity width or rounding point is approximated.
            always @(posedge gclk) {o_val,o_row,o_seg,o_n,o_err,o_pos}<=tree_payload[62*m+:62];
            assign pv[m]=o_v;assign pval[32*m+:32]=o_val;assign prow[16*m+:16]=o_row;
            assign pseg[5*m+:5]=o_seg;assign pnseg[5*m+:5]=o_n;assign perr[m]=o_err;assign ppos[3*m+:3]=o_pos;
            reg bkf_r;
            always @(posedge clk or negedge rst) if (!rst) bkf_r<=0;else bkf_r<=bank_fault_source[m];
            assign bkf[m]=bkf_r;
        end
        if (1) begin : g_qo
            reg [1:0] busy_d,ff_d;
            reg ffq,fq;
            always @(posedge clk or negedge rst_q)
                if (!rst_q) begin busy_d<=0;ff_d<=0;ffq<=0;fq<=0;end
                else begin
                    busy_d<={busy_d[0],busy_source};ff_d<={ff_d[0],frontend_fault_source};
                    ffq<=ff_d[0];fq<=ffq || (|bkf);
                end
            assign busy=busy_d[0];assign q_fault=fq;
        end
    end
    wire [31:0] ta={ppos[2:0],prow[15:0],pseg[4:0],3'd0,pnseg[4:0]};
    wire [31:0] tb={ppos[5:3],prow[31:16],pseg[9:5],3'd0,pnseg[9:5]};
    wire node_fault;
    ot_v41_retn_w17w10 #(.RD(64),.RST(1),.BYPASS(1)) u_return
        (.clk(clk),.rst_n(rst_n),.a_v(pv[0]),.a_t(ta),.a_d(pval[31:0]),.a_e(perr[0]),
         .b_v(pv[1]),.b_t(tb),.b_d(pval[63:32]),.b_e(perr[1]),
         .o_v(node_v),.o_t(node_t),.o_d(node_d),.o_e(node_e),.fault(node_fault),.quiet());
    // Separate actual root-input cut: intermediate return levels remain outside
    // this minimum component. Do not connect the first node directly to the spine.
    wire p_v;
    wire [67:0] p_d;
    ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_prv(.clk(clk),.rst_n(rst_n),.d(root_v),.q(p_v));
    ot_hdc_delay #(.W(68),.D(1)) u_prd(.clk(clk),.rst_n(rst_n),
        .d({root_e,root_row,root_bf,root_pos,root_fp32}),.q(p_d));
    reg q0_v;
    reg [65:0] q0_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) q0_v<=0;else q0_v<=p_v;
    always @(posedge clk) q0_d<={p_d[67],p_d[64:51],p_d[50:0]}; // source q0_row is14 bits
    assign captured_root={q0_v,q0_d};
    reg sticky_fault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sticky_fault<=0;else if (q_fault || node_fault || ld_fault) sticky_fault<=1;
    assign fault=sticky_fault;
endmodule
