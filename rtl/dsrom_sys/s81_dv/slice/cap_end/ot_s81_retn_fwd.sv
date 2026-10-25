`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81/PORTFIX-DEAD D-CAPEND (2026-10-25): ot_s81_retn_fwd = the ONE-SIDED return-tree node.  A node of the capture tree
// whose b side has no lane at a slice-row end (no frame drives it) is not built as ot_s81_retn_static with b tied 0:
// it is this node, with no b port at all.  Cycle- and bit-exact with ot_s81_retn_static #(WIN, RST) (and with the cap
// root's copy ot_s81sl_cap_rt_retn) whose b side is idle: with no b word there is no sibling, no merge, no exit-slot
// collision (F1..F4 cannot fire), so every a word is FORWARDED at  arrival + WIN + 10 + RST  edges with tag = norm(tag),
// data and err unchanged (bench tools/s81_slice/cap_end/fwd_eq.sh: retn_static / cap_rt_retn with b = 0 vs this node,
// random a streams, every output bit every edge).  The compiler's calendar (tools/s81/static_return_calendar.py) is
// unchanged: a lone word's exit edge is the same.
//   P1 port register, P2 normalised-tag register (as the full node), then a plain delay of the remaining edges; valid
//   bits reset, data unreset (as the full node).  No fault output: a one-sided node has no compiler obligation to check.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_retn_fwd #(
    parameter integer WIN = 2,           // the replaced node's sibling window (edges)
    parameter integer RST = 1            // the replaced node's output register stages
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        a_v,
    input  wire [31:0] a_t,
    input  wire [31:0] a_d,
    input  wire        a_e,
    output wire        o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e
);
    localparam integer TW = 32;
    localparam integer LAT = WIN + 10 + RST;   // the full node's forward latency (early + WIN + 10 + RST)
    // ot_v41_ret_pkg norm, closed form, verbatim from ot_s81_retn_static
    function automatic [TW-1:0] norm(input [TW-1:0] t);
        reg [18:0] row;
        reg [4:0] lo, n, c;
        reg [2:0] k, kf;
        integer j;
        begin
            {row, lo, k, n} = t;
            for (j = 0; j < 5; j = j + 1)
                c[j] = !(lo == 5'd0 && (6'd1 << j) >= {1'b0, n}) && lo[j] == 1'b0 && ({1'b0, lo} + (6'd1 << j)) >= {1'b0, n};
            kf = k;
            if (k < 3'd5) begin
                kf = 3'd5;
                for (j = 4; j >= 0; j = j - 1)
                    if (j >= k && !c[j]) kf = j;
            end
            norm = {row, lo, kf, n};
        end
    endfunction
    reg p1_v, p2_v; reg [31:0] p1_t, p1_d, p2_t, p2_d; reg p1_e, p2_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin p1_v <= 1'b0; p2_v <= 1'b0; end
                                           else begin p1_v <= a_v; p2_v <= p1_v; end
    always @(posedge clk) begin p1_t <= a_t; p1_d <= a_d; p1_e <= a_e; p2_t <= norm(p1_t); p2_d <= p1_d; p2_e <= p1_e; end
    // remaining LAT - 2 edges: valid with reset, word without
    reg [LAT-3:0] vq;
    always @(posedge clk or negedge rst_n) if (!rst_n) vq <= '0; else vq <= {vq[LAT-4:0], p2_v};
    wire [64:0] wq;
    ot_hdc_delay #(.W(65), .D(LAT - 2)) u_wd (.clk(clk), .rst_n(rst_n), .d({p2_t, p2_d, p2_e}), .q(wq));
    assign o_v = vq[LAT-3];
    assign o_t = wq[64:33];   // word without reset (as the full node): meaningful with o_v only
    assign o_d = wq[32:1];
    assign o_e = wq[0];
`ifndef SYNTHESIS
    initial if (LAT < 4) $fatal(1, "ot_s81_retn_fwd: LAT >= 4");
`endif
endmodule
`default_nettype wire
