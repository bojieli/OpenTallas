// Native fault-pin successor. Arithmetic instance, parameters and data pins are
// byte-for-byte the legacy leaf's interface and schedule. Only fault visibility
// gains one edge so the physical fault pins launch directly from local flops.
module ot_qwen_tile_lsl_fp1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_d,
    input  wire          first_d,
    input  wire [3:0]    split_d,
    input  wire [255:0]  w_d,
    input  wire [127:0]  x_d,
    output wire [63:0]   t_out,
    output reg  [7:0]    lfault,
    output reg           tfault
);
    wire [7:0] lf_raw;
    wire tf_raw;
    // q14 r11 (2026-10-14): reset pin register.  Native pin audit of the CLOSED view qfd_tile_lsl_fp1-p1-e63a36620
    // (TT R 166.9): rst_n capture 230.9 ps > 190 -- the port fanned out to the lane-slice reset relays and the nine
    // fault-pin flops.  The port now lands in ONE kept flop (async assert, registered deassert); everything resets
    // from it.  Reset release is 1 clk edge later (compiler/die: hold reset +1 edge); data/fault latency unchanged.
    // OT_LSL_RST_MUT (bench mutant only): bypass the pin register.
    (* keep = "true", dont_touch = "true" *) reg rs_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs_q <= 1'b0; else rs_q <= 1'b1;
`ifdef OT_LSL_RST_MUT
    wire rs = rst_n;
`else
    wire rs = rs_q;
`endif
    ot_qwen_w12_lane_slice #(.G(4), .NPL(2), .IL(8), .MUL_LAT(8), .ACC_LAT(7), .TREE_LAT(7), .LRST(3), .ANR(1), .TMUT(0)) u_ls (
        .clk(clk), .rst_n(rs), .v_d(v_d), .first_d(first_d), .split_d(split_d), .w_d(w_d), .x_d(x_d),
        .t_out(t_out), .lfault(lf_raw), .tfault(tf_raw));
    // Real same-clock fault capture; async assertion preserves exception reset.
    // Arithmetic lane/tree reset relays remain exactly the legacy LRST=3 body.
    wire [8:0] fault_pin_raw = {tf_raw,lf_raw};
    always @(posedge clk or negedge rs)
        if (!rs) begin lfault <= 0; tfault <= 0; end
        else begin {tfault,lfault} <= fault_pin_raw; end
endmodule
