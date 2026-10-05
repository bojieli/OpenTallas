`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_tp_seq_w12_f12: 1.2 GHz successor of rtl/rom/ot_qwen_tp_seq_w12.sv (that file stays byte-identical).
// REG_OUT = 0 elaborates the original logic exactly.  REG_OUT = 1 (HBM-accel fmax closure, 2026-10-04):
// the collective/vector-memory outputs vm_re, vm_raddr, c_valid, c_last and c_mode are REGISTERS loaded from
// the module's next state (zero-cycle look-ahead), so every output is a flop and the internal rd_go / c_fire
// read those flops.  Cycle for cycle the outputs equal the original's (lockstep bench
// rtl/test/hbm_accel_qwen/fmax/tb_qwen_tp_seq_f12_lockstep.sv); no cycle is added.
// ---------------------------------------------------------------------------
module ot_qwen_tp_seq_w12_rnext #(
    parameter integer R_NEXT = 0, // default-off complete same-clock return packet cut
    parameter integer REG_OUT = 0,
    parameter integer REG_CDATA = 0,     // c_data from a head register (maintained = q_d[q_r]); needs REG_OUT
    parameter integer ENABLE_AR256 = 0,
    parameter integer N    = 4,
    parameter integer NW   = 16,
    parameter integer PAW  = 12,
    parameter integer VWA  = 8,
    parameter integer DAW  = 6,
    parameter integer FW   = 512,
    parameter integer TAGW = 32,
    // Qwen full-vocabulary descriptors extend row0 with reserved bits
    // [19:18]; the existing 64-bit descriptor shape is unchanged.
    parameter integer QWEN_FULLSHAPE = 0,
    parameter integer RB   = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    // package controller side (the core's handshake)
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    output reg               done,
    output reg  [NW-1:0]     next_token,
    output reg  [31:0]       next_val,
    output reg               fault,
    output wire              coll_busy,
    // decode core
    output wire              core_start,
    output wire [NW-1:0]     core_token,
    output wire [NW-1:0]     core_pos,
    input  wire              core_done,
    input  wire [NW-1:0]     core_next_token,
    input  wire [31:0]       core_next_val,
    input  wire              core_fault,
    output reg  [PAW-1:0]    prog_base,
    // segment descriptors (synchronous read)
    output reg               desc_re,
    output reg  [DAW-1:0]    desc_addr,
    input  wire [63:0]       desc_q,
    // vector memory word port (synchronous read)
    output reg               vm_re,
    output reg  [VWA-1:0]    vm_raddr,
    input  wire [FW-1:0]     vm_rq,
    output reg               vm_we,
    output wire [VWA-1:0]    vm_waddr,
    output wire [FW-1:0]     vm_wdata,
    // one-shot collective unit (ot_rom_oneshot_allreduce die port)
    output wire              c_valid,
    input  wire              c_ready,
    output wire [FW-1:0]     c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [TAGW-1:0]   c_tag,
    input  wire              r_valid,
    input  wire [FW-1:0]     r_data,
    input  wire              r_last,
    input  wire [RB-1:0]     r_rank,
    input  wire              r_err
);
    reg p_valid;
    reg [FW-1:0] p_data;
    reg p_last, p_err;
    reg [RB-1:0] p_rank;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p_valid <= 1'b0;
        else p_valid <= r_valid && (st == S_COLL);
    always @(posedge clk) if (r_valid && (st == S_COLL)) begin
        p_data <= r_data; p_last <= r_last; p_rank <= r_rank; p_err <= r_err;
    end
    wire rx_valid = R_NEXT != 0 ? p_valid : r_valid;
    wire [FW-1:0] rx_data = R_NEXT != 0 ? p_data : r_data;
    wire rx_last = R_NEXT != 0 ? p_last : r_last;
    wire [RB-1:0] rx_rank = R_NEXT != 0 ? p_rank : r_rank;
    wire rx_err = R_NEXT != 0 ? p_err : r_err;
    localparam [1:0] K_END = 2'd0, K_AR = 2'd1, K_ARGMAX = 2'd2;
    localparam [2:0] S_IDLE = 0, S_DESC = 1, S_DLAT = 2, S_RUN = 3, S_CWAIT = 4, S_COLL = 5;
    reg [2:0]     st;
    reg [NW-1:0]  tok_r, pos_r;
    reg [DAW-1:0] seg;
    reg [1:0]     kind;
    reg [VWA-1:0] vw;
    reg [8:0]     nw;
    reg [NW-1:0]  row0;

    reg    core_start_r, coll_busy_r;
    assign core_start = (REG_OUT != 0) ? core_start_r : (st == S_RUN);
    assign core_token = tok_r;
    assign core_pos   = pos_r;
    assign coll_busy  = (REG_OUT != 0) ? coll_busy_r : (st == S_COLL);
    assign c_tag      = {tok_r, pos_r[7:0], {(8 - DAW){1'b0}}, seg};

    // argmax order: larger logit wins (ties are impossible across ranks' rows
    // except by value, and then the earlier rank -- the lower row -- stays)
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction

    // -- transmit: vector-memory words (all-reduce) or the argmax record ------------------
    localparam integer QD = 4;
    reg [FW-1:0] q_d [0:QD-1];
    reg [1:0]    q_w, q_r;
    reg [2:0]    q_n;
    reg [8:0]    rd_k, tx_k, rx_k;
    reg          rd_v;
    reg    [FW-1:0] cd_r;
    reg    [VWA-1:0] vm_waddr_q, vm_waddr_u;
    reg    [FW-1:0]  vm_wdata_q, vm_wdata_u;
    // REG_CDATA: the vector-memory write word / address load on every edge (meaningful only with vm_we), so
    // no receive-side decode enables 512 flops; the original's held value is the same whenever vm_we is high
    assign vm_waddr = (REG_CDATA != 0) ? vm_waddr_u : vm_waddr_q;
    assign vm_wdata = (REG_CDATA != 0) ? vm_wdata_u : vm_wdata_q;
    always @(posedge clk) begin vm_waddr_u <= vw + rx_k; vm_wdata_u <= rx_data; end
    assign c_data  = (REG_CDATA != 0) ? cd_r : q_d[q_r];
    wire   c_valid_c = (st == S_COLL) && (q_n != 0);
    wire   c_mode_c  = (kind == K_ARGMAX);
    wire   c_last_c  = (tx_k == ((kind == K_ARGMAX) ? 9'd0 : nw - 1'b1));
    wire   rd_go_c   = (st == S_COLL) && kind == K_AR && rd_k < nw && (q_n + rd_v) < QD;
    reg    c_valid_r, c_mode_r, c_last_r, rd_go_r;
    reg    [VWA-1:0] ra_r;
    assign c_valid = (REG_OUT != 0) ? c_valid_r : c_valid_c;
    assign c_mode  = (REG_OUT != 0) ? c_mode_r  : c_mode_c;
    assign c_last  = (REG_OUT != 0) ? c_last_r  : c_last_c;
    wire   c_fire  = c_valid && c_ready;
    wire   rd_go   = (REG_OUT != 0) ? rd_go_r : rd_go_c;

    reg [NW-1:0] best_i;
    reg [31:0]   best_v;
    wire [31:0]  g_val = rx_data[31:0];
    wire [NW-1:0] g_idx = rx_data[32 +: NW];
    wire [8:0]   rx_total = (kind == K_ARGMAX) ? N : nw;

    always @(*) begin
        vm_re = rd_go;
        vm_raddr = (REG_OUT != 0) ? ra_r : vw + rd_k;
    end

    // -- REG_OUT look-ahead: the next state of the registers the outputs read (mirrors the FSM below) -------
    reg [2:0]     st_n;
    reg [1:0]     kind_n;
    reg [8:0]     nw_n, rd_k_n, tx_k_n;
    reg [VWA-1:0] vw_n;
    reg [2:0]     q_n_n;
    reg [1:0]     q_w_n;
    always @(*) begin
        st_n = st; kind_n = kind; nw_n = nw; vw_n = vw; rd_k_n = rd_k; tx_k_n = tx_k; q_n_n = q_n; q_w_n = q_w;
        case (st)
            S_IDLE: if (start) st_n = S_DLAT;
            S_DESC: st_n = S_DLAT;
            S_DLAT: if (!desc_re) begin
                kind_n = desc_q[1:0]; vw_n = desc_q[2 +: 8];
                nw_n = (ENABLE_AR256 != 0 && desc_q[1:0] == K_AR && desc_q[10 +: 8] == 8'd0) ? 9'd256 : {1'b0, desc_q[10 +: 8]};
                st_n = S_RUN;
            end
            S_RUN: st_n = S_CWAIT;
            S_CWAIT: if (core_done) begin
                rd_k_n = 0; tx_k_n = 0;
                if (kind == K_END) st_n = S_IDLE;
                else begin
                    if (kind == K_ARGMAX) begin q_n_n = q_n + 1'b1; q_w_n = q_w + 1'b1; end
                    st_n = S_COLL;
                end
            end
            S_COLL: begin
                if (rd_go) rd_k_n = rd_k + 1'b1;
                if (rd_v) q_w_n = q_w + 1'b1;
                // c_fire's term is added at the registers (both cases precomputed, c_fire selects)
                q_n_n = q_n + (rd_v ? 1'b1 : 1'b0);
                if (rx_valid && rx_k == rx_total - 1'b1) st_n = (kind == K_AR) ? S_DESC : S_IDLE;
            end
            default: st_n = S_IDLE;
        endcase
    end
    generate if (REG_OUT != 0) begin : g_regout
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                c_valid_r <= 1'b0; c_mode_r <= 1'b0; c_last_r <= 1'b0; rd_go_r <= 1'b0; ra_r <= 0;
                core_start_r <= 1'b0; coll_busy_r <= 1'b0;
            end else begin
                core_start_r <= (st_n == S_RUN);
                coll_busy_r  <= (st_n == S_COLL);
                // c_fire is only possible in S_COLL: the fired case is tx_k + 1 and q_n_n - 1
                c_valid_r <= (st_n == S_COLL) && (c_fire ? (q_n_n != 3'd1) : (q_n_n != 0));
                c_mode_r  <= (kind_n == K_ARGMAX);
                c_last_r  <= c_fire ? (tx_k + 1'b1 == ((kind_n == K_ARGMAX) ? 9'd0 : nw_n - 1'b1))
                                    : (tx_k_n == ((kind_n == K_ARGMAX) ? 9'd0 : nw_n - 1'b1));
                rd_go_r   <= (st_n == S_COLL) && kind_n == K_AR && rd_k_n < nw_n &&
                             (c_fire ? ((q_n_n - 3'd1) + rd_go) < QD : (q_n_n + rd_go) < QD);
                ra_r      <= vw_n + rd_k_n[VWA-1:0];
            end
        end
        if (REG_CDATA != 0) begin : g_cdata
            // Transmit queue with REGISTERED, per-64-bit-slice write selects.  The free slot q_w is written on
            // every edge it is free during S_CWAIT (the argmax record; a don't-care word when the segment is an
            // all-reduce) and on every rd_v edge in S_COLL (the vector-memory word) -- the original writes are
            // a subset of these, and a free slot holds nothing.  c_data is q_d[q_r] whenever c_valid: two head
            // registers hold the entries q_r and q_r + 1 as they will be after this edge, and a registered
            // copy of c_fire selects between them, so no 512-bit select waits for the collective's ready.
            localparam integer NS = FW / 64;
            reg [FW-1:0] qd [0:QD-1];
            (* keep *) reg [QD-1:0] w1h  [0:NS-1];   // slot written this cycle
            (* keep *) reg [NS-1:0] dcw;             // data source: argmax record (S_CWAIT) / vm_rq
            (* keep *) reg [QD-1:0] r1h  [0:NS-1];   // q_r one-hot
            (* keep *) reg [QD-1:0] r11h [0:NS-1];   // q_r + 1 one-hot
            (* keep *) reg [NS-1:0] fsel;            // c_fire of the previous edge
            reg [FW-1:0] cda, cdb;
            wire [FW-1:0] rec = {{(FW - 32 - NW){1'b0}}, core_next_token + row0, core_next_val};
            wire [1:0] q_r_n = q_r + (c_fire ? 2'd1 : 2'd0);
            wire wen_n = ((st_n == S_CWAIT) && (q_n_n != QD)) || ((st_n == S_COLL) && rd_go);
            genvar sl, kq;
            for (sl = 0; sl < NS; sl = sl + 1) begin : g_s
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) begin w1h[sl] <= 0; dcw[sl] <= 1'b0; r1h[sl] <= 1; r11h[sl] <= 2; fsel[sl] <= 1'b0; end
                    else begin
                        w1h[sl] <= wen_n ? (1 << q_w_n) : 0;
                        dcw[sl] <= (st_n == S_CWAIT);
                        r1h[sl] <= 1 << q_r_n;
                        r11h[sl] <= 1 << (q_r_n + 2'd1);
                        fsel[sl] <= c_fire;
                    end
                wire [63:0] wd = dcw[sl] ? rec[64*sl +: 64] : vm_rq[64*sl +: 64];
                reg [63:0] na, nb;
                integer kk;
                always @(*) begin
                    na = 64'd0; nb = 64'd0;
                    for (kk = 0; kk < QD; kk = kk + 1) begin
                        na = na | ({64{r1h[sl][kk]}}  & (w1h[sl][kk] ? wd : qd[kk][64*sl +: 64]));
                        nb = nb | ({64{r11h[sl][kk]}} & (w1h[sl][kk] ? wd : qd[kk][64*sl +: 64]));
                    end
                end
                always @(posedge clk) begin cda[64*sl +: 64] <= na; cdb[64*sl +: 64] <= nb; end
                for (kq = 0; kq < QD; kq = kq + 1) begin : g_w
                    always @(posedge clk) if (w1h[sl][kq]) qd[kq][64*sl +: 64] <= wd;
                end
                always @(*) cd_r[64*sl +: 64] = fsel[sl] ? cdb[64*sl +: 64] : cda[64*sl +: 64];
            end
        end
    end else begin : g_comb
        always @(*) begin core_start_r = 1'b0; coll_busy_r = 1'b0; c_valid_r = 1'b0; c_mode_r = 1'b0; c_last_r = 1'b0; rd_go_r = 1'b0; ra_r = 0; end
    end endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; next_token <= 0; next_val <= 0;
            tok_r <= 0; pos_r <= 0; seg <= 0; kind <= K_END; vw <= 0; nw <= 0; row0 <= 0;
            prog_base <= 0; desc_re <= 1'b0; desc_addr <= 0;
            vm_we <= 1'b0; vm_waddr_q <= 0; vm_wdata_q <= 0;
            q_w <= 0; q_r <= 0; q_n <= 0; rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_v <= 1'b0;
            best_i <= 0; best_v <= 0;
        end else begin
            desc_re <= 1'b0;
            vm_we <= 1'b0;
            rd_v <= rd_go;
            case (st)
                S_IDLE: if (start) begin
                    tok_r <= token; pos_r <= pos; seg <= 0; done <= 1'b0;
                    desc_re <= 1'b1; desc_addr <= 0; st <= S_DLAT;
                end
                S_DESC: begin desc_re <= 1'b1; desc_addr <= seg; st <= S_DLAT; end
                S_DLAT: if (!desc_re) begin
                    kind <= desc_q[1:0]; vw <= desc_q[2 +: 8];
                    nw <= (ENABLE_AR256 != 0 && desc_q[1:0] == K_AR && desc_q[10 +: 8] == 8'd0) ? 9'd256 : {1'b0, desc_q[10 +: 8]};
                    prog_base <= desc_q[32 +: PAW];
                    row0 <= (QWEN_FULLSHAPE != 0) ?
                            ({desc_q[19:18], desc_q[63:48]}) : desc_q[48 +: NW];
                    st <= S_RUN;
                end
                S_RUN: st <= S_CWAIT;              // the core samples core_start on this edge
                S_CWAIT: if (core_done) begin
                    if (core_fault) fault <= 1'b1;
                    rd_k <= 0; tx_k <= 0; rx_k <= 0;
                    if (kind == K_END) begin
                        done <= 1'b1; next_token <= core_next_token + row0; next_val <= core_next_val;
                        st <= S_IDLE;
                    end else begin
                        if (kind == K_ARGMAX) begin
                            // the die's own {logit, row} is the one record it gathers
                            q_d[q_w] <= {{(FW - 32 - NW){1'b0}}, core_next_token + row0, core_next_val};
                            q_w <= q_w + 1'b1;
                            q_n <= q_n + 1'b1;
                        end
                        st <= S_COLL;
                    end
                end
                S_COLL: begin
                    // queue: vector-memory words read one cycle earlier; pop on send
                    if (rd_go) rd_k <= rd_k + 1'b1;
                    if (rd_v) begin q_d[q_w] <= vm_rq; q_w <= q_w + 1'b1; end
                    if (c_fire) begin q_r <= q_r + 1'b1; tx_k <= tx_k + 1'b1; end
                    q_n <= q_n + (rd_v ? 1'b1 : 1'b0) - (c_fire ? 1'b1 : 1'b0);
                    // receive
                    if (rx_valid) begin
                        if (rx_err) fault <= 1'b1;
                        rx_k <= rx_k + 1'b1;
                        if (rx_last != (rx_k == rx_total - 1'b1)) fault <= 1'b1;
                        if (kind == K_AR) begin
                            vm_we <= 1'b1; vm_waddr_q <= vw + rx_k; vm_wdata_q <= rx_data;
                        end else begin
                            if (rx_rank != rx_k[RB-1:0]) fault <= 1'b1;
                            if (rx_k == 0 || okey(g_val) > okey(best_v)) begin
                                best_v <= g_val; best_i <= g_idx;
                            end
                        end
                        if (rx_k == rx_total - 1'b1) begin
                            if (kind == K_AR) begin
                                seg <= seg + 1'b1; st <= S_DESC;
                            end else begin
                                done <= 1'b1; st <= S_IDLE;
                                if (okey(g_val) > okey(best_v)) begin
                                    next_token <= g_idx; next_val <= g_val;
                                end else begin
                                    next_token <= best_i; next_val <= best_v;
                                end
                            end
                        end
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
