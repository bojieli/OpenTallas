`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_tp_seq_async_sys: rtl/rom/ot_qwen_tp_seq_async_w12.sv (claude/qwen-async-collective-20261003 @ 839bab031,
// unchanged there) with the three default-off additions of rtl/qwen_sys/ot_qwen_tp_seq_sys.sv (TAG_FULL,
// STRAY_FAULT, WDOG) and a fault_code output: the Qwen ROM system top's sequencer when SEQ_ASYNC = 1.
// The original header follows.
// Asynchronous-collective variant of ot_qwen_tp_seq_w12 (which stays
// byte-identical): the tensor-group sequencer of one die, with an opt-in
// CUT-THROUGH all-reduce (dataflow level 5, collective fusion).
//
// ASYNC_COLL = 0 (default): identical behaviour to ot_qwen_tp_seq_w12; the ME
// observation ports are ignored.
//
// ASYNC_COLL = 1: an all-reduce descriptor with bit [20] (CUT) set is sent
// WHILE the core still runs the segment, instead of after its END.  The
// sequencer observes the matrix engine's result writes (the die's vw_me_*
// ports) and keeps one bit per vector-memory word of the all-reduce region
// [vw, vw + nw); word k is sent, in word order, as soon as the engine has
// written all 16 of its lanes in one result write in this segment (the
// engine's masks are full except past the op's output count), or once the
// core reports END, whose barrier means every write has landed (so a word
// written in partial masks waits for END: slower, never early).  Receives are
// accepted from the first one and written back in word order exactly as
// before; the segment advances when the core is done AND the last word is
// received.  The per-word rank-order fold ((p0+p1)+p2)+p3 in
// ot_rom_oneshot_allreduce, the word order, the record tags and the `last`
// protocol checks are unchanged: only the send time moves.
//
// Program contract for CUT (checked by tools/qwen_rom_async_coll.py, which is
// the only producer of the bit): in the segment, the last operation before END
// is the one ME op that writes the whole region, no other ME op of the segment
// writes into it, nothing after it reads or writes it, and END carries a
// barrier.  A descriptor without CUT runs the legacy path, so a binary with
// ASYNC_COLL = 1 runs every existing image unchanged.
// ---------------------------------------------------------------------------
module ot_qwen_tp_seq_async_sys #(
    // ---- the ot_qwen_tp_seq_sys additions (default-off), on the asynchronous-collective sequencer -------------
    // TAG_FULL = 1: collective tag {step generation[1:0], full position, token, segment}; TAGW >= 2 + 2 NW + DAW.
    // STRAY_FAULT = 1: a collective record while no collective is live (S_COLL, or a cut-through segment's S_CWAIT).
    // WDOG > 0: no core done / send / receive for WDOG cycles in S_CWAIT or S_COLL faults.
    parameter integer TAG_FULL = 0,
    parameter integer STRAY_FAULT = 0,
    parameter integer WDOG = 0,
    parameter integer ENABLE_AR256 = 0,
    parameter integer ASYNC_COLL = 0,      // 1: decode descriptor bit [20] as a cut-through all-reduce
    parameter integer NP   = 1,            // ME result-port groups observed (G >> SMIN)
    parameter integer MAW  = 24,           // ME result word-address width
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
    input  wire              r_err,
    // matrix-engine result writes of the die (observation only; ASYNC_COLL = 1)
    input  wire [NP-1:0]     me_we,
    input  wire [NP*MAW-1:0] me_addr,
    input  wire [NP*16-1:0]  me_mask,
    output reg  [2:0]        fault_code       // [0] core/collective/protocol [1] stray record [2] watchdog
);
    localparam [1:0] K_END = 2'd0, K_AR = 2'd1, K_ARGMAX = 2'd2;
    localparam [2:0] S_IDLE = 0, S_DESC = 1, S_DLAT = 2, S_RUN = 3, S_CWAIT = 4, S_COLL = 5;
    localparam integer CUT_BIT = 20;
    localparam integer LN = FW / 32;          // lanes per vector-memory word
    reg [2:0]     st;
    reg [NW-1:0]  tok_r, pos_r;
    reg [DAW-1:0] seg;
    reg [1:0]     kind;
    reg [VWA-1:0] vw;
    reg [8:0]     nw;
    reg [NW-1:0]  row0;
    reg           cut;                      // this segment's all-reduce is cut-through
    reg           core_fin, rx_fin;         // cut-through: the core's END seen / the last word received

    assign core_start = (st == S_RUN);
    assign core_token = tok_r;
    assign core_pos   = pos_r;
    reg [1:0]     gen;
    reg [31:0]    wd_c;
    generate if (TAG_FULL != 0) begin : g_tag_full
        assign c_tag = {{(TAGW - 2 - 2*NW - DAW){1'b0}}, gen, pos_r, tok_r, seg};
    end else begin : g_tag_w12
        assign c_tag = {tok_r, pos_r[7:0], {(8 - DAW){1'b0}}, seg};
    end endgenerate
    // the collective is live in S_COLL, and for a cut-through segment already while the core runs
    wire   coll_on    = (st == S_COLL) || (cut && st == S_CWAIT);
    assign coll_busy  = coll_on;

    // argmax order: larger logit wins (ties are impossible across ranks' rows
    // except by value, and then the earlier rank -- the lower row -- stays)
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction

    // -- cut-through scoreboard: region words the engine has written whole this segment -------------
    // one bit per word, set by a full-mask result write: a decoder per port and a port-OR per word
    reg  [255:0]  lw;
    wire [7:0]    rd_w = rd_k[7:0];
    wire          word_ok = !cut || core_fin || lw[rd_w];

    // -- transmit: vector-memory words (all-reduce) or the argmax record ------------------
    localparam integer QD = 4;
    reg [FW-1:0] q_d [0:QD-1];
    reg [1:0]    q_w, q_r;
    reg [2:0]    q_n;
    reg [8:0]    rd_k, tx_k, rx_k;
    reg          rd_v;
    assign c_valid = coll_on && (q_n != 0);
    assign c_data  = q_d[q_r];
    assign c_mode  = (kind == K_ARGMAX);
    assign c_last  = (tx_k == ((kind == K_ARGMAX) ? 9'd0 : nw - 1'b1));
    wire   c_fire  = c_valid && c_ready;
    wire   rd_go   = coll_on && kind == K_AR && rd_k < nw && (q_n + rd_v) < QD && word_ok;

    reg [NW-1:0] best_i;
    reg [31:0]   best_v;
    wire [31:0]  g_val = r_data[31:0];
    wire [NW-1:0] g_idx = r_data[32 +: NW];
    wire [8:0]   rx_total = (kind == K_ARGMAX) ? N : nw;
    wire         rx_last = r_valid && (rx_k == rx_total - 1'b1);

    always @(*) begin
        vm_re = rd_go;
        vm_raddr = vw + rd_k;
    end

    // per port: the region word offset it writes whole this cycle (one-hot over 256 words)
    wire [255:0] hit_p [0:NP-1];
    wire [255:0] hit;
    genvar gp;
    generate
        for (gp = 0; gp < NP; gp = gp + 1) begin : g_port
            wire [MAW-1:0] a   = me_addr[gp*MAW +: MAW];
            wire [MAW-1:0] off = a - {{(MAW - VWA){1'b0}}, vw};
            wire           in  = me_we[gp] && (&me_mask[gp*16 +: LN]) && a >= {{(MAW - VWA){1'b0}}, vw}
                                 && off < {{(MAW - 9){1'b0}}, nw};
            assign hit_p[gp] = in ? (256'd1 << off[7:0]) : 256'd0;
        end
    endgenerate
    integer pi;
    reg [255:0] hit_or;
    always @(*) begin
        hit_or = 256'd0;
        for (pi = 0; pi < NP; pi = pi + 1) hit_or = hit_or | hit_p[pi];
    end
    assign hit = hit_or;
    always @(posedge clk) begin
        if (ASYNC_COLL != 0) begin
            if (st == S_DLAT) lw <= 256'd0;
            else if (cut && (st == S_RUN || st == S_CWAIT)) lw <= lw | hit;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; next_token <= 0; next_val <= 0;
            tok_r <= 0; pos_r <= 0; seg <= 0; kind <= K_END; vw <= 0; nw <= 0; row0 <= 0;
            prog_base <= 0; desc_re <= 1'b0; desc_addr <= 0;
            vm_we <= 1'b0; vm_waddr <= 0; vm_wdata <= 0;
            q_w <= 0; q_r <= 0; q_n <= 0; rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_v <= 1'b0;
            best_i <= 0; best_v <= 0; cut <= 1'b0; core_fin <= 1'b0; rx_fin <= 1'b0;
            gen <= 0; wd_c <= 0; fault_code <= 0;
        end else begin
            // successor checks (default-off)
            if (STRAY_FAULT != 0 && r_valid && !coll_on) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (WDOG != 0) begin
                if ((st == S_COLL || st == S_CWAIT) && !(r_valid || c_fire || core_done)) begin
                    wd_c <= wd_c + 1;
                    if (wd_c >= WDOG) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
                end else wd_c <= 0;
            end
            desc_re <= 1'b0;
            vm_we <= 1'b0;
            rd_v <= rd_go;
            // queue (vector-memory words read one cycle earlier; pop on send) and receive: in S_COLL,
            // and for a cut-through segment from the core's start
            if (coll_on) begin
                if (rd_go) rd_k <= rd_k + 1'b1;
                if (rd_v) begin q_d[q_w] <= vm_rq; q_w <= q_w + 1'b1; end
                if (c_fire) begin q_r <= q_r + 1'b1; tx_k <= tx_k + 1'b1; end
                q_n <= q_n + (rd_v ? 1'b1 : 1'b0) - (c_fire ? 1'b1 : 1'b0);
                if (r_valid) begin
                    if (r_err) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                    rx_k <= rx_k + 1'b1;
                    if (r_last != (rx_k == rx_total - 1'b1)) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                    if (kind == K_AR) begin
                        vm_we <= 1'b1; vm_waddr <= vw + rx_k; vm_wdata <= r_data;
                    end else begin
                        if (r_rank != rx_k[RB-1:0]) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                        if (rx_k == 0 || okey(g_val) > okey(best_v)) begin
                            best_v <= g_val; best_i <= g_idx;
                        end
                    end
                end
            end
            case (st)
                S_IDLE: if (start) begin
                    tok_r <= token; pos_r <= pos; seg <= 0; done <= 1'b0; gen <= gen + 1'b1;
                    desc_re <= 1'b1; desc_addr <= 0; st <= S_DLAT;
                end
                S_DESC: begin desc_re <= 1'b1; desc_addr <= seg; st <= S_DLAT; end
                S_DLAT: if (!desc_re) begin
                    kind <= desc_q[1:0]; vw <= desc_q[2 +: 8];
                    nw <= (ENABLE_AR256 != 0 && desc_q[1:0] == K_AR && desc_q[10 +: 8] == 8'd0) ? 9'd256 : {1'b0, desc_q[10 +: 8]};
                    prog_base <= desc_q[32 +: PAW];
                    row0 <= (QWEN_FULLSHAPE != 0) ?
                            ({desc_q[19:18], desc_q[63:48]}) : desc_q[48 +: NW];
                    cut <= (ASYNC_COLL != 0) && desc_q[1:0] == K_AR && desc_q[CUT_BIT];
                    core_fin <= 1'b0; rx_fin <= 1'b0;
                    rd_k <= 0; tx_k <= 0; rx_k <= 0;
                    st <= S_RUN;
                end
                S_RUN: st <= S_CWAIT;              // the core samples core_start on this edge
                S_CWAIT: begin
                    if (cut && rx_last) rx_fin <= 1'b1;        // only after every word was sent: see word_ok
                    if (core_done) begin
                        if (core_fault) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                        if (cut) begin
                            // the transfer is already running: keep its counters
                            core_fin <= 1'b1;
                            if (rx_fin || rx_last) begin
                                cut <= 1'b0; seg <= seg + 1'b1; st <= S_DESC;
                            end else st <= S_COLL;
                        end else begin
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
                    end
                end
                S_COLL: begin
                    if (rx_last) begin
                        if (kind == K_AR) begin
                            cut <= 1'b0; seg <= seg + 1'b1; st <= S_DESC;
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
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
