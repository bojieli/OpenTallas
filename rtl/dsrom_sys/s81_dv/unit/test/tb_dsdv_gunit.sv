`timescale 1ns/1ps
// S81U-1 bench for dsdv_gunit (whole unit: router + HC coefficients) against tools/hdc_golden_v41 (vectors:
// gunit_vectors.py -> gv.hex in cwd).  Cycle-driven (Verilator, main tb_dsdv_gunit.cpp).  Per case:
//   cw   table rows of set c % 2 (56 bias rows, 6 HC base rows, the scale row; the other `which` slot gets junk), the
//        router job, later the HC job;
//   SC   the 55 SC V beats (7 scores each) in random row order on random rung directions with random gaps (two a cycle);
//   HP   the 25 accumulation windows (sum of squares first, then the 24 fn rows in random order), each window's 32 beats
//        in random order / direction, 1-2 a cycle, window completions >= 20 edges apart (case 1: exactly 20, dense);
// Checks: every non-idle beat leaving the unit on EITHER side is the next expected CTL row write (SC / HP beats are
// sunk): router ids row, weights rows, then the six HC coefficient rows -- ids, routing weights and the 24 coefficients
// bit-exact; the last-SC -> ids-row and last-HP -> first-coefficient-row latencies identical in every case (fixed
// schedule); no fault.  +N=<cases> +SEED=<n>.  Prints GUNIT PASS / GUNIT FAIL <n>.
module tb_dsdv_gunit (input wire clk);
    localparam integer V = 276, NEMAX = 448, NE = 384, K = 6, CR = 1 + 2 * NEMAX + 2 * K, CH = 4800 + 24 + 3 + 1 + 24;
    localparam integer CW = CR + CH;
`ifndef MUT
    localparam integer MUT = 0;
`else
    localparam integer MUT = `MUT;
`endif
    reg rst_n = 0;
    reg [V-1:0] vi_s = 0, vi_n = 0; wire [V-1:0] vo_s, vo_n;
    reg cw_v = 0; reg [9:0] cw_a = 0; reg [255:0] cw_d = 0; wire fault;
    // GUNIT2: the rung crosses L5 / L4 / L0 (6 edges) above the stop and L1 / L3 (4 edges) below it.  The compiler knows
    // both times of flight; the bench equalises them by launching the S-side beats FT_N - FT_S edges later, so the stop
    // (and its window / spacing contract) sees the order the bench schedules.  Latencies are reported at the unit pins
    // and at the stop's own pins (pins - 2 FT_N: vo_n leaves through the same 6 edges).
    localparam integer FT_N = 6, FT_S = 4;
    reg [V-1:0] vs_d [0:FT_N-FT_S-1];
    integer q;
    always @(posedge clk) begin vs_d[0] <= vi_s; for (q = 1; q < FT_N - FT_S; q = q + 1) vs_d[q] <= vs_d[q - 1]; end
    dsdv_gunit #(.V(V), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .sid(4'd3), .vi_s(vs_d[FT_N-FT_S-1]), .vo_s(vo_s), .vi_n(vi_n),
        .vo_n(vo_n), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .fault(fault));
    reg [31:0] mem [0:CW*16-1];
    integer N, c, i, j, r, t, errs, cyc, ph, k, base, hb, nexp, gotn, gots, tsc, thp, lr0, lh0, lr, lh, a, nw, dense;
    integer perm [0:63];
    integer acco [0:24];
    reg [31:0] lf;
    reg [V-1:0] exq [0:8];
    reg [V-1:0] b;
    reg [9:0] row, rowh; reg [4:0] lm; reg [15:0] sm; reg set, wh;
    reg [127:0] d; reg [31:0] p0, p1;
    function [31:0] nx(input [31:0] x); nx = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]}; endfunction
    function [V-1:0] ctl(input [9:0] a_, input [3:0] m, input [127:0] d_, input [15:0] s_, input [4:0] l_);
        begin ctl = 0; ctl[0] = 1; ctl[12:9] = 4'd3; ctl[21 +: 16] = s_; ctl[37 +: 5] = 5'd5; ctl[42 +: 5] = l_;
              ctl[47 +: 10] = a_; ctl[57 +: 4] = m; ctl[61 +: 128] = d_; end
    endfunction
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 4;
        if (!$value$plusargs("SEED=%d", lf)) lf = 1;
        lf = lf ^ 32'h5bd1e995;
        $readmemh("gv.hex", mem);
        errs = 0; lr0 = -1; lh0 = -1; cyc = 0; ph = 0; c = 0; k = 0; gotn = 0; gots = 0; nexp = 0;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        // ------------------------------------------------ monitor (DUT outputs of the previous edge)
        if (rst_n && vo_n != 0) begin
            if (gotn < nexp && vo_n == exq[gotn]) begin
                if (gotn == 0) lr = cyc - tsc;
                if (gotn == 3) lh = cyc - thp;
                gotn = gotn + 1;
            end else begin errs = errs + 1; if (errs < 8) $display("ERR case %0d unexpected vo_n beat (got %0d of %0d)", c, gotn, nexp); end
        end
        if (rst_n && vo_s != 0) begin
            if (gots < nexp && vo_s == exq[gots]) gots = gots + 1;
            else begin errs = errs + 1; if (errs < 8) $display("ERR case %0d unexpected vo_s beat (got %0d of %0d)", c, gots, nexp); end
        end
        // ------------------------------------------------ stimulus
        cw_v <= 0; vi_s <= 0; vi_n <= 0;
        case (ph)
            0: begin k = k + 1; if (k == 4) begin rst_n <= 1; ph = 1; end end
            1: begin                                                    // case setup
                base = c * CW; hb = base + CR; set = c[0];
                lf = nx(lf); row = lf[9:0]; lf = nx(lf); lm = lf[4:0]; sm = lf[31:16]; lf = nx(lf); rowh = lf[9:0];
                wh = lf[12]; dense = (c == 1);
                p0 = {5'd0, mem[base+1+2*NEMAX+2][8:0], mem[base+1+2*NEMAX+1][8:0], mem[base+1+2*NEMAX][8:0]};
                p1 = {5'd0, mem[base+1+2*NEMAX+5][8:0], mem[base+1+2*NEMAX+4][8:0], mem[base+1+2*NEMAX+3][8:0]};
                exq[0] = ctl(row, 4'h3, {64'd0, p1, p0}, sm, lm);
                for (i = 0; i < 4; i = i + 1) d[32 * i +: 32] = mem[base + 1 + 2 * NEMAX + K + i];
                exq[1] = ctl(row + 10'd1, 4'hf, d, sm, lm);
                exq[2] = ctl(row + 10'd2, 4'h3, {64'd0, mem[base + 1 + 2 * NEMAX + K + 5], mem[base + 1 + 2 * NEMAX + K + 4]}, sm, lm);
                for (r = 0; r < 6; r = r + 1) begin
                    for (i = 0; i < 4; i = i + 1) d[32 * i +: 32] = mem[hb + 4800 + 28 + 4 * r + i];
                    exq[3 + r] = ctl(rowh + r[9:0], 4'hf, d, sm, lm);
                end
                nexp = 3; gotn = 0; gots = 0;
                for (r = 0; r < 55; r = r + 1) perm[r] = r;
                for (r = 54; r > 0; r = r - 1) begin lf = nx(lf); j = lf % (r + 1); i = perm[r]; perm[r] = perm[j]; perm[j] = i; end
                k = 0; ph = 2;
            end
            2: begin                                                    // table rows 0..62 of the set
                cw_v <= 1; cw_a <= {1'b0, set, 2'b00, k[5:0]}; cw_d <= 256'd0;
                if (k < 56) for (j = 0; j < 8; j = j + 1) cw_d[32 * j +: 32] <= mem[base + 1 + 8 * k + j];
                else if (k < 62) begin
                    for (j = 0; j < 8; j = j + 1)
                        cw_d[32 * j +: 32] <= ((k - 56) / 3 == wh) ? mem[hb + 4800 + 8 * ((k - 56) % 3) + j] : nx(lf + j);
                end else begin
                    cw_d[255:224] <= mem[hb + 4800 + 27]; cw_d[223:192] <= mem[base];
                    for (j = 0; j < 3; j = j + 1) begin
                        cw_d[96 * wh + 32 * j +: 32] <= mem[hb + 4800 + 24 + j];
                        cw_d[96 * (1 - wh) + 32 * j +: 32] <= nx(lf ^ j);
                    end
                end
                k = k + 1; if (k == 63) begin k = 0; ph = 3; end
            end
            3: begin                                                    // router job
                cw_v <= 1; cw_a <= 10'b10_0000_0000; cw_d <= {215'd0, set, 9'd384, row, lm, sm}; r = 0; ph = 4;
            end
            4: begin                                                    // SC beats
                lf = nx(lf);
                if (lf[1:0] != 2'd0) begin
                    for (t = 0; t < 2; t = t + 1) if (r < 55 && (t == 0 || lf[5:4] == 2'd0)) begin
                        b = 0; b[0] = 1; b[3:1] = 3'd5; b[40 +: 10] = perm[r][9:0];
                        for (j = 0; j < 7; j = j + 1)
                            b[52 + 32 * j +: 32] = (7 * perm[r] + j < NE) ? mem[base + 1 + NEMAX + 7 * perm[r] + j] : 32'h0;
                        if ((t == 0 && lf[8]) || (t == 1 && !lf[8])) vi_s <= b; else vi_n <= b;
                        r = r + 1;
                    end
                    tsc = cyc;
                end
                if (r == 55) begin k = 0; ph = 5; end
            end
            5: begin k = k + 1; if (k == 300) begin                     // router done; HC job + accumulation order
                if (gotn != 3 || gots != 3) begin errs = errs + 1; $display("ERR case %0d router beats n %0d s %0d", c, gotn, gots); end
                cw_v <= 1; cw_a <= 10'b10_0000_0001; cw_d <= {214'd0, wh, set, 9'd0, rowh, lm, sm};
                nexp = 9;
                acco[0] = 24; for (a = 1; a < 25; a = a + 1) acco[a] = a - 1;
                for (a = 24; a > 1; a = a - 1) begin lf = nx(lf); j = 1 + lf % a; i = acco[a]; acco[a] = acco[j]; acco[j] = i; end
                a = 0; ph = 6;
            end end
            6: begin                                                    // window start: shuffle the 32 (g, h)
                for (r = 0; r < 32; r = r + 1) perm[r] = r;
                for (r = 31; r > 0; r = r - 1) begin lf = nx(lf); j = lf % (r + 1); i = perm[r]; perm[r] = perm[j]; perm[j] = i; end
                r = 0; ph = 7;
            end
            7: begin                                                    // HP beats of window a
                lf = nx(lf);
                if (dense || lf[1:0] != 2'd0) begin
                    for (t = 0; t < 2; t = t + 1) if (r < 32 && (t == 0 || dense || lf[5:4] != 2'd0)) begin
                        b = 0; b[0] = 1; b[3:1] = 3'd7; b[40 +: 5] = acco[a]; b[45 +: 4] = perm[r] >> 1; b[49] = perm[r] & 1;
                        for (j = 0; j < 6; j = j + 1) b[52 + 32 * j +: 32] = mem[hb + 12 * (16 * acco[a] + (perm[r] >> 1)) + 6 * (perm[r] & 1) + j];
                        if ((t == 0 && lf[8]) || (t == 1 && !lf[8])) vi_s <= b; else vi_n <= b;
                        r = r + 1;
                    end
                end
                if (r == 32) begin thp = cyc; k = 0; a = a + 1; ph = (a == 25) ? 9 : 8; end
            end
            8: begin k = k + 1; if (k >= 3 && (dense || k >= 3 + lf[3:0])) ph = 6; end   // >= 20 edges per window
            9: begin k = k + 1; if (k == 1300) begin
                if (gotn != 9 || gots != 9) begin errs = errs + 1; $display("ERR case %0d CTL beats n %0d s %0d", c, gotn, gots); end
                if (lr0 < 0) lr0 = lr; else if (lr != lr0) begin errs = errs + 1; $display("ERR case %0d router latency %0d vs %0d", c, lr, lr0); end
                if (lh0 < 0) lh0 = lh; else if (lh != lh0) begin errs = errs + 1; $display("ERR case %0d HC latency %0d vs %0d", c, lh, lh0); end
                c = c + 1; ph = (c == N) ? 10 : 1;
            end end
            10: begin
                if (fault) begin errs = errs + 1; $display("ERR fault"); end
                if (errs == 0) $display("GUNIT PASS cases=%0d router_lat=%0d (last SC -> ids row at the stop pins; %0d at the unit pins) hc_lat=%0d (last HP -> first coef row at the stop pins; %0d at the unit pins)", N, lr0 - 2 * FT_N, lr0, lh0 - 2 * FT_N, lh0);
                else $display("GUNIT FAIL %0d (MUT=%0d)", errs, MUT);
                $finish;
            end
            default: ;
        endcase
    end
endmodule
