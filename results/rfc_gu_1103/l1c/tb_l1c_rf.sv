`timescale 1ns/1ps
// S81-RF1 (DIE-S81-51/RF-C/gu 11-03): dsdv_gunit_l1c RE-FORM bench.  gold = RF 0 / OLAT 0 (the pre-RE-FORM form),
// gate = RF 1 / OLAT 1 (one exchange per stage, four interleaved accumulators, face lockup latches).  Same stimulus:
// segments of 1..10 back-to-back beats (front 0 flags {v, f, l}; four fronts' descending top-6 lists of records
// {v, key, ~b, ~k, ninf} with (b, k) unique per front within a segment, random invalid tails, random key ties), random
// idle gaps with garbage data / flags between segments, random gather-reply flags, rare front faults.  Check, every
// edge after reset: gate select ports {i_v, i_ids, g_go, g_hit, g_a, fault} == gold's 12 edges earlier, gate {s_v, s_d}
// == gold's same edge, bit for bit.  Prints L1C_RF PASS / FAIL <n> (+ the count of valid id rows compared).
module tb_l1c_rf (input wire clk);
    localparam integer D = 12;
    reg rst_n = 0;
    reg f_v = 0, f_f = 0, f_l = 0, f_g = 0; reg [4*245-1:0] f_d = 0; reg [3:0] f_flt = 0;
    wire gg0, gg1, iv0, iv1, sv0, sv1, ft0, ft1; wire [23:0] gh0, gh1; wire [41:0] ga0, ga1; wire [53:0] id0, id1;
    wire [191:0] sd0, sd1;
    dsdv_gunit_l1c #(.RF(0), .OLAT(0)) u_old (.clk(clk), .rst_n(rst_n), .f_v(f_v), .f_f(f_f), .f_l(f_l), .f_g(f_g),
        .f_d(f_d), .f_flt(f_flt), .g_go(gg0), .g_hit(gh0), .g_a(ga0), .i_v(iv0), .i_ids(id0), .s_v(sv0), .s_d(sd0), .fault(ft0));
    dsdv_gunit_l1c #(.RF(1), .OLAT(1)) u_new (.clk(clk), .rst_n(rst_n), .f_v(f_v), .f_f(f_f), .f_l(f_l), .f_g(f_g),
        .f_d(f_d), .f_flt(f_flt), .g_go(gg1), .g_hit(gh1), .g_a(ga1), .i_v(iv1), .i_ids(id1), .s_v(sv1), .s_d(sd1), .fault(ft1));
    localparam integer SW = 1 + 24 + 42 + 1 + 54 + 1;
    wire [SW-1:0] sel0 = {gg0, gh0, ga0, iv0, id0, ft0}, sel1 = {gg1, gh1, ga1, iv1, id1, ft1};
    reg [SW-1:0] hist [0:D-1];
    integer cyc = 0, errs = 0, rows = 0, ncyc, seglen = 0, beat = 0, gap = 0, q, j, x, y, nv;
    reg [127:0] used [0:3];
    reg [40:0] rec [0:5]; reg [40:0] tmp; reg [245:0] w;
    reg [6:0] bk; reg [31:0] key;
    initial begin if (!$value$plusargs("CYC=%d", ncyc)) ncyc = 200000; end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        // ---------------------------------------------------------------- check (outputs of the previous edge)
        if (cyc > 40) begin
            if (sel1 !== hist[D-1]) begin errs = errs + 1; if (errs < 6) $display("ERR cyc %0d select ports differ (gate %0h gold-12 %0h)", cyc, sel1, hist[D-1]); end
            if ({sv1, sd1} !== {sv0, sd0}) begin errs = errs + 1; if (errs < 6) $display("ERR cyc %0d gather reply differs", cyc); end
            if (iv1) rows = rows + 1;
        end
        hist[0] <= sel0; for (x = 1; x < D; x = x + 1) hist[x] <= hist[x-1];
        // ---------------------------------------------------------------- stimulus for the next edge
        rst_n <= (cyc >= 4);
        f_g <= $urandom % 4 == 0; f_flt <= ($urandom % 5000 == 0) ? 4'b1 << ($urandom % 4) : 4'd0;
        if (seglen == 0 && gap == 0) begin seglen = 1 + $urandom % 10; beat = 0; gap = $urandom % 4 == 0 ? 0 : $urandom % 5;
            for (q = 0; q < 4; q = q + 1) used[q] = 128'd0; end
        if (seglen > 0) begin
            f_v <= 1; f_f <= beat == 0; f_l <= beat == seglen - 1;
            for (q = 0; q < 4; q = q + 1) begin
                nv = ($urandom % 4 == 0) ? $urandom % 7 : 6;              // valid records this beat (rest invalid)
                for (j = 0; j < 6; j = j + 1) begin
                    do bk = $urandom % 128; while (used[q][bk]);
                    used[q][bk] = 1'b1;
                    key = ($urandom % 3 == 0) ? {28'd0, 4'($urandom % 4)} : $urandom;   // frequent ties
                    rec[j] = {j < nv, key, ~bk[6:4], ~bk[3:0], 1'($urandom)};
                end
                for (x = 0; x < 6; x = x + 1) for (y = 0; y < 5 - x; y = y + 1)
                    if (rec[y][40:1] < rec[y+1][40:1]) begin tmp = rec[y]; rec[y] = rec[y+1]; rec[y+1] = tmp; end
                for (j = 0; j < 6; j = j + 1) w[41*j +: 41] = rec[j];
                f_d[245*q +: 245] <= {w[245:206], w[204:0]};
            end
            beat = beat + 1; seglen = (beat == seglen) ? 0 : seglen;
        end else begin
            gap = gap - 1; f_v <= 0; f_f <= $urandom; f_l <= $urandom;
            for (q = 0; q < 4; q = q + 1) f_d[245*q +: 245] <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        end
        if (cyc == ncyc) begin
            if (errs == 0 && rows > 1000) $display("L1C_RF PASS cycles=%0d id_rows=%0d (gate select ports = gold +%0d edges, gather reply +0)", ncyc, rows, D);
            else $display("L1C_RF FAIL %0d (id_rows %0d)", errs, rows);
            $finish;
        end
    end
endmodule
