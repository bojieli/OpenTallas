`timescale 1ns/1ps
// Logical reticle boundary for repeated opaque exchange streams. This is not a
// UCIe PHY or a latency/bandwidth model. Every accepted beat carries its own
// transaction, user, position, exchange and topology revision, so two users may be
// interleaved. A last beat completes a vector; an abort beat terminates a
// partial vector, after all earlier accepted beats have been delivered.
//
// Completion has its own one-entry ready/valid register. A terminal beat is
// held at the FIFO head while that register is full, so neither completion
// nor payload can disappear under independent downstream backpressure.
// Reset discards uncompleted transactions; the controller must replay them.
module ot_qwen_activation_handoff #(
    parameter integer DATA_W = 256,
    parameter integer TXN_W = 16,
    parameter integer USER_W = 8,
    parameter integer POS_W = 16,
    parameter integer CUT_W = 8,
    parameter integer XCHG_W = 8,
    parameter integer DEPTH = 4
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  s_valid,
    output wire                  s_ready,
    input  wire [DATA_W-1:0]     s_data,
    input  wire [TXN_W-1:0]      s_txn,
    input  wire [USER_W-1:0]     s_user,
    input  wire [POS_W-1:0]      s_pos,
    input  wire [CUT_W-1:0]      s_cut,
    input  wire [XCHG_W-1:0]     s_exchange,
    input  wire                  s_first,
    input  wire                  s_last,
    input  wire                  s_abort,
    output wire                  m_valid,
    input  wire                  m_ready,
    output wire [DATA_W-1:0]     m_data,
    output wire [TXN_W-1:0]      m_txn,
    output wire [USER_W-1:0]     m_user,
    output wire [POS_W-1:0]      m_pos,
    output wire [CUT_W-1:0]      m_cut,
    output wire [XCHG_W-1:0]     m_exchange,
    output wire                  m_first,
    output wire                  m_last,
    output wire                  m_abort,
    output reg                   done_valid,
    input  wire                  done_ready,
    output reg [TXN_W-1:0]       done_txn,
    output reg [USER_W-1:0]      done_user,
    output reg [POS_W-1:0]       done_pos,
    output reg [CUT_W-1:0]       done_cut,
    output reg [XCHG_W-1:0]      done_exchange,
    output reg                   done_aborted,
    output wire [$clog2(DEPTH+1)-1:0] level,
    output reg                   fault
);
    localparam integer PTR_W = (DEPTH <= 2) ? 1 : $clog2(DEPTH);
    localparam integer CNT_W = $clog2(DEPTH + 1);
    localparam integer BEAT_W = DATA_W + TXN_W + USER_W + POS_W + CUT_W + XCHG_W + 3;
    localparam [PTR_W-1:0] LAST_PTR = PTR_W'(DEPTH-1);
    localparam [CNT_W-1:0] CAPACITY = CNT_W'(DEPTH);
    reg [BEAT_W-1:0] fifo [0:DEPTH-1];
    reg [PTR_W-1:0] rd_ptr, wr_ptr;
    reg [CNT_W-1:0] count;

    function automatic [PTR_W-1:0] advance(input [PTR_W-1:0] ptr);
        advance = (ptr == LAST_PTR) ? {PTR_W{1'b0}} : ptr + 1'b1;
    endfunction

    wire [BEAT_W-1:0] head = fifo[rd_ptr];
    assign {m_abort, m_last, m_first, m_exchange, m_cut, m_pos, m_user, m_txn, m_data} = head;
    wire terminal_head = m_last | m_abort;
    assign m_valid = rst_n && (count != 0) && (!terminal_head || !done_valid);
    wire pop = m_valid && m_ready;
    assign s_ready = rst_n && ((count < CAPACITY) || pop);
    wire push = s_valid && s_ready;
    assign level = count;

    initial if (DEPTH < 2) $error("activation handoff DEPTH must be at least two");

    always @(posedge clk) begin
        if (!rst_n) begin
            rd_ptr <= 0;
            wr_ptr <= 0;
            count <= 0;
            done_valid <= 0;
            done_txn <= 0;
            done_user <= 0;
            done_pos <= 0;
            done_cut <= 0;
            done_exchange <= 0;
            done_aborted <= 0;
            fault <= 0;
        end else begin
            if (push) begin
                fifo[wr_ptr] <= {s_abort, s_last, s_first, s_exchange, s_cut, s_pos,
                                 s_user, s_txn, s_data};
                wr_ptr <= advance(wr_ptr);
                if (s_abort && s_last) fault <= 1'b1;
            end
            if (pop) rd_ptr <= advance(rd_ptr);
            case ({push, pop})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
            if (done_valid && done_ready) done_valid <= 1'b0;
            if (pop && terminal_head) begin
                done_valid <= 1'b1;
                done_txn <= m_txn;
                done_user <= m_user;
                done_pos <= m_pos;
                done_cut <= m_cut;
                done_exchange <= m_exchange;
                done_aborted <= m_abort;
            end
        end
    end
endmodule
