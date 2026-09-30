`timescale 1ns/1ps
// Self-checking bench of ot_hdc_v41x_attn_tile against tools/hdc_golden_v41.py
// (chunk8).  Stimulus: one word per cycle from +in=<hex> (NCYC words) --
// {iv, ibank, ib, ld_v, ld_mode, ld_bank, ld_grp, ld_w}, LSB first as listed
// from the right; expected results: one word per output beat from +exp=<hex>
// (NOUT words) -- per head {flt, y}.  Every output beat is compared in order;
// y is compared only where the golden value is finite (flt = 0).  Prints
//   V41XTILE beats=<n> checked=<n> errors=<n> faults=<n> first_ov=<cycle> last_ov=<cycle>
// PWORDS = 2 appends {ld_w2v, ld_w_hi[TD*16]} above iv (the two-word p-load port); PWORDS = 1 is unchanged.
module tb_hdc_v41x_attn_tile (input wire clk);
    parameter integer H = 16;
    parameter integer TD = 64;
    parameter integer NCYC = 64;
    parameter integer NOUT = 16;
    parameter integer PWORDS = 1;
    parameter integer NBANK = 3;
    parameter integer FPL = 3;             // tile add / product latencies (3/3 = as built)
    parameter integer FML = 3;
    localparam integer BW = 2;
    localparam integer LATT = 3 + FML + FPL * (7 + $clog2(TD / 8));   // input -> ov (36 at TD = 64, 3/3)
    localparam integer WIN0 = 1 + BW + TD * 18 + 1 + 1 + BW + 8 + TD * 16;
    localparam integer WIN = WIN0 + ((PWORDS > 1) ? TD * 16 + 1 : 0);
    localparam integer WEXP = H * 33;

    reg [WIN-1:0]  stim [0:NCYC-1];
    reg [WEXP-1:0] expv [0:NOUT-1];
    reg [1023:0] fin, fexp;
    initial begin
        if (!$value$plusargs("in=%s", fin)) begin $display("+in missing"); $finish; end
        if (!$value$plusargs("exp=%s", fexp)) begin $display("+exp missing"); $finish; end
        $readmemh(fin, stim);
        $readmemh(fexp, expv);
    end

    reg rst_n = 1'b0;
    integer cyc = 0;
    wire [WIN-1:0] w = (cyc >= 4 && cyc - 4 < NCYC) ? stim[cyc - 4] : {WIN{1'b0}};
    wire [TD*16-1:0] ld_w = w[TD*16-1:0];
    wire [7:0] ld_grp = w[TD*16 +: 8];
    wire [BW-1:0] ld_bank = w[TD*16+8 +: BW];
    wire ld_mode = w[TD*16+8+BW];
    wire ld_v = w[TD*16+9+BW];
    localparam integer IB0 = TD*16 + 10 + BW;
    wire [TD*18-1:0] ib = w[IB0 +: TD*18];
    wire [BW-1:0] ibank = w[IB0 + TD*18 +: BW];
    wire iv = w[IB0 + TD*18 + BW];
    wire [PWORDS*TD*16-1:0] ld_wp;
    wire ld_w2v;
    generate
        if (PWORDS > 1) begin : g_p2
            assign ld_wp = {w[WIN0 +: TD*16], ld_w};
            assign ld_w2v = w[WIN0 + TD*16];
        end else begin : g_p1
            assign ld_wp = ld_w;
            assign ld_w2v = 1'b0;
        end
    endgenerate

    wire ov;
    wire [H*32-1:0] oy;
    wire [H-1:0] oflt;
    ot_hdc_v41x_attn_tile #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(FML)) dut (
        .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy), .oflt(oflt));

    integer nout = 0, errors = 0, checked = 0, faults = 0, first_ov = -1, last_ov = -1, h;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 2) rst_n <= 1'b1;
        if (ov) begin
            if (first_ov < 0) first_ov = cyc;
            last_ov = cyc;
            if (nout >= NOUT) begin
                errors = errors + 1;
            end else begin
                for (h = 0; h < H; h = h + 1) begin
                    checked = checked + 1;
                    if (expv[nout][h*33 + 32]) begin
                        faults = faults + 1;
                        if (!oflt[h]) begin
                            errors = errors + 1;
                            if (errors < 10) $display("MISS-FAULT beat %0d head %0d", nout, h);
                        end
                    end else if (oflt[h] || oy[h*32 +: 32] !== expv[nout][h*33 +: 32]) begin
                        errors = errors + 1;
                        if (errors < 10) $display("MISMATCH beat %0d head %0d got %08x f%0d exp %08x", nout, h,
                                                  oy[h*32 +: 32], oflt[h], expv[nout][h*33 +: 32]);
                    end
                end
            end
            nout = nout + 1;
        end
        if (cyc == NCYC + 44 + LATT) begin
            if (nout != NOUT) errors = errors + 1;
            $display("V41XTILE beats=%0d checked=%0d errors=%0d faults=%0d first_ov=%0d last_ov=%0d",
                     nout, checked, errors, faults, first_ov, last_ov);
            $finish;
        end
    end
endmodule
