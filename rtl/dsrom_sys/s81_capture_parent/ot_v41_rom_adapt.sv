`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rom_adapt: the core's weight ops on the adopted V4.1 ROM field (W17; X_ROM = 1 in ot_hdc_core_v41x).
//
// The core issues two kinds of weight op, both of which run on the one ROM field through ot_v41_spine:
//   QE LINQ  (golden linear_q, FP8/FP4 weights): x = VM[xbase .. xbase + 32*nb), rows -> VM[obase + n] as
//            BF16 (upper half of the word), or FP32 when `unrounded` (the wo_b K-split partial); an expert op
//            (ind) adds VM[ibase] * istride to the weight base.
//   ME weight op (me_wsrc = 0; golden mv / linear_bf16 with BF16 weights): x = VM[xbase + c*xcs + k] over the
//            2^split chunks of me_k, rows -> VM[obase*W + n] as FP32.  Only the contiguous layouts the full-shape
//            program emits are accepted (xks = 1, xcs = me_k, xjs = 0, ots = IL, ojs = 1, me_round = 1,
//            no argmax); anything else raises `fault` rather than computing something else.
// PHASE KEY ROM: entry p (one per phase the die's field holds) = {[31] valid, [30] ME op, [29:0] weight key};
// the key of an op is its weight base (+ expert id * istride).  The lookup is a parallel compare (a CAM over
// 2^PHW entries); an op whose key is in no entry faults (a sparse expert image fails closed).
// Positions (MTP): mx_m positions at x stride xps and output stride ops, as the core's engines.
// ---------------------------------------------------------------------------
module ot_v41_rom_adapt #(
    parameter integer S81_CAPTURE=0,
    parameter integer AW = 30,
    parameter integer NW = 21,
    parameter integer W = 16,
    parameter integer IL = 8,
    parameter integer PHW = 6,
    parameter integer VAW = 19
) (
    input wire capture_command_ready,
    input  wire              clk,
    input  wire              rst_n,
    // QE LINQ op
    input  wire              q_go,
    input  wire [AW-1:0]     q_xbase,
    input  wire [7:0]        q_nb,
    input  wire [AW-1:0]     q_wbase,
    input  wire              q_ind,
    input  wire [AW-1:0]     q_ibase,
    input  wire [AW-1:0]     q_istride,
    input  wire [AW-1:0]     q_obase,
    input  wire              q_unrounded,
    // ME weight op
    input  wire              m_go,
    input  wire [NW-1:0]     m_k,
    input  wire [1:0]        m_split,
    input  wire [AW-1:0]     m_wbase,
    input  wire [AW-1:0]     m_xbase,
    input  wire [AW-1:0]     m_xks,
    input  wire [AW-1:0]     m_xcs,
    input  wire [AW-1:0]     m_xjs,
    input  wire [AW-1:0]     m_obase,
    input  wire [AW-1:0]     m_ots,
    input  wire [AW-1:0]     m_ojs,
    input  wire              m_round,
    input  wire              m_amax,
    input  wire              m_mmode,
    // positions (both)
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps,
    input  wire [AW-1:0]     i_ops,
    output wire              ready,
    output wire              idle,
    // expert id read (VM, registered response)
    output reg               vi_re,
    output reg  [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    // spine op port
    output reg               s_go,
    output reg  [PHW-1:0]    s_ph,
    output reg  [2:0]        s_np,
    output reg  [VAW-1:0]    s_xbase,
    output reg  [VAW-1:0]    s_xps,
    output reg  [VAW-1:0]    s_obase,
    output reg  [VAW-1:0]    s_ops,
    output reg  [1:0]        s_fmt,          // 0 phase ROM, 1 all FP32, 2 all BF16
    input  wire              s_ready,
    input  wire              s_idle,
    output reg               fault
);
    reg [31:0] keyrom [0:(1 << PHW)-1] /*verilator public_flat_rw*/;
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial begin
        for (ii = 0; ii < (1 << PHW); ii = ii + 1) keyrom[ii] = 32'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) $readmemh({rom_dir, "/spine_keys.hex"}, keyrom);
    end
    localparam [2:0] S_IDLE = 3'd0, S_IDX = 3'd1, S_IDXW = 3'd2, S_LOOK = 3'd3, S_GO = 3'd4, S_WAIT = 3'd5;
    reg [2:0] st;
    reg        me_op;
    reg [AW-1:0] key, stride;
    reg [PHW-1:0] hit_p;
    reg        hit;
    integer k;
    always @* begin
        hit = 1'b0; hit_p = '0;
        for (k = (1 << PHW) - 1; k >= 0; k = k - 1)
            if (keyrom[k][31] && keyrom[k][30] == me_op && keyrom[k][29:0] == 30'(key)) begin
                hit = 1'b1; hit_p = PHW'(k);
            end
    end
    assign ready = st == S_IDLE && (S81_CAPTURE ? capture_command_ready : s_ready);
    assign idle = st == S_IDLE && s_idle;
    // ME contiguity: x chunks back to back, rows back to back
    wire m_ok = m_xks == AW'(1) && m_xcs == AW'(m_k) && m_xjs == '0 && m_ots == AW'(IL) && m_ojs == AW'(1) &&
                m_round && !m_amax && !m_mmode;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; s_go <= 1'b0; vi_re <= 1'b0; fault <= 1'b0;
        end else begin
            s_go <= 1'b0; vi_re <= 1'b0;
            case (st)
                S_IDLE: begin
                    if (q_go) begin
                        me_op <= 1'b0; key <= q_wbase; stride <= q_istride;
                        s_np <= (i_m == 3'd0) ? 3'd0 : i_m - 3'd1;
                        s_xbase <= VAW'(q_xbase); s_xps <= VAW'(i_xps); s_obase <= VAW'(q_obase); s_ops <= VAW'(i_ops);
                        s_fmt <= q_unrounded ? 2'd1 : 2'd2;
                        if (q_ind) begin vi_re <= 1'b1; vi_addr <= q_ibase; st <= S_IDX; end
                        else st <= S_LOOK;
                    end else if (m_go) begin
                        me_op <= 1'b1; key <= m_wbase;
                        s_np <= (i_m == 3'd0) ? 3'd0 : i_m - 3'd1;
                        s_xbase <= VAW'(m_xbase); s_xps <= VAW'(i_xps);
                        s_obase <= VAW'(m_obase * AW'(W)); s_ops <= VAW'(i_ops * AW'(W));
                        s_fmt <= 2'd1;
                        if (!m_ok) fault <= 1'b1;
                        st <= S_LOOK;
                    end
                end
                S_IDX: st <= S_IDXW;                        // registered VM response
                S_IDXW: begin key <= key + AW'(vi_q) * stride; st <= S_LOOK; end
                S_LOOK: begin
                    if (!hit) fault <= 1'b1;
                    s_ph <= hit_p; st <= S_GO;
                end
                S_GO: if (s_ready) begin s_go <= 1'b1; st <= S_WAIT; end
                S_WAIT: if (!s_go && s_idle) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
