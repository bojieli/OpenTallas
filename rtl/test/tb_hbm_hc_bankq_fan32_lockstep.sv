`timescale 1ns/1ps
`default_nettype none
// STEWARD-HBMe/HC 10-23: lockstep proof FAN32 = 0 (canonical ot_hbm_hc_bankq_core) vs FAN32 = 1 (ot_hbm_hc_bankrc_core
// with every clock entry tied to clk) for the three die-bound bank tops.  Identical random stimulus (reset, descriptors,
// beats, write/read controls, chain inputs) into both; EVERY output bit compared with !== on EVERY edge.
//   +define+VAR=0 bankq (CPI=CPO=1, die b1/b3/b4/b5)   VAR=1 bankq_ft (die b2/b6)   VAR=2 bankq0 (DRLY 1, CPO 1, die b0)
//   +define+MUTB=k : MUT k on the FAN32=1 side only (2 = landing copy 5 writes the next hold slot -> must FAIL)
// PASS line: HCB_FAN32_LOCKSTEP PASS var=<v> cycles=<n> compared=<bits*edges>; FAIL: HCB_FAN32_LOCKSTEP FAIL ...
`ifndef VAR
`define VAR 0
`endif
`ifndef MUTB
`define MUTB 0
`endif
`ifndef NCYC
`define NCYC 20000
`endif
module tb_hbm_hc_bankq_fan32_lockstep;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg d_v, d_ss; reg [6:0] d_nv; reg [9:0] d_wa, d_xa;
    reg [2047:0] sum_in; reg f_in;
    reg xb_v; reg [1:0] xb_beat; reg [255:0] xb_d;
    reg wv, xv, j; reg [9:0] wa;
    reg [2048:0] s_i;
    reg fa_xb_v, fb_xb_v, fa_wv, fb_wv, fa_xv, fb_xv, fa_j, fb_j, fa_rst_n, fb_rst_n, fa_wfault, fb_wfault;
    reg [1:0] fa_xb_beat, fb_xb_beat; reg [255:0] fa_xb_d, fb_xb_d; reg [9:0] fa_wa, fb_wa;
    localparam integer OW = 1 + 1 + 7 + 10 + 10 + 2048 + 1 + 1 + 2049 + 2 * (1 + 2 + 256 + 1 + 1 + 1 + 10 + 1 + 1);
    wire [OW-1:0] oa, ob;
    task automatic rnd;
        integer k;
        begin
            d_v = $urandom; d_ss = $urandom; d_nv = $urandom; d_wa = $urandom; d_xa = $urandom; f_in = $urandom;
            for (k = 0; k < 64; k = k + 1) sum_in[k*32 +: 32] = $urandom;
            for (k = 0; k < 64; k = k + 1) s_i[k*32 +: 32] = $urandom;
            s_i[2048] = $urandom;
            xb_v = $urandom; xb_beat = $urandom; for (k = 0; k < 8; k = k + 1) xb_d[k*32 +: 32] = $urandom;
            wv = $urandom; xv = $urandom; j = $urandom; wa = $urandom;
            {fa_xb_v, fb_xb_v, fa_wv, fb_wv, fa_xv, fb_xv, fa_j, fb_j, fa_wfault, fb_wfault} = $urandom;
            fa_rst_n = rst_n; fb_rst_n = rst_n;
            fa_xb_beat = $urandom; fb_xb_beat = $urandom; fa_wa = $urandom; fb_wa = $urandom;
            for (k = 0; k < 8; k = k + 1) begin fa_xb_d[k*32 +: 32] = $urandom; fb_xb_d[k*32 +: 32] = $urandom; end
        end
    endtask
    genvar s;
    for (s = 0; s < 2; s = s + 1) begin : g_side
        localparam integer F = s, M = (s == 1) ? `MUTB : 0;
        wire o_v, o_ss, f_out, wfault; wire [6:0] o_nv; wire [9:0] o_wa, o_xa; wire [2047:0] sum_out; wire [2048:0] s_o;
        wire fa_xb_v_o, fb_xb_v_o, fa_wv_o, fb_wv_o, fa_xv_o, fb_xv_o, fa_j_o, fb_j_o, fa_rst_n_o, fb_rst_n_o;
        wire fa_wfault_o, fb_wfault_o; wire [1:0] fa_xb_beat_o, fb_xb_beat_o; wire [255:0] fa_xb_d_o, fb_xb_d_o;
        wire [9:0] fa_wa_o, fb_wa_o;
        if (`VAR == 0) begin : g_q
            ot_hbm_hc_bankq_static #(.MUT(M), .CPI(1), .CPO(1), .FAN32(F)) dut (.clk(clk), .rst_n(rst_n),
                .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv),
                .o_wa(o_wa), .o_xa(o_xa), .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out),
                .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault));
            assign s_o = '0;
            assign {fa_xb_v_o, fb_xb_v_o, fa_wv_o, fb_wv_o, fa_xv_o, fb_xv_o, fa_j_o, fb_j_o, fa_rst_n_o, fb_rst_n_o,
                    fa_wfault_o, fb_wfault_o, fa_xb_beat_o, fb_xb_beat_o, fa_xb_d_o, fb_xb_d_o, fa_wa_o, fb_wa_o} = '0;
        end else if (`VAR == 1) begin : g_ft
            ot_hbm_hc_bankq_ft_static #(.MUT(M), .FAN32(F)) dut (.clk(clk), .rst_n(rst_n),
                .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv),
                .o_wa(o_wa), .o_xa(o_xa), .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out),
                .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault),
                .fa_xb_v(fa_xb_v), .fa_xb_beat(fa_xb_beat), .fa_xb_d(fa_xb_d), .fa_wv(fa_wv), .fa_xv(fa_xv), .fa_j(fa_j),
                .fa_wa(fa_wa), .fa_xb_v_o(fa_xb_v_o), .fa_xb_beat_o(fa_xb_beat_o), .fa_xb_d_o(fa_xb_d_o),
                .fa_wv_o(fa_wv_o), .fa_xv_o(fa_xv_o), .fa_j_o(fa_j_o), .fa_wa_o(fa_wa_o),
                .fb_xb_v(fb_xb_v), .fb_xb_beat(fb_xb_beat), .fb_xb_d(fb_xb_d), .fb_wv(fb_wv), .fb_xv(fb_xv), .fb_j(fb_j),
                .fb_wa(fb_wa), .fb_xb_v_o(fb_xb_v_o), .fb_xb_beat_o(fb_xb_beat_o), .fb_xb_d_o(fb_xb_d_o),
                .fb_wv_o(fb_wv_o), .fb_xv_o(fb_xv_o), .fb_j_o(fb_j_o), .fb_wa_o(fb_wa_o),
                .fa_rst_n(fa_rst_n), .fb_rst_n(fb_rst_n), .fa_rst_n_o(fa_rst_n_o), .fb_rst_n_o(fb_rst_n_o),
                .fa_wfault(fa_wfault), .fb_wfault(fb_wfault), .fa_wfault_o(fa_wfault_o), .fb_wfault_o(fb_wfault_o));
            assign s_o = '0;
        end else begin : g_b0
            ot_hbm_hc_bankq0_static #(.MUT(M), .DRLY(1), .CPO(1), .FAN32(F)) dut (.clk(clk), .rst_n(rst_n),
                .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv),
                .o_wa(o_wa), .o_xa(o_xa), .sum_out(sum_out), .f_out(f_out),
                .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault),
                .s_i(s_i), .s_o(s_o));
            assign {fa_xb_v_o, fb_xb_v_o, fa_wv_o, fb_wv_o, fa_xv_o, fb_xv_o, fa_j_o, fb_j_o, fa_rst_n_o, fb_rst_n_o,
                    fa_wfault_o, fb_wfault_o, fa_xb_beat_o, fb_xb_beat_o, fa_xb_d_o, fb_xb_d_o, fa_wa_o, fb_wa_o} = '0;
        end
        wire [OW-1:0] o = {o_v, o_ss, o_nv, o_wa, o_xa, sum_out, f_out, wfault, s_o,
                           fa_xb_v_o, fa_xb_beat_o, fa_xb_d_o, fa_wv_o, fa_xv_o, fa_j_o, fa_wa_o, fa_rst_n_o, fa_wfault_o,
                           fb_xb_v_o, fb_xb_beat_o, fb_xb_d_o, fb_wv_o, fb_xv_o, fb_j_o, fb_wa_o, fb_rst_n_o, fb_wfault_o};
    end
    assign oa = g_side[0].o; assign ob = g_side[1].o;
    integer cyc = 0, bad = 0, first_bad = -1, active = 0;
    longint compared = 0;
    initial begin
        rnd();
        repeat (12) @(posedge clk);
        #0.1 rst_n = 1;
    end
    always @(negedge clk) begin
        if (rst_n) begin
            if (oa !== ob) begin
                bad = bad + 1;
                if (first_bad < 0) first_bad = cyc;
                if (bad <= 4) for (integer b = 0; b < OW; b = b + 1) if (oa[b] !== ob[b])
                    $display("HCB_FAN32_DIFF cyc=%0d bit=%0d a=%b b=%b", cyc, b, oa[b], ob[b]);
            end
            if (oa[OW-1 -: 1] === 1'b1 || |oa[OW-20 -: 2048]) active = active + 1;
            compared = compared + OW;
        end
        rnd();
        cyc = cyc + 1;
        if (cyc == `NCYC) begin
            if (bad == 0) $display("HCB_FAN32_LOCKSTEP PASS var=%0d mutb=%0d cycles=%0d compared=%0d active_edges=%0d", `VAR, `MUTB, cyc, compared, active);
            else $display("HCB_FAN32_LOCKSTEP FAIL var=%0d mutb=%0d cycles=%0d mismatching_edges=%0d first=%0d", `VAR, `MUTB, cyc, bad, first_bad);
            $finish;
        end
    end
endmodule
`default_nettype wire
