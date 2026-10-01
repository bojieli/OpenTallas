`timescale 1ns/1ps
// Self-check of rtl/chip/ot_v41_vm_crot_port.sv: for random bases and every slice of the strip, every lane's element
// e = B + l must be found at output position p = NG * (w mod 8) + c (column c = e mod NG, local word w = e / NG) of
// the bank array, in the bank / row the port names, and the rotate amount must map p to lane l.
module tb_v41_vm_crot_port #(parameter integer NG = 128, parameter integer NCOL = 16, parameter integer VMA = 19) (input wire clk);
    localparam integer LG = $clog2(NG), RA = VMA - LG - 4, LR = LG + 3, NS = NG / NCOL;
    reg [VMA-1:0] b;
    wire [NS-1:0] ov;
    wire [NS*NCOL*2*RA-1:0] orow;
    wire [NS*NCOL*8-1:0] obsel;
    wire [NS*LR-1:0] orot;
    genvar g;
    for (g = 0; g < NS; g = g + 1) begin : g_s
        ot_v41_vm_crot_port #(.NG(NG), .NCOL(NCOL), .COL0(g * NCOL), .VMA(VMA), .NCLS(1)) u (.clk(clk), .v(1'b1),
            .base(b), .o_v(ov[g]), .o_row(orow[g*NCOL*2*RA +: NCOL*2*RA]), .o_bsel(obsel[g*NCOL*8 +: NCOL*8]),
            .o_rot(orot[g*LR +: LR]));
    end
    integer cyc = 0, bad = 0, checked = 0, l, e, c, w, p, sl, col, s, bk;
    reg [VMA-1:0] bq;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        bq <= b;
        b <= VMA'($urandom) & ((1 << VMA) - 1 - 8 * NG);
        if (cyc > 1) begin
            for (l = 0; l < 8 * NG; l = l + 1) begin
                e = 32'(bq) + l; c = e % NG; w = e / NG; p = NG * (w % 8) + c;
                sl = c / NCOL; col = c % NCOL; s = w % 8;
                bk = obsel[(sl*NCOL + col)*8 + s];
                if (bk != ((w >> 3) & 1) || orow[((sl*NCOL + col)*2 + bk)*RA +: RA] != RA'(w >> 4) ||
                    ((p - 32'(orot[sl*LR +: LR])) & (8*NG - 1)) != l) bad = bad + 1;
                checked = checked + 1;
            end
        end
        if (cyc == 2000) begin
            $display("CROTPORT checked=%0d bad=%0d", checked, bad);
            $finish;
        end
    end
    initial b = 0;
endmodule
