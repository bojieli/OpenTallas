`timescale 1ns/1ps
// RF-H bf_col lockstep: (1) ot_v41_bmul2_rne_prepare XS=1 vs XS=2 (y/fault exactly +1 cycle);
// (2) ot_v41_bf16_lanes3 RNECUT=0 vs RNECUT=1 with the bf_col parameters (every output exactly +1 cycle).
module tb;
    localparam integer TRW = 7;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer seed, cyc, errs = 0, nv = 0, nsub = 0, NC;
    reg pv_; reg [31:0] pa, pb;
    wire [31:0] y1, y2; wire f1, f2;
    ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1), .XS(1)) m1 (.clk(clk), .rst_n(rst_n), .v(pv_), .a(pa), .b(pb), .y(y1), .fault(f1));
    ot_v41_bmul2_rne_prepare #(.GRADUAL_RNE(1), .XS(2)) m2 (.clk(clk), .rst_n(rst_n), .v(pv_), .a(pa), .b(pb), .y(y2), .fault(f2));
    reg v; reg [255:0] w, x; reg [2:0] slot; reg first, last, fin; reg [TRW-1:0] tree; reg ze_d;
    wire ov0, ov1, of0, of1, oe0, oe1, ft0, ft1; wire [31:0] oval0, oval1; wire [TRW-1:0] ot0, ot1;
    ot_v41_bf16_lanes3 #(.NCHB(8), .TRW(TRW), .GRADUAL_RNE(1), .RC(1), .XST(2), .TNODE(1), .RNECUT(0)) l0 (
        .fclk(clk), .rst_pin(rst_n), .ze_d(ze_d), .v(v), .w(w), .x(x), .slot(slot), .first(first), .last(last), .tree(tree),
        .final_i(fin), .ov(ov0), .oval(oval0), .otree(ot0), .ofinal(of0), .oerr(oe0), .fault(ft0));
    ot_v41_bf16_lanes3 #(.NCHB(8), .TRW(TRW), .GRADUAL_RNE(1), .RC(1), .XST(2), .TNODE(1), .RNECUT(1)) l1 (
        .fclk(clk), .rst_pin(rst_n), .ze_d(ze_d), .v(v), .w(w), .x(x), .slot(slot), .first(first), .last(last), .tree(tree),
        .final_i(fin), .ov(ov1), .oval(oval1), .otree(ot1), .ofinal(of1), .oerr(oe1), .fault(ft1));
    // half the operands from a small-exponent band, so products land in the gradual-underflow (subnormal RNE) range
    function automatic [15:0] bf(input integer dummy);
        reg [15:0] r; begin r = $random(seed); if (r[0]) r[14:7] = 8'd1 + ($unsigned($random(seed)) % 70); bf = r; end
    endfunction
    reg [31:0] h_y; reg h_f; reg [31:0] h_oval; reg h_ov, h_of, h_oe, h_ft; reg [TRW-1:0] h_ot;
    integer k;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", NC)) NC = 200000;
        pv_ = 0; pa = 0; pb = 0; v = 0; w = 0; x = 0; slot = 0; first = 0; last = 0; fin = 0; tree = 0; ze_d = 1;
        repeat (4) @(posedge clk); #0.1 rst_n = 1;
        for (cyc = 0; cyc < NC; cyc = cyc + 1) begin
            @(posedge clk); #0.1;
            if (cyc > 2) begin   // new(now) == old(previous cycle)
                if (y2 !== h_y || f2 !== h_f) begin errs = errs + 1; if (errs < 5) $display("PRIM MISMATCH cyc %0d %h/%b vs %h/%b", cyc, y2, f2, h_y, h_f); end
                if (ov1 !== h_ov || of1 !== h_of || oe1 !== h_oe || ft1 !== h_ft || (h_ov && (oval1 !== h_oval || ot1 !== h_ot))) begin
                    errs = errs + 1; if (errs < 5) $display("LANES MISMATCH cyc %0d ov %b/%b val %h/%h", cyc, ov1, h_ov, oval1, h_oval); end
            end
            if (ov0) nv = nv + 1;
            if (y1[30:23] == 0 && y1[22:0] != 0) nsub = nsub + 1;
            h_y = y1; h_f = f1; h_ov = ov0; h_of = of0; h_oe = oe0; h_ft = ft0; h_oval = oval0; h_ot = ot0;
            pv_ = $random(seed); pa = {bf(0), 16'd0}; pb = {bf(0), 16'd0};
            v = ($unsigned($random(seed)) % 4) != 0;
            for (k = 0; k < 16; k = k + 1) begin w[16*k +: 16] = bf(0); x[16*k +: 16] = bf(0); end
            slot = $random(seed); first = $random(seed); last = $random(seed); fin = $random(seed); tree = $random(seed);
            ze_d = 1;   // free clock: the +1 relation is per gated edge, so the compare runs ungated
        end
        if (errs == 0 && nv > 0 && nsub > 0) $display("RNECUT PASS cycles=%0d lane_out=%0d prim_subnormal_y=%0d errors=0", NC, nv, nsub);
        else $display("RNECUT FAIL errors=%0d lane_out=%0d prim_subnormal_y=%0d", errs, nv, nsub);
        $finish;
    end
endmodule
