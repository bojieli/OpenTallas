`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// redesign-qwen 2026-10-09: the KV-die landing write queue as HARDENED TILES (owner: no monoliths, no single-face pin
// walls).  ot_qkvd_kv_wq_dist as one 172.8 x 1,296 master still failed (qkd_kvwq_d{a,b} EF -1,238 / -1,327: 9.3 k output
// pins on one face, the output flops 260 ps of wire + 550 ps of buffers from their pins).  Here the block is split into
//   ot_qkvd_kv_wq_ctl   x 1  pin capture of the posted rows, the QD-row queue, the head bookkeeping (credits, durable
//                            pulse, faults) and one REGISTERED FEED PORT per quarter group (sector, address, lane, tag)
//   ot_qkvd_kv_wq_grp   x 4  one quarter group (8 PCs on one span of the landing): feed pin flops, the group head, room /
//                            write-done of its own PCs (pin flops), the 8 PCs' output flops, a registered return report
// joined by registered abutted boundaries (feed: ctl output flop -> RLY relays -> grp pin flop; return: grp flop -> RLY
// relays -> ctl pin flop).  Same ports, layout, credits and fault contract as ot_qkvd_kv_wq; +2 + 2 RLY core cycles a row
// (posted, off the token path).  One row in flight, as the base.
// MUT (must FAIL the write-path bench): 1 = sectors 1 / 2 swap PC groups, 2 = wrong quarter's bytes, 3 = quarter 0 never
// pushed.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_wq_grp #(
    parameter integer GP   = 8,
    parameter integer TAGW = 9,
    parameter integer NOPUSH = 0             // MUT 3 on this group
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // feed (from the ctl tile's output flops, possibly relayed)
    input  wire                 f_v,
    input  wire [255:0]         f_d,
    input  wire [23:0]          f_sec,
    input  wire [GP-1:0]        f_lane,
    input  wire [TAGW-1:0]      f_tag,
    // this group's PCs
    output reg  [GP-1:0]        w_v,
    output reg  [24*GP-1:0]     w_sec,
    output reg  [256*GP-1:0]    w_data,
    output reg  [TAGW*GP-1:0]   w_tag,
    input  wire [GP-1:0]        w_room,
    input  wire [GP-1:0]        wd_v,
    input  wire [TAGW*GP-1:0]   wd_tag,
    // return report (registered)
    output reg                  r_v,
    output reg                  r_bad
);
    // pin flops
    reg            p_v;
    reg [255:0]    p_d;
    reg [23:0]     p_sec;
    reg [GP-1:0]   p_lane;
    reg [TAGW-1:0] p_tag;
    reg [GP-1:0]   room_r, wdv_r;
    reg [TAGW*GP-1:0] wdt_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin p_v <= 1'b0; room_r <= 0; wdv_r <= 0; end
        else begin p_v <= f_v; room_r <= w_room; wdv_r <= wd_v; end
    always @(posedge clk) begin p_d <= f_d; p_sec <= f_sec; p_lane <= f_lane; p_tag <= f_tag; wdt_r <= wd_tag; end
    // group head
    reg            gv, gsent, gdone, rq;
    reg [255:0]    gd;
    reg [23:0]     gsec;
    reg [GP-1:0]   glane;
    reg [TAGW-1:0] gtag;
    wire           gpush = gv && !gsent && rq && (NOPUSH == 0);
    reg            wd_any, wd_bad;
    integer k;
    always @* begin
        wd_any = 1'b0; wd_bad = 1'b0;
        for (k = 0; k < GP; k = k + 1)
            if (wdv_r[k]) begin
                wd_any = 1'b1;
                if (wdt_r[TAGW*k +: TAGW] != gtag || !gsent || gdone || !gv) wd_bad = 1'b1;
            end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin gv <= 1'b0; gsent <= 1'b0; gdone <= 1'b0; rq <= 1'b0; r_v <= 1'b0; r_bad <= 1'b0; end
        else begin
            r_v <= wd_any && !wd_bad;
            r_bad <= wd_bad;
            if (p_v) begin gv <= 1'b1; gsent <= 1'b0; gdone <= 1'b0; rq <= 1'b0; end
            else begin
                gsent <= gsent | gpush;
                gdone <= gdone | wd_any;
                rq <= (|(room_r & glane)) && !gpush;
            end
        end
    end
    always @(posedge clk) if (p_v) begin gd <= p_d; gsec <= p_sec; glane <= p_lane; gtag <= p_tag; end
    genvar i;
    generate for (i = 0; i < GP; i = i + 1) begin : g_pc
        always @(posedge clk or negedge rst_n)
            if (!rst_n) w_v[i] <= 1'b0;
            else w_v[i] <= gpush && glane[i];
        always @(posedge clk) if (gpush && glane[i]) begin
            w_data[256*i +: 256] <= gd;
            w_sec[24*i +: 24] <= gsec;
            w_tag[TAGW*i +: TAGW] <= gtag;
        end
    end endgenerate
endmodule


module ot_qkvd_kv_wq_ctl #(
    parameter integer HD   = 128,
    parameter integer QD   = 4,
    parameter integer TAGW = 9,
    parameter integer MUT  = 0
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
            f_v <= {4{hload}};
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
    always @(posedge clk) if (hload) begin
        for (gi = 0; gi < 4; gi = gi + 1) begin
            f_d[256*gi +: 256] <= h_row[256*((MUT == 2) ? (swq(gi) ^ 2'd1) : swq(gi)) +: 256];
            f_sec[24*gi +: 24] <= sec_of(h_id[21:16], h_id[15:14], h_id[13:0]);
            f_lane[8*gi +: 8] <= 8'd1 << h_id[2:0];
            f_tag[TAGW*gi +: TAGW] <= TAGW'({h_slot, swq(gi)});
        end
    end
endmodule


