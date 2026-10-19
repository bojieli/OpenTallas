// QW-SRAM3 10-19: kit-level binding of ot_sram_1r1w_64x512_m1_r2c2 to its <=5.21 pins/um successor
// ot_sram_1r1w_64x512_m1_r2c2_p192_bs (build_qw_p192_1019.py --bit-sliced: each face carries whole bit slices). Same ports, behaviour and
// read latency; only the abstract (0.192 um pin pitch, taller W/E faces) and the
// Liberty (M4 pin-lead RC) differ. A kit binds the successor by listing THIS file plus
// ot_sram_1r1w_64x512_m1_r2c2_p192_bs_bb.v in place of ot_sram_1r1w_64x512_m1_r2c2_bb.v (never both). Zero added cycles.
module ot_sram_1r1w_64x512_m1_r2c2 (
    input wire clk,
    input wire r_ce_in,
    input wire [5:0] r_addr_in,
    output wire [511:0] rd_out,
    input wire w_ce_in,
    input wire [5:0] w_addr_in,
    input wire [511:0] wd_in,
    input wire [511:0] w_mask_in,
    input wire [1:0] rr_en,
    input wire [11:0] rr_addr,
    input wire [1:0] cr_en,
    input wire [17:0] cr_sel
);
    ot_sram_1r1w_64x512_m1_r2c2_p192_bs u_p192 (.clk(clk), .r_ce_in(r_ce_in), .r_addr_in(r_addr_in), .rd_out(rd_out), .w_ce_in(w_ce_in), .w_addr_in(w_addr_in), .wd_in(wd_in), .w_mask_in(w_mask_in), .rr_en(rr_en), .rr_addr(rr_addr), .cr_en(cr_en), .cr_sel(cr_sel));
endmodule
