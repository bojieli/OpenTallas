`timescale 1ns/1ps
// ---- hardened leaves of dsfd_engram_c_hl ------------------------------------------------------------------------
// Return relay leaf, 256 bits (one master, placed twice: at the PB0 and PB1 read-data source pins).
module ot_engc_rr256 (input wire ck, rst_n, input wire [255:0] d, output wire [255:0] q);
    (* keep = "true", dont_touch = "true" *) reg [255:0] r;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) r <= 256'b0;
`ifdef OT_ENGC_HL_MUT_RR
        else r <= {d[127:0], d[255:128]};      // negative control: returned word halves swapped (beyond SECDED)
`else
        else r <= d;
`endif
    assign q = r;
endmodule
// Return relay leaf, 64 bits (PB2 read-data source pins).
module ot_engc_rr64 (input wire ck, rst_n, input wire [63:0] d, output wire [63:0] q);
    (* keep = "true", dont_touch = "true" *) reg [63:0] r;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) r <= 64'b0;
`ifdef OT_ENGC_HL_MUT_RR64
        else r <= {d[62:0], d[63]};            // negative control: PB2 returned word rotated
`else
        else r <= d;
`endif
    assign q = r;
endmodule
// Control leaf: one clock, the eight 2-flop reset conditioners (async assert by the die reset, released on this
// leaf's clock; each terminal is a registered output pin to its child's reset pin), the three former parent pipes on
// their reference edges and resets, and the registered consumer ACK into the startup barrier.
module ot_engc_ctl_leaf (
    input  wire ck, rst,
    output wire rst_win_n, rst_io_n, rst_ws_n, rst_pb1_n, rst_pb0_n, rst_pb2_n, rst_lkp_n, rst_sink_n,
    input  wire [5:0] child_rso, output wire [7:0] states, output wire rso,
    input  wire [7:0] s_rdy, s_perr, output wire [7:0] s_rdy_q, s_perr_q,
    input  wire [5:0] x_oh, input wire [7:0] x_a, input wire [319:0] x_d,
    output wire [5:0] x_oh_q, output wire [7:0] x_a_q, output wire [319:0] x_d_q,
    input  wire [3:0] vrel, output wire [3:0] vrel_q
);
    ot_engc_hl_rsync u_rst_win  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_win_n));
    ot_engc_hl_rsync u_rst_io   (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_io_n));
    ot_engc_hl_rsync u_rst_ws   (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_ws_n));
    ot_engc_hl_rsync u_rst_pb1  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_pb1_n));
    ot_engc_hl_rsync u_rst_pb0  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_pb0_n));
    ot_engc_hl_rsync u_rst_pb2  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_pb2_n));
    ot_engc_hl_rsync u_rst_lkp  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_lkp_n));
    ot_engc_hl_rsync u_rst_sink (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_sink_n));
    assign states = {rst_sink_n, rst_lkp_n, rst_pb2_n, rst_pb0_n, rst_pb1_n, rst_ws_n, rst_io_n, rst_win_n};
    ot_engc_hl_pipe #(.W(16)) u_status_win (.clk(ck), .rst_n(rst_win_n), .d({s_perr, s_rdy}), .q({s_perr_q, s_rdy_q}));
`ifdef OT_ENGC_HL_MUT_CTL
    // negative control: the transit's address LSB is lost (bank 0 writes land on the wrong row)
    ot_engc_hl_pipe #(.W(334)) u_xtrans_pb0 (.clk(ck), .rst_n(rst_pb0_n), .d({x_oh, x_a[7:1], 1'b0, x_d}), .q({x_oh_q, x_a_q, x_d_q}));
`else
    ot_engc_hl_pipe #(.W(334)) u_xtrans_pb0 (.clk(ck), .rst_n(rst_pb0_n), .d({x_oh, x_a, x_d}), .q({x_oh_q, x_a_q, x_d_q}));
`endif
    ot_engc_hl_pipe #(.W(4)) u_release_sink (.clk(ck), .rst_n(rst_sink_n), .d(vrel), .q(vrel_q));
    // Registered consumer ACK: all 14 genuine release states (8 conditioners here + 6 child rso), asynchronously
    // revoked by the die reset, so no combinational input->output path crosses this leaf.
    (* keep = "true", dont_touch = "true" *) reg ack_q;
    always @(posedge ck or negedge rst)
        if (!rst) ack_q <= 1'b0;
`ifdef OT_ENGC_RSO_MUT_MISSING_PB2
        else ack_q <= &{child_rso[4:0], states};      // negative control: misses genuine final PB2 release
`else
        else ack_q <= &{child_rso, states};
`endif
    assign rso = ack_q;
endmodule

// Leaf-local copies (same logic as ot_engc_reset_sync / ot_engc_*_pipe of dsfd_engram_c.sv) so the leaves synthesize
// without the parent file and its generated table package.
module ot_engc_hl_rsync(input wire clk, input wire async_rst_n, output wire sync_rst_n);
    (* keep = "true", dont_touch = "true", async_reg = "true" *) reg [1:0] reset_pipe;
    always @(posedge clk or negedge async_rst_n)
        if (!async_rst_n) reset_pipe <= 2'b00;
        else reset_pipe <= {reset_pipe[0], 1'b1};
    assign sync_rst_n = reset_pipe[1];
endmodule
module ot_engc_hl_pipe #(parameter integer W = 1) (input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    (* keep = "true", dont_touch = "true" *) reg [W-1:0] r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r <= {W{1'b0}};
        else r <= d;
    assign q = r;
endmodule
