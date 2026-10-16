`timescale 1ns/1ps
// tb_s81_static_ratio_cross: one VCO tick clock, source /SDIV and destination /DDIV with every divider phase (PH_W,
// PH_R) and marker release edge (REL).  Every destination edge after the epoch must deliver exactly the source word of
// edge src(rc) = NS*(rc/ND) + rc%ND - LAG (0 for the compiled bubble phases and before the lag fills), fault 0; with
// SKIPV the source puts a valid word in a never-read phase and the fault must rise.
module tb_s81_static_ratio_cross;
    parameter integer NS = 4, ND = 3, PH_W = 0, PH_R = 0, REL = 5, MUT = 0, SKIPV = 0, W = 40, WRN = 0;
    localparam integer SDIV = 12 / NS, DDIV = 12 / ND;
    localparam integer LAG = (NS < ND) ? 1 : 0;
    reg tick = 0; always #0.5 tick = ~tick;
    integer tc = 0; always @(posedge tick) tc <= tc + 1;
    reg w_ck = 0, r_ck = 0;
    always @(posedge tick) begin
        w_ck <= ((tc + PH_W) % SDIV) < (SDIV / 2) ? 1'b0 : 1'b1;
        r_ck <= ((tc + PH_R) % DDIV) < (DDIV / 2) ? 1'b0 : 1'b1;
    end
    reg w_rst_n = 0, r_rst_n = 0;
    reg [W-1:0] i = 0;
    wire [W-1:0] o; wire o_live, fault;
    ot_s81_static_ratio_cross #(.W(W), .NS(NS), .ND(ND), .VBIT(0), .WRN(WRN), .MUT(MUT)) dut (.w_ck(w_ck), .w_rst_n(w_rst_n),
        .i(i), .r_ck(r_ck), .r_rst_n(r_rst_n), .o(o), .o_live(o_live), .fault(fault));
    function automatic [W-1:0] word(input integer j);
        reg [W-1:0] x; integer ph, sd;
        begin
            sd = j;
            x = {$random(sd), $random(sd)} ^ (j * 40'h9E3779B97F);
            ph = j % NS;
            x[0] = (NS > ND && ph >= ND) ? ((SKIPV != 0 && j == 39) ? 1'b1 : 1'b0) : 1'b1;
            word = x;
        end
    endfunction
    integer we = 0, nw = 0;
    always @(posedge w_ck) begin
        if (nw == REL) w_rst_n <= 1'b1;
        nw <= nw + 1;
    end
    // the word sampled at source edge j (the j-th w_ck edge with w_rst_n high) is presented before it
    always @(posedge w_ck) begin
        #0.05;
        if (w_rst_n) begin i = word(we); we = we + 1; end else i = word(0);
    end
    integer rc = -1, bad = 0, chk = 0, raw;
    reg [W-1:0] exp_;
    initial begin
        #3 r_rst_n = 1;
    end
    always @(posedge r_ck) begin
        #0.05;
        if (o_live && rc < 0) rc = 0; else if (rc >= 0) rc = rc + 1;
        if (rc >= 0) begin
            raw = NS * (rc / ND) + rc % ND;
            if ((ND > NS && rc % ND >= NS) || raw < LAG) exp_ = 0; else exp_ = word(raw - LAG);
            if (o !== exp_) begin bad = bad + 1; if (bad < 5) $display("RATIO_STATIC mismatch rc %0d got %h want %h", rc, o, exp_); end
            chk = chk + 1;
        end
    end
    initial begin
        #2000;
        if (SKIPV != 0) begin
            if (fault !== 1'b1) begin $display("RATIO_STATIC FAIL skipped-phase valid not flagged"); $fatal(1); end
            $display("RATIO_STATIC PASS skipped-phase valid word flagged (fault 1) NS %0d ND %0d", NS, ND);
        end else begin
            if (fault !== 1'b0) bad = bad + 1;
            if (bad || chk < 100) begin $display("RATIO_STATIC FAIL %0d mismatches (%0d checked, fault %b)", bad, chk, fault); $fatal(1); end
            $display("RATIO_STATIC PASS %0d destination edges exact NS %0d ND %0d phase w%0d r%0d rel %0d", chk, NS, ND, PH_W, PH_R, REL);
        end
        $finish;
    end
endmodule
