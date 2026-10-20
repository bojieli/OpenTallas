`timescale 1ns/1ps
// KV-PARAMS4 10-20: K-tree native-32 successor vs the closed originals, every output compared every cycle (incl. reset).
//   +mode=ktree    ot_qkh_ktree #(7, 6, 1035273459)    vs ot_qkh_ktree_nc32c
//   +mode=ktreelk  ot_qkh_ktree_lk #(7, 6, 1035273459) vs ot_qkh_ktree_lk_nc32c (per-lane kpv skew injected)
//   +mode=mul      ot_hdc_fp32_mul_lat #(6)            vs ot_hdc_fp32_mul_lat_ncr (random operands, both operands live)
//   ktreelk (and every +rst_every run): sc_d compared when the reference scale multiply's valid_out was high (the only
//   cycles the static schedule reads sc_d); the lk reset landing (+2 edges) exposes reset-window partial-pipeline garbage.
//   +rst_every=N   re-assert rst_n for 1..8 cycles at random every ~N cycles (off-phase / mid-stream reset); sc_d is then
//                  compared only when the reference scale multiply's valid_out was high at the capturing edge (the tile
//                  has no data-valid output: the static schedule reads sc_d only there; the NC adders do not clear
//                  their unread payload on reset, as in ot_qkh_lane8_nc32c).  sc_f / g_f are compared every cycle.
// Prints TB_QKH_KT32C PASS <mode> ... or MISMATCH lines + TB_QKH_KT32C FAIL.
module tb_qkh_kt32c;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    integer cyc = 0, errors = 0, checks = 0, n = 200000, warm = 0, seed = 1, rst_every = 0, rst_hold = 0;
    reg [255:0] mode;
    function automatic [31:0] fpr(input integer s);
        reg [31:0] r; integer k;
        begin
            r = $urandom; k = $urandom % 8;
            if (k < 3) fpr = r;
            else if (k < 6) fpr = {r[31], 8'd120 + {5'd0, r[25:23]}, r[22:0]};
            else case (r[26:24])
                3'd0: fpr = {r[31], 31'd0};
                3'd1: fpr = {r[31], 8'hff, 23'd0};
                3'd2: fpr = {r[31], 8'hff, r[22:0] | 23'd1};
                3'd3: fpr = {r[31], 8'd0, r[22:0]};
                3'd4: fpr = {r[31], 8'hfe, r[22:0]};
                3'd5: fpr = {r[31], 8'd1, r[22:0]};
                3'd6: fpr = {r[31], 8'd2 + {5'd0, r[22:20]}, r[22:0]};   // multiply subnormal results
                default: fpr = r;
            endcase
        end
    endfunction
    reg [511:0] kpin; reg kv; reg [15:0] kpvv; reg [15:0] kgf;
    wire [31:0] ksc0, ksc1, lsc0, lsc1; wire ksf0, ksf1, kgf0, kgf1, lsf0, lsf1, lgf0, lgf1;
    ot_qkh_ktree #(.ADD_LAT(7), .MUL_LAT(6), .SCALE(32'd1035273459)) u_kt0 (.clk(clk), .rst_n(rst_n), .kp_in(kpin), .kpv_in(kv),
        .gf_in(kgf), .sc_d(ksc0), .sc_f(ksf0), .g_f(kgf0));
    ot_qkh_ktree_nc32c #(.ADD_LAT(7), .MUL_LAT(6), .SCALE(32'd1035273459)) u_kt1 (.clk(clk), .rst_n(rst_n), .kp_in(kpin), .kpv_in(kv),
        .gf_in(kgf), .sc_d(ksc1), .sc_f(ksf1), .g_f(kgf1));
    ot_qkh_ktree_lk #(.ADD_LAT(7), .MUL_LAT(6), .SCALE(32'd1035273459)) u_lk0 (.clk(clk), .rst_n(rst_n), .kp_in(kpin), .kpv_in(kpvv),
        .gf_in(kgf), .sc_d(lsc0), .sc_f(lsf0), .g_f(lgf0));
    ot_qkh_ktree_lk_nc32c #(.ADD_LAT(7), .MUL_LAT(6), .SCALE(32'd1035273459)) u_lk1 (.clk(clk), .rst_n(rst_n), .kp_in(kpin), .kpv_in(kpvv),
        .gf_in(kgf), .sc_d(lsc1), .sc_f(lsf1), .g_f(lgf1));
    reg mv; reg [31:0] ma, mb; wire [31:0] my0, my1; wire [1:0] me0, me1; wire mvo0, mvo1;
    ot_hdc_fp32_mul_lat #(.LAT(6)) u_m0 (.clk(clk), .rst_n(rst_n), .valid_in(mv), .a(ma), .b(mb), .y(my0), .err(me0), .valid_out(mvo0));
    ot_hdc_fp32_mul_lat_ncr #(.LAT(6)) u_m1 (.clk(clk), .rst_v({21{rst_n}}), .valid_in(mv), .a(ma), .a_nrm({ma, ma}), .b(mb), .y(my1), .err(me1), .valid_out(mvo1));
    reg svq0 = 0, svq1 = 0;
    always @(posedge clk) begin svq0 <= u_kt0.u_scale.valid_out; svq1 <= u_lk0.u_kt.u_scale.valid_out; end
    wire qd0 = svq0, qd1 = svq1;   // sc_d read slots only (constant-b multiply: reset-window payload differs, never read)
    integer i;
    task automatic drive;
        begin
            for (i = 0; i < 16; i = i + 1) kpin[32*i +: 32] <= fpr(i);
            kv <= $urandom; kgf <= (($urandom % 64) == 0) ? 16'($urandom) : 16'd0;
            kpvv <= (($urandom % 32) == 0) ? 16'($urandom) : {16{1'($urandom)}};
            mv <= $urandom; ma <= fpr(20); mb <= fpr(21);
        end
    endtask
    task automatic cmp(input [255:0] what, input [63:0] x0, input [63:0] x1);
        begin
            checks = checks + 1;
            if (x0 !== x1) begin
                errors = errors + 1;
                if (errors <= 20) $display("MISMATCH %0s cycle %0d ref %h nc %h", what, cyc, x0, x1);
            end
        end
    endtask
    initial begin
        if (!$value$plusargs("mode=%s", mode)) mode = "ktree";
        void'($value$plusargs("n=%d", n));
        void'($value$plusargs("warm=%d", warm));
        void'($value$plusargs("rst_every=%d", rst_every));
        if ($value$plusargs("seed=%d", seed)) void'($urandom(seed));
        drive();
        repeat (8) @(posedge clk);
        rst_n <= 1'b1;
        while (cyc < n + warm + 40) begin
            @(posedge clk);
            cyc = cyc + 1;
            drive();
            if (rst_every > 0) begin
                if (rst_hold > 0) begin rst_hold = rst_hold - 1; if (rst_hold == 0) rst_n <= 1'b1; end
                else if (($urandom % rst_every) == 0) begin rst_hold = 1 + ($urandom % 8); #0.3 rst_n <= 1'b0; end
            end
            #0.5;
            if (cyc > warm) begin
                if (mode == "ktree") begin
                    if (qd0) cmp("ktree.sc_d", {32'd0, ksc0}, {32'd0, ksc1}); cmp("ktree.f", {62'd0, ksf0, kgf0}, {62'd0, ksf1, kgf1});
                end else if (mode == "ktreelk") begin
                    if (qd1) cmp("lk.sc_d", {32'd0, lsc0}, {32'd0, lsc1}); cmp("lk.f", {62'd0, lsf0, lgf0}, {62'd0, lsf1, lgf1});
                end else begin
                    cmp("mul.y", {32'd0, my0}, {32'd0, my1}); cmp("mul.e/v", {61'd0, me0, mvo0}, {61'd0, me1, mvo1});
                end
            end
        end
        if (errors == 0) $display("TB_QKH_KT32C PASS %0s cycles %0d checks %0d warm %0d", mode, cyc, checks, warm);
        else $display("TB_QKH_KT32C FAIL %0s errors %0d of %0d checks", mode, errors, checks);
        $finish;
    end
endmodule
