`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hgi-1010/d (2026-10-10): the HGI SM control LEAF -- how ot_hgi_sm_record (inside the command processor) reaches each
// of the die's 32 SM elements (ot_hbm_accel_smh) over the registered control trunk / cdist stations of the die.
// The trunk is a chain of registers of unknown depth (stations, wire stages, pin flops), so the element's same-edge
// valid / ready handshakes (start / start_ready, d_valid / d_ready) cannot cross it; they become one-credit pulse links:
//   down: start / d_valid leave the CP as ONE-EDGE PULSES with their fields (held stable until the ack), sent only while
//         no earlier pulse of that kind is unacknowledged (1 credit per kind per SM);
//   up:   the element side holds the pulse in a one-entry buffer, presents it to the SM until its ready, then returns a
//         one-edge ACK pulse (start_ack / d_ack); the CP side shows the adapter its ready (start_ready / d_ready) for
//         the one edge the ack lands, which is exactly the adapter's consume condition (cmd && ready).
// Level signals cross unchanged: release_in (down), arrive / busy / released (up), and the coarse clock-gate WAKE cg_en
// (down) rides in the same leaf as start, so its lead over the first start (>= 2 edges at the adapter) is preserved at
// the SM.  The SM's sticky fault rides the result leaf (fault bit of rl), not this leaf.
// LEAF LAYOUT (bit 0 first; WL = 112 = the die's 103-bit sm_desc leaf + 9):
//   [0] start  [13:1] op_rows  [29:14] op_c  [37:30] op_g  [38] op_gs  [40:39] op_fmt  [41] release_in
//   [42] busy^  [43] arrive^  [44] released^  [45] d_valid  [77:46] d_base  [101:78] d_lines  [102] d_ack^
//   [109:103] op_xb  [110] cg_en  [111] start_ack^                                           (^ = up, SM -> CP)
// Exact at transaction level: every start / descriptor the adapter issues is delivered once, with its fields, and
// consumed once; no field changes while a pulse is unacknowledged (the adapter holds its fields until consumed).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_leaf_cp #(parameter integer CW = 106, MUT_NOCREDIT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [CW-1:0] cmd,       // the adapter's per-SM command (ot_hgi_sm_record sm_cmd layout)
    input  wire          cg_en,
    input  wire          fault,     // the SM's sticky fault (from the result side)
    output wire [3:0]    ret,       // {fault, arrive, d_ready, start_ready} to the adapter
    output reg  [111:0]  dn,        // leaf down bits (up positions 0)
    input  wire [111:0]  up         // leaf up bits as they arrive (down positions ignored)
);
    // adapter command fields: {release_in, d_lines 24, d_base 32, d_valid, op_xb 7, op_fmt 2, op_gs, op_g 8, op_c 16,
    // op_rows 13, start}
    wire c_start = cmd[0], c_dv = cmd[48], c_rel = cmd[105];
    reg s_out, d_out;                        // a pulse of that kind is unacknowledged
    wire s_ack = up[111], d_ack = up[102];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s_out <= 1'b0; d_out <= 1'b0; dn <= 112'd0; end
        else begin
            dn[0] <= c_start && (!s_out || MUT_NOCREDIT != 0);  // pulse once per start (mutant: every edge)
            dn[45] <= c_dv && !d_out;
            if (c_start && !s_out) s_out <= 1'b1; else if (s_ack) s_out <= 1'b0;
            if (c_dv && !d_out) d_out <= 1'b1; else if (d_ack) d_out <= 1'b0;
            dn[13:1] <= cmd[13:1]; dn[29:14] <= cmd[29:14]; dn[37:30] <= cmd[37:30]; dn[38] <= cmd[38];
            dn[40:39] <= cmd[40:39]; dn[41] <= c_rel; dn[77:46] <= cmd[80:49]; dn[101:78] <= cmd[104:81];
            dn[109:103] <= cmd[47:41]; dn[110] <= cg_en;
        end
    end
    // ready exactly on the edge the ack lands (the adapter consumes start && ready on that edge); the adapter keeps its
    // command high and its fields stable until then
    assign ret = {fault, up[43], d_ack && d_out, s_ack && s_out};
endmodule

// the element side: one SM's leaf <-> its ot_hbm_accel_smh control ports
module ot_hgi_sm_leaf_el #(parameter integer RW = 13, XB = 7) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [111:0]  dn,
    output reg  [111:0]  up,
    // to the SM
    output reg           start,
    input  wire          start_ready,
    output reg  [RW-1:0] op_rows,
    output reg  [15:0]   op_c,
    output reg  [7:0]    op_g,
    output reg           op_gs,
    output reg  [1:0]    op_fmt,
    output reg  [XB-1:0] op_xb,
    input  wire          busy,
    output reg           d_valid,
    input  wire          d_ready,
    output reg  [31:0]   d_base,
    output reg  [23:0]   d_lines,
    input  wire          arrive,
    output reg           release_in,
    input  wire          released,
    output reg           cg_en
);
    reg [4:0] err;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin start <= 1'b0; d_valid <= 1'b0; up <= 112'd0; release_in <= 1'b0; cg_en <= 1'b1; end
        else begin
            up[111] <= start && start_ready; up[102] <= d_valid && d_ready;
            up[42] <= busy; up[43] <= arrive; up[44] <= released;
            release_in <= dn[41]; cg_en <= dn[110];
            if (start && start_ready) start <= 1'b0;
            if (dn[0]) begin
                start <= 1'b1; op_rows <= dn[RW:1]; op_c <= dn[29:14]; op_g <= dn[37:30]; op_gs <= dn[38];
                op_fmt <= dn[40:39]; op_xb <= dn[103 +: XB];
            end
            if (d_valid && d_ready) d_valid <= 1'b0;
            if (dn[45]) begin d_valid <= 1'b1; d_base <= dn[77:46]; d_lines <= dn[101:78]; end
        end
    end
endmodule
`default_nettype wire
