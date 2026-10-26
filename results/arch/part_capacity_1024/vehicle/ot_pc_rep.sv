// PART-CAP 2026-10-24: OpenROAD partition-capacity vehicle.  N copies of the closed tile ot_qkh_lane8 (KV-die hg/hgi
// partitions are 64 x this lane), flattened into one P&R run.  Copies are made structurally distinct (no yosys merge)
// by a systolic input delay chain (copy k sees the port inputs k cycles late) and a registered XOR output chain.
// Measurement vehicle only: not a design block.
module ot_pc_rep #(
    parameter integer N = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    c_in,
    input  wire [63:0]   row_in,
    input  wire [15:0]   e_in,
    input  wire [11:0]   lt_in,
    input  wire [1:0]    hid,
    input  wire [1:0]    bsel,
    input  wire          q_valid_in,
    input  wire [5:0]    q_beat_in,
    input  wire [127:0]  q_data_in,
    output wire [31:0]   kp,
    output wire          kpv,
    output wire [63:0]   nb,
    output wire          gf
);
    localparam integer IW = 4 + 64 + 16 + 12 + 2 + 2 + 1 + 6 + 128;   // 235
    localparam integer OW = 32 + 1 + 64 + 1;                           // 98
    wire [IW-1:0] din [0:N-1];
    reg  [IW-1:0] dly [1:N-1];
    wire [OW-1:0] dout [0:N-1];
    reg  [OW-1:0] acc [0:N-1];
    assign din[0] = {c_in, row_in, e_in, lt_in, hid, bsel, q_valid_in, q_beat_in, q_data_in};
    genvar k;
    generate
        for (k = 0; k < N; k = k + 1) begin : g_c
            if (k > 0) begin : g_d
                always @(posedge clk) dly[k] <= din[k-1];
                assign din[k] = dly[k];
            end
            ot_qkh_lane8 u_l (
                .clk(clk), .rst_n(rst_n),
                .c_in(din[k][234:231]), .row_in(din[k][230:167]), .e_in(din[k][166:151]), .lt_in(din[k][150:139]),
                .hid(din[k][138:137]), .bsel(din[k][136:135]), .q_valid_in(din[k][134]), .q_beat_in(din[k][133:128]),
                .q_data_in(din[k][127:0]),
                .kp(dout[k][97:66]), .kpv(dout[k][65]), .nb(dout[k][64:1]), .gf(dout[k][0]));
            if (k == 0) begin : g_a0
                always @(posedge clk) acc[0] <= dout[0];
            end else begin : g_a
                always @(posedge clk) acc[k] <= acc[k-1] ^ dout[k];
            end
        end
    endgenerate
    assign {kp, kpv, nb, gf} = acc[N-1];
endmodule
