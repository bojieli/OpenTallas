// Qwen ROM die corridor station (qfd_cst_n / qfd_cst_s) and column head (qfd_chead_e / _w): the hardened frame
// (52.68 x 103.656 um r20c) of one registered corridor stage.  The corridor carries DW = 508 downstream bits
// (instruction 379 + go 1 + x 128; the 64 + 64 clock / reset bits of the 637-bit corridor are tree wires, not data)
// and the upstream ready.  Margin rule (owner 2026-10-06): every boundary is register-to-register, every output
// driven by its own kept flop copy (corridor out, tap out, split out never share a driver):
//   b_d  <= a_d            (corridor onward)          t_d <= a_d   (tap to the tile, TAP = 1)
//   c_d  <= a_d            (SPLIT = 1: the column head's second corridor, north / south)
//   a_r  <= b_r & t_r [& c_r]   (registered AND of the downstream readies: one cycle per station, as the corridor's
//                                ready word is priced in the die path audit)
// Values are a pure one-cycle delay (tools: rtl/test/tb_qwen_die_station.sv).
module ot_qwen_die_station #(
    parameter integer DW = 508,
    parameter integer TAP = 1,
    parameter integer SPLIT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [DW-1:0] a_d,
    output wire          a_r,
    output wire [DW-1:0] b_d,
    input  wire          b_r,
    output wire [((TAP != 0) ? DW : 1)-1:0] t_d,     // 1 bit (tied 0) when TAP = 0
    input  wire          t_r,
    output wire [((SPLIT != 0) ? DW : 1)-1:0] c_d,   // 1 bit (tied 0) when SPLIT = 0
    input  wire          c_r
);
    (* keep *) reg [DW-1:0] b_q;
    always @(posedge clk) b_q <= a_d;
    assign b_d = b_q;
    generate if (TAP != 0) begin : g_tap
        (* keep *) reg [DW-1:0] t_q;
        always @(posedge clk) t_q <= a_d;
        assign t_d = t_q;
    end else begin : g_notap
        assign t_d = 1'b0;
    end endgenerate
    generate if (SPLIT != 0) begin : g_split
        (* keep *) reg [DW-1:0] c_q;
        always @(posedge clk) c_q <= a_d;
        assign c_d = c_q;
    end else begin : g_nosplit
        assign c_d = 1'b0;
    end endgenerate
    // ready inputs captured at their pins, the AND registered at the output pin
    reg br_q, tr_q, cr_q, ar_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin br_q <= 1'b0; tr_q <= 1'b0; cr_q <= 1'b0; ar_q <= 1'b0; end
        else begin
            br_q <= b_r; tr_q <= (TAP != 0) ? t_r : 1'b1; cr_q <= (SPLIT != 0) ? c_r : 1'b1;
            ar_q <= br_q & tr_q & cr_q;
        end
    assign a_r = ar_q;
endmodule
