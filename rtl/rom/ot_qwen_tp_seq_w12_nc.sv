`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_tp_seq_w12_nc (sys-takeover 2026-10-09, registry qfd_native_collective_binding): successor of
// ot_qwen_tp_seq_w12 (which stays byte-identical) for the Qwen ROM die's native collective binding through
// ot_qwen_die_coll_xfifo.  Same descriptors, tags, fold / gather semantics and faults; two boundary changes:
//   * collective send by CREDITS (no ready crosses the master face): CR forward credits at reset (= the coll_xfifo's
//     CR), c_cr returns one; c_valid is asserted only on a credited send (every c_valid is a word); a credit count
//     above CR is a fault.  r_cr returns one credit per received word (the word is consumed on arrival).
//   * vector-memory read by RETURNED VALID: vm_re / vm_raddr request a row, the word is captured when vm_qv comes
//     back (any station / memory latency, in order); a queue slot is reserved per request (QD slots) and a vm_qv with
//     nothing outstanding is a fault.  The write-back (vm_we / vm_waddr / vm_wdata) is unchanged.
// The original header follows.
//
// Tensor-group sequencer of one die: runs a decode step of the die's program
// segment by segment and the one-shot collective after each segment.
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
module ot_qwen_tp_seq_w12_nc #(
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
    parameter integer CR   = 8,      // forward credits at reset (= ot_qwen_die_coll_xfifo CR)
    parameter integer QD   = 8,      // send queue slots (read requests reserve one each)
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
    input  wire              vm_qv,          // a requested row word returns (in request order)
    input  wire [FW-1:0]     vm_rq,
    output reg               vm_we,
    output reg  [VWA-1:0]    vm_waddr,
    output reg  [FW-1:0]     vm_wdata,
    // one-shot collective unit (ot_rom_oneshot_allreduce die port)
    output wire              c_valid,        // a credited word (no ready)
    input  wire              c_cr,           // one forward credit returned
    output wire [FW-1:0]     c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [TAGW-1:0]   c_tag,
    input  wire              r_valid,
    input  wire [FW-1:0]     r_data,
    input  wire              r_last,
    input  wire [RB-1:0]     r_rank,
    input  wire              r_err,
    output reg               r_cr            // one credit per received word
);
    localparam [1:0] K_END = 2'd0, K_AR = 2'd1, K_ARGMAX = 2'd2;
    localparam [2:0] S_IDLE = 0, S_DESC = 1, S_DLAT = 2, S_RUN = 3, S_CWAIT = 4, S_COLL = 5;
    reg [2:0]     st;
    reg [NW-1:0]  tok_r, pos_r;
    reg [DAW-1:0] seg;
    reg [1:0]     kind;
    reg [VWA-1:0] vw;
    reg [8:0]     nw;
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
    localparam integer QB = (QD > 1) ? $clog2(QD) : 1;
    localparam integer CB = $clog2(CR + 1) + 1;
    reg [FW-1:0] q_d [0:QD-1];
    reg [QB-1:0] q_w, q_r;
    reg [QB:0]   q_n, rq_n;          // queued words, outstanding reads
    reg [CB-1:0] cred;
    reg [8:0]    rd_k, tx_k, rx_k;
    wire   c_have  = (st == S_COLL) && (q_n != 0);
`ifdef OT_SEQNC_MUT_NOCREDIT
    wire   c_fire  = c_have;                       // mutant: send without a credit
`else
    wire   c_fire  = c_have && (cred != 0);
`endif
    assign c_valid = c_fire;
    assign c_data  = q_d[q_r];
    assign c_mode  = (kind == K_ARGMAX);
    assign c_last  = (tx_k == ((kind == K_ARGMAX) ? 9'd0 : nw - 1'b1));
    wire   rd_go   = (st == S_COLL) && kind == K_AR && rd_k < nw && (q_n + rq_n) < QD;
`ifdef OT_SEQNC_MUT_FIXEDLAT
    reg    rd_go_q;                                // mutant: the base's one-edge read assumption (ignores vm_qv)
    always @(posedge clk or negedge rst_n) if (!rst_n) rd_go_q <= 1'b0; else rd_go_q <= rd_go;
    wire   rd_v    = rd_go_q;
`else
    wire   rd_v    = vm_qv;
`endif

    reg [NW-1:0] best_i;
    reg [31:0]   best_v;
    wire [31:0]  g_val = r_data[31:0];
    wire [NW-1:0] g_idx = r_data[32 +: NW];
    wire [8:0]   rx_total = (kind == K_ARGMAX) ? N : nw;

    always @(*) begin
        vm_re = rd_go;
        vm_raddr = vw + rd_k;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; next_token <= 0; next_val <= 0;
            tok_r <= 0; pos_r <= 0; seg <= 0; kind <= K_END; vw <= 0; nw <= 0; row0 <= 0;
            prog_base <= 0; desc_re <= 1'b0; desc_addr <= 0;
            vm_we <= 1'b0; vm_waddr <= 0; vm_wdata <= 0;
            q_w <= 0; q_r <= 0; q_n <= 0; rq_n <= 0; rd_k <= 0; tx_k <= 0; rx_k <= 0;
            best_i <= 0; best_v <= 0; cred <= CR[CB-1:0]; r_cr <= 1'b0;
        end else begin
            desc_re <= 1'b0;
            vm_we <= 1'b0;
            r_cr <= r_valid;
            cred <= cred - (c_fire ? 1'b1 : 1'b0) + (c_cr ? 1'b1 : 1'b0);
            if (cred - (c_fire ? 1'b1 : 1'b0) + (c_cr ? 1'b1 : 1'b0) > CR) fault <= 1'b1;
            rq_n <= rq_n + (rd_go ? 1'b1 : 1'b0) - (vm_qv ? 1'b1 : 1'b0);
            if (vm_qv && rq_n == 0) fault <= 1'b1;
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
                    if (r_valid) begin
                        if (r_err) fault <= 1'b1;
                        rx_k <= rx_k + 1'b1;
                        if (r_last != (rx_k == rx_total - 1'b1)) fault <= 1'b1;
                        if (kind == K_AR) begin
`ifdef OT_SEQNC_MUT_WBADDR
                            vm_we <= 1'b1; vm_waddr <= vw + rx_k + 1'b1; vm_wdata <= r_data;   // mutant: write-back one row off
`else
                            vm_we <= 1'b1; vm_waddr <= vw + rx_k; vm_wdata <= r_data;
`endif
                        end else begin
                            if (r_rank != rx_k[RB-1:0]) fault <= 1'b1;
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
