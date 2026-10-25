`timescale 1ns/1ps
// S81-P9-FACE/CAPC: ot_s81sl_capc5r (8 lanes, absent lanes driven 0 as the die did) vs ot_s81sl_capc5r_n #(NRT)
// (absent lanes do not exist).  Random traffic on the present lanes (valid + rst bits set ~half the cycles), random cfg.
// Every output compared every cycle after reset release.  PASS = 0 mismatches.
module tb_capc5r_n_eq (input wire clk);
    parameter integer NRT = 3;
    parameter integer CYC = 6000;
    reg rst_n;
    integer c = 0;
    reg [559:0] rt8; reg cfg_v; reg [159:0] cfg_d;
    wire [5:0] a_sv, b_sv; wire [71:0] a_sa, b_sa; wire [191:0] a_sd, b_sd;
    wire [3:0] a_nv, b_nv; wire [47:0] a_na, b_na; wire [127:0] a_nd, b_nd; wire a_f, b_f;
    ot_s81sl_capc5r u_a (.rt_w(rt8[279:0]), .rt_e(rt8[559:280]), .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_s_v(a_sv), .cw_s_a(a_sa), .cw_s_d(a_sd), .cw_n_v(a_nv), .cw_n_a(a_na), .cw_n_d(a_nd), .fault(a_f),
        .ck_rt(clk), .ck_cw(clk), .ck_ce(clk), .ck_rn(clk), .ck_rs(clk),
        .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_ce(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n));
    ot_s81sl_capc5r_n #(.NRT(NRT)) u_b (.rt(rt8[70*NRT-1:0]), .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_s_v(b_sv), .cw_s_a(b_sa), .cw_s_d(b_sd), .cw_n_v(b_nv), .cw_n_a(b_na), .cw_n_d(b_nd), .fault(b_f),
        .ck_rt(clk), .ck_cw(clk), .ck_ce(clk), .ck_rn(clk), .ck_rs(clk),
        .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_ce(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n));
    integer l, mis = 0, act = 0, vs = 0, aw = 0, ae = 0;
    reg [69:0] lw;
    always @(negedge clk) begin
        rt8 = 560'd0;
        for (l = 0; l < NRT; l = l + 1) begin
            lw = {$random, $random, $random};
            lw[0] = (c > 40); lw[1] = ($random & 1) && (c > 60);
            lw[67] = 1'b0; lw[69] = 1'b0;              // no injected lane error / fault
            rt8[70*l +: 70] = lw;
        end
        cfg_v = (($random & 63) == 0); cfg_d = {$random, $random, $random, $random, $random};
    end
    always @(posedge clk) if (c > 30) begin
        if ({a_sv, a_sa, a_sd, a_nv, a_na, a_nd, a_f} !== {b_sv, b_sa, b_sd, b_nv, b_na, b_nd, b_f}) begin
            mis = mis + 1;
            if (mis < 5) $display("MISMATCH c=%0d sv %h/%h nv %h/%h f %b/%b", c, a_sv, b_sv, a_nv, b_nv, a_f, b_f);
        end
        if ({u_a.w_v, u_a.w_t, u_a.w_d, u_a.w_e, u_a.w_f} !== {u_b.w_v, u_b.w_t, u_b.w_d, u_b.w_e, u_b.w_f}) begin
            mis = mis + 1; if (mis < 5) $display("W-TREE MISMATCH c=%0d", c);
        end
        if ({u_a.e_v__l_rt, u_a.e_t__l_rt, u_a.e_d__l_rt, u_a.e_e__l_rt, u_a.e_f__l_rt} !==
            {u_b.e_v__l_rt, u_b.e_t__l_rt, u_b.e_d__l_rt, u_b.e_e__l_rt, u_b.e_f__l_rt}) begin
            mis = mis + 1; if (mis < 5) $display("E-WORD MISMATCH c=%0d", c);
        end
        if (u_a.w_v) aw = aw + 1;
        if (u_a.e_v__l_rt) ae = ae + 1;
        if (|a_sv || |a_nv) act = act + 1;
        if (a_f) vs = vs + 1;
    end
    always @(posedge clk) begin
        c <= c + 1;
        rst_n <= (c >= 8);
        if (c == CYC) begin
            $display("NRT=%0d cycles=%0d mismatches=%0d w_tree_valid=%0d e_word_valid=%0d cw_out_valid=%0d fault_cycles=%0d %s", NRT, CYC, mis, aw, ae, act, vs,
                     (mis == 0 && aw > 0 && (NRT <= 4 || ae > 0)) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
