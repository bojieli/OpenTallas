`timescale 1ns/1ps
// S81-HEAD (10-24): cycle-lockstep equivalence of the census-safe tile element ot_s81hd_elem against the CLOSED view's
// RTL (ot_dsrom_head_elem at the closure source f11f3cc47, renamed ot_dsrom_head_elem_f11 by tools/s81_head/hd_elem_eq.sh)
// at ONE parameter set (-G LV / PAD / JOIN / ROWS / CUT / SPLIT9; IOREG 1, SAFE 1 as both closed views).
// Both DUTs read the same ROM images (+OT_ROM_DIR, INSTANCE) and see the same inputs every cycle; every common output
// (o_v o_d l_v l_d done best_row best_bits best_key fault) is compared every cycle.
// MODE 0: protocol: go every GAP cycles, x random every cycle, (JOIN) b_v for row k at go + B0 + 256 k with random b_d.
// MODE 1: stress: go / b_v random (1 / GO_P, 1 / B_P), x random: compares fault / reject paths too.
// Prints "EQ_PASS cycles N events o_v A l_v B done C fault D" or "EQ_FAIL ..." (first 10 mismatches listed).
module tb_s81hd_elem_eq #(
    parameter integer LV = 8, PAD = 0, JOIN = 1, ROWS = 32,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SPLIT9 = 0,
    parameter INSTANCE = "ga0"
);
    reg clk = 1'b0, rst_n = 1'b0;
    always #0.5 clk = ~clk;
    reg go = 1'b0, b_v = 1'b0;
    reg [16:0] row0 = 17'd21888;
    reg [255:0] x = '0;
    reg [31:0] b_d = '0;
    wire        a_ov, a_lv, a_done, a_flt, r_ov, r_lv, r_done, r_flt;
    wire [31:0] a_od, a_ld, a_bb, a_bk, r_od, r_ld, r_bb, r_bk;
    wire [16:0] a_br, r_br;
    wire        nc_hv; wire [31:0] nc_hd; wire [16:0] nc_hr;
    ot_s81hd_elem #(.LV(LV), .PAD(PAD), .JOIN(JOIN), .ROWS(ROWS), .CUT(CUT), .SPLIT9(SPLIT9), .INSTANCE(INSTANCE),
                    .IOREG(1), .SAFE(1)) u_a (
        .clk(clk), .rst_n(rst_n), .go(go), .row0(row0), .x(x), .b_v(b_v), .b_d(b_d), .o_v(a_ov), .o_d(a_od),
        .l_v(a_lv), .l_d(a_ld), .head_v(nc_hv), .head_d(nc_hd), .head_row(nc_hr), .done(a_done), .best_row(a_br),
        .best_bits(a_bb), .best_key(a_bk), .fault(a_flt));
    ot_dsrom_head_elem_f11 #(.LV(LV), .PAD(PAD), .JOIN(JOIN), .ROWS(ROWS), .CUT(CUT), .SPLIT9(SPLIT9),
                             .INSTANCE(INSTANCE), .IOREG(1), .SAFE(1)) u_r (
        .clk(clk), .rst_n(rst_n), .go(go), .row0(row0), .x(x), .b_v(b_v), .b_d(b_d), .o_v(r_ov), .o_d(r_od),
        .l_v(r_lv), .l_d(r_ld), .done(r_done), .best_row(r_br), .best_bits(r_bb), .best_key(r_bk), .fault(r_flt));
    integer mode, ncyc, gap, b0, go_p, b_p, seed, cyc = 0, bad = 0, n_ov = 0, n_lv = 0, n_done = 0, n_flt = 0, k;
    // qualified compare (the bundle's contract): valids, done and fault every cycle; o_d under o_v, l_d under l_v,
    // best_* under done (the census copy loads its key / operand registers every cycle and reads them under valid)
    wire [148:0] va = {a_ov, a_ov ? a_od : 32'd0, a_lv, a_lv ? a_ld : 32'd0, a_done, a_done ? {a_br, a_bb, a_bk} : 81'd0, a_flt};
    wire [148:0] vr = {r_ov, r_ov ? r_od : 32'd0, r_lv, r_lv ? r_ld : 32'd0, r_done, r_done ? {r_br, r_bb, r_bk} : 81'd0, r_flt};
    always @(negedge clk) if (rst_n) begin
        if (va !== vr) begin
            bad = bad + 1;
            if (bad <= 10) $display("MISMATCH cyc %0d a %h r %h", cyc, va, vr);
        end
        n_ov += a_ov; n_lv += a_lv; n_done += a_done; n_flt += a_flt;
    end
    integer xfin;
    function automatic [255:0] rnd256();
        for (int i = 0; i < 8; i++) rnd256[32*i +: 32] = $urandom;
        // XFIN 1: |x| in [2^-15, 2^1) (exponent 0x70..0x7f): products and sums stay finite, so the argmax / done path
        // runs fault-free; XFIN 0: raw random BF16 (Inf / NaN / overflow: the sticky-fault path)
        if (xfin) for (int l = 0; l < 16; l++) rnd256[16*l+7 +: 8] = 8'h70 + 8'(rnd256[16*l+7 +: 4]);
    endfunction
    initial begin
        if (!$value$plusargs("MODE=%d", mode)) mode = 0;
        if (!$value$plusargs("CYCLES=%d", ncyc)) ncyc = 30000;
        if (!$value$plusargs("GAP=%d", gap)) gap = 9000;
        if (!$value$plusargs("B0=%d", b0)) b0 = 40;
        if (!$value$plusargs("GO_P=%d", go_p)) go_p = 3000;
        if (!$value$plusargs("B_P=%d", b_p)) b_p = 200;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("XFIN=%d", xfin)) xfin = 1;
        void'($urandom(seed));
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);
        for (cyc = 0; cyc < ncyc; cyc++) begin
            x = rnd256();
            if (mode == 0) begin
                go = (cyc % gap) == 0;
                k = (cyc % gap) - b0;
                b_v = JOIN && k >= 0 && (k % 256) == 0 && k / 256 < ROWS;
            end else begin
                go = ($urandom % go_p) == 0;
                b_v = JOIN && ($urandom % b_p) == 0;
            end
            b_d = $urandom;
            if (go) row0 = 17'($urandom % 100000);
            @(negedge clk);
        end
        if (bad == 0 && n_ov > 0 && (JOIN == 0 || n_lv > 0))
            $display("EQ_PASS cycles %0d events o_v %0d l_v %0d done %0d fault_cycles %0d", ncyc, n_ov, n_lv, n_done, n_flt);
        else
            $display("EQ_FAIL cycles %0d mismatches %0d events o_v %0d l_v %0d done %0d fault_cycles %0d", ncyc, bad, n_ov,
                     n_lv, n_done, n_flt);
        $finish;
    end
endmodule
