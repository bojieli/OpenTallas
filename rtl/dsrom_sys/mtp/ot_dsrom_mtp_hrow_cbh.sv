// dsfd_mtp_hrow_cbh: HALF chain bank tile of dsfd_mtp_hrow (S-ELEM-PQ/HROW 2026-10-16).
//
// Why (measured): the full-bank tiles dsfd_mtp_hrow_cbe / cbw (4 x ot_sram_1r1w_1024x256, 475.2 x 216 um) cannot meet the
// tile clock rule.  Closed cbw r8b (293-leaf spine, W entry): TT insertion R 538.5 ps, spread 89.2 ps; r5g TritonCTS W
// entry: 385..501 ps (spread 116); n1-0030 CTS gate, TritonCTS from the N-face centre with every pin flop anchored at its
// face: 326.9..447.7 ps (R 406.2, spread 120.8).  The insertion follows the pin-to-farthest-sink distance (~0.95 ps/um
// here: 583 um W entry, 453 um N centre); a 216 um hub with 12k sinks measures 286 ps at 324 um.  The bank is therefore
// split by data bits into two identical half tiles of 2 macros (512 data bits each), one column, ~250 x 216 um.
//
// The half core is ot_dsrom_mtp_hrow_cbcore narrowed to 512 data bits: same chain stage (pin flop -> out flop, 2 edges a
// tile), same bank decode on the replicated {a 14, v} command bits, same 3-edge read join.  Both halves of a bank see the
// same command bits on the same edge, so the pair is cycle-identical to the full bank at its ports (0 cycles added).
// Every data port lands in / leaves from a dedicated kept flop (inputs wi/ri/di/id + the kept SRAM launch copies,
// outputs wo/ro/dq): the tile is registered at every pin in RTL.
//
// Die composition: dsfd_mtp_hrow_cbp (wiring only, no state) = the two halves of one bank with the die's bit split; the
// die (ot_dsrom_mtp_hrow_die.sv, HALF_BANKS=1) places it for every bank (cbe and cbw alike: one master, the return
// column is the same master mirrored).
module ot_dsrom_mtp_hrow_cbhcore (
    input  wire          clk, rn,
    input  wire [3:0]    bid,
    input  wire [526:0]  f_w,  output wire [526:0] t_w,     // {d 512, a 14, v}
    input  wire [14:0]   f_r,  output wire [14:0]  t_r,     // {a 14, v}
    input  wire [512:0]  f_d,  output wire [512:0] t_d      // {d 512, v}
);
    (* keep = 1 *) reg [526:0] wi; (* keep = 1 *) reg [14:0] ri;
    reg [526:0] wo; reg [14:0] ro; reg [512:0] di, dq; reg [3:0] id; reg [511:0] cap; reg s1, s2;
    wire we = wi[0] && wi[14:11] == id;
    wire re = ri[0] && ri[14:11] == id;
    always @(posedge clk or negedge rn)
        if (!rn) begin wi[0] <= 1'b0; wo[0] <= 1'b0; ri[0] <= 1'b0; ro[0] <= 1'b0; di[0] <= 1'b0; dq[0] <= 1'b0;
                       s1 <= 1'b0; s2 <= 1'b0; end
        else begin wi[0] <= f_w[0]; wo[0] <= wi[0]; ri[0] <= f_r[0]; ro[0] <= ri[0]; di[0] <= f_d[0];
                   dq[0] <= di[0] | s2; s1 <= re; s2 <= s1; end
    always @(posedge clk) begin
        id <= bid;
        wi[526:1] <= f_w[526:1]; wo[526:1] <= wi[526:1];
        ri[14:1] <= f_r[14:1]; ro[14:1] <= ri[14:1];
        di[512:1] <= f_d[512:1]; dq[512:1] <= di[512:1] | (cap & {512{s2}});
    end
    wire [511:0] rdo;
    genvar gc;
    generate for (gc = 0; gc < 2; gc = gc + 1) begin : g_c
        (* keep = 1 *) reg [9:0] macro_wa, macro_ra;
        (* keep = 1 *) reg [255:0] macro_wd;
        always @(posedge clk) begin
            macro_wa <= f_w[10:1]; macro_ra <= f_r[10:1];
            macro_wd <= f_w[15 + 256*gc +: 256];
        end
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk),
            .r_ce_in(re), .r_addr_in(macro_ra), .rd_out(rdo[256*gc +: 256]),
            .w_ce_in(we), .w_addr_in(macro_wa), .wd_in(macro_wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end endgenerate
    always @(posedge clk) cap <= rdo;
    assign t_w = wo; assign t_r = ro; assign t_d = dq;
endmodule

module dsfd_mtp_hrow_cbh (
    input  wire       ck, rst, input wire [3:0] f_bid,
    input  wire [526:0] f_w, output wire [526:0] t_w, input wire [14:0] f_r, output wire [14:0] t_r,
    input  wire [512:0] f_d, output wire [512:0] t_d
`ifdef OT_HROW_RESET_ACK
    ,output wire rst_ack
`endif
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck), .rst_n_async(rst), .rst_n(rn));
    ot_dsrom_mtp_hrow_cbhcore u_c (.clk(ck), .rn(rn), .bid(f_bid), .f_w(f_w), .t_w(t_w), .f_r(f_r), .t_r(t_r),
                                   .f_d(f_d), .t_d(t_d));
`ifdef OT_HROW_RESET_ACK
    dsfd_mtp_reset_ack u_ack(.clk(ck),.request_n(rst),.local_release(rn),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(rst_ack));
`endif
endmodule

// one bank = two half tiles (die wiring only): half h holds data bits [512 h +: 512] of the 1,024-bit row; the command
// bits {a 14, v} and the read command go to both halves; the response valid is half 0's (both are the same flop
// function of the same command bits).  Port-compatible with dsfd_mtp_hrow_cbe / cbw.
module dsfd_mtp_hrow_cbp (
    input  wire       ck, rst, input wire [3:0] f_bid,
    input  wire [1038:0] f_w, output wire [1038:0] t_w, input wire [14:0] f_r, output wire [14:0] t_r,
    input  wire [1024:0] f_d, output wire [1024:0] t_d
`ifdef OT_HROW_RESET_ACK
    ,output wire rst_ack
`endif
);
    wire [526:0] tw0, tw1; wire [14:0] tr0, tr1; wire [512:0] td0, td1;
`ifdef OT_HROW_RESET_ACK
    wire a0, a1; assign rst_ack = a0 & a1;
`endif
    dsfd_mtp_hrow_cbh u_h0 (.ck(ck), .rst(rst), .f_bid(f_bid), .f_w({f_w[15 +: 512], f_w[14:0]}), .t_w(tw0),
                            .f_r(f_r), .t_r(tr0), .f_d({f_d[1 +: 512], f_d[0]}), .t_d(td0)
`ifdef OT_HROW_RESET_ACK
                            ,.rst_ack(a0)
`endif
);
    dsfd_mtp_hrow_cbh u_h1 (.ck(ck), .rst(rst), .f_bid(f_bid), .f_w({f_w[527 +: 512], f_w[14:0]}), .t_w(tw1),
                            .f_r(f_r), .t_r(tr1), .f_d({f_d[513 +: 512], f_d[0]}), .t_d(td1)
`ifdef OT_HROW_RESET_ACK
                            ,.rst_ack(a1)
`endif
);
    assign t_w = {tw1[526:15], tw0[526:15], tw0[14:0]};
    assign t_r = tr0;
    assign t_d = {td1[512:1], td0[512:1], td0[0]};
endmodule
