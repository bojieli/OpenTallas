`timescale 1ns/1ps
// RTL-BUILD-S81 (10-18): xfin ENG-mode bench.  16 real ot_s81dv_xfin leaves on the plan's snake exchange ring (street
// links LS stages, end-column links LE stages, both directions, as tb_s81dv_xfin16) run one ENG go: slice g receives
// the 12 x 5 golden beat partials of its beats 5g .. 5g+4 (p.mem from tools/s81_dv/xfin_eng_golden.py; s_i = v*5 +
// leaf), all slices on the same cycles, ORD 0 = leaf-major (5 x 12), 1 = vector-major (12 x 5), GAP idle cycles
// between partials.  Checks: every slice emits copies 0..3 once each, hh / kk / dd equal the golden csum totals over
// D = 5120 bit for bit, no fault.  Then a second go in ENG proves the go reset (same check again).
// Prints DVXFIN16E ... then PASS / FAIL.  Negative controls: +define+OT_S81DV_MUT_ETAG / +define+OT_S81DV_MUT_EASSOC.
module tb_s81dv_xfin16e #(parameter integer LS = 9, parameter integer LE = 29, parameter integer ORD = 0,
                          parameter integer GAP = 0);
    localparam integer NS = 16, NVL = 5, NB = 80, KW = 1 + 4 + 8 + NVL * 32, NP = 12 * NVL;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0] pm [0:12*NB-1]; reg [31:0] tm [0:11];
    initial begin $readmemh("p.mem", pm); $readmemh("t.mem", tm); end
    reg rst_n = 1'b0, go = 1'b0, sv = 1'b0; reg [7:0] si = 0; reg [3:0] vv = 0; reg [2:0] ll = 0;
    wire [NS-1:0] rb_v, flt, e_v; wire [31:0] rb_d [0:NS-1]; wire [1:0] e_c [0:NS-1];
    wire [31:0] e_hh [0:NS-1], e_kk [0:NS-1], e_dd [0:NS-1];
    wire [KW-1:0] eo [0:NS-1], wo [0:NS-1], wi [0:NS-1], ei [0:NS-1];
    genvar g;
    generate
        for (g = 0; g < NS; g = g + 1) begin : sl
            wire [31:0] sg = pm[vv * NB + g * NVL + ll];
            ot_s81dv_xfin #(.NS(NS), .NVL(NVL), .SIW(8)) u (.clk(clk), .rst_n(rst_n), .go(go), .mode(1'b1), .sid(g[3:0]),
                .eps(32'h358637bd), .s_v(sv), .s_i(si), .s(sg),
                .wi_v(wi[g][KW-1]), .wi_h(wi[g][KW-2 -: 4]), .wi_b(wi[g][KW-6 -: 8]), .wi_d(wi[g][NVL*32-1:0]),
                .ei_v(ei[g][KW-1]), .ei_h(ei[g][KW-2 -: 4]), .ei_b(ei[g][KW-6 -: 8]), .ei_d(ei[g][NVL*32-1:0]),
                .eo_v(eo[g][KW-1]), .eo_h(eo[g][KW-2 -: 4]), .eo_b(eo[g][KW-6 -: 8]), .eo_d(eo[g][NVL*32-1:0]),
                .wo_v(wo[g][KW-1]), .wo_h(wo[g][KW-2 -: 4]), .wo_b(wo[g][KW-6 -: 8]), .wo_d(wo[g][NVL*32-1:0]),
                .rb_v(rb_v[g]), .rb_d(rb_d[g]), .e_v(e_v[g]), .e_c(e_c[g]), .e_hh(e_hh[g]), .e_kk(e_kk[g]),
                .e_dd(e_dd[g]), .fault(flt[g]));
            localparam integer L = (g == 7 || g == NS - 1) ? LE : LS;
            ot_hdc_delay #(.W(KW), .D(L), .RESET(1)) u_le (.clk(clk), .rst_n(rst_n), .d(eo[g]), .q(wi[(g + 1) % NS]));
            ot_hdc_delay #(.W(KW), .D(L), .RESET(1)) u_lw (.clk(clk), .rst_n(rst_n), .d(wo[(g + 1) % NS]), .q(ei[g]));
        end
    endgenerate
    integer cyc = 0, i, err = 0, ne = 0, nrb = 0, nf = 0, run = 0, t_go = -1, t_last_p = -1, t_last_e = -1, n = 0, ph = 0;
    integer lat_go [0:1], lat_p [0:1];
    reg [3:0] seen [0:NS-1];
    integer T0 = 100, T1 = 2100;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        go <= 1'b0; sv <= 1'b0;
        if (cyc == T0 || cyc == T1) begin
            go <= 1'b1; t_go = cyc; n = 0; t_last_e = -1;
            for (i = 0; i < NS; i = i + 1) seen[i] = 4'd0;
        end
        if ((cyc > T0 + 1 && cyc < T1 - 400) || cyc > T1 + 1) begin
            if (n < NP && ((cyc - (cyc > T1 ? T1 : T0) - 2) % (GAP + 1)) == 0) begin
                sv <= 1'b1;
                if (ORD == 0) begin vv <= n % 12; ll <= n / 12; si <= (n % 12) * NVL + n / 12; end
                else begin vv <= n / NVL; ll <= n % NVL; si <= n; end
                n = n + 1;
                t_last_p = cyc + 1;
            end
        end
        for (i = 0; i < NS; i = i + 1) begin
            if (rb_v[i]) nrb = nrb + 1;
            if (e_v[i]) begin
                ne = ne + 1; t_last_e = cyc;
                if (seen[i][e_c[i]]) begin err = err + 1; $display("DUP copy %0d slice %0d", e_c[i], i); end
                seen[i][e_c[i]] = 1'b1;
                if (e_hh[i] !== tm[e_c[i]] || e_kk[i] !== tm[4 + e_c[i]] || e_dd[i] !== tm[8 + e_c[i]]) begin
                    if (err < 8) $display("E MISMATCH slice %0d copy %0d hh %h/%h kk %h/%h dd %h/%h", i, e_c[i],
                        e_hh[i], tm[e_c[i]], e_kk[i], tm[4 + e_c[i]], e_dd[i], tm[8 + e_c[i]]);
                    err = err + 1;
                end
            end
        end
        if (flt != 0) nf = nf + 1;
        if (cyc == T1 - 2 || cyc == T1 + 1998) begin
            lat_go[ph] = t_last_e - t_go; lat_p[ph] = t_last_e - t_last_p;
            for (i = 0; i < NS; i = i + 1) if (seen[i] != 4'hf) begin err = err + 1; if (err < 12) $display("MISSING slice %0d seen %b", i, seen[i]); end
            ph = ph + 1;
        end
        if (cyc == T1 + 2000) begin
            $display("DVXFIN16E slices=%0d e_results=%0d err=%0d fault_cycles=%0d rb=%0d go_to_last_e=%0d,%0d last_partial_to_last_e=%0d,%0d ORD=%0d GAP=%0d LS=%0d LE=%0d",
                     NS, ne, err, nf, nrb, lat_go[0], lat_go[1], lat_p[0], lat_p[1], ORD, GAP, LS, LE);
            if (err == 0 && ne == 2 * 4 * NS && nf == 0 && nrb == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
