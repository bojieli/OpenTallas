`timescale 1ns/1ps
// RTLGAP-POOL 10-22: bit-exactness of the pool-local census-safe units (ot_psf_*) against the shared originals
// (ot_hdc_fp32_add_f12_l4, ot_hdc_fp32_mul_f12_l5, ot_dsrom_su_fdiv_f12 NR 0, ot_hdc_v41x_exp LM 5 / LA 4), one random
// operand pair an edge (biased: specials, subnormals, near-equal, cancellation), outputs compared in order.
module tb_psf_eq;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg v = 0; reg [31:0] a = 0, b = 0, xe = 0;
    integer N, n_in = 0, nerr = 0;
    integer cnt [0:3];
    function automatic [31:0] rnd_fp(input integer mode);
        reg [31:0] r; integer k;
        begin
            r = $urandom; k = $urandom % 16;
            case (k)
                0: r[30:23] = 8'd0;                         // subnormal / zero
                1: r[30:0] = 31'd0;                         // zero
                2: r[30:23] = 8'hff;                        // inf / nan
                3: r[30:23] = 8'd1 + ($urandom % 3);        // near subnormal
                4: r[30:23] = 8'd254 - ($urandom % 3);      // near overflow
                5: r[22:0] = 23'h7fffff;                    // rounding carry
                6: r[22:0] = $urandom % 4;
                default: r[30:23] = 8'd100 + ($urandom % 56);
            endcase
            rnd_fp = r;
        end
    endfunction
    // originals
    wire [31:0] ya0, ym0, yd0, ye0; wire [1:0] ea0, em0; wire va0, vm0, vd0, ve0, fd0, fe0;
    ot_hdc_fp32_add_f12_l4 o_add (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya0), .err(ea0), .valid_out(va0));
    ot_hdc_fp32_mul_f12_l5 o_mul (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym0), .err(em0), .valid_out(vm0));
    ot_dsrom_su_fdiv_f12 #(.NR(0)) o_div (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(yd0), .vo(vd0), .fault(fd0));
    ot_hdc_v41x_exp #(.LM(5), .LA(4)) o_exp (.clk(clk), .rst_n(rst_n), .v(v), .x(xe), .y(ye0), .vo(ve0), .fault(fe0));
    // successors
    wire [31:0] ya1, ym1, yd1, ye1; wire [1:0] ea1, em1; wire va1, vm1, vd1, ve1, fd1, fe1, dp, ep;
    ot_psf_add n_add (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya1), .err(ea1), .valid_out(va1));
    ot_psf_mul n_mul (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym1), .err(em1), .valid_out(vm1));
    ot_psf_div n_div (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(yd1), .vo(vd1), .vpre(dp), .fault(fd1));
    ot_psf_exp #(.LM(7), .LA(6)) n_exp (.clk(clk), .rst_n(rst_n), .v(v), .x(xe), .y(ye1), .vo(ve1), .vpre(ep), .fault(fe1));
    reg [33:0] qa [$]; reg [33:0] qm [$]; reg [32:0] qd [$]; reg [32:0] qe [$];
    always @(posedge clk) if (rst_n) begin
        if (va0) qa.push_back({ea0, ya0});
        if (vm0) qm.push_back({em0, ym0});
        if (vd0) qd.push_back({fd0, yd0});
        if (ve0) qe.push_back({fe0, ye0});
        if (va1) begin
            if (qa.size() == 0) begin nerr = nerr + 1; $display("ADD extra output"); end
            else begin reg [33:0] e; e = qa.pop_front(); cnt[0] = cnt[0] + 1;
                if (e != {ea1, ya1}) begin nerr = nerr + 1; if (nerr < 20) $display("ADD MISMATCH exp %h got %h", e, {ea1, ya1}); end end
        end
        if (vm1) begin
            if (qm.size() == 0) begin nerr = nerr + 1; $display("MUL extra output"); end
            else begin reg [33:0] e; e = qm.pop_front(); cnt[1] = cnt[1] + 1;
                if (e != {em1, ym1}) begin nerr = nerr + 1; if (nerr < 20) $display("MUL MISMATCH exp %h got %h", e, {em1, ym1}); end end
        end
        if (vd1) begin
            if (qd.size() == 0) begin nerr = nerr + 1; $display("DIV extra output"); end
            else begin reg [32:0] e; e = qd.pop_front(); cnt[2] = cnt[2] + 1;
                if (e != {fd1, yd1}) begin nerr = nerr + 1; if (nerr < 20) $display("DIV MISMATCH exp %h got %h", e, {fd1, yd1}); end end
        end
        if (ve1) begin
            if (qe.size() == 0) begin nerr = nerr + 1; $display("EXP extra output"); end
            else begin reg [32:0] e; e = qe.pop_front(); cnt[3] = cnt[3] + 1;
                if (e != {fe1, ye1}) begin nerr = nerr + 1; if (nerr < 20) $display("EXP MISMATCH exp %h got %h", e, {fe1, ye1}); end end
        end
    end
    // operand trace for the mismatch report
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 200000;
        cnt[0] = 0; cnt[1] = 0; cnt[2] = 0; cnt[3] = 0;
        repeat (20) @(negedge clk); rst_n = 1; repeat (20) @(negedge clk);
        while (n_in < N) begin
            @(negedge clk);
            v = ($urandom % 8) != 0;
            a = rnd_fp(0); b = rnd_fp(1);
            if (($urandom % 4) == 0) b = {~a[31], a[30:0]} ^ ($urandom % 64);        // cancellation
            if (($urandom % 8) == 0) b = {$urandom % 2, a[30:23] - ($urandom % 30), $urandom % (1 << 23)};
            // exp argument: mostly the pool's range s - m <= 0, some anything
            case ($urandom % 4)
                0: xe = rnd_fp(2);
                1: xe = {1'b1, 8'd100 + ($urandom % 34), 23'($urandom)};
                default: xe = {$urandom % 2, 8'd110 + ($urandom % 24), 23'($urandom)};
            endcase
            if (v) n_in = n_in + 1;
        end
        @(negedge clk); v = 0;
        repeat (200) @(negedge clk);
        if (qa.size() || qm.size() || qd.size() || qe.size()) begin nerr = nerr + 1; $display("PENDING %0d %0d %0d %0d", qa.size(), qm.size(), qd.size(), qe.size()); end
        $display("PSF_EQ inputs %0d compared add %0d mul %0d div %0d exp %0d errors %0d", n_in, cnt[0], cnt[1], cnt[2], cnt[3], nerr);
        if (nerr != 0 || cnt[0] != n_in || cnt[1] != n_in || cnt[2] != n_in || cnt[3] != n_in) $fatal(1, "PSF_EQ_FAIL");
        $display("PSF_EQ_PASS");
        $finish;
    end
endmodule
