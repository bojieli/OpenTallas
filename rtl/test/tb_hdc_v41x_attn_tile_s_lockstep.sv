`timescale 1ns/1ps
// Lockstep bench: ot_hdc_v41x_attn_tile_s (head groups) against ot_hdc_v41x_attn_tile_l, the same random stimulus
// on every input every cycle (loads in both modes, random banks/groups/words, random issue beats with random
// stored-format elements incl. pads, NaN codes and extreme scales), every output compared every cycle.
// Prints TILESLOCK cycles=<n> mismatches=<m> ov=<valid outputs seen>.
module tb_hdc_v41x_attn_tile_s_lockstep (input wire clk);
    parameter integer H = 16;
    parameter integer TD = 32;
    parameter integer NBANK = 3;
    parameter integer BW = 2;
    parameter integer PWORDS = 1;
    parameter integer FPL = 7;
    parameter integer FML = 6;
    parameter integer HG = 4;
    parameter integer F12 = 0;              // tile_s with the f12 adds (tile_l keeps ot_hdc_fp32_add_lat, same function)
    parameter integer NCYC = 20000;
    reg rst_n = 1'b0;
    reg ld_v, ld_mode, ld_w2v, iv;
    reg [BW-1:0] ld_bank, ibank;
    reg [7:0] ld_grp;
    reg [PWORDS*TD*16-1:0] ld_w;
    reg [TD*18-1:0] ib;
    // tile_s FML 8 is tile_l FML 6 two cycles later (one dequantiser + one product stage, loads delayed alike)
    localparam integer FMLL = (FML == 8) ? 6 : FML;
    localparam integer XD = FML - FMLL;
    wire ov_l0, ov_l, ov_s;
    wire [H*32-1:0] oy_l0, oy_l, oy_s;
    wire [H-1:0] of_l0, of_l, of_s;
    ot_hdc_v41x_attn_tile_l #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(FMLL)) u_l (
        .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
        .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov_l0), .oy(oy_l0), .oflt(of_l0));
    ot_hdc_v41x_dly #(.W(1 + H*32 + H), .D(XD)) u_xd (.clk(clk), .d({ov_l0, oy_l0, of_l0}), .q({ov_l, oy_l, of_l}));
    ot_hdc_v41x_attn_tile_s #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(FML),
                              .HG(HG), .F12(F12)) u_s (
        .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
        .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov_s), .oy(oy_s), .oflt(of_s));
    integer cyc = 0, mism = 0, nov = 0, i;
    function automatic [15:0] rbf16(input integer dummy);
        reg [15:0] x;
        begin
            x = $random;
            case ($urandom % 8)
                0: x[14:7] = 8'd0;                       // subnormal / zero
                1: x[14:7] = 8'hff;                      // nonfinite
                2: x[14:7] = 8'd120 + ($urandom % 16);   // near 1
                default: ;
            endcase
            rbf16 = x;
        end
    endfunction
    function automatic [17:0] relem(input integer dummy);
        reg [17:0] e;
        begin
            e = {$random} ;
            e[17] = (($urandom % 16) == 0);              // pad
            if (($urandom % 4) == 0) e[15:8] = 8'h7f;    // E4M3 NaN-ish codes
            if (($urandom % 4) == 0) e[7:0] = 8'd127 + ($urandom % 8) - 4;
            relem = e;
        end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        ld_v <= (($urandom % 3) == 0);
        ld_mode <= $urandom % 2;
        ld_w2v <= $urandom % 2;
        ld_bank <= $urandom % NBANK;
        ld_grp <= (($urandom % 8) == 0) ? $urandom : ($urandom % H);
        for (i = 0; i < PWORDS * TD; i = i + 1) ld_w[i*16 +: 16] <= rbf16(0);
        iv <= (($urandom % 4) != 0);
        ibank <= $urandom % NBANK;
        for (i = 0; i < TD; i = i + 1) ib[i*18 +: 18] <= relem(0);
        if (rst_n) begin
            if (ov_l) nov <= nov + 1;
            if (ov_l !== ov_s || oy_l !== oy_s || of_l !== of_s) begin
                mism <= mism + 1;
                if (mism < 5) $display("MISMATCH cyc=%0d ov %b/%b oy %h / %h of %h / %h", cyc, ov_l, ov_s, oy_l, oy_s,
                                       of_l, of_s);
            end
        end
        if (cyc == NCYC) begin
            $display("TILESLOCK cycles=%0d mismatches=%0d ov=%0d", cyc, mism, nov);
            // nonzero exit on any mismatch, or if no output was ever compared (rule 2026-10-05)
            if (mism != 0 || nov == 0) $fatal(1, "TILESLOCK FAIL mismatches=%0d ov=%0d", mism, nov);
            $finish;
        end
    end
endmodule
