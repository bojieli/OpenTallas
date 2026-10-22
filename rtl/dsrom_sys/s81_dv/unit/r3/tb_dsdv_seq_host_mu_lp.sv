`timescale 1ns/1ps
// STW-S81c-COLLA3 10-22: lockstep dsdv_seq_host_mu_lp (exact dsdv_seq_host_mu ports) against the reference
// dsdv_seq_host_mu built on the r3_lp compiler re-schedule: dsdv_seq_host_c_r3_rsref (lp.py reference, +2 edges per landed
// crossing) + dsdv_mu_hslot NSLOT 47, both on rst_n delayed RD = face landing 2 + relay 4 + core RB 4 = 10 edges (rev2).  The rev2 hslot relay
// stage moves the hslot timeline +1 edge, so t_kd / t_mf are compared against the reference delayed by exactly 1 edge.  Every output port,
// including t_kd (hslot slot word) and t_mf, is compared every cycle after warm-up.  Mutants: MU_LP_MUT 1 (hslot reset
// epoch slip), 2 (t_kd without slot word), LPMUT (r3_lp landing mutant -> MUT of u_core).
module tb_dsdv_seq_host_mu_lp;
    parameter integer MU_LP_MUT = 0, LPMUT = 0, NC = 8000, SEED = 1;
    localparam integer V = 276, RD = 10, WARM = 32 + RD + 24, BOOT0 = 32 + RD - 2, GAP = 48, RLW = 100, ST0 = BOOT0 + 64;
    reg clk = 1'b0;  always #0.5 clk = ~clk;
    reg rst = 1'b0;  reg [RD-1:0] rst_dl = 0;
    always @(posedge clk) rst_dl <= {rst_dl[RD-2:0], rst};
    wire rst_f = rst_dl[RD-1];
    reg [7:0] tap_k, sink_k; reg [V-1:0] vi_s, vi_n; reg [514:0] f_host; reg [3:0] f_lf; reg [52:0] f_ks; reg [25:0] f_mc;
    reg [1:0] s_jd_w, s_jd_e, st_rg_w, st_rg_e; reg [8:0] s_hc_w, s_hc_e;
    wire [V-1:0] l_vo_s, l_vo_n, r_vo_s, r_vo_n; wire [76:0] l_t_host, r_t_host; wire [53:0] l_t_kd, r_t_kd, r_kd;
    wire [3:0] l_t_mf, r_t_mf; wire [32:0] l_s_j, r_s_j; wire [291:0] l_s_hw_w, l_s_hw_e, r_s_hw_w, r_s_hw_e;
    wire l_cw_v, r_cw_v; wire [9:0] l_cw_a, r_cw_a; wire [255:0] l_cw_d, r_cw_d; wire [31:0] r_ku;
    dsdv_seq_host_mu_lp #(.V(V), .NSLOT(47), .MUT(LPMUT), .MU_LP_MUT(MU_LP_MUT)) u_lp (.ck(clk), .rst_n(rst),
        .tap_k(tap_k), .sink_k(sink_k), .vi_s(vi_s), .vo_s(l_vo_s), .vi_n(vi_n), .vo_n(l_vo_n), .f_host(f_host), .t_host(l_t_host),
        .f_lf(f_lf), .f_ks(f_ks), .t_kd(l_t_kd), .f_mc(f_mc), .t_mf(l_t_mf), .s_j(l_s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e),
        .s_hw_w(l_s_hw_w), .s_hw_e(l_s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e),
        .cw_v(l_cw_v), .cw_a(l_cw_a), .cw_d(l_cw_d));
    dsdv_seq_host_c_r3_rsref #(.V(V), .STAGE(0), .RL(1), .CHILD_MUT(0)) u_ref (.ck(clk), .rst_n(rst_f), .tap_k(tap_k),
        .sink_k(sink_k), .vi_s(vi_s), .vi_n(vi_n), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e),
        .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .vo_s(r_vo_s), .vo_n(r_vo_n), .t_host(r_t_host),
        .t_kd(r_kd), .s_j(r_s_j), .s_hw_w(r_s_hw_w), .s_hw_e(r_s_hw_e), .cw_v(r_cw_v), .cw_a(r_cw_a), .cw_d(r_cw_d));
    dsdv_mu_hslot #(.NSLOT(47), .MUT(0)) u_rhs (.ck(clk), .rst_n(rst_f), .f_ks(f_ks), .f_kd(r_kd), .f_mc(f_mc), .t_ku(r_ku), .t_mf(r_t_mf0));
    wire [53:0] r_t_kd0 = {r_kd[53:32], r_ku[30:0], 1'b0};
    reg  [53:0] r_t_kd_q; reg [3:0] r_t_mf_q; wire [3:0] r_t_mf0;
    always @(posedge clk) begin r_t_kd_q <= r_t_kd0; r_t_mf_q <= r_t_mf0; end
    assign r_t_kd = r_t_kd_q; assign r_t_mf = r_t_mf_q;
    integer cyc, nc, bad, kuact;
    task rnd_inputs; begin
        tap_k = $urandom; sink_k = $urandom; f_lf = $urandom; s_jd_w = $urandom; s_jd_e = $urandom; s_hc_w = $urandom;
        s_hc_e = $urandom; st_rg_w = $urandom; st_rg_e = $urandom;
        vi_s = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
        vi_n = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
        f_host = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
        f_ks = {$urandom,$urandom};
        // starts only after the boot programme, ~1 in 8 cycles (a legal calendar: GAP >= NSLOT, NSLOT < RL < period)
        f_ks[52] = (cyc >= ST0) && ($urandom % 8 == 0);
        // hslot boot programme (legal calendar so the slot table really returns users): NSLOT gap words of GAP..GAP+6 edges,
        // then the RL word, then idle.  BOOT0 sits 2 edges before the reference reset release, so a reset-epoch slip of
        // the hslot (MU_LP_MUT 1) captures a different number of gap words and is observable on t_kd/t_mf
        if (cyc >= BOOT0 && cyc < BOOT0 + 47) f_mc = {1'b1, 1'b0, 24'(GAP + (cyc - BOOT0) % 7)};   // non-uniform gaps: the wrap point is observable
        else if (cyc == BOOT0 + 47) f_mc = {1'b1, 1'b1, 24'(RLW)};
        else f_mc = {1'b0, 1'b0, 24'($urandom)};
    end endtask
`define CMP(p) nc = nc + 1; if (l_``p !== r_``p) begin bad = bad + 1; if (bad <= 6) $display("MU_LP_MISMATCH port=%s cycle=%0d ref=%h lp=%h", `"p`", cyc, r_``p, l_``p); end
    initial begin
        nc = 0; bad = 0; kuact = 0; cyc = 0; void'($urandom(SEED)); rnd_inputs;
        for (cyc = 0; cyc < NC; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == 32) rst = 1'b1;
            rnd_inputs;
            if (cyc > WARM) begin
                `CMP(vo_s) `CMP(vo_n) `CMP(t_host) `CMP(t_kd) `CMP(t_mf) `CMP(s_j) `CMP(s_hw_w) `CMP(s_hw_e) `CMP(cw_v) `CMP(cw_a) `CMP(cw_d)
                if (r_ku[31]) kuact = kuact + 1;
            end
        end
        if (bad == 0 && nc > 0) $display("MU_LP_LOCKSTEP PASS MU_LP_MUT=%0d LPMUT=%0d compared=%0d cycles=%0d ku_valid=%0d", MU_LP_MUT, LPMUT, nc, NC, kuact);
        else $display("MU_LP_LOCKSTEP FAIL MU_LP_MUT=%0d LPMUT=%0d mismatches=%0d of %0d ku_valid=%0d", MU_LP_MUT, LPMUT, bad, nc, kuact);
        $finish;
    end
endmodule
