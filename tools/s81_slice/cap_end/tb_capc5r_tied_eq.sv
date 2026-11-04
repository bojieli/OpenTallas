`timescale 1ns/1ps
// DIE-S81-53/CAPEND (11-04): lockstep of the ONE plan master ot_s81sl_capc5r, with the dead row-end lanes tied 0 exactly as the
// landed slices ot_s81sl_slice_c{1,3}x_k8_cap5r_lp_{w3,e6} now tie them, against the old row-end masters ot_s81sl_capc5r_w3 / _e6.
// Same random stimulus on the live ports; every output compared every edge in the low phase (the RF1 / OLATCH out-faces change
// at the falling edge), plus the root's fcause.  Periodic re-reset, so the sticky fault cannot freeze the comparison.
//   -GNL=3 (w3) | 6 (e6), -GN=edges, -GSEED, -GCMUT: 0 none (must PASS); mutants that must FAIL:
//     1 live lane tied on the master side (lane NL-1); 2 master reads landing 0 K+1 (master MUT 2, read off by one);
//     3 the dead lane is NOT tied on the master side (lane NL carries the stimulus: proves dead lanes are observable)
// `CAPC5R_REF names the master under test (capc5r_tied_eq.sh passes an RF1 / OLATCH preprocessed copy).
`ifndef CAPC5R_REF
`define CAPC5R_REF ot_s81sl_capc5r
`endif
module tb_capc5r_tied_eq #(parameter integer NL = 3, parameter integer N = 200000, parameter integer SEED = 1, parameter integer CMUT = 0);
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg cfg_v; reg [159:0] cfg_d;
    reg [559:0] lanes;                 // 8 stimulus lanes x 70; only lanes < NL are live on the die
    wire [559:0] live;
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_l
        assign live[70 * gl +: 70] = (gl < NL) ? lanes[70 * gl +: 70] : 70'd0;
    end endgenerate
    // master-side lanes: the tie the slice makes, or a mutant of it
    wire [559:0] mlive = (CMUT == 1) ? (live & ~(560'((70'h3fffffffffffffffff)) << (70 * (NL - 1))))
                       : (CMUT == 3) ? (live | (lanes & (560'((70'h3fffffffffffffffff)) << (70 * NL)))) : live;
    wire [5:0] sv0, sv1; wire [71:0] sa0, sa1; wire [191:0] sd0, sd1; wire [3:0] nv0, nv1; wire [47:0] na0, na1; wire [127:0] nd0, nd1;
    wire f0, f1;
    `CAPC5R_REF #(.MUT((CMUT == 2) ? 2 : 0)) u_ref (.ck_rt(clk), .ck_cw(clk), .ck_ce(clk), .ck_rn(clk), .ck_rs(clk),
        .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_ce(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n),
        .rt_w(mlive[279:0]), .rt_e(mlive[559:280]), .cfg_v(cfg_v), .cfg_d(cfg_d),
        .cw_s_v(sv0), .cw_s_a(sa0), .cw_s_d(sd0), .cw_n_v(nv0), .cw_n_a(na0), .cw_n_d(nd0), .fault(f0));
    wire [15:0] fc0 = u_ref.u_rt.fcause, fc1;
    generate if (NL == 3) begin : g_w3
        ot_s81sl_capc5r_w3 u_var (.ck_rt(clk), .ck_cw(clk), .ck_rn(clk), .ck_rs(clk),
            .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n),
            .rt_w(live[209:0]), .cfg_v(cfg_v), .cfg_d(cfg_d),
            .cw_s_v(sv1), .cw_s_a(sa1), .cw_s_d(sd1), .cw_n_v(nv1), .cw_n_a(na1), .cw_n_d(nd1), .fault(f1));
        assign fc1 = u_var.u_rt.fcause;
    end else begin : g_e6
        ot_s81sl_capc5r_e6 u_var (.ck_rt(clk), .ck_cw(clk), .ck_ce(clk), .ck_rn(clk), .ck_rs(clk),
            .rst_n_rt(rst_n), .rst_n_cw(rst_n), .rst_n_ce(rst_n), .rst_n_rn(rst_n), .rst_n_rs(rst_n),
            .rt_w(live[279:0]), .rt_e(live[419:280]), .cfg_v(cfg_v), .cfg_d(cfg_d),
            .cw_s_v(sv1), .cw_s_a(sa1), .cw_s_d(sd1), .cw_n_v(nv1), .cw_n_a(na1), .cw_n_d(nd1), .fault(f1));
        assign fc1 = u_var.u_rt.fcause;
    end endgenerate
    integer seed, cyc, mism, outs, fedges, wvalid, l, rv;
    function [31:0] tag(input integer r);          // small domain, so slots and keys collide (as tb_ot_s81sl_cap_rt_rf1)
        reg [2:0] pos; reg [15:0] row; reg [4:0] lo, n; reg [2:0] k;
        begin
            pos = r[1:0]; row = {14'd0, r[3:2]}; k = r[6:4] % 5; n = 5'd1 + r[11:7] % 31;
            lo = r[16:12] & ~((5'd1 << k) - 5'd1);
            tag = {pos, row, lo, k, n};
        end
    endfunction
    task drive;
        begin
            for (l = 0; l < 8; l = l + 1) begin
                rv = $random(seed);
                lanes[70 * l + 0] = 1'b1;                                // frame rst_n
                lanes[70 * l + 1] = rv[0] & rv[1] & rv[2];               // valid
                lanes[70 * l + 2] = rv[3];
                lanes[70 * l + 3 +: 32] = tag($random(seed));            // tag
                lanes[70 * l + 35 +: 32] = $random(seed);                // FP32 data
                lanes[70 * l + 67] = ((cyc / 20000) % 2 == 1) && (rv[15:8] == 8'd0);  // err: odd re-reset windows only
                lanes[70 * l + 68] = rv[4];
                lanes[70 * l + 69] = ((cyc / 20000) % 2 == 1) && (rv[27:16] == 12'd0);  // fault: odd windows only
            end
            cfg_v = (cyc % 4096) == 37;
            cfg_d = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            cfg_d[28:27] = 2'd1; cfg_d[26:24] = 3'd3; cfg_d[44:29] = 16'd0; cfg_d[55:45] = 11'd4;
        end
    endtask
    initial begin
        seed = SEED; mism = 0; outs = 0; fedges = 0; wvalid = 0; cyc = 0;
        lanes = 0; cfg_v = 0; cfg_d = 0;
        repeat (80) @(negedge clk);
        rst_n = 1;
        repeat (40) @(negedge clk);                       // reset run + landing epochs
        for (cyc = 0; cyc < N; cyc = cyc + 1) begin
            @(negedge clk); #0.1;
            // re-reset (>= 64 edges, owner rst_n rule) so a sticky fault does not freeze the comparison
            if ((cyc % 20000) == 19900) rst_n = 0; else if ((cyc % 20000) == 19990) rst_n = 1;
            if ({sv0, sa0, sd0, nv0, na0, nd0, f0, fc0} !== {sv1, sa1, sd1, nv1, na1, nd1, f1, fc1}) begin
                mism = mism + 1;
                if (mism < 6) $display("MISMATCH cyc %0d v %h/%h %h/%h f %b/%b fc %h/%h", cyc, sv0, sv1, nv0, nv1, f0, f1, fc0, fc1);
            end
            if (|sv0 || |nv0) outs = outs + 1;
            if (f0 === 1'b1) fedges = fedges + 1;
            if (|live[1 +: 1] || |live[71 +: 1] || |live[141 +: 1]) wvalid = wvalid + 1;
            drive;
        end
        $display("CAPC5R_TIED_EQ NL=%0d SEED=%0d CMUT=%0d %s edges %0d mismatches %0d cw_valid_edges %0d fault_edges %0d lane_valid_edges %0d",
                 NL, SEED, CMUT, (mism == 0 && outs > 0) ? "PASS" : "FAIL", N, mism, outs, fedges, wvalid);
        $finish;
    end
endmodule
