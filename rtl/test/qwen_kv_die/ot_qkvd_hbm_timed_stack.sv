`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qkvd_hbm_timed_stack -- SIMULATION ONLY (qwen-1010/b 2026-10-10, budget audit row qrom_kvdie_hbm_model).
// One HBM3E stack of the KV die on the TIMING-FAITHFUL model ot_hdc_v41x_idx_hbm (32 pseudo-channels, REFpb with the
// refresh-aware choice REFPB 3, FR-FCFS over a reorder window, controller + PHY latency, 1.0 TB/s peak = 32 sectors per
// 1.024 ns), in place of the layer bench's idealised token bucket (750 B/cycle/stack, 16 cycles, no refresh / banks).
//
// The KV-die read path it stands for (results/arch/qwen_kv_die_20261009/CONTRACT.md): a row (layer, g, v, t) is 4
// sectors; sector q goes to PC {q, t[2:0]} of stack t[8:7] at the per-PC sector index {layer, g, v, t[13:9], t[6:3]};
// the landing read crossbar gathers the 4 sectors and returns rows to each row engine in request order.  Here:
//   * each engine request (a row) is split into its 4 sector reads, queued per PC (the CDC / controller queue), and
//     issued to the model's per-PC port (one sector a read, tag {engine, slot, q});
//   * the per-PC sector index goes through the stream-PC map of tb_hbm_svc_kvs (kaddr: bank {j[9:7], j[1:0]}, column
//     j[6:2], row ROW0 + j[>=10], XOR-folded onto the PC as the controller decodes it);
//   * a per-engine reorder buffer (NSLOT rows; the engine's credits bound its outstanding rows) releases a row when its
//     4 sectors are back, in request order: row_rdy[x] with its (v, g, t); the C++ harness then drives the row data.
// The model runs on the core clock with CLK_PS = the core period (it keeps time in ps).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_hbm_timed_stack #(
    parameter integer R      = 8,          // row engines of this stack
    parameter integer NSLOT  = 64,         // reorder slots per engine (>= the engine's outstanding-row credit)
    parameter integer CLK_PS = 833,
    parameter integer REFPB  = 3,
    parameter integer PULLIN = 0,
    parameter integer ROW0   = 64,
    parameter integer PCQ    = 256,        // sector requests queued per PC ahead of the model port
    parameter integer RQ_FAR = 0,          // qwen-1010/b: die relay stations ectl -> landing (rq) of the far engines
    parameter integer RS_FAR = 0           //   and landing -> ectl (rs); engines R/2..R-1 are the far column, 0..R/2-1 abut
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [R-1:0]      rq_v_i,
    input  wire [R-1:0]      rq_vv_i,      // 0 K row, 1 V row
    input  wire [R-1:0]      rq_g_i,
    input  wire [13*R-1:0]   rq_t_i,
    output wire [R-1:0]      row_rdy,
    output wire [R-1:0]      row_vv,
    output wire [R-1:0]      row_g,
    output wire [13*R-1:0]   row_t,
    output reg               fault
);
    localparam integer NPC = 32, AW = 30, TAGW = 17, SW = $clog2(NSLOT);
    // ---- the die relay stations of the row path (registered stages; the far column only) ----
    wire [R-1:0] rq_v, rq_vv, rq_g; wire [13*R-1:0] rq_t;
    reg  [R-1:0] row_rdy_r, row_vv_r, row_g_r; reg [13*R-1:0] row_t_r;
    genvar gx;
    generate for (gx = 0; gx < R; gx = gx + 1) begin : g_rl
        localparam integer DQ_ = (gx >= R / 2) ? RQ_FAR : 0;
        localparam integer DS_ = (gx >= R / 2) ? RS_FAR : 0;
        if (DQ_ > 0) begin : g_q
            ot_hdc_delay #(.W(1), .D(DQ_), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(rq_v_i[gx]), .q(rq_v[gx]));
            ot_hdc_delay #(.W(15), .D(DQ_)) u_d (.clk(clk), .rst_n(rst_n), .d({rq_vv_i[gx], rq_g_i[gx], rq_t_i[13*gx +: 13]}),
                                                .q({rq_vv[gx], rq_g[gx], rq_t[13*gx +: 13]}));
        end else begin : g_q0
            assign rq_v[gx] = rq_v_i[gx]; assign rq_vv[gx] = rq_vv_i[gx]; assign rq_g[gx] = rq_g_i[gx];
            assign rq_t[13*gx +: 13] = rq_t_i[13*gx +: 13];
        end
        if (DS_ > 0) begin : g_s
            ot_hdc_delay #(.W(1), .D(DS_), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(row_rdy_r[gx]), .q(row_rdy[gx]));
            ot_hdc_delay #(.W(15), .D(DS_)) u_d (.clk(clk), .rst_n(rst_n), .d({row_vv_r[gx], row_g_r[gx], row_t_r[13*gx +: 13]}),
                                                .q({row_vv[gx], row_g[gx], row_t[13*gx +: 13]}));
        end else begin : g_s0
            assign row_rdy[gx] = row_rdy_r[gx]; assign row_vv[gx] = row_vv_r[gx]; assign row_g[gx] = row_g_r[gx];
            assign row_t[13*gx +: 13] = row_t_r[13*gx +: 13];
        end
    end endgenerate
    // ---- the timed stack ----
    reg  [NPC-1:0]      m_v;
    wire [NPC-1:0]      m_rdy;
    reg  [NPC*AW-1:0]   m_addr;
    reg  [NPC*TAGW-1:0] m_tag;
    wire [NPC-1:0]      m_rsp_v;
    wire [NPC*TAGW-1:0] m_rsp_tag;
    wire [NPC*4-1:0]    m_rsp_beat;
    wire [NPC*256-1:0]  m_rsp_data;
    wire [NPC-1:0]      m_wr_done;
    ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .DW(256), .MEM_WORDS(1024), .TAGW(TAGW), .LENW(4), .BEATW(4), .QD(64),
                          .REFPB(REFPB), .PULLIN(PULLIN), .MEM_MODE(1), .CLK_PS(CLK_PS)) u_m (
        .clk(clk), .rst_n(rst_n), .req_v(m_v), .req_rdy(m_rdy), .req_addr(m_addr), .req_len({NPC{4'd1}}),
        .req_tag(m_tag), .req_we({NPC{1'b0}}), .req_wdata({NPC*256{1'b0}}), .req_wstrb({NPC*32{1'b0}}),
        .wr_done(m_wr_done), .rsp_v(m_rsp_v), .rsp_rdy({NPC{1'b1}}), .rsp_tag(m_rsp_tag), .rsp_beat(m_rsp_beat),
        .rsp_data(m_rsp_data));
    // the stream-PC map (tb_hbm_svc_kvs kaddr): PC p, per-PC sector index j -> model sector address
    function automatic [29:0] kaddr(input integer pc, input integer j);
        integer row, bank, col, bhi, blo, hi5;
        begin
            row = ROW0 + (j >> 10); bank = (((j >> 7) & 7) << 2) | (j & 3); col = (j >> 2) & 31;
            bhi = (bank >> 2) ^ ((row >> 2) & 7); blo = (bank & 3) ^ (row & 3); hi5 = ((row & 3) << 3) | bhi;
            kaddr = 30'((row << 15) | (bhi << 12) | (col << 7) | (((pc ^ col ^ hi5) & 31) << 2) | blo);
        end
    endfunction
    // ---- per-PC sector request queues (the CDC / controller queue) ----
    reg [AW-1:0]   pq_a [0:NPC-1][0:PCQ-1];
    reg [TAGW-1:0] pq_t [0:NPC-1][0:PCQ-1];
    integer        pq_rp [0:NPC-1], pq_n [0:NPC-1];
    // ---- per-engine reorder buffers ----
    reg [2:0]  sl_cnt [0:R-1][0:NSLOT-1];
    reg        sl_vv  [0:R-1][0:NSLOT-1];
    reg        sl_g   [0:R-1][0:NSLOT-1];
    reg [12:0] sl_t   [0:R-1][0:NSLOT-1];
    integer    wp [0:R-1], rp [0:R-1], nout [0:R-1];
    // statistics (printed at the end of the run when +hbmt_stats): row latency issue -> release, sector issue -> return
    longint    sl_t0 [0:R-1][0:NSLOT-1];
    longint    cyc_n = 0, rows_n = 0, lat_sum = 0, lat_max = 0, busy_n = 0, first_rq = -1, last_rel = 0;
    longint    pc_sec [0:31];
    integer    hist [0:7];
    integer x, q, p, k, j, s, e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (p = 0; p < NPC; p = p + 1) begin pq_rp[p] = 0; pq_n[p] = 0; end
            for (x = 0; x < R; x = x + 1) begin wp[x] = 0; rp[x] = 0; nout[x] = 0; end
            m_v <= 0; m_addr <= 0; m_tag <= 0; row_rdy_r <= 0; row_vv_r <= 0; row_g_r <= 0; row_t_r <= 0; fault <= 1'b0;
        end else begin
            cyc_n = cyc_n + 1;
            // 1. the model accepted last edge's offers
            for (p = 0; p < NPC; p = p + 1)
                if (m_v[p] && m_rdy[p]) begin pc_sec[p] = pc_sec[p] + 1; pq_rp[p] = (pq_rp[p] + 1) % PCQ; pq_n[p] = pq_n[p] - 1; end
            // 2. returned sectors -> their engine's slot
            for (p = 0; p < NPC; p = p + 1)
                if (m_rsp_v[p]) begin
                    e = m_rsp_tag[p*TAGW + 2 + SW +: 3]; s = m_rsp_tag[p*TAGW + 2 +: SW];
                    sl_cnt[e][s] = sl_cnt[e][s] + 3'd1;
                end
            // 3. new engine requests: a slot each, 4 sector reads on PCs {q, t[2:0]}
            for (x = 0; x < R; x = x + 1)
                if (rq_v[x]) begin
                    if (nout[x] == NSLOT) fault <= 1'b1;
                    s = wp[x];
                    sl_t0[x][s] = cyc_n; if (first_rq < 0) first_rq = cyc_n;
                    sl_cnt[x][s] = 3'd0; sl_vv[x][s] = rq_vv[x]; sl_g[x][s] = rq_g[x]; sl_t[x][s] = rq_t[13*x +: 13];
                    wp[x] = (wp[x] + 1) % NSLOT; nout[x] = nout[x] + 1;
                    for (q = 0; q < 4; q = q + 1) begin
                        p = (q << 3) | (rq_t[13*x +: 3]);
                        j = (rq_g[x] << 9) | (rq_vv[x] << 8) | (rq_t[13*x + 9 +: 4] << 4) | rq_t[13*x + 3 +: 4];
                        if (pq_n[p] == PCQ) fault <= 1'b1;
                        k = (pq_rp[p] + pq_n[p]) % PCQ;
                        pq_a[p][k] = kaddr(p, j);
                        pq_t[p][k] = TAGW'((x << (2 + SW)) | (s << 2) | q);
                        pq_n[p] = pq_n[p] + 1;
                    end
                end
            // 4. offers to the model: each PC queue head
            for (p = 0; p < NPC; p = p + 1) begin
                m_v[p] <= (pq_n[p] != 0);
                m_addr[p*AW +: AW] <= pq_a[p][pq_rp[p]];
                m_tag[p*TAGW +: TAGW] <= pq_t[p][pq_rp[p]];
            end
            // 5. in-order release, one row a cycle per engine
            for (x = 0; x < R; x = x + 1) begin
                row_rdy_r[x] <= 1'b0;
                if (nout[x] != 0 && sl_cnt[x][rp[x]] == 3'd4) begin
                    row_rdy_r[x] <= 1'b1; row_vv_r[x] <= sl_vv[x][rp[x]]; row_g_r[x] <= sl_g[x][rp[x]];
                    row_t_r[13*x +: 13] <= sl_t[x][rp[x]];
                    sl_cnt[x][rp[x]] = 3'd0;
                    rows_n = rows_n + 1; lat_sum = lat_sum + (cyc_n - sl_t0[x][rp[x]]); last_rel = cyc_n;
                    if (cyc_n - sl_t0[x][rp[x]] > lat_max) lat_max = cyc_n - sl_t0[x][rp[x]];
                    hist[((cyc_n - sl_t0[x][rp[x]]) >> 5) > 7 ? 7 : ((cyc_n - sl_t0[x][rp[x]]) >> 5)] = hist[((cyc_n - sl_t0[x][rp[x]]) >> 5) > 7 ? 7 : ((cyc_n - sl_t0[x][rp[x]]) >> 5)] + 1;
                    rp[x] = (rp[x] + 1) % NSLOT; nout[x] = nout[x] - 1;
                end
            end
        end
    end
    initial begin for (k = 0; k < 8; k = k + 1) hist[k] = 0; for (k = 0; k < 32; k = k + 1) pc_sec[k] = 0; end
    final begin
        $fwrite(32'h80000002, "HBMT_STATS rows %0d lat_mean %0d lat_max %0d span %0d rows_per_cyc_x1000 %0d hist32 %0d %0d %0d %0d %0d %0d %0d %0d pc0 %0d pc31 %0d\n",
                rows_n, rows_n ? lat_sum / rows_n : 0, lat_max, last_rel - first_rq, (last_rel > first_rq) ? rows_n * 1000 / (last_rel - first_rq) : 0,
                hist[0], hist[1], hist[2], hist[3], hist[4], hist[5], hist[6], hist[7], pc_sec[0], pc_sec[31]);
    end
endmodule
