`timescale 1ns/1ps
// Opt-in binary feed successor. Original ctl RTL and closed views remain pinned.
// FLANE_BINARY=1: existing8-bit physical lane output has index in low3, high5zero.
// No off-tile encoder, no extra pipeline edge. MUT5 corrupts binary lane index.
module ot_qkvd_kv_wq_ctl_binary #(
    parameter integer HD   = 128,
    parameter integer QD   = 4,
    parameter integer TAGW = 9,
    parameter integer MUT  = 0,
    parameter integer HEAD_PIPE = 0,         // opt-in selected-row capture before feed pin flops
    parameter integer FLANE_BINARY = 0       // opt-in; default reproduces the legacy one-hot feed
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  kvw_v,
    input  wire [1:0]            kvw_vg,
    input  wire [13:0]           kvw_t,
    input  wire [5:0]            kvw_layer,
    input  wire [HD*8-1:0]       kvw_d,
    output reg                   kvw_cr,
    // feed ports, one per quarter group (output flops)
    output reg  [3:0]            f_v,
    output reg  [4*256-1:0]      f_d,
    output reg  [4*24-1:0]       f_sec,
    output reg  [4*8-1:0]        f_lane,
    output reg  [4*TAGW-1:0]     f_tag,
    // return reports, one per group (land in pin flops)
    input  wire [3:0]            r_v,
    input  wire [3:0]            r_bad,
    output reg                   rw_v,
    output reg  [21:0]           rw_id,
    output reg                   fault
);
    localparam integer QA = (QD > 1) ? $clog2(QD) : 1;
    function automatic [1:0] swq(input [1:0] q);
        swq = (MUT == 1 && q == 2'd1) ? 2'd2 : (MUT == 1 && q == 2'd2) ? 2'd1 : q;
    endfunction
    function automatic [23:0] sec_of(input [5:0] layer, input [1:0] vg, input [13:0] t);
        sec_of = {7'd0, layer, vg[0], vg[1], t[13:9], t[6:3]};
    endfunction
    reg              iv;
    reg  [1:0]       ivg;
    reg  [13:0]      it;
    reg  [5:0]       il;
    reg  [HD*8-1:0]  id;
    reg  [3:0]       rv_r, rb_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv <= 1'b0; rv_r <= 0; rb_r <= 0; end
        else begin iv <= kvw_v; rv_r <= r_v; rb_r <= r_bad; end
    always @(posedge clk) begin ivg <= kvw_vg; it <= kvw_t; il <= kvw_layer; id <= kvw_d; end
    reg  [HD*8-1:0]  qd  [0:QD-1];
    reg  [21:0]      qid [0:QD-1];
    reg  [QA:0]      qw, qr;
    wire             q_empty = (qw == qr);
    wire             q_full = (qw[QA-1:0] == qr[QA-1:0]) && (qw[QA] != qr[QA]);
    always @(posedge clk) if (iv) begin qd[qw[QA-1:0]] <= id; qid[qw[QA-1:0]] <= {il, ivg, it}; end
    reg              hv;
    reg  [21:0]      hid;
    reg  [3:0]       done;
    wire             retire = hv && (done == 4'hF);
    wire             hload = (!hv || retire) && !q_empty;
    wire [HD*8-1:0]  h_row = qd[qr[QA-1:0]];
    wire [21:0]      h_id  = qid[qr[QA-1:0]];
    wire [QA-1:0]    h_slot = qr[QA-1:0];
    reg hp_v;
    reg [HD*8-1:0] hp_row;
    reg [21:0] hp_id;
    reg [QA-1:0] hp_slot;
    generate if (HEAD_PIPE != 0) begin : g_head_pipe
        always @(posedge clk or negedge rst_n)
            if (!rst_n) hp_v <= 1'b0;
            else hp_v <= hload;
        always @(posedge clk) if (hload) begin
            hp_row <= h_row; hp_id <= h_id; hp_slot <= h_slot;
        end
    end endgenerate
    wire feed_load = (HEAD_PIPE != 0) ? hp_v : hload;
    wire [HD*8-1:0] feed_row = (HEAD_PIPE != 0) ? hp_row : h_row;
    wire [21:0] feed_id = (HEAD_PIPE != 0) ? hp_id : h_id;
    wire [QA-1:0] feed_slot = (HEAD_PIPE != 0) ? hp_slot : h_slot;
    // the return report of group g marks sector swq(g)
    wire [3:0] r_q;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_rq
        assign r_q[swq(g)] = rv_r[g];
    end endgenerate
    integer gi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qw <= 0; qr <= 0; kvw_cr <= 1'b0; rw_v <= 1'b0; fault <= 1'b0; hv <= 1'b0; done <= 4'd0; f_v <= 4'd0;
        end else begin
            kvw_cr <= 1'b0; rw_v <= 1'b0;
            f_v <= {4{feed_load}};
            if (iv) begin
                if (q_full) fault <= 1'b1;
                qw <= qw + 1'b1;
            end
            if (|rb_r) fault <= 1'b1;
            if (|(r_q & done)) fault <= 1'b1;
            done <= done | r_q;
            if (retire) begin hv <= 1'b0; kvw_cr <= 1'b1; rw_v <= 1'b1; rw_id <= hid; end
            if (hload) begin hv <= 1'b1; qr <= qr + 1'b1; done <= 4'd0; hid <= h_id; end
        end
    end
    always @(posedge clk) if (feed_load) begin
        for (gi = 0; gi < 4; gi = gi + 1) begin
            f_d[256*gi +: 256] <= feed_row[256*((MUT == 2) ? (swq(gi) ^ 2'd1) : swq(gi)) +: 256];
            f_sec[24*gi +: 24] <= sec_of(feed_id[21:16], feed_id[15:14], feed_id[13:0]);
            f_lane[8*gi +: 8] <= (FLANE_BINARY != 0) ? {5'd0, feed_id[2:0] ^ ((MUT == 5) ? 3'd1 : 3'd0)} : (8'd1 << feed_id[2:0]);
            f_tag[TAGW*gi +: TAGW] <= TAGW'({feed_slot, swq(gi)});
        end
    end
endmodule
