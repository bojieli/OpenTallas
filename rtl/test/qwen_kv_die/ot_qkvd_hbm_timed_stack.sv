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
    parameter integer PCQ    = 256         // sector requests queued per PC ahead of the model port
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [R-1:0]      rq_v,
    input  wire [R-1:0]      rq_vv,        // 0 K row, 1 V row
    input  wire [R-1:0]      rq_g,
    input  wire [13*R-1:0]   rq_t,
    output reg  [R-1:0]      row_rdy,
    output reg  [R-1:0]      row_vv,
    output reg  [R-1:0]      row_g,
    output reg  [13*R-1:0]   row_t,
    output reg               fault
);
    localparam integer NPC = 32, AW = 30, TAGW = 17, SW = $clog2(NSLOT);
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
    integer x, q, p, k, j, s, e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (p = 0; p < NPC; p = p + 1) begin pq_rp[p] = 0; pq_n[p] = 0; end
            for (x = 0; x < R; x = x + 1) begin wp[x] = 0; rp[x] = 0; nout[x] = 0; end
            m_v <= 0; m_addr <= 0; m_tag <= 0; row_rdy <= 0; row_vv <= 0; row_g <= 0; row_t <= 0; fault <= 1'b0;
        end else begin
            // 1. the model accepted last edge's offers
            for (p = 0; p < NPC; p = p + 1)
                if (m_v[p] && m_rdy[p]) begin pq_rp[p] = (pq_rp[p] + 1) % PCQ; pq_n[p] = pq_n[p] - 1; end
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
                row_rdy[x] <= 1'b0;
                if (nout[x] != 0 && sl_cnt[x][rp[x]] == 3'd4) begin
                    row_rdy[x] <= 1'b1; row_vv[x] <= sl_vv[x][rp[x]]; row_g[x] <= sl_g[x][rp[x]];
                    row_t[13*x +: 13] <= sl_t[x][rp[x]];
                    sl_cnt[x][rp[x]] = 3'd0;
                    rp[x] = (rp[x] + 1) % NSLOT; nout[x] = nout[x] - 1;
                end
            end
        end
    end
endmodule
