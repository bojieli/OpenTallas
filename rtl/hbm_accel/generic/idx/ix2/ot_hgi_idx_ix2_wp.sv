`timescale 1ns/1ps
`default_nettype none
// ix2 write tile (hbm-redesign-idx 2026-10-13): the two credited links of the beat tile land in pin flops and 4-deep
// queues; four sector packers (O ids, R values, D ids, D values; <= 8 words a cycle each, masked partial sectors);
// each packer's registered sector goes to write lane sector mod 8.  A lane takes at most one of the four registered
// packer outputs a cycle (fixed order O, R, D ids, D values; per-lane VM credits): a 4-way choice a lane.
module ot_hgi_idx_ix2_wp #(
    parameter integer LQ = 10
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire          run,
    input  wire          flush,
    input  wire          has_r_i,
    input  wire [17:0]   o_base_i, r_base_i, d_base_i, d_stride_i,
    input  wire          t_v,
    input  wire [3:0]    t_n,
    input  wire [159:0]  t_o,
    input  wire [135:0]  t_r,
    output reg           t_cr,
    input  wire          d_v,
    input  wire [1:0]    d_n,
    input  wire [65:0]   d_p,
    output reg           d_cr,
    output reg  [8*280-1:0] wwq,
    input  wire [7:0]    wwq_cr,
    input  wire [7:0]    wwq_done,
    output reg           wg_req,
    input  wire          wg_gnt,
    output reg           wp_idle
);
    localparam integer CB = $clog2(LQ) + 1;
    integer l, i;
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    reg st_q, st_2, run_q, fl_q, has_r, tv_q, dv_q, wgnt_q; reg [7:0] wcr_q, wdn_q;
    reg [17:0] o_base, r_base, d_base, d_stride, dx_base; reg [299:0] ti; reg [67:0] di;
    always @(posedge clk or negedge rn)
        if (!rn) begin st_q <= 1'b0; st_2 <= 1'b0; run_q <= 1'b0; fl_q <= 1'b0; tv_q <= 1'b0; dv_q <= 1'b0; wgnt_q <= 1'b0;
            wcr_q <= 8'd0; wdn_q <= 8'd0; end
        else begin st_q <= start; st_2 <= st_q; run_q <= run; fl_q <= flush; tv_q <= t_v; dv_q <= d_v; wgnt_q <= wg_gnt;
            wcr_q <= wwq_cr; wdn_q <= wwq_done; end
    always @(posedge clk) begin
        has_r <= has_r_i; o_base <= o_base_i; r_base <= r_base_i; d_base <= d_base_i; d_stride <= d_stride_i;
        dx_base <= d_base + d_stride; ti <= {t_n, t_r, t_o}; di <= {d_n, d_p};
    end
    // ---------------------------------------------------------------- link queues
    reg [299:0] tq [0:3]; reg [1:0] tqw, tqr; reg [2:0] tqn;
    // The CLOSED beat tile has four D link credits. Return a credit when this
    // landing FIFO has reserved space, rather than waiting for the packers to
    // consume the beat through a six-edge round trip (4/6 beats per cycle).
    // Acknowledge the pin landing directly. Withhold above nine queued beats;
    // reserve four outstanding credits plus the registered landing stages,
    // so sixteen entries cannot overflow even when the packers stall.
    reg [67:0] dq [0:15]; reg [3:0] dqw, dqr; reg [4:0] dqn;
    reg [2:0] dc_pending;
    // Bookkeeping consumes only pin-registered signals. dc_available folds
    // the prior pin arrival and prior ACK into the pending count; current d_v
    // only reaches the registered ACK through OR/AND, never an input adder.
    wire [2:0] dc_available = dc_pending + 3'(dv_q) - 3'(d_cr);
    // r7 (native audit of CLOSED r6: capture 218.6 ps > 190 on d_v, the only input that reached a register through
    // logic): the ACK now consumes the pin flop dv_q only (dc_available already counts it), so every input is a pure
    // pin capture.  Credit return of a beat after an idle link is one edge later; streaming acks stay one a cycle.
    wire dc_ack = dc_available != 3'd0 && dqn < 5'd10;
    wire [299:0] tqh = tq[tqr];
    // Cache the D FIFO head: isolate its sixteen-way read mux from the
    // packers' word-placement stage. Direct landing bypass supplies a new
    // head when an empty/last-entry queue receives a beat on this edge.
    reg [67:0] dqh;
    always @(posedge clk) begin
        if (dv_q && (dqn == 5'd0 || (d_go && dqn == 5'd1))) dqh <= di;
        else if (d_go && dqn > 5'd1) dqh <= dq[dqr + 4'd1];
    end
    wire [3:0] pk_rdy, pk_ev, pk_empty; wire [59:0] pk_sec; wire [1023:0] pk_d; wire [31:0] pk_m;
    reg [3:0] e_take; reg fl_pend, fl_done;
    wire t_go = tqn != 3'd0 && pk_rdy[0] && (pk_rdy[1] || !has_r);
    wire d_go = dqn != 5'd0 && pk_rdy[2] && pk_rdy[3];
    wire fl_go = fl_pend && tqn == 3'd0 && dqn == 5'd0 && !tv_q && !dv_q && (&pk_rdy);
    reg [255:0] w_o, w_r, w_di, w_dx;
    always @* begin
        for (i = 0; i < 8; i = i + 1) begin
            w_o[i*32 +: 32] = {12'd0, tqh[i*20 +: 20]};
            w_r[i*32 +: 32] = tqh[160 + i*17 + 16] ? 32'hFF80_0000 : {tqh[160 + i*17 +: 16], 16'd0};
        end
        w_di = {192'd0, 15'd0, dqh[17 +: 17], 15'd0, dqh[0 +: 17]};
        w_dx = {192'd0, dqh[50 +: 16], 16'd0, dqh[34 +: 16], 16'd0};
    end
    ot_hgi_idx_ix2_pack u_p0 (.clk(clk), .rn(rn), .ld(st_2), .base(o_base), .in_v(t_go), .in_n(tqh[299:296]), .in_w(w_o),
        .flush(fl_go), .rdy(pk_rdy[0]), .e_v(pk_ev[0]), .e_sec(pk_sec[0 +: 15]), .e_d(pk_d[0 +: 256]), .e_m(pk_m[0 +: 8]),
        .e_take(e_take[0]), .empty(pk_empty[0]));
    ot_hgi_idx_ix2_pack u_p1 (.clk(clk), .rn(rn), .ld(st_2), .base(r_base), .in_v(t_go && has_r), .in_n(tqh[299:296]), .in_w(w_r),
        .flush(fl_go), .rdy(pk_rdy[1]), .e_v(pk_ev[1]), .e_sec(pk_sec[15 +: 15]), .e_d(pk_d[256 +: 256]), .e_m(pk_m[8 +: 8]),
        .e_take(e_take[1]), .empty(pk_empty[1]));
    ot_hgi_idx_ix2_pack u_p2 (.clk(clk), .rn(rn), .ld(st_2), .base(d_base), .in_v(d_go), .in_n({2'd0, dqh[67:66]}), .in_w(w_di),
        .flush(fl_go), .rdy(pk_rdy[2]), .e_v(pk_ev[2]), .e_sec(pk_sec[30 +: 15]), .e_d(pk_d[512 +: 256]), .e_m(pk_m[16 +: 8]),
        .e_take(e_take[2]), .empty(pk_empty[2]));
    ot_hgi_idx_ix2_pack u_p3 (.clk(clk), .rn(rn), .ld(st_2), .base(dx_base), .in_v(d_go), .in_n({2'd0, dqh[67:66]}), .in_w(w_dx),
        .flush(fl_go), .rdy(pk_rdy[3]), .e_v(pk_ev[3]), .e_sec(pk_sec[45 +: 15]), .e_d(pk_d[768 +: 256]), .e_m(pk_m[24 +: 8]),
        .e_take(e_take[3]), .empty(pk_empty[3]));
    // ---------------------------------------------------------------- write lanes
    // r5 (Claude group-B4 10-14; native audit of the CLOSED r3 view: launch 271.7 ps > 220 on 1,393 outputs; the r4pin
    // gate with every output on its own pin flop measured reg->reg -27.8 ps = the 15-level packer select cone had to reach
    // the pin flops): the lane payload is registered once INSIDE (wwq_s, next to the packers) and the output register wwq
    // is a pure flop -> wire -> flop copy at the pins.  +1 edge on every write lane (credits are spent at selection,
    // unchanged; the receiver sees each sector one edge later).
    reg [8*280-1:0] wwq_s;
    reg [CB-1:0] wcred [0:7]; reg [11:0] w_out; reg [7:0] w_used; reg [1:0] w_src [0:7]; reg [2:0] e_ln; reg [3:0] wdn_cnt;
    always @* begin
        w_used = 8'd0; e_take = 4'd0;
        for (l = 0; l < 8; l = l + 1) w_src[l] = 2'd0;
        for (i = 0; i < 4; i = i + 1) begin
            e_ln = pk_sec[i*15 +: 3];
            if (pk_ev[i] && wgnt_q && wg_req && !w_used[e_ln] && wcred[e_ln] != '0) begin
                e_take[i] = 1'b1; w_used[e_ln] = 1'b1; w_src[e_ln] = 2'(i);
            end
        end
        wdn_cnt = 4'd0;
        for (l = 0; l < 8; l = l + 1) wdn_cnt = wdn_cnt + {3'd0, wdn_q[l]};
    end
    always @(posedge clk) begin
        if (tv_q) tq[tqw] <= ti;
        if (dv_q) dq[dqw] <= di;
        for (l = 0; l < 8; l = l + 1) begin
            if (w_used[l])
                wwq_s[l*280 +: 279] <= {pk_sec[w_src[l]*15 +: 15], pk_d[w_src[l]*256 +: 256], pk_m[w_src[l]*8 +: 8]};
            wwq[l*280 +: 279] <= wwq_s[l*280 +: 279];
        end
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin
            tqw <= 2'd0; tqr <= 2'd0; tqn <= 3'd0; dqw <= 4'd0; dqr <= 4'd0; dqn <= 5'd0; dc_pending <= 3'd0; t_cr <= 1'b0; d_cr <= 1'b0;
            fl_pend <= 1'b0; fl_done <= 1'b0; wg_req <= 1'b0; wp_idle <= 1'b0; w_out <= 12'd0;
            for (l = 0; l < 8; l = l + 1) begin wcred[l] <= CB'(LQ); wwq[l*280 + 279] <= 1'b0; wwq_s[l*280 + 279] <= 1'b0; end
        end else begin
            t_cr <= t_go; d_cr <= dc_ack;
            dc_pending <= dc_available;
            if (tv_q) tqw <= tqw + 2'd1;
            if (t_go) tqr <= tqr + 2'd1;
            tqn <= tqn + 3'(tv_q) - 3'(t_go);
            if (dv_q) dqw <= dqw + 4'd1;
            if (d_go) dqr <= dqr + 4'd1;
            dqn <= dqn + 5'(dv_q) - 5'(d_go);
            for (l = 0; l < 8; l = l + 1) begin
                wcred[l] <= wcred[l] + CB'(wcr_q[l]) - CB'(w_used[l]);
                wwq_s[l*280 + 279] <= w_used[l]; wwq[l*280 + 279] <= wwq_s[l*280 + 279];
            end
            w_out <= w_out + 12'(e_take[0]) + 12'(e_take[1]) + 12'(e_take[2]) + 12'(e_take[3]) - {8'd0, wdn_cnt};
            if (fl_q) fl_pend <= 1'b1; else if (fl_go) fl_pend <= 1'b0;
            if (fl_go) fl_done <= 1'b1;
            if (tv_q || dv_q || fl_q) wg_req <= 1'b1;
            wp_idle <= fl_done && (&pk_empty) && e_take == 4'd0 && w_out == 12'd0;
            if (!run_q) wg_req <= 1'b0;
            if (st_q) begin
                tqw <= 2'd0; tqr <= 2'd0; tqn <= 3'd0; dqw <= 4'd0; dqr <= 4'd0; dqn <= 5'd0; dc_pending <= 3'd0; fl_pend <= 1'b0; fl_done <= 1'b0;
                wg_req <= 1'b0; wp_idle <= 1'b0;
            end
        end
endmodule

// One output sector packer: up to 8 words a cycle appended at the running word address; a sector leaves (registered,
// with its word mask) when the run crosses the sector end, or on flush when words are pending.
module ot_hgi_idx_ix2_pack (
    input  wire         clk,
    input  wire         rn,
    input  wire         ld,
    input  wire [17:0]  base,
    input  wire         in_v,
    input  wire [3:0]   in_n,
    input  wire [255:0] in_w,
    input  wire         flush,
    output wire         rdy,
    output reg          e_v,
    output reg  [14:0]  e_sec,
    output reg  [255:0] e_d,
    output reg  [7:0]   e_m,
    input  wire         e_take,
    output wire         empty
);
    integer x;
    reg [17:0] a; reg [255:0] pd; reg [7:0] pm;          // word address of the next word, pending sector image / mask
    reg [511:0] nd; reg [15:0] nm; reg [3:0] wx;
    // TWO places for an emitted sector (head e_*, second e2_*): rdy is flops only (!e2_v), so the lane arbitration
    // (e_take) no longer runs into the link queues' go and this packer's word placement (10-13: that loop was a
    // 15-level stage, pre-CTS -132 ps).  An emit only happens under rdy.
    reg e2_v; reg [14:0] e2_sec; reg [255:0] e2_d; reg [7:0] e2_m;
    assign rdy = !e2_v;
    assign empty = !e_v && !e2_v && pm == 8'd0;
    always @* begin
        nd = {256'd0, pd}; nm = {8'd0, pm};
        for (x = 0; x < 8; x = x + 1) begin
            wx = {1'b0, a[2:0]} + 4'(x);
            if (in_v && 4'(x) < in_n) begin nd[{28'd0, wx}*32 +: 32] = in_w[x*32 +: 32]; nm[wx] = 1'b1; end
        end
    end
    wire emit = (in_v && nm[7] && ({1'b0, a[2:0]} + in_n >= 4'd8)) || (flush && nm[7:0] != 8'd0);
    always @(posedge clk) begin
        if (ld) a <= base;
        else if (in_v) a <= a + {14'd0, in_n};
        if (e_v && e_take && e2_v) begin e_sec <= e2_sec; e_d <= e2_d; e_m <= e2_m; end
        else if (emit && (!e_v || e_take)) begin e_sec <= a[17:3]; e_d <= nd[255:0]; e_m <= nm[7:0]; end
        if (emit) begin e2_sec <= a[17:3]; e2_d <= nd[255:0]; e2_m <= nm[7:0]; end
        if (in_v || flush) pd <= emit ? nd[511:256] : nd[255:0];
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin e_v <= 1'b0; e2_v <= 1'b0; pm <= 8'd0; end
        else begin
            if (emit) e_v <= 1'b1; else if (e_take) e_v <= e2_v;
            if (e_take) e2_v <= 1'b0; else if (emit && e_v) e2_v <= 1'b1;
            if (ld) pm <= 8'd0;
            else if (in_v || flush) pm <= emit ? nm[15:8] : nm[7:0];
        end
endmodule
`default_nettype wire
