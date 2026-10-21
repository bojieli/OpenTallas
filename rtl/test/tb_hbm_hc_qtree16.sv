`timescale 1ns/1ps
// HBM-HCBANK6 10-20: lockstep of the hard tree slice ot_hbm_hc_qtree16_static (native-fanout LAT-7 adders, kit
// hbm_hcq_tree16_c1) against the SAFE 1 form of the same 16-leaf subtree: s_i pin register + 15 ot_hdc_fp32_add_lat
// LAT 7 DRST 0 (exactly ot_hbm_hc_qcen_static SAFE 1 levels 1..4).  Random operands (biased exponents so that
// cancellation, carry, subnormal, overflow and zero paths occur), random valid pulses, every edge compared:
// node valids always, sums / errors whenever valid.  +define+MUT=4 builds the slice with swapped level-1 pairs (must FAIL).
`ifndef MUT
`define MUT 0
`endif
module tb_hbm_hc_qtree16;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg v_i = 0; reg [511:0] s_in = 0;
    wire [31:0] y; wire v; wire [14:0] nv; wire [29:0] e;
    ot_hbm_hc_qtree16_static #(.MUT(`MUT)) dut (.clk(clk), .rst_n(rst_n), .v_i(v_i), .s_in(s_in), .y(y), .v(v), .nv_o(nv), .e_o(e));
    // reference: SAFE 1 subtree slice (leaf valid registered with the data, like vl[VD-1] vs vl[VD-2])
    reg rv; reg [511:0] rs;
    always @(posedge clk) begin rs <= s_in; rv <= rst_n ? v_i : 1'b0; end
    wire [15*32-1:0] nd; wire [14:0] rnv; wire [29:0] re;
    for (genvar l = 1; l <= 4; l = l + 1) begin : g_lvl
        localparam integer N = 16 >> l, OFF = 16 - (32 >> l), POFF = 16 - (64 >> l);
        for (genvar i = 0; i < N; i = i + 1) begin : g_n
            wire [31:0] a, b; wire va;
            if (l == 1) begin : g_leaf
                assign a = rs[(2*i)*32 +: 32]; assign b = rs[(2*i+1)*32 +: 32]; assign va = rv;
            end else begin : g_up
                assign a = nd[(POFF + 2*i)*32 +: 32]; assign b = nd[(POFF + 2*i + 1)*32 +: 32]; assign va = rnv[POFF + 2*i];
            end
            ot_hdc_fp32_add_lat #(.LAT(7), .DRST(0)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(va), .a(a), .b(b),
                .y(nd[(OFF + i)*32 +: 32]), .err(re[(OFF + i)*2 +: 2]), .valid_out(rnv[OFF + i]));
        end
    end
    function automatic [31:0] rnd_fp;
        input integer k;
        reg [31:0] r; reg [7:0] ex;
        begin
            r = $urandom;
            case (r[3:0])
                4'd0: ex = 8'd0;                         // zero / subnormal
                4'd1: ex = 8'hff;                        // inf / nan
                4'd2: ex = 8'hfe;                        // overflow pressure
                4'd3: ex = 8'd1;
                default: ex = 8'd120 + 8'(r[8:4] & 5'd15);   // close exponents -> cancellation / carries
            endcase
            rnd_fp = {r[31], ex, r[30:9]^{14'd0, 9'(k)}};
            if (r[13:10] == 4'd0) rnd_fp[30:0] = 31'd0;
        end
    endfunction
    integer cyc = 0, checks = 0, bad = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 6) rst_n <= 1;
        if (cyc == 3000) rst_n <= 0;           // in-flight reset
        if (cyc == 3005) rst_n <= 1;
        // no task within 10 edges of a reset release (the slice's own relay releases 3 edges after rst_n)
        v_i <= (($urandom % 3) != 0) && !(cyc < 18) && !(cyc >= 2998 && cyc < 3018);
        for (integer k = 0; k < 16; k = k + 1) s_in[k*32 +: 32] <= rnd_fp(k);
        if (rst_n && cyc > 8) begin
            checks <= checks + 1;
            if (nv !== rnv || v !== rnv[14]) begin bad <= bad + 1; if (bad < 5) $display("MISMATCH valid cyc=%0d %h %h", cyc, nv, rnv); end
            for (integer n = 0; n < 15; n = n + 1)
                if (rnv[n] && (e[n*2 +: 2] !== re[n*2 +: 2])) begin bad <= bad + 1; if (bad < 5) $display("MISMATCH err n=%0d cyc=%0d", n, cyc); end
            if (rnv[14] && y !== nd[14*32 +: 32]) begin bad <= bad + 1; if (bad < 5) $display("MISMATCH y cyc=%0d %h %h", cyc, y, nd[14*32 +: 32]); end
        end
        if (cyc == 20000) begin
            if (bad == 0 && checks > 15000) $display("QTREE16 PASS MUT=%0d checks=%0d", `MUT, checks);
            else $display("QTREE16 FAIL MUT=%0d bad=%0d checks=%0d", `MUT, bad, checks);
            $finish;
        end
    end
endmodule
