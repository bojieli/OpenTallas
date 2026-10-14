`timescale 1ns/1ps
`default_nettype none
// Distinct candidate exposing every actual leaf clock. All roots must share
// coherent engine edges with actual phi-R delivery; tied-clock simulation does
// not qualify clock delivery, reset routing, parent pins or absolute placement.
// Fixed production state LQ10/LD16/NB32/OD64/RQ16/SPAN1, frontend FACE_FF1,
// CORE FIN1 and write PAY/FIN split. FIN boundary remains unqualified.
module ot_hgi_qdq_q_pin4_clocks #(parameter integer MUT=0) (
    input  wire [13:0]       leaf_clk,
    input  wire              rst_n,
    input  wire [682:0]      rec,          // {n_O, n_A, desc_O, desc_A, header, valid} (hgi_die_dispatch 'quant')
    output wire [2:0]        ret,          // {fault, done, ready}
    output wire [8*16-1:0]   wrq,
    input  wire [7:0]        wrq_cr,
    input wire [513:0] wrr_p0, wrr_p1, wrr_p2, wrr_p3,
    output wire [8*280-1:0]  wwq,
    input  wire [7:0]        wwq_cr,
    input  wire [7:0]        wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);

`ifdef OT_HARD_CHILDREN
    initial $fatal(1,"candidate CORE/PAY/FIN bindings and geometry remain unqualified; no old hard view substitution");
`endif
    wire[2055:0]wrr={wrr_p3,wrr_p2,wrr_p1,wrr_p0};
    wire s1_v, s3_v, nfault; wire [189:0] s3;
    wire [7:0] c_pop, e_push; wire [3:0] e_ovf; wire [8*256-1:0] hq; wire [3:0] lq_rst_n; wire dec_rst_n, asm_rst_n, wr_rst_n;
    wire d_v, vo, qfault, dfault; wire [17:0] d_hd; wire [1023:0] d_x; wire [511:0] y;
    wire [127:0] d_h = {d_hd[17:8], 46'd0, d_hd[7:0], 64'd0};   // the decode's only header fields (constants are wires)
    wire bp_v, a_fire, a_bad_c, a_bad_w, a_idle, m_v, w_wf, w_fin, w_bad, w_idle, c_act;
    wire [39:0] bp; wire [7:0] a_pop; wire [18:0] m;
    wire gs1,gv,gfault,fs1,one_s1,ffault,overflow;wire[189:0]gp_front,fp_front;
    ot_hgi_qdq_fr u_general(.clk(leaf_clk[7]),.rst_n(rst_n),.rec(rec),.s1_v(gs1),.s3_v(gv),.s3(gp_front),.nfault(gfault));
    ot_hgi_qdq_fr_one_payload_face u_one(.clk(leaf_clk[8]),.rst_n(rst_n),.rec(rec),.s1_v(fs1),.one_s1(one_s1),.payload(fp_front),.nfault(ffault));
    ot_hgi_qdq_fr_capture_retire u_retire(.clk(leaf_clk[9]),.rst_n(rst_n),.accept(fs1),.accept_one(one_s1),.fast_payload(fp_front),
      .general_v(gv),.general_payload(gp_front),.s3_v(s3_v),.s3(s3),.overflow(overflow));
    assign s1_v=fs1;assign nfault=gfault|ffault|overflow;
    ot_hgi_qdq_core #(.LQ(10), .LD(16), .NB(32), .RQ(16), .SPANPIPE(1), .MUT(MUT), .FIN_BYPASS(1)) u_core (
        .clk(leaf_clk[10]), .rst_n(rst_n), .i_s1_v(s1_v), .i_s3_v(s3_v), .i_s3(s3), .i_nfault(nfault), .ret(ret), .wrq(wrq),
        .wrq_cr(wrq_cr), .rg_req(rg_req), .rg_gnt(rg_gnt), .asm_rst_n(asm_rst_n), .bp_v(bp_v), .bp(bp), .i_pop(a_pop),
        .i_fire(a_fire), .i_abad(a_bad_c), .i_aidle(a_idle), .o_act(c_act), .i_fin(w_fin), .i_wbad(w_bad), .i_widle(w_idle));
    ot_hgi_qdq_asm #(.LD(16), .NB(32), .OD(64), .MUT(MUT)) u_asm (
        .clk(leaf_clk[11]), .rst_n(asm_rst_n), .bp_v(bp_v), .bp(bp), .hq_p0(hq[511:0]), .hq_p1(hq[1023:512]),
        .hq_p2(hq[1535:1024]), .hq_p3(hq[2047:1536]), .e_push(e_push), .e_ovf(e_ovf), .c_pop(c_pop),
        .lq_rst_n(lq_rst_n), .dec_rst_n(dec_rst_n), .wr_rst_n(wr_rst_n), .d_v(d_v), .d_hd(d_hd), .d_x(d_x), .o_pop(a_pop),
        .o_fire(a_fire), .o_bad_c(a_bad_c), .o_idle(a_idle), .m_v(m_v), .m(m), .o_bad_w(a_bad_w), .i_wf(w_wf));
    ot_hgi_qdq_wr_split #(.LQ(10),.OD(64),.RQ(16))u_wr(
        .clk_pay(leaf_clk[12]),.clk_fin(leaf_clk[13]),.rst_n(wr_rst_n),.m_v(m_v),.m(m),.i_bad(a_bad_w),.vo(vo),.qfault(qfault),.dfault(dfault),.y(y),
        .wwq(wwq),.wwq_cr(wwq_cr),.wwq_done(wwq_done),.wg_req(wg_req),.wg_gnt(wg_gnt),.i_act(c_act),.o_wf(w_wf),
        .o_fin(w_fin),.o_bad(w_bad),.o_idle(w_idle),.pay_bad(),.fin_bad());
    genvar gp;
    generate for (gp = 0; gp < 4; gp = gp + 1) begin : g_lq
        ot_hgi_qdq_lq u_lq (.clk(leaf_clk[3+gp]), .rst_n(lq_rst_n[gp]), .wrr(wrr[gp*2*257 +: 2*257]), .c_pop(c_pop[gp*2 +: 2]),
            .hq(hq[gp*512 +: 512]), .e_push(e_push[gp*2 +: 2]), .e_ovf(e_ovf[gp]));
    end endgenerate
    wire[17:0]hd={d_h[127:118],d_h[71:64]};wire[1023:0]xs,xb,xa;wire bvo,bfo;wire[511:0]byo;
    ot_hgi_qw_dxl u_dxl(.clk(leaf_clk[0]),.x(d_x),.xs(xs),.xb(xb),.xa(xa));
    ot_hgi_qw_dbq u_dbq(.clk(leaf_clk[1]),.rst_n(dec_rst_n),.v(d_v),.hd(hd),.xs(xs),.xb(xb),.bvo(bvo),.bfo(bfo),.byo(byo));
    ot_hgi_qw_daq u_daq(.clk(leaf_clk[2]),.rst_n(dec_rst_n),.v(d_v),.hd(hd),.xs(xs),.xa(xa),.bvo(bvo),.bfo(bfo),.byo(byo),.vo(vo),.y(y),.fault(qfault),.decode_fault(dfault));
endmodule
`default_nettype wire
