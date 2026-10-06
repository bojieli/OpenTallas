`timescale 1ns/1ps
// Lockstep bench: ot_gpu_coll_mux_f12 vs ot_gpu_coll_mux (NSM 2 and 4, NL 128) on random request/response traffic,
// every output compared every cycle.  Prints MUXLS owner64=%0d nsm=<n> cycles=<c> grants=<g> mismatches=<m>.
module tb_coll_mux_owner64_ls #(parameter integer OWNER64=0);
    localparam integer NL = 128;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    integer cyc = 0;
    genvar gi;
    for (gi = 0; gi < 2; gi = gi + 1) begin : g_cfg
        localparam integer NSM = (gi == 0) ? 2 : 4;
        reg  [NSM-1:0] s_req_v, s_mode, s_rsp_rdy;
        reg  [NSM*8-1:0] s_count;
        reg  [NSM*NL*32-1:0] s_data;
        reg  m_req_rdy, m_rsp_v;
        reg  [NL*32-1:0] m_rsp_data;
        wire [NSM-1:0] a_rdy, b_rdy, a_rv, b_rv;
        wire [NL*32-1:0] a_rd, b_rd, a_md, b_md;
        wire a_mv, b_mv, a_mm, b_mm, a_mr, b_mr;
        wire [7:0] a_mc, b_mc;
        ot_gpu_coll_mux #(.ENABLE(1), .NSM(NSM), .NL(NL)) ua (.clk(clk), .rst_n(rst_n), .s_req_v(s_req_v),
            .s_req_rdy(a_rdy), .s_mode(s_mode), .s_count(s_count), .s_data(s_data), .s_rsp_v(a_rv), .s_rsp_rdy(s_rsp_rdy),
            .s_rsp_data(a_rd), .m_req_v(a_mv), .m_req_rdy(m_req_rdy), .m_mode(a_mm), .m_count(a_mc), .m_data(a_md),
            .m_rsp_v(m_rsp_v), .m_rsp_rdy(a_mr), .m_rsp_data(m_rsp_data));
        ot_gpu_coll_mux_owner64 #(.OWNER64(OWNER64), .ENABLE(1), .NSM(NSM), .NL(NL)) ub (.clk(clk), .rst_n(rst_n), .s_req_v(s_req_v),
            .s_req_rdy(b_rdy), .s_mode(s_mode), .s_count(s_count), .s_data(s_data), .s_rsp_v(b_rv), .s_rsp_rdy(s_rsp_rdy),
            .s_rsp_data(b_rd), .m_req_v(b_mv), .m_req_rdy(m_req_rdy), .m_mode(b_mm), .m_count(b_mc), .m_data(b_md),
            .m_rsp_v(m_rsp_v), .m_rsp_rdy(b_mr), .m_rsp_data(m_rsp_data));
        integer mis = 0, grants = 0;
        always @(negedge clk) begin   // drive random inputs away from the edge
            s_req_v <= $urandom; s_mode <= $urandom; s_rsp_rdy <= $urandom;
            for (integer i = 0; i < NSM * 8; i = i + 32) s_count[i +: 8] <= $urandom;
            for (integer i = 0; i < NSM; i = i + 1) s_count[i*8 +: 8] <= $urandom;
            for (integer i = 0; i < NSM * NL; i = i + 1) s_data[32*i +: 32] <= $urandom;
            for (integer i = 0; i < NL; i = i + 1) m_rsp_data[32*i +: 32] <= $urandom;
            m_req_rdy <= $urandom; m_rsp_v <= $urandom;
        end
        always @(posedge clk) if (rst_n) begin
            if (a_mv && m_req_rdy) grants = grants + 1;
            if ({a_rdy, a_rv, a_rd, a_mv, a_mm, a_mr, a_mc} !== {b_rdy, b_rv, b_rd, b_mv, b_mm, b_mr, b_mc} ||
                (a_mv && a_md !== b_md)) begin
                mis = mis + 1;
                if (mis < 4) $display("MUXLSMISMATCH nsm=%0d cyc=%0d", NSM, cyc);
            end
        end
        final $display("MUXLS owner64=%0d nsm=%0d cycles=%0d grants=%0d mismatches=%0d", OWNER64, NSM, cyc, grants, mis);
    end
    initial begin
        repeat (5) @(posedge clk);
        rst_n = 1;
        repeat (200000) begin @(posedge clk); cyc = cyc + 1; end
        $finish;
    end
endmodule
