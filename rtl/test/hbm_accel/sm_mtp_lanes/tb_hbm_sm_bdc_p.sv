`timescale 1ns/1ps
// Lane-equivalence bench for the sizing-only P-lane SM leaf datapath (rtl/hbm_accel/sm/mtp_lanes/ot_hbm_sm_bdc_p.sv).
// For random FP8 / FP4 block-dot and BF16 vectors, lane p of the P-lane DUT must equal, cycle for cycle and bit for bit,
// an independent instance of the PRODUCTION single-lane column (ot_hbm_accel_smh_bdc / ot_hbm_accel_smh_tcc) fed the same
// weight word and lane p's activation.  P = 1 compares the variant with the current tile itself.
// MUT=1 (negative control): the DUT's last lane reads lane 0's activation -> must report LANE MISMATCH.
module tb_hbm_sm_bdc_p;
    parameter integer P = 4;
    parameter integer MUT = 0;
    parameter integer CHUNKS = 12;
    parameter integer K = 16;            // terms per chunk (golden chunk length used by the bench)
    localparam integer IL = 8, XB = 532, TAGW = 16;
    reg clk = 0; always #0.4166665 clk = ~clk;
    reg rst_n = 0, iv = 0, first = 0, last = 0, fp4 = 0;
    reg [TAGW-1:0] tag = 0;
    reg [XB-1:0] w = 0;            reg [P*XB-1:0] x = 0;
    reg [255:0]  fw = 0;           reg [P*256-1:0] fx = 0;
    wire dov, dfault, fov, ffault;
    wire [P*32-1:0] dy, fy;
    wire [TAGW-1:0] dtag, ftag;
    ot_hbm_sm_bdc_p #(.P(P), .MUT(MUT)) dut (.clk(clk), .rst_a(rst_n), .i_v(iv), .i_first(first), .i_last(last),
        .i_fp4(fp4), .i_tag(tag), .i_w(w), .i_x(x), .ov(dov), .y(dy), .otag(dtag), .fault(dfault));
    ot_hbm_sm_tcc_p #(.P(P), .MUT(MUT)) dutf (.clk(clk), .rst_a(rst_n), .i_v(iv), .i_first(first), .i_last(last),
        .i_tag(tag), .i_w(fw), .i_x(fx), .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
    wire [P-1:0] rov, rfault, qov, qfault;
    wire [P*32-1:0] ry, qy;
    wire [P*TAGW-1:0] rtag, qtag;
    genvar g;
    generate for (g = 0; g < P; g = g + 1) begin : g_ref
        ot_hbm_accel_smh_bdc #(.IL(IL)) u_ref (.clk(clk), .rst_a(rst_n), .i_v(iv), .i_first(first), .i_last(last),
            .i_fp4(fp4), .i_tag(tag), .i_w(w), .i_x(x[g*XB +: XB]), .ov(rov[g]), .y(ry[32*g +: 32]),
            .otag(rtag[TAGW*g +: TAGW]), .fault(rfault[g]));
        ot_hbm_accel_smh_tcc u_reff (.clk(clk), .rst_a(rst_n), .i_v(iv), .i_first(first), .i_last(last),
            .i_tag(tag), .i_w(fw), .i_x(fx[g*256 +: 256]), .ov(qov[g]), .y(qy[32*g +: 32]),
            .otag(qtag[TAGW*g +: TAGW]), .fault(qfault[g]));
    end endgenerate
    // operands (layouts as ot_hbm_accel_smh_bdc): FP8 E4M3 (never NaN), FP4 E2M1 nibbles, 10-bit block exponents in [-6, 6], BF16 in a normal range
    function automatic [7:0] fp8r(input integer dummy);
        reg [7:0] b; begin b = $urandom; if (b[6:0] == 7'h7F) b[6:0] = 7'h7E; fp8r = b; end
    endfunction
    function automatic [XB-1:0] blk(input integer is_w, input integer f4);
        integer l, i; reg [XB-1:0] z; reg signed [9:0] e; begin
        z = 0;
        for (l = 0; l < 2; l = l + 1) begin
            // weight word: {we[2x10], wq[2x256]}; activation word: per block {xe[10], xq[256]} (266-bit stride)
            for (i = 0; i < 32; i = i + 1) z[(is_w ? 256 : 266)*l + 8*i +: 8] = (is_w && f4) ? {4'd0, 4'($urandom)} : fp8r(0);
            e = $signed(10'($urandom % 13)) - 10'sd6;
            if (is_w) z[512 + 10*l +: 10] = e; else z[266*l + 256 +: 10] = e;
        end
        blk = z; end
    endfunction
    function automatic [255:0] bf(input integer dummy);
        integer i; reg [255:0] z; begin
        for (i = 0; i < 16; i = i + 1) z[16*i +: 16] = {1'($urandom), 8'(112 + $urandom % 32), 7'($urandom)};
        bf = z; end
    endfunction
    reg [31:0] ysum = 0, fsum = 0;
    integer nz = 0;
    integer errors = 0, compared = 0, fcompared = 0, ch, k, r, p, cyc = 0;
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        for (p = 0; p < P; p = p + 1) begin
            if (dov !== rov[p] || (rov[p] && (dy[32*p +: 32] !== ry[32*p +: 32] || dtag !== rtag[TAGW*p +: TAGW]))) begin
                errors = errors + 1;
                if (errors < 8) $display("LANE MISMATCH bdc lane=%0d cyc=%0d ov %b/%b y %h/%h", p, cyc, dov, rov[p],
                                         dy[32*p +: 32], ry[32*p +: 32]);
            end else if (rov[p]) begin compared = compared + 1; ysum = ysum ^ dy[32*p +: 32]; if (dy[32*p +: 31] != 0) nz = nz + 1; end
            if (fov !== qov[p] || (qov[p] && (fy[32*p +: 32] !== qy[32*p +: 32] || ftag !== qtag[TAGW*p +: TAGW]))) begin
                errors = errors + 1;
                if (errors < 8) $display("LANE MISMATCH tcc lane=%0d cyc=%0d ov %b/%b y %h/%h", p, cyc, fov, qov[p],
                                         fy[32*p +: 32], qy[32*p +: 32]);
            end else if (qov[p]) begin fcompared = fcompared + 1; fsum = fsum ^ fy[32*p +: 32]; end
        end
        if (dfault !== 1'b0 && cyc > 40) begin errors = errors + 1;
            if (errors < 4) $display("LANE MISMATCH dut fault cyc=%0d ref_fault=%b af=%b tf=%b tv=%b", cyc, rfault,
                dut.g_lane[0].u_l.u_bd.af, dut.g_lane[0].u_l.u_bd.tf_l, dut.g_lane[0].u_l.u_bd.tv_l); end
    end
    initial begin
        if (!$value$plusargs("seed=%d", k)) k = 1;
        void'($urandom(k));
        repeat (12) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        for (ch = 0; ch < CHUNKS; ch = ch + 1) begin
            for (k = 0; k < K; k = k + 1) begin
                // activation of term k: one word per lane, shared by the IL interleaved rows (as a matvec)
                for (p = 0; p < P; p = p + 1) begin x[p*XB +: XB] = blk(0, 0); fx[p*256 +: 256] = bf(0); end
                for (r = 0; r < IL; r = r + 1) begin
                    @(posedge clk); #0.05;
                    iv = 1; first = (k == 0); last = (k == K - 1); fp4 = ch[0]; tag = 16'(ch * IL + r);
                    w = blk(1, ch[0]); fw = bf(0);
                end
            end
            if (ch % 3 == 2) begin @(posedge clk); #0.05; iv = 0; repeat (IL - 1) @(posedge clk); end
        end
        @(posedge clk); #0.05; iv = 0; first = 0; last = 0;
        repeat (120) @(negedge clk);
        if (compared != P * CHUNKS * IL || fcompared != P * CHUNKS * IL) begin
            errors = errors + 1; $display("LANE MISMATCH count bdc=%0d tcc=%0d expected=%0d", compared, fcompared, P*CHUNKS*IL);
        end
        if (errors) $fatal(1, "LANE MISMATCH errors=%0d P=%0d MUT=%0d", errors, P, MUT);
        $display("PASS P-LANE P=%0d bdc_results=%0d tcc_results=%0d chunks=%0d K=%0d nonzero_bdc=%0d xor_bdc=%h xor_tcc=%h (bit-exact vs production single-lane columns)",
                 P, compared, fcompared, CHUNKS, K, nz, ysum, fsum);
        $finish;
    end
    initial begin #2000000; $fatal(1, "timeout"); end
endmodule
