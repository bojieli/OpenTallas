`timescale 1ns/1ps
// KV-PARAMS3 10-20: the no-copy (nc) K-tree / lane8 variants vs the closed originals, cycle by cycle (Verilator 5.050).
//   +mode=add    ot_hdc_fp32_add_lat_nr #(7) vs ot_hdc_fp32_add_lat_nc #(7): random / near-exponent / special operands
//   +mode=prod   ot_qwen_nearhbm_prod vs ot_qwen_nearhbm_prod_nc: ALL 2^16 x 2^8 operand pairs
//   +mode=lane8  ot_qkh_lane8 #(7, 12) vs ot_qkh_lane8_nc32c #(7, 12): random control / data
//   +mode=ktree  ot_qkh_ktree #(7, 6, 1035273459) vs ot_qkh_ktree_nc: random partials / valids / faults
//   +warm=N      compare only from cycle N after reset release (random power-up runs: unreset datapath registers of
//                the two instances power up unlike each other and are compared once the stimulus has rewritten them);
//                with +verilator+rand+reset+0 (zero power-up) warm=0 compares from the first edge, reset included
// Prints TB_QKH_NC PASS <mode> ... or MISMATCH lines + TB_QKH_NC FAIL.
module tb_qkh_nc;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    integer cyc = 0, errors = 0, checks = 0, n = 200000, warm = 0, seed = 1;
    reg [255:0] mode;
    // ---- operand generator: a third random bits, a third near-equal exponents, a third specials -----------------
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
                default: fpr = r;
            endcase
        end
    endfunction
    // ---- adder ---------------------------------------------------------------------------------------------------
    reg         av; reg [31:0] aa, ab;
    wire [31:0] ay0, ay1; wire [1:0] ae0, ae1; wire avo0, avo1;
    ot_hdc_fp32_add_lat_nr #(.LAT(7)) u_add0 (.clk(clk), .rst_n(rst_n), .valid_in(av), .a(aa), .b(ab), .y(ay0), .err(ae0), .valid_out(avo0));
    ot_hdc_fp32_add_lat_ncr #(.LAT(7)) u_add1 (.clk(clk), .rst_n(rst_n), .rst_y(rst_n), .valid_in(av), .a(aa), .b(ab), .y(ay1), .err(ae1), .valid_out(avo1));
    // ---- product -------------------------------------------------------------------------------------------------
    reg         pv; reg [15:0] pa; reg [7:0] pk;
    wire [31:0] py0, py1; wire pf0, pf1, pvo0, pvo1;
    ot_qwen_nearhbm_prod    u_prod0 (.clk(clk), .rst_n(rst_n), .valid_in(pv), .a(pa), .k(pk), .y(py0), .fault(pf0), .valid_out(pvo0));
    ot_qwen_nearhbm_prod_ncr u_prod1 (.clk(clk), .rst_n(rst_n), .rst_y(rst_n), .valid_in(pv), .a(pa), .k(pk), .y(py1), .fault(pf1), .valid_out(pvo1));
    // ---- lane8 ---------------------------------------------------------------------------------------------------
    reg [3:0] lc; reg [63:0] lrow; reg [15:0] le; reg [11:0] llt; reg [1:0] lhid, lbs; reg lqv; reg [5:0] lqb; reg [127:0] lqd;
    wire [31:0] lkp0, lkp1; wire lkpv0, lkpv1, lgf0, lgf1; wire [63:0] lnb0, lnb1;
    ot_qkh_lane8 #(.ADD_LAT(7), .LTW(12)) u_l80 (.clk(clk), .rst_n(rst_n), .c_in(lc), .row_in(lrow), .e_in(le), .lt_in(llt),
        .hid(lhid), .bsel(lbs), .q_valid_in(lqv), .q_beat_in(lqb), .q_data_in(lqd), .kp(lkp0), .kpv(lkpv0), .nb(lnb0), .gf(lgf0));
    ot_qkh_lane8_nc32c #(.ADD_LAT(7), .LTW(12)) u_l81 (.clk(clk), .rst_n(rst_n), .c_in(lc), .row_in(lrow), .e_in(le), .lt_in(llt),
        .hid(lhid), .bsel(lbs), .q_valid_in(lqv), .q_beat_in(lqb), .q_data_in(lqd), .kp(lkp1), .kpv(lkpv1), .nb(lnb1), .gf(lgf1));
    // ---- ktree ---------------------------------------------------------------------------------------------------
    reg [511:0] kpin; reg kv; reg [15:0] kgf;
    wire [31:0] ksc0, ksc1; wire ksf0, ksf1, kgf0, kgf1;
    ot_qkh_ktree #(.ADD_LAT(7), .MUL_LAT(6), .SCALE(32'd1035273459)) u_kt0 (.clk(clk), .rst_n(rst_n), .kp_in(kpin), .kpv_in(kv),
        .gf_in(kgf), .sc_d(ksc0), .sc_f(ksf0), .g_f(kgf0));
    ot_qkh_ktree_nc #(.ADD_LAT(7), .MUL_LAT(6), .SCALE(32'd1035273459)) u_kt1 (.clk(clk), .rst_n(rst_n), .kp_in(kpin), .kpv_in(kv),
        .gf_in(kgf), .sc_d(ksc1), .sc_f(ksf1), .g_f(kgf1));

    reg [31:0] pcount;
    integer i;
    task automatic drive;
        begin
            av <= $urandom; aa <= fpr(0); ab <= fpr(1);
            pv <= 1'b1; pa <= pcount[23:8]; pk <= pcount[7:0];
            lc <= $urandom; lrow <= {$urandom, $urandom}; le <= fpr(2) >> 16; llt <= $urandom;
            lhid <= (cyc < 64) ? 2'd1 : lhid; lbs <= (cyc < 64) ? 2'd2 : lbs;
            lqv <= $urandom; lqb <= ($urandom % 2) ? {2'b0, 2'd1, 2'd2} : (($urandom % 2) ? {2'b01, 2'd1, 2'd2} : 6'($urandom));
            lqd <= {$urandom, $urandom, $urandom, $urandom};
            for (i = 0; i < 16; i = i + 1) kpin[32*i +: 32] <= fpr(i);
            kv <= $urandom; kgf <= (($urandom % 64) == 0) ? 16'($urandom) : 16'd0;
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
        if (!$value$plusargs("mode=%s", mode)) mode = "add";
        void'($value$plusargs("n=%d", n));
        void'($value$plusargs("warm=%d", warm));
        if ($value$plusargs("seed=%d", seed)) void'($urandom(seed));
        if (mode == "prod")begin n=1<<24;void'($value$plusargs("prod_n=%d",n));end
        pcount = 0;
        void'($value$plusargs("prod_start=%h",pcount));
        drive();
        repeat (8) @(posedge clk);
        rst_n <= 1'b1;
        while (cyc < n + warm + 40) begin
            @(posedge clk);
            cyc = cyc + 1;
            pcount = pcount + 1;
            drive();
            #0.5;
            if (cyc > warm) begin
                if (mode == "add") begin
                    cmp("add.y", {32'd0, ay0}, {32'd0, ay1}); cmp("add.err/v", {62'd0, ae0}, {62'd0, ae1}); cmp("add.v", {63'd0, avo0}, {63'd0, avo1});
                end else if (mode == "prod") begin
                    cmp("prod.y", {32'd0, py0}, {32'd0, py1}); cmp("prod.f/v", {62'd0, pf0, pvo0}, {62'd0, pf1, pvo1});
                end else if (mode == "lane8") begin
                    cmp("lane8.kp", {32'd0, lkp0}, {32'd0, lkp1}); cmp("lane8.nb", lnb0, lnb1);
                    cmp("lane8.kpv/gf", {62'd0, lkpv0, lgf0}, {62'd0, lkpv1, lgf1});
                end else begin
                    cmp("ktree.sc_d", {32'd0, ksc0}, {32'd0, ksc1}); cmp("ktree.f", {62'd0, ksf0, kgf0}, {62'd0, ksf1, kgf1});
                end
            end
        end
        if (errors == 0) $display("TB_QKH_NC PASS %0s cycles %0d checks %0d warm %0d", mode, cyc, checks, warm);
        else $display("TB_QKH_NC FAIL %0s errors %0d of %0d checks", mode, errors, checks);
        $finish;
    end
endmodule
