`timescale 1ns/1ps
// Minimum native parent: one complete element, never an engine projection.
// QX remains opt-in. Physical characterization selects QX=10 explicitly.
module ot_v41_qx10_native_parent #(parameter integer QX=0) (
    input wire clk, rst_n,
    input wire [1629:0] broadcast_source,
    input wire [47:0] cfg_rom_q,
    input wire root_v, root_e,
    input wire [15:0] root_row, root_bf,
    input wire [2:0] root_pos,
    input wire [31:0] root_fp32,
    output wire [1629:0] f_bus,
    output wire [10:0] cfg_rom_a,
    output wire node_v, node_e,
    output wire [31:0] node_t, node_d,
    output wire busy, fault,
    output wire [66:0] captured_root
);
    wire cfg_go,go,go_bf,xs_v,xb_v;
    wire [5:0] cfg_ph;
    wire [2:0] cfg_np,xs_b,xs_pos,xb_pos,xb_b;
    wire [1:0] go_tag,xs_sv;
    wire [7:0] xs_p;
    wire [255:0] xs_q0,xs_q1;
    wire [9:0] xs_e0,xs_e1;
    wire [3:0] xb_sv;
    wire [31:0] xb_u;
    wire [1023:0] xb_d;
    wire [1629:0] bc;
    if (1) begin : u_sp
        if (1) begin : g_bst
            ot_hdc_delay #(.W(1630),.D(3),.RESET(1)) u_bst
                (.clk(clk),.rst_n(rst_n),.d(broadcast_source),.q(bc));
        end
    end
    assign f_bus=bc;
    assign {cfg_go,cfg_ph,cfg_np,go,go_bf,go_tag,xs_v,xs_p,xs_b,xs_sv,xs_q0,xs_e0,xs_q1,
            xs_e1,xs_pos,xb_pos,xb_v,xb_b,xb_sv,xb_u,xb_d}=bc;
    wire c_v,go_load,ld_busy,ld_fault;
    wire [4:0] c_a;
    wire [47:0] c_d;
    // Copernicus's r3 lowering fix makes the existing reset-only hold explicit;
    // no new fault mode, constant-fault substitution or pipeline edge.
    ot_v41_pair_pq_ld_frontend #(.PHW(6),.PQ(0)) u_ld
        (.clk(clk),.rst_n(rst_n),.cfg_go(cfg_go),.cfg_ph(cfg_ph),.cfg_np(cfg_np),.go(go),
         .e_sh_free(1'b1),.e_bank_free(1'b1),.cm_a(cfg_rom_a),.cm_q(cfg_rom_q),
         .c_v(c_v),.c_a(c_a),.c_d(c_d),.go_e(go_load),.ld_busy(ld_busy),.fault(ld_fault));
    wire [1:0] pv,perr;
    wire [63:0] pval;
    wire [31:0] prow;
    wire [9:0] pseg,pnseg;
    wire [5:0] ppos;
    wire q_fault;
    // Selected source owns the ICG, free/gated control, arithmetic and FOUR
    // g_mac[0/1].g_pp.u_rom[0/1] real 4096-row macros. No cut-engine ports.
    ot_v41_rom_elem_q_qx_w10 #(.NB(2),.MTP(1),.EARLY(1),.FAST(1),.PP(1),.FRONT_PAR(0),
        .QTIMING_FIX(1),.QPIPE(1),.QP_XS(1),.QP_CAP(0),.QP_P1(1),.QP_CSAM(10),
        .QZ(1),.QZ_NS(8),.QZ_NE(4),.QY(1),.QX(QX)) u_qx
        (.clk(clk),.rst_n(rst_n),.cfg_v(c_v),.cfg_a(c_a),.cfg_d(c_d),
         .go(go_load && !go_bf),.xs_v(xs_v),.xs_p(xs_p),.xs_b(xs_b),.xs_sv(xs_sv),
         .xs_q0(xs_q0),.xs_e0(xs_e0),.xs_q1(xs_q1),.xs_e1(xs_e1),.xs_pos(xs_pos),
         .pv(pv),.pval(pval),.prow(prow),.pseg(pseg),.pnseg(pnseg),.perr(perr),.ppos(ppos),
         .busy(busy),.fault(q_fault));
    wire [31:0] ta={ppos[2:0],prow[15:0],pseg[4:0],3'd0,pnseg[4:0]};
    wire [31:0] tb={ppos[5:3],prow[31:16],pseg[9:5],3'd0,pnseg[9:5]};
    wire node_fault;
    ot_v41_retn_w17w10 #(.RD(64),.RST(1),.BYPASS(1)) u_return
        (.clk(clk),.rst_n(rst_n),.a_v(pv[0]),.a_t(ta),.a_d(pval[31:0]),.a_e(perr[0]),
         .b_v(pv[1]),.b_t(tb),.b_d(pval[63:32]),.b_e(perr[1]),
         .o_v(node_v),.o_t(node_t),.o_d(node_d),.o_e(node_e),.fault(node_fault),.quiet());
    // Root-input capture is a separate native cut; the first return node
    // does not stand in for the omitted intermediate return network.
    wire p_v;
    wire [67:0] p_d;
    ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_prv(.clk(clk),.rst_n(rst_n),.d(root_v),.q(p_v));
    ot_hdc_delay #(.W(68),.D(1)) u_prd(.clk(clk),.rst_n(rst_n),
        .d({root_e,root_row,root_bf,root_pos,root_fp32}),.q(p_d));
    reg q0_v;
    reg [65:0] q0_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) q0_v<=0;else q0_v<=p_v;
    always @(posedge clk) q0_d<={p_d[67],p_d[64:51],p_d[50:0]};
    assign captured_root={q0_v,q0_d};
    reg sticky_fault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sticky_fault<=0;
        else if (q_fault || node_fault || ld_fault) sticky_fault<=1;
    assign fault=sticky_fault;
endmodule
