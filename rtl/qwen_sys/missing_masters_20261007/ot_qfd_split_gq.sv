`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// kv-die 2026-10-09 (coordinator: the ROM-die split stations are the largest Qwen ROM loss, +107 L0 / +198 a layer):
// GO QUEUES on the split partition (opt-in, tools/qwen_missing/partition_token.py --gq N; GQ = 0 keeps
// ot_qfd_split_exact.sv's issue shell byte-for-byte).
//
// The issue shell of ot_qfd_split_exact.sv holds a unit not-ready for RT = DCU + DUC edges after every go: the
// controller cannot issue the next op until the stationed status of the last one is post-accept.  A streaming stream
// unit (back-to-back same-class ops) and short ops pay RT on every issue.
//
// Here every unit takes its go + NEXT fields into a GQ-entry FIFO on its own side of the stations.  The UNIT decides
// acceptance with its own, unstationed ready, exactly as in the base core (pop = head valid && the unit's ready for
// the head's fields), so ops start at the unit in base order under the base acceptance rule; the controller only
// needs a free entry (credit: pushes - the unit's pop count returned through the DUC stations).
//   * status (crossing class B): idle and progress / rows leave the unit masked while its queue holds an op
//     (idle_q = idle && empty; progress_q = empty ? progress : 0): a queued op's producer view is never the previous
//     op's.  The controller-side RT mask still covers a go in flight and the status return.
//   * class C (AMAX samples): the AMAX wait uses idle_q (engine idle AND nothing queued).
//   * the pop count crosses as a 4-bit counter, so a status held over several controller edges (the engine stations
//     run on the gated engine clock) is never counted twice.
// ---------------------------------------------------------------------------
module ot_qfd_go_queue #(
    parameter integer W = 8,             // NEXT field bits
    parameter integer D = 2
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         go_in,           // the stationed go
    input  wire [W-1:0] f_in,            // the stationed NEXT fields (sampled with go_in)
    input  wire         unit_ready,      // the unit's own ready for f_out (unstationed)
    output wire         go_out,          // the go the unit sees
    output wire [W-1:0] f_out,           // the head's fields (held after the pop)
    output wire         empty,
    output reg  [3:0]   popc,            // pops so far (mod 16), returned through the DUC stations
    output reg          fault            // push into a full queue (credit violation)
);
    localparam integer AW = (D > 1) ? $clog2(D) : 1;
    reg [W-1:0] mem [0:D-1];
    reg [AW-1:0] rp, wp;
    reg [AW:0]   n;
    reg [W-1:0]  hold;
    wire pop = (n != 0) && unit_ready;
    assign go_out = pop;
    assign f_out = (n != 0) ? mem[rp] : hold;
    assign empty = (n == 0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rp <= 0; wp <= 0; n <= 0; popc <= 4'd0; fault <= 1'b0; end
        else begin
            if (go_in) begin
                if (n == D && !pop) fault <= 1'b1;
                wp <= (wp == D - 1) ? {AW{1'b0}} : wp + 1'b1;
            end
            if (pop) begin rp <= (rp == D - 1) ? {AW{1'b0}} : rp + 1'b1; popc <= popc + 4'd1; end
            n <= n + (go_in ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        end
    end
    always @(posedge clk) begin
        if (go_in) mem[wp] <= f_in;
        if (pop) hold <= mem[rp];
    end
endmodule

// The controller's view of a queued unit: ready = a free queue entry (+ the AMAX idle wait); idle / progress masked for
// RT after a go (the go in flight + the status return), then the unit's queue-masked status.
module ot_qfd_issue_shell_gq #(
    parameter integer RT_ME = 0,
    parameter integer RT_SU = 0,
    parameter integer GQ = 2
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        me_go,
    input  wire        su_go,
    input  wire        me_en,
    input  wire        me_amax,
    input  wire        d_me_idle,          // idle_q, stationed
    input  wire [15:0] d_me_progress,      // progress_q, stationed
    input  wire [3:0]  d_me_popc,
    input  wire        d_su_idle,
    input  wire [15:0] d_su_progress, d_su_rows,
    input  wire [3:0]  d_su_popc,
    output wire        c_me_ready, c_me_idle,
    output wire [15:0] c_me_progress,
    output wire        c_su_ready, c_su_idle,
    output wire [15:0] c_su_progress, c_su_rows
);
    localparam integer CW = 8;
    reg [CW-1:0] sh_me, sh_su;
    reg [3:0]    pc_me, pc_su;             // pushes (mod 16)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sh_me <= 0; sh_su <= 0; pc_me <= 4'd0; pc_su <= 4'd0; end
        else begin
            if (me_go) begin sh_me <= RT_ME[CW-1:0]; pc_me <= pc_me + 4'd1; end
            else if (sh_me != 0 && me_en) sh_me <= sh_me - 1'b1;
            if (su_go) begin sh_su <= RT_SU[CW-1:0]; pc_su <= pc_su + 4'd1; end
            else if (sh_su != 0) sh_su <= sh_su - 1'b1;
        end
    end
    wire [3:0] q_me = pc_me - d_me_popc;   // ops pushed and not yet seen popped (queued or in flight)
    wire [3:0] q_su = pc_su - d_su_popc;
    wire m_me = (sh_me != 0);
    wire m_su = (sh_su != 0);
    wire am_wait = (RT_ME != 0) && me_amax && !(d_me_idle && !m_me && (q_me == 0));
    assign c_me_ready    = (q_me < GQ) && !am_wait;
    assign c_me_idle     = !m_me && (q_me == 0) && d_me_idle;
    assign c_me_progress = (m_me || q_me != 0) ? 16'd0 : d_me_progress;
    assign c_su_ready    = (q_su < GQ);
    assign c_su_idle     = !m_su && (q_su == 0) && d_su_idle;
    assign c_su_progress = (m_su || q_su != 0) ? 16'd0 : d_su_progress;
    assign c_su_rows     = (m_su || q_su != 0) ? 16'd0 : d_su_rows;
endmodule
