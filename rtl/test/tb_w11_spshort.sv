`timescale 1ns/1ps
// Equivalence of the short softplus units (rtl/hdc/v41x/ot_hdc_v41x_spshort.sv)
// against the committed pipes, one operand per cycle.  UNIT selects the check:
//   0  ot_hdc_v41x_softplus_s (124; 107 at PCUT 0) vs ot_hdc_v41x_softplus (162): sp, r, fault
//   1  ot_hdc_v41x_exp_s (40; 33 at PCUT 0)       vs ot_hdc_v41x_exp (49): y, fault
//   2  ot_hdc_fsqrt4 (16)           vs ot_hdc_fsqrt (31): y, fault
//      Units 0-2 take x = LO, LO+1, ... (N words, wrapping): +LO=<hex> +N=<count>.
//   3  ot_hdc_hstep #(K) for the 8 softplus and 5 exp Horner constants vs
//      ot_hdc_qmul -> ot_hdc_qadd(., K); ot_hdc_fp32_mul_x2 vs qmul -> qmul(., 2);
//      ot_hdc_addpos2 vs ot_hdc_qadd on same-sign operands; biased random words
//      after a sweep of every (a exponent near K) x (every b exponent) pair.
//      +N=<cycles>; the stream is +verilator+seed+<n>.
// Prints: W11SP unit=<u> n=<checked> err=<e> [refused=<r> unjustified=<j>] ...
module tb_w11_spshort #(parameter integer UNIT = 0, parameter integer PCUT = 1) (input wire clk);
    localparam integer D_SP = PCUT ? 124 : 107, D_EXP = PCUT ? 40 : 33;
    reg rst_n = 1'b0;
    reg [63:0] cyc = 0, fed = 0, n = 64'd1000000;
    reg [31:0] lo = 32'd0;
    reg [31:0] x = 32'd0;
    reg        v = 1'b0;
    integer seed = 1;
    initial begin
        if (!$value$plusargs("N=%d", n)) n = 64'd1000000;
        if (!$value$plusargs("LO=%h", lo)) lo = 32'd0;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n && fed < n) begin
            x <= lo + fed[31:0];
            v <= 1'b1;
            fed <= fed + 1;
        end else v <= 1'b0;
    end
    reg [63:0] nchk = 0, nerr = 0, nfault = 0;
    reg        done = 1'b0;
    wire unit_mismatch;

    generate
    if (UNIT == 0) begin : g_sp
        assign unit_mismatch = 1'b0;
        wire [31:0] s0, r0, s1, r1, s1d, r1d;
        wire v0, v1, f0, f1, v1d, f1d;
        ot_hdc_v41x_softplus   u_old (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .sp(s0), .r(r0), .vo(v0), .fault(f0));
        ot_hdc_v41x_softplus_s #(.PCUT(PCUT)) u_new (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .sp(s1), .r(r1), .vo(v1), .fault(f1));
        ot_hdc_delay #(.W(66), .D(162 - D_SP), .RESET(1)) d_n (clk, rst_n, {v1, f1, s1, r1}, {v1d, f1d, s1d, r1d});
        always @(posedge clk) if (rst_n) begin
            if (v0) begin
                nchk = nchk + 1;
                if (f0) nfault = nfault + 1;
                if (!v1d || f1d != f0 || (!f0 && (s1d != s0 || r1d != r0))) begin
                    if (nerr < 10) $display("MISMATCH sp x=%08h old sp=%08h r=%08h f=%b new sp=%08h r=%08h f=%b",
                                            x, s0, r0, f0, s1d, r1d, f1d);
                    nerr = nerr + 1;
                end
            end
            if (v1d && !v0) nerr = nerr + 1;
        end
    end else if (UNIT == 1) begin : g_exp
        assign unit_mismatch = 1'b0;
        wire [31:0] y0, y1, y1d;
        wire v0, v1, f0, f1, v1d, f1d;
        ot_hdc_v41x_exp   u_old (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(y0), .vo(v0), .fault(f0));
        ot_hdc_v41x_exp_s #(.PCUT(PCUT)) u_new (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(y1), .vo(v1), .p_pre(), .n_pre(), .fault(f1));
        ot_hdc_delay #(.W(34), .D(49 - D_EXP), .RESET(1)) d_n (clk, rst_n, {v1, f1, y1}, {v1d, f1d, y1d});
        always @(posedge clk) if (rst_n) begin
            if (v0) begin
                nchk = nchk + 1;
                if (f0) nfault = nfault + 1;
                if (!v1d || f1d != f0 || y1d != y0) begin
                    if (nerr < 10) $display("MISMATCH exp old y=%08h f=%b new y=%08h f=%b", y0, f0, y1d, f1d);
                    nerr = nerr + 1;
                end
            end
            if (v1d && !v0) nerr = nerr + 1;
        end
    end else if (UNIT == 2) begin : g_sq
        assign unit_mismatch = 1'b0;
        wire [31:0] y0, y1, y1d;
        wire v0, v1, f0, f1, v1d, f1d;
        ot_hdc_fsqrt  u_old (.clk(clk), .rst_n(rst_n), .v(v), .a(x), .y(y0), .vo(v0), .fault(f0));
        ot_hdc_fsqrt4 u_new (.clk(clk), .rst_n(rst_n), .v(v), .a(x), .y(y1), .vo(v1), .fault(f1));
        ot_hdc_delay #(.W(34), .D(31 - 16), .RESET(1)) d_n (clk, rst_n, {v1, f1, y1}, {v1d, f1d, y1d});
        always @(posedge clk) if (rst_n) begin
            if (v0) begin
                nchk = nchk + 1;
                if (f0) nfault = nfault + 1;
                if (!v1d || f1d != f0 || y1d != y0) begin
                    if (nerr < 10) $display("MISMATCH sqrt old y=%08h f=%b new y=%08h f=%b", y0, f0, y1d, f1d);
                    nerr = nerr + 1;
                end
            end
            if (v1d && !v0) nerr = nerr + 1;
        end
    end else begin : g_units
        localparam integer NK = 13;
        localparam [32*NK-1:0] KS = {32'h3D888889, 32'h3D9D89D9, 32'h3DBA2E8C, 32'h3DE38E39, 32'h3E124925,
                                     32'h3E4CCCCD, 32'h3EAAAAAB, 32'h3F800000,                 // softplus 1/15 .. 1
                                     32'h3C088889, 32'h3D2AAAAB, 32'h3E2AAAAB, 32'h3F000000,
                                     32'h3F7FFFFF};                                         // exp 1/120 .. 1/2; and 1 - ulp
        reg [63:0] hchk [0:NK-1];
        reg [63:0] herr [0:NK-1];
        reg [63:0] href [0:NK-1];
        reg [63:0] hunj [0:NK-1];
        integer q;
        wire [NK-1:0] hbad;
        assign unit_mismatch = (|hbad) || xerr != 0 || x0err != 0 || aerr != 0;
        initial for (q = 0; q < NK; q = q + 1) begin hchk[q] = 0; herr[q] = 0; href[q] = 0; hunj[q] = 0; end
        //: a biased word: exponent e, a mantissa that is random or has long runs
        function automatic [31:0] word(input s, input [7:0] e, input [31:0] r, input [2:0] pat);
            reg [22:0] m;
            begin
                case (pat)
                    3'd0: m = 23'h7FFFFF;
                    3'd1: m = 23'd0;
                    3'd2: m = {r[22:4], 4'hF};
                    3'd3: m = {r[22:4], 4'h0};
                    3'd4: m = 23'h400000 | r[5:0];
                    default: m = r[22:0];
                endcase
                word = {s, e, m};
            end
        endfunction
        genvar gk;
        for (gk = 0; gk < NK; gk = gk + 1) begin : g_k
            assign hbad[gk] = herr[gk] != 0 || hunj[gk] != 0;
            localparam [31:0] K = KS[32*(NK-1-gk) +: 32];
            localparam integer KF = K[30:23];
            reg [31:0] a, b;
            reg        hv = 1'b0;
            reg [31:0] r0, r1, r2, r3;
            integer da, dd, ea, eb;
            always @(posedge clk) begin
                hv <= rst_n && fed < n;
                r0 = $random; r1 = $random; r2 = $random; r3 = $random;
                if (fed < 64'd12 * 256 * 8) begin              // sweep: a near K, every b exponent
                    ea = KF - 8 + (fed[63:11] % 12);
                    eb = fed[10:3];
                    a <= word(r3[0], ea[7:0], r0, fed[2:0]);
                    b <= word(r3[1], eb[7:0], r1, r2[2:0]);
                end else if (r3[3:0] == 4'd0) begin            // any words
                    a <= word(r3[4], r2[7:0], r0, r3[7:5]);
                    b <= word(r3[8], r2[15:8], r1, r3[11:9]);
                end else begin                                 // product d = -3 .. 40 below K
                    da = $signed({1'b0, r2[3:0]}) - 10;        // a's binade around K's
                    dd = (r2[15:8] % 44) - 3;
                    ea = KF + da;
                    eb = KF - dd - ea + 127 + ((r2[16]) ? 1 : 0);
                    if (ea < 1) ea = 1;
                    if (eb < 0) eb = 0;
                    if (eb > 254) eb = 254;
                    a <= word(r3[4], ea[7:0], r0, r3[7:5]);
                    b <= word(r3[8], eb[7:0], r1, r3[11:9]);
                end
            end
            wire [31:0] yn, pm, yr, pm_d, yn_d;
            wire fn, fm, fa, fn_d, fm_d, vn;
            ot_hdc_hstep #(.K(K), .CUT(PCUT)) u_h (.clk(clk), .rst_n(rst_n), .v(hv), .a(a), .b(b), .y(yn), .vo(vn), .fault(fn));
            ot_hdc_qmul m_r (clk, rst_n, hv, a, b, pm, fm);
            ot_hdc_qadd a_r (clk, rst_n, 1'b1, pm, K, yr, fa);
            ot_hdc_delay #(.W(34), .D(2 - PCUT), .RESET(1)) d_n (clk, rst_n, {fn, yn}, {fn_d, yn_d});
            ot_hdc_delay #(.W(33), .D(3), .RESET(1)) d_m (clk, rst_n, {fm, pm}, {fm_d, pm_d});
            wire vr;
            ot_hdc_delay #(.W(1), .D(2 - PCUT), .RESET(1)) d_v (clk, rst_n, vn, vr);
            always @(posedge clk) if (rst_n && vr) begin
                hchk[gk] = hchk[gk] + 1;
                if (fn_d) begin
                    href[gk] = href[gk] + 1;
                    if (!(fm_d || fa || pm_d[30:23] >= KF - 1)) hunj[gk] = hunj[gk] + 1;
                end else if (fm_d || fa || yn_d != yr) begin
                    if (herr[gk] < 5) $display("MISMATCH hstep K=%08h y=%08h ref=%08h (P=%08h f=%b%b)", K, yn_d, yr, pm_d, fm_d, fa);
                    herr[gk] = herr[gk] + 1;
                end
            end
        end
        // mul_x2 and addpos2
        reg [31:0] ma, mb, pa_, pb_;
        reg        mv = 1'b0;
        reg [31:0] s0, s1, s2, s3;
        always @(posedge clk) begin
            mv <= rst_n && fed < n;
            s0 = $random; s1 = $random; s2 = $random; s3 = $random;
            ma <= word(s3[0], (s3[4]) ? s2[7:0] : (8'd100 + s2[7:0] % 8'd40), s0, s3[7:5]);
            mb <= word(s3[1], (s3[8]) ? s2[15:8] : (8'd60 + s2[15:8] % 8'd100), s1, s3[11:9]);
            pa_ <= (s3[15:12] == 4'd0) ? {s3[2], 31'd0} : word(s3[2], (s3[16]) ? s2[23:16] : (8'd120 + s2[23:16] % 8'd16), s0 ^ s1, s3[19:17]);
            pb_ <= (s3[23:20] == 4'd0) ? {s3[2], 31'd0} : word(s3[2], (s3[24]) ? s2[31:24] : (8'd100 + s2[31:24] % 8'd40), s0 + s1, s3[27:25]);
        end
        wire [31:0] xy, xp, xr, xy_d;
        wire xf, xf1, xf2, xf_d, xf1_d;
        ot_hdc_fp32_mul_x2 #(.CUT(PCUT)) u_x2 (.clk(clk), .rst_n(rst_n), .v(mv), .a(ma), .b(mb), .y(xy), .fault(xf));
        ot_hdc_qmul m_x1 (clk, rst_n, mv, ma, mb, xp, xf1);
        ot_hdc_qmul m_x2r (clk, rst_n, 1'b1, xp, 32'h40000000, xr, xf2);
        ot_hdc_delay #(.W(33), .D(3 - PCUT), .RESET(1)) d_x (clk, rst_n, {xf, xy}, {xf_d, xy_d});
        ot_hdc_delay #(.W(1), .D(3), .RESET(1)) d_x1 (clk, rst_n, xf1, xf1_d);
        wire [31:0] x0y, xp_d;
        wire x0f, xf1_d1;
        ot_hdc_fp32_mul_x2 #(.DOUBLE(0), .CUT(PCUT)) u_x0 (.clk(clk), .rst_n(rst_n), .v(mv), .a(ma), .b(mb), .y(x0y), .fault(x0f));
        ot_hdc_delay #(.W(33), .D(PCUT), .RESET(1)) d_xp (clk, rst_n, {xf1, xp}, {xf1_d1, xp_d});
        wire mv4;
        ot_hdc_delay #(.W(1), .D(3 + PCUT), .RESET(1)) d_mv4 (clk, rst_n, mv, mv4);
        reg [63:0] x0chk = 0, x0err = 0;
        always @(posedge clk) if (rst_n && mv4) begin
            x0chk = x0chk + 1;
            if (x0f != xf1_d1 || (!x0f && x0y != xp_d)) begin
                if (x0err < 5) $display("MISMATCH mul4 y=%08h ref=%08h f=%b ref_f=%b", x0y, xp_d, x0f, xf1_d1);
                x0err = x0err + 1;
            end
        end
        wire [31:0] ay, ar, ay_d;
        wire af, arf, af_d;
        ot_hdc_addpos2 u_ap (.clk(clk), .rst_n(rst_n), .v(mv), .a(pa_), .b(pb_), .y(ay), .fault(af));
        ot_hdc_qadd a_ap (clk, rst_n, mv, pa_, pb_, ar, arf);
        ot_hdc_delay #(.W(33), .D(1), .RESET(1)) d_a (clk, rst_n, {af, ay}, {af_d, ay_d});
        wire mv6, mv3;
        ot_hdc_delay #(.W(1), .D(6), .RESET(1)) d_mv6 (clk, rst_n, mv, mv6);
        ot_hdc_delay #(.W(1), .D(3), .RESET(1)) d_mv3 (clk, rst_n, mv, mv3);
        reg [63:0] xchk = 0, xerr = 0, achk = 0, aerr = 0;
        always @(posedge clk) if (rst_n) begin
            if (mv6) begin
                xchk = xchk + 1;
                if (xf_d != (xf1_d | xf2) || (!xf_d && xy_d != xr)) begin
                    if (xerr < 5) $display("MISMATCH mul_x2 y=%08h ref=%08h f=%b ref_f=%b%b", xy_d, xr, xf_d, xf1_d, xf2);
                    xerr = xerr + 1;
                end
            end
            if (mv3) begin
                achk = achk + 1;
                if (af_d != arf || (!af_d && ay_d != ar)) begin
                    if (aerr < 5) $display("MISMATCH addpos2 y=%08h ref=%08h f=%b ref_f=%b", ay_d, ar, af_d, arf);
                    aerr = aerr + 1;
                end
            end
        end
        always @(posedge clk) if (done) begin
            for (q = 0; q < NK; q = q + 1)
                $display("W11SP hstep K=%08h n=%0d err=%0d refused=%0d unjustified=%0d",
                         KS[32*(NK-1-q) +: 32], hchk[q], herr[q], href[q], hunj[q]);
            $display("W11SP mul_x2 n=%0d err=%0d", xchk, xerr);
            $display("W11SP mul4 n=%0d err=%0d", x0chk, x0err);
            $display("W11SP addpos2 n=%0d err=%0d", achk, aerr);
        end
    end
    endgenerate

    always @(posedge clk) begin
        if (fed == n && !v && cyc > n + 400 && !done) done <= 1'b1;
        if (done) begin
            $display("W11SP unit=%0d lo=%08h n=%0d err=%0d fault=%0d", UNIT, lo, nchk, nerr, nfault);
            if (nerr != 0 || unit_mismatch) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
            $finish;
        end
    end
endmodule
