// q13 spec r5 leaf 1 (2026-10-13): one code ROM bank row of the W12 ROM tile as a hardened leaf (x5 a tile, hardened
// once): the row's two ot_rom_4096x266_m8 macros (columns 0 / 1) and their macro-side registers
// (ot_qwen_rom_bank_regs_w12 at W 16: request copies, capture, CAPX rungs, select copies; ~2.4k flops on the leaf's own
// short clock tree, so the macro clock and its capture flops balance locally).  Parameter-free top (as ot_qwen_tile_lsl).
// Face: 14 inputs that feed only flops (req_d from the parent's request relay flops, sel_d from its select flop),
// 1,024 flop outputs (the masked BF16 words: pair p at 512*p).  Pure re-hierarchy of ot_qwen_rom_tile_w12 at RPH 0.
module ot_qwen_tile_rpair (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [12:0]   req_d,
    input  wire          sel_d,
    output wire [1023:0] cv
);
    wire [25:0]  rom_req;
    wire [531:0] rom_rd;
    ot_qwen_rom_bank_regs_w12 #(.W(16), .TMUT(0)) u_br (.clk(clk), .rst_n(rst_n), .req_d(req_d), .sel_d(sel_d),
        .rom_req(rom_req), .rom_rd(rom_rd), .cv(cv));
    genvar p;
    generate for (p = 0; p < 2; p = p + 1) begin : g_col
        ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(rom_req[13*p + 12]), .addr_in(rom_req[13*p +: 12]),
            .rd_out(rom_rd[266*p +: 266]));
    end endgenerate
endmodule
