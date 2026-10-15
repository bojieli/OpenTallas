`timescale 1ns/1ps
// ---- hardened leaves of dsfd_engram_c_hl ------------------------------------------------------------------------
// Return relay leaf, 256 bits (one master, placed twice: at the PB0 and PB1 read-data source pins).
// B6 10-14: like rr64 it conditions the async die reset itself (routed hl2 view: the 421-um rst_io_n net into 256 flops
// across the 166-um leaf captured at 264 ps > 190).
module ot_engc_rr256 (input wire ck, rst, input wire [255:0] d, output wire [255:0] q);
    wire rst_n;
    ot_engc_hl_rsync u_rst (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_n));
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
// Return relay leaf, 256 bits, W-to-N form (die r6 16:26, v19_engram_hl: u_rr1 at pb1's E face, d on W at the pb1.r_d
// y, q on N toward io.rd1).  Same body as ot_engc_rr256; a separate master because one master cannot carry both faces.
module ot_engc_rr256w (input wire ck, rst_n, input wire [255:0] d, output wire [255:0] q);
    (* keep = "true", dont_touch = "true" *) reg [255:0] r;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) r <= 256'b0;
`ifdef OT_ENGC_HL_MUT_RRW
        else r <= {d[127:0], d[255:128]};      // negative control: PB1 returned word halves swapped (beyond SECDED)
`else
        else r <= d;
`endif
    assign q = r;
endmodule
// Return relay leaf, 64 bits (PB2 read-data source pins).  Die r6 16:26: the ctl -> rr2 reset hop is >= 533 um, so
// this leaf takes the ASYNC die reset 'rst' and conditions it itself (2 flops on ck; data-only relay, its release
// edge is not part of any handshake).
module ot_engc_rr64 (input wire ck, rst, input wire [63:0] d, output wire [63:0] q);
    wire rst_n;
    ot_engc_hl_rsync u_rst (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_n));
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
// Control leaf, x part (die r6 16:26 split of the former ot_engc_ctl_leaf; 36.288 x 88.56 in the pb1|pb0 column):
// the 334-bit PB1 -> PB0 write transit pipe on rst_pb0_n, the io/pb1/pb0/pb2 reset conditioners (registered outputs
// to the child reset pins) and the registered partial ACK ack_x = &{child_rso_x, states_x} (async revoked by rst).
module ot_engc_ctl_x (
    input  wire ck, rst,
    input  wire [5:0] x_oh, input wire [7:0] x_a, input wire [319:0] x_d,
    output wire [5:0] x_oh_q, output wire [7:0] x_a_q, output wire [319:0] x_d_q,
    output wire rst_io_n, rst_pb1_n, rst_pb0_n, rst_pb2_n,
    input  wire [3:0] child_rso_x,            // {pb2, pb0, pb1, io}
    output wire [3:0] states_x,               // {pb2, pb0, pb1, io}
    output wire ack_x
);
    ot_engc_hl_rsync u_rst_io   (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_io_n));
    ot_engc_hl_rsync u_rst_pb1  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_pb1_n));
    ot_engc_hl_rsync u_rst_pb0  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_pb0_n));
    ot_engc_hl_rsync u_rst_pb2  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_pb2_n));
    assign states_x = {rst_pb2_n, rst_pb0_n, rst_pb1_n, rst_io_n};
    // transit: only the 6 one-hot write enables carry a reset (they qualify the word); the 328 address / data bits are
    // plain registers (gate 21:5x: one reset conditioner driving 334 flops = 337 loads > 256)
    ot_engc_hl_pipe #(.W(6)) u_xtrans_pb0 (.clk(ck), .rst_n(rst_pb0_n), .d(x_oh), .q(x_oh_q));
    (* keep = "true", dont_touch = "true" *) reg [327:0] xt_q;
    always @(posedge ck)
`ifdef OT_ENGC_HL_MUT_CTL
        xt_q <= {x_a[7:1], 1'b0, x_d};       // negative control: the transit's address LSB is lost (bank 0 writes land on the wrong row)
`else
        xt_q <= {x_a, x_d};
`endif
    assign {x_a_q, x_d_q} = xt_q;
    (* keep = "true", dont_touch = "true" *) reg ack_q;
    always @(posedge ck or negedge rst)
        if (!rst) ack_q <= 1'b0;
`ifdef OT_ENGC_RSO_MUT_MISSING_PB2
        else ack_q <= &{child_rso_x[2:0], states_x};  // negative control: misses genuine final PB2 release
`else
        else ack_q <= &{child_rso_x, states_x};
`endif
    assign ack_x = ack_q;
endmodule
// Control leaf, s part (die r6 16:26; 43.2 x 17.28 above sink, W of win): the win/ws/lkp/sink reset conditioners, the
// 16-bit status pipe (win domain) and the 4-bit release pipe (sink domain), and the registered consumer ACK
// rso = &{child_rso_s, states_s, ack_x_i}; ack_x_i is ctl_x's ack_x through one die relay (dsfd_rly_1_EW, +1 cycle
// of startup-ACK latency only).  Async revoked by rst: no combinational input -> output path crosses the leaf.
module ot_engc_ctl_s (
    input  wire ck, rst,
    output wire rst_win_n, rst_ws_n, rst_lkp_n, rst_sink_n,
    input  wire [1:0] child_rso_s,            // {ws, win}
    output wire [3:0] states_s,               // {sink, lkp, ws, win}
    input  wire ack_x_i,
    output wire rso,
    input  wire [7:0] s_rdy, s_perr, output wire [7:0] s_rdy_q, s_perr_q,
    input  wire [3:0] vrel, output wire [3:0] vrel_q
);
    ot_engc_hl_rsync u_rst_win  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_win_n));
    ot_engc_hl_rsync u_rst_ws   (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_ws_n));
    ot_engc_hl_rsync u_rst_lkp  (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_lkp_n));
    ot_engc_hl_rsync u_rst_sink (.clk(ck), .async_rst_n(rst), .sync_rst_n(rst_sink_n));
    assign states_s = {rst_sink_n, rst_lkp_n, rst_ws_n, rst_win_n};
    ot_engc_hl_pipe #(.W(16)) u_status_win (.clk(ck), .rst_n(rst_win_n), .d({s_perr, s_rdy}), .q({s_perr_q, s_rdy_q}));
`ifdef OT_ENGC_HL_MUT_CTLS
    // negative control: the consumer's slot release (vrel[0] = rel_v) never reaches the sink (slots never free)
    ot_engc_hl_pipe #(.W(4)) u_release_sink (.clk(ck), .rst_n(rst_sink_n), .d({vrel[3:1], 1'b0}), .q(vrel_q));
`else
    ot_engc_hl_pipe #(.W(4)) u_release_sink (.clk(ck), .rst_n(rst_sink_n), .d(vrel), .q(vrel_q));
`endif
    (* keep = "true", dont_touch = "true" *) reg ack_q;
    always @(posedge ck or negedge rst)
        if (!rst) ack_q <= 1'b0;
        else ack_q <= &{child_rso_s, states_s, ack_x_i};
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
