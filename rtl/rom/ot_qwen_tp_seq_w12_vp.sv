`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Tensor-group sequencer of one die: runs a decode step of the die's program
// segment by segment and the one-shot collective after each segment.
//
// ot_qwen_tp_seq_w12_vp: successor of ot_qwen_tp_seq_w12 for the speculative
// verify step (tools/qwen_rom_verify_program_w12.py).  ENABLE_ARP = 0 (default)
// is ot_qwen_tp_seq_w12 cycle for cycle.  ENABLE_ARP = 1 adds
//   * a wide all-reduce: the count's high bits in descriptor [23:20] (unused
//     before), so one all-reduce streams p x 256 words (p positions back to
//     back) -- one fill/drain of the link for the whole verify block;
//   * kind 3 ARGMAX_NEXT: gather the argmax like ARGMAX, record it as the
//     next position's token (tok_vec/val_vec, n_tok) and continue with the
//     next segment; the final ARGMAX also records.  One argmax per verify
//     position.
// VWA must cover vw + p x 256 words.
//
// LA = 1 (timing, default-off; cycle-for-cycle and record-for-record identical to LA = 0): the
// single-cycle control decisions read registered look-ahead flags instead of re-deriving them
// from counters each cycle -- the last-beat flag rx_last_r (rx_k == rx_total - 1, updated from
// rx_k + 1 == rx_total - 1 on each beat), the transmit read gate's rd_more_r (rd_k < nw) and
// coll_ar_r (st == S_COLL && kind == K_AR), registered kind decodes, and a one-hot record slot
// n_oh (n_tok as a one-hot word: no slot decoder in front of the tok_vec / val_vec enables).
// The argmax gather keeps the running best's order key okey(best_v) in a register (best_k) and
// compares keys with a log-depth tree (ot_qwen_seq_key_gt, levels kept), in two copies: one steers
// the running best, one the gathered record (fin_tok / fin_val, kept as one bus).
// The die's row offset (core_next_token + row0) and the receive counter's increment use the kept
// log-depth adders of rtl/hdc/ot_hdc_prefix.sv.  The two output buses that were combinational are
// registered without a cycle: vm_raddr is a running address register (vw + rd_k, valid with vm_re) and
// c_data is a first-word-fall-through head register (q_d[q_r], valid with c_valid) updated from the
// queue's next state.
// Closes the per-position record path at 1.2 GHz SS (results/rtl/qwen_dspark_closure_20261004).
//
// In a 4-die package (docs/ARCHITECTURE_ATLAS.html 6.6) every die holds a
// slice of every matrix (tools/hdc_golden.Model.decode_token_tp): QKV and
// gate/up by output rows, o and down by input columns -- whose partial
// outputs must be all-reduced before the residual add -- and lm_head by
// vocabulary rows, whose argmax is all-gathered.  tools/hdc_program.py cuts
// the die's program at those points into segments, each ending in END, and
// writes one descriptor per segment (encode_segments):
//
//   [1:0]   kind   0 END: the step is over
//                  1 ALL-REDUCE: vector-memory words [vw, vw + nw) are this
//                    die's partial; replace them with the rank-order sum
//                  2 ARGMAX: all-gather {logit, row} and keep the best in
//                    rank order (strictly greater wins, so a tie keeps the
//                    lower die, i.e. the lower vocabulary row)
//   [9:2]   vw     vector-memory word
//   [17:10] nw     words (an all-reduce's 0 is 256 words: one 4,096-element FP32 vector at 16 lanes)
//   [47:32] base   program word of the segment's first instruction
//   [63:48] row0   vocabulary row of this die's lm_head row 0
//
// The sequencer sits between the package controller (ot_rom_pkg_ctrl, whose
// start/done handshake it presents unchanged) and the decode core (whose
// start/done it drives once per segment; the program ROM adds `prog_base`
// to the core's program address).  Collective records are tagged
// {token, position, segment}; ot_rom_oneshot_die faults if the four dies'
// tags of one word disagree.  `coll_busy` marks the cycles the die spends
// in a collective (the collective latency share of a step).
// ---------------------------------------------------------------------------
module ot_qwen_tp_seq_w12_vp #(
    parameter integer ENABLE_AR256 = 0,
    parameter integer ENABLE_ARP = 0,
    parameter integer LA = 0,
    parameter integer NTOK = 8,
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
    // ENABLE_ARP: per-position argmax records (position i of the step in slot i)
    output reg  [NTOK*NW-1:0] tok_vec,
    output reg  [NTOK*32-1:0] val_vec,
    output reg  [3:0]        n_tok,
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
    output reg  [VWA-1:0]    vm_waddr,
    output reg  [FW-1:0]     vm_wdata,
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
    localparam [1:0] K_END = 2'd0, K_AR = 2'd1, K_ARGMAX = 2'd2, K_ARGNEXT = 2'd3;
    localparam integer CW = 13;          // word counters: up to 4,095 words an all-reduce
    localparam [CW-1:0] NCW = N;
    localparam [2:0] S_IDLE = 0, S_DESC = 1, S_DLAT = 2, S_RUN = 3, S_CWAIT = 4, S_COLL = 5;
    reg [2:0]     st;
    reg [NW-1:0]  tok_r, pos_r;
    reg [DAW-1:0] seg;
    reg [1:0]     kind;
    reg [VWA-1:0] vw;
    reg [CW-1:0]  nw;
    reg           k_amax_r, k_ar_r, k_next_r;   // LA: registered kind decodes (loaded with kind)
    wire          is_amax = (LA != 0) ? k_amax_r : ((kind == K_ARGMAX) || (ENABLE_ARP != 0 && kind == K_ARGNEXT));
    wire          is_ar   = (LA != 0) ? k_ar_r : (kind == K_AR);
    wire          is_next = (LA != 0) ? k_next_r : (ENABLE_ARP != 0 && kind == K_ARGNEXT);
    reg [NW-1:0]  row0;

    assign core_start = (st == S_RUN);
    assign core_token = tok_r;
    assign core_pos   = pos_r;
    assign coll_busy  = (st == S_COLL);
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
    reg [CW-1:0] rd_k, tx_k, rx_k;
    reg          rd_v;
    reg          rx_last_r, rd_more_r, coll_ar_r;   // LA look-ahead flags
    reg [CW-1:0] rx_tm2;                           // LA: rx_total - 2 of the current collective
    reg [CW-1:0] nw_m1;                            // LA: nw - 1
    reg [NTOK-1:0] n_oh;                           // LA: one-hot record slot (n_tok), 0 when full
    assign c_valid = (st == S_COLL) && (q_n != 0);
    reg  [FW-1:0]  c_head;                         // LA: q_d[q_r] as a register
    reg  [VWA-1:0] rd_addr;                        // LA: vw + rd_k as a register
    assign c_data  = (LA != 0) ? c_head : q_d[q_r];
    assign c_mode  = is_amax;
    assign c_last  = (tx_k == (is_amax ? {CW{1'b0}} : ((LA != 0) ? nw_m1 : nw - 1'b1)));
    wire   c_fire  = c_valid && c_ready;
    wire   rd_go   = (LA != 0) ? (coll_ar_r && rd_more_r && (q_n + rd_v) < QD)
                               : ((st == S_COLL) && kind == K_AR && rd_k < nw && (q_n + rd_v) < QD);

    reg [NW-1:0] best_i;
    reg [31:0]   best_v;
    wire [31:0]  g_val = r_data[31:0];
    wire [NW-1:0] g_idx = r_data[32 +: NW];
    wire [CW-1:0] rx_total = is_amax ? N : nw;
    wire          rx_last  = (LA != 0) ? rx_last_r : (rx_k == rx_total - 1'b1);
    wire          rec_room = (LA != 0) ? (n_oh != 0) : (n_tok < NTOK);
    // LA: running best's key in a register, tree comparators (one for the best, one for the record)
    reg  [31:0]   best_k;
    reg           rx_first_r;
    wire [31:0]   g_key = okey(g_val);
    wire          gt_b_la, gt_r_la;
    wire          gt_b = (LA != 0) ? gt_b_la : (okey(g_val) > okey(best_v));
    wire          gt_r = (LA != 0) ? gt_r_la : (okey(g_val) > okey(best_v));
    wire          rx_first = (LA != 0) ? rx_first_r : (rx_k == 0);
    (* keep *) wire [NW-1:0] fin_tok = gt_r ? g_idx : best_i;
    // the die's own {logit, row}: core_next_token + row0; the receive counter's increment
    wire [NW-1:0] tok_row_la, tok_row;
    wire [CW-1:0] rx_k1_la, rx_k1;
    generate if (LA != 0) begin : g_la
        ot_qwen_seq_key_gt u_gt_b (.a(g_key), .b(best_k), .gt(gt_b_la));
        ot_qwen_seq_key_gt u_gt_r (.a(g_key), .b(best_k), .gt(gt_r_la));
        ot_hdc_ksadd_k #(.W(NW)) u_tok_row (.a(core_next_token), .b(row0), .cin(1'b0), .s(tok_row_la), .cout());
        ot_hdc_inc_k #(.W(CW)) u_rx_inc (.a(rx_k), .inc(1'b1), .y(rx_k1_la), .co());
    end else begin : g_nla
        assign gt_b_la = 1'b0; assign gt_r_la = 1'b0; assign tok_row_la = {NW{1'b0}}; assign rx_k1_la = {CW{1'b0}};
    end endgenerate
    assign tok_row = (LA != 0) ? tok_row_la : core_next_token + row0;
    assign rx_k1   = (LA != 0) ? rx_k1_la : rx_k + 1'b1;
    (* keep *) wire [31:0]   fin_val = gt_r ? g_val : best_v;

    always @(*) begin
        vm_re = rd_go;
        vm_raddr = (LA != 0) ? rd_addr : vw + rd_k;
    end
    // LA head register: the queue's next head, from the writes and pop of this cycle
    wire          hq_wr_a = (st == S_CWAIT) && core_done && kind != K_END && is_amax;
    wire          hq_wr_b = (st == S_COLL) && rd_v;
    wire [FW-1:0] hq_wd   = hq_wr_b ? vm_rq : {{(FW - 32 - NW){1'b0}}, tok_row, core_next_val};
    wire [1:0]    hq_r_n  = q_r + (((st == S_COLL) && c_fire) ? 2'd1 : 2'd0);
    always @(posedge clk)
        if (LA != 0) c_head <= ((hq_wr_a || hq_wr_b) && q_w == hq_r_n) ? hq_wd : q_d[hq_r_n];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; next_token <= 0; next_val <= 0;
            tok_r <= 0; pos_r <= 0; seg <= 0; kind <= K_END; vw <= 0; nw <= 0; row0 <= 0;
            prog_base <= 0; desc_re <= 1'b0; desc_addr <= 0;
            vm_we <= 1'b0; vm_waddr <= 0; vm_wdata <= 0;
            q_w <= 0; q_r <= 0; q_n <= 0; rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_v <= 1'b0;
            best_i <= 0; best_v <= 0; best_k <= 32'h8000_0000; rx_first_r <= 1'b0;
            tok_vec <= 0; val_vec <= 0; n_tok <= 0;
            k_amax_r <= 1'b0; k_ar_r <= 1'b0; k_next_r <= 1'b0;
            rx_last_r <= 1'b0; rd_more_r <= 1'b0; coll_ar_r <= 1'b0; rx_tm2 <= 0; nw_m1 <= 0; n_oh <= 0; rd_addr <= 0;
        end else begin
            desc_re <= 1'b0;
            vm_we <= 1'b0;
            rd_v <= rd_go;
            case (st)
                S_IDLE: if (start) begin
                    tok_r <= token; pos_r <= pos; seg <= 0; done <= 1'b0; n_tok <= 0;
                    n_oh <= {{(NTOK - 1){1'b0}}, 1'b1};
                    desc_re <= 1'b1; desc_addr <= 0; st <= S_DLAT;
                end
                S_DESC: begin desc_re <= 1'b1; desc_addr <= seg; st <= S_DLAT; end
                S_DLAT: if (!desc_re) begin
                    kind <= desc_q[1:0]; vw <= desc_q[2 +: 8];
                    k_amax_r <= (desc_q[1:0] == K_ARGMAX) || (ENABLE_ARP != 0 && desc_q[1:0] == K_ARGNEXT);
                    k_ar_r   <= (desc_q[1:0] == K_AR);
                    k_next_r <= (ENABLE_ARP != 0 && desc_q[1:0] == K_ARGNEXT);
                    nw <= (ENABLE_ARP != 0 && desc_q[1:0] == K_AR && desc_q[20 +: 4] != 4'd0) ?
                              {{(CW - 12){1'b0}}, desc_q[20 +: 4], desc_q[10 +: 8]} :
                          (ENABLE_AR256 != 0 && desc_q[1:0] == K_AR && desc_q[10 +: 8] == 8'd0) ? 13'd256 :
                              {{(CW - 8){1'b0}}, desc_q[10 +: 8]};
                    prog_base <= desc_q[32 +: PAW];
                    row0 <= (QWEN_FULLSHAPE != 0) ?
                            ({desc_q[19:18], desc_q[63:48]}) : desc_q[48 +: NW];
                    // the wide count's [23:20] are row0 bits nowhere: only all-reduce descriptors carry them
                    st <= S_RUN;
                end
                S_RUN: begin
                    st <= S_CWAIT;                 // the core samples core_start on this edge
                    // LA: the collective's constants, from the registers loaded at S_DLAT
                    nw_m1  <= nw - 1'b1;
                    rx_tm2 <= (is_amax ? NCW : nw) - 2'd2;
                end
                S_CWAIT: if (core_done) begin
                    if (core_fault) fault <= 1'b1;
                    rd_k <= 0; tx_k <= 0; rx_k <= 0; rx_first_r <= 1'b1; rd_addr <= vw;
                    rx_last_r <= (rx_tm2 == {CW{1'b1}});        // rx_total == 1
                    rd_more_r <= (nw_m1 != {CW{1'b1}});         // nw != 0
                    coll_ar_r <= (kind != K_END) && is_ar;
                    if (kind == K_END) begin
                        done <= 1'b1; next_token <= tok_row; next_val <= core_next_val;
                        st <= S_IDLE;
                    end else begin
                        if (is_amax) begin
                            // the die's own {logit, row} is the one record it gathers
                            q_d[q_w] <= {{(FW - 32 - NW){1'b0}}, tok_row, core_next_val};
                            q_w <= q_w + 1'b1;
                            q_n <= q_n + 1'b1;
                        end
                        st <= S_COLL;
                    end
                end
                S_COLL: begin
                    // queue: vector-memory words read one cycle earlier; pop on send
                    if (rd_go) begin
                        rd_k <= rd_k + 1'b1;
                        rd_addr <= rd_addr + 1'b1;
                        rd_more_r <= (rd_k != nw_m1);           // rd_k + 1 < nw (rd_k < nw here)
                    end
                    if (rd_v) begin q_d[q_w] <= vm_rq; q_w <= q_w + 1'b1; end
                    if (c_fire) begin q_r <= q_r + 1'b1; tx_k <= tx_k + 1'b1; end
                    q_n <= q_n + (rd_v ? 1'b1 : 1'b0) - (c_fire ? 1'b1 : 1'b0);
                    // receive
                    if (r_valid) begin
                        if (r_err) fault <= 1'b1;
                        rx_k <= rx_k1;
                        rx_first_r <= 1'b0;
                        rx_last_r <= (rx_k == rx_tm2);           // the next beat is the last
                        if (r_last != rx_last) fault <= 1'b1;
                        if (is_ar) begin
                            vm_we <= 1'b1; vm_waddr <= vw + rx_k; vm_wdata <= r_data;
                        end else begin
                            if (r_rank != rx_k[RB-1:0]) fault <= 1'b1;
                            if (rx_first || gt_b) begin
                                best_v <= g_val; best_i <= g_idx; best_k <= g_key;
                            end
                        end
                        if (rx_last) begin
                            coll_ar_r <= 1'b0;
                            if (is_ar) begin
                                seg <= seg + 1'b1; st <= S_DESC;
                            end else begin
                                if (ENABLE_ARP != 0 && rec_room) begin
                                    if (LA != 0) begin : rec_oh
                                        integer j;
                                        for (j = 0; j < NTOK; j = j + 1)
                                            if (n_oh[j]) begin
                                                tok_vec[j*NW +: NW] <= fin_tok; val_vec[j*32 +: 32] <= fin_val;
                                            end
                                    end else begin
                                        tok_vec[n_tok*NW +: NW] <= fin_tok; val_vec[n_tok*32 +: 32] <= fin_val;
                                    end
                                    n_tok <= n_tok + 1'b1;
                                    n_oh <= n_oh << 1;
                                end
                                if (is_next) begin
                                    seg <= seg + 1'b1; st <= S_DESC;
                                end else begin
                                    done <= 1'b1; st <= S_IDLE;
                                end
                                next_token <= fin_tok; next_val <= fin_val;
                            end
                        end
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule

// a > b on 32-bit unsigned keys, log depth: nibble compares, then three (gt, eq) merge levels; every
// level is kept so the mapper cannot re-ripple it in context (repo memory abc-re-ripples-adders-in-context).
module ot_qwen_seq_key_gt (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire        gt
);
    (* keep *) wire [7:0] g0, e0;
    (* keep *) wire [3:0] g1, e1;
    (* keep *) wire [1:0] g2, e2;
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : l0
            assign g0[i] = a[4*i +: 4] > b[4*i +: 4];
            assign e0[i] = a[4*i +: 4] == b[4*i +: 4];
        end
        for (i = 0; i < 4; i = i + 1) begin : l1
            assign g1[i] = g0[2*i+1] | (e0[2*i+1] & g0[2*i]);
            assign e1[i] = e0[2*i+1] & e0[2*i];
        end
        for (i = 0; i < 2; i = i + 1) begin : l2
            assign g2[i] = g1[2*i+1] | (e1[2*i+1] & g1[2*i]);
            assign e2[i] = e1[2*i+1] & e1[2*i];
        end
    endgenerate
    assign gt = g2[1] | (e2[1] & g2[0]);
endmodule
