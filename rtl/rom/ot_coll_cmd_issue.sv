`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-coll-io r5 2026-10-14 (OWNER 0ah static cycle schedule): COMMAND ISSUER of the static TP8 collective.
// The compiler's collective commands for one stage are written over the program-write face (pw_*) and issued at
// their compiled cycles by the shared fixed-issue core ot_qwen_fixed_issue (q_compile_schedule / q_control, main
// rtl/qwen_sys/static_schedule_20261014): same sparse calendar semantics (two-record prefetch from a one-edge store,
// issue exactly at row cycle, END row at the stop cycle, candidate / availability checked as faults, never waited for).
// This instance owns unit 2 (= collective message); unit 3 (copy) rows are refused (cp_available 0 -> fault).
//
// PW layout (64-bit words, BASE assigned by q_control; DEPTH rows):
//   BASE + 2k     row k   {cycle[31:0] @ [31:0], words[15:0] @ [47:32], mode @ [48], end @ [49], 0 @ [63:50]}
//   BASE + 2k + 1 tag k   {0 @ [63:32], tag[31:0]}
//   BASE + 2*DEPTH seal   {16'h434c "CL" @ [63:48], 0 @ [47:38], count[5:0] @ [37:32], stop_cycle[31:0]}
// Row cycles count from the stage start: a row with cycle x reaches the collective's cmd_* pins (combinational
// from the issue core, same cycle as issue_v) x + 1 cycles after the cycle start is presented.  The last row must be
// the END row (end 1) at stop_cycle.  A start before the seal, a bad seal, an unloaded descriptor at its issue
// cycle, a late / out-of-order row, or a command the collective cannot accept (cmd_free 0) sets the sticky fault;
// the timeline is never stretched.
// ---------------------------------------------------------------------------
module ot_coll_cmd_issue #(
    parameter integer DEPTH = 8,
    parameter integer BASE  = 0,
    parameter integer TAGW  = 32
) (
    input  wire            clk, rst_n,
    input  wire            pw_v,
    input  wire [9:0]      pw_addr,
    input  wire [63:0]     pw_data,
    input  wire            start,
    input  wire            cmd_free,      // from the collective (fault check only)
    output wire            cmd_v,
    output wire            cmd_mode,
    output wire [15:0]     cmd_words,
    output wire [TAGW-1:0] cmd_tag,
    output wire            active, done,
    output wire            image_ready,   // sealed configuration fact; never gates issue
    output wire            fault
);
    localparam integer RAW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    initial if (DEPTH > 31 || BASE + 2 * DEPTH > 1023) $error("ot_coll_cmd_issue: DEPTH <= 31, PW window in 0..1023");
    reg [31:0] cyc  [0:DEPTH-1];
    reg [15:0] wds  [0:DEPTH-1];
    reg        mde  [0:DEPTH-1];
    reg        endr [0:DEPTH-1];
    reg [TAGW-1:0] tg [0:DEPTH-1];
    reg [DEPTH-1:0] header_loaded, tag_loaded;
    `ifdef OT_COLL_ISSUE_MUT_HALF_LOADED
    wire [DEPTH-1:0] loaded = header_loaded | tag_loaded;
`else
    wire [DEPTH-1:0] loaded = header_loaded & tag_loaded;
`endif
    reg [31:0] stop_q; reg [5:0] count_q; reg sealed, cfg_fault;
    wire in_rows = pw_v && pw_addr >= BASE && pw_addr < BASE + 2 * DEPTH;
    wire [9:0] off = pw_addr - 10'(BASE);
    wire [RAW-1:0] ri = off[RAW:1];
    wire seal_w = pw_v && pw_addr == BASE + 2 * DEPTH;
    always @(posedge clk) if (in_rows) begin
        if (!off[0]) begin cyc[ri] <= pw_data[31:0]; wds[ri] <= pw_data[47:32]; mde[ri] <= pw_data[48];
                           endr[ri] <= pw_data[49]; end
        else tg[ri] <= pw_data[TAGW-1:0];
    end
    wire run;
    integer ck_row;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin header_loaded <= 0; tag_loaded <= 0; sealed <= 1'b0; stop_q <= 0; count_q <= 0; cfg_fault <= 1'b0; end
        else begin
            // Nonzero BASE shares the dense controller image: PW0 begins
            // a new image. Active images are never replaced mid-timeline.
            if (BASE != 0 && pw_v && pw_addr == 0) begin
                if (run) cfg_fault <= 1'b1;
                else begin header_loaded <= 0; tag_loaded <= 0;
                    sealed <= 1'b0; count_q <= 0; stop_q <= 0; end
            end
            if (in_rows) begin
                if (off[0]) tag_loaded[ri] <= 1'b1; else header_loaded[ri] <= 1'b1;
                if (sealed || run) cfg_fault <= 1'b1;
            end
            if (seal_w) begin
                sealed <= 1'b1; stop_q <= pw_data[31:0]; count_q <= pw_data[37:32];
                if (pw_data[63:48] != 16'h434c || pw_data[47:38] != 0 || pw_data[37:32] == 0 ||
                    pw_data[37:32] > DEPTH) cfg_fault <= 1'b1;
            end
            if (start && !sealed) cfg_fault <= 1'b1;
            // Check completeness without consulting uninitialized row contents.
            // A missing header cannot be diagnosed by reaching its issue cycle.
            if (seal_w || start) begin
                for (ck_row = 0; ck_row < DEPTH; ck_row = ck_row + 1)
                    if (ck_row < (seal_w ? pw_data[37:32] : count_q) &&
                        loaded[ck_row] !== 1'b1) cfg_fault <= 1'b1;
            end
        end
    // one-edge synchronous calendar store -> fixed-issue core
    wire slot_re; wire [11:0] slot_addr; reg [46:0] slot_q;
    wire [RAW-1:0] sa = slot_addr[RAW-1:0];
    always @(posedge clk) if (slot_re)
        slot_q <= (slot_addr < DEPTH && slot_addr < count_q)
                ? {endr[sa], endr[sa] ? 2'd0 : 2'd2, 12'(slot_addr), cyc[sa]}
                : {1'b1, 2'd3, 12'hfff, 32'hffffffff};             // beyond the sealed rows: refused (unit 3)
    wire issue_v, end_v, cp_v; wire [1:0] cp_index; wire [11:0] issue_pc; wire [1:0] issue_unit;
    wire [31:0] cycle; wire core_fault;
    wire [RAW-1:0] ip = issue_pc[RAW-1:0];
    ot_qwen_fixed_issue #(.ROW_AW(12), .OWN(2)) u_core (
        .clk(clk), .rst_n(rst_n), .start(start && sealed), .stop_cycle(stop_q),
        .slot_re(slot_re), .slot_addr(slot_addr), .slot_q(slot_q),
        .candidate_v(issue_pc < DEPTH && loaded[ip]), .candidate_pc(issue_pc), .candidate_unit(issue_unit),
        .available(cmd_free), .end_ok(cmd_free), .cp_available(1'b0),
        .issue_v(issue_v), .end_v(end_v), .cp_v(cp_v), .cp_index(cp_index), .issue_pc(issue_pc),
        .issue_unit(issue_unit), .active(active), .done(done), .cycle(cycle), .fault(core_fault));
    assign run       = active;
    assign image_ready = sealed && !cfg_fault;
    assign cmd_v     = issue_v;
    assign cmd_mode  = issue_v ? mde[ip] : 1'b0;
    assign cmd_words = issue_v ? wds[ip] : 16'd0;
    assign cmd_tag   = issue_v ? tg[ip] : {TAGW{1'b0}};
    assign fault     = core_fault | cfg_fault;
endmodule
