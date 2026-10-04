`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_window_la_stage: the packed WINDOW staging buffer of ot_dsrom_window_attn_source_la
// (claude/dsrom-s81-window-bind-20261004).  Successor of ot_chip_v41x_window_stage4 for the wide load:
// the same four-bank row organisation (absolute row 4q + b in bank b, slot q mod 32) and the same two-cycle,
// one-four-row-request-a-cycle read path into the attention row merge; but filled by up to NPC sectors a cycle
// (one response port per HBM pseudo-channel) instead of one.
//
// Landing.  Each bank is split into 17 sector columns (16 code sectors of 256 b, the scale sector's low
// 128 b), every column a 32-entry single-write-port array: 68 columns, each written at most once a cycle.
// A response beat (granule tag t, beat j -> window sector s = 4 t + j, slot = s / 17, column = s mod 17)
// is first registered in a one-entry per-pseudo-channel buffer together with its decoded slot / column.
// From the buffers, the lowest pseudo-channel targeting a column writes it; a beat that loses holds its
// buffer and back-pressures its pseudo-channel (in_rdy = buffer free or draining).  The accepted beats are
// also forwarded (acc_*) to ot_dsrom_window_stream_la, whose issue / completion accounting therefore sees
// exactly the beats that landed.  Every decision reads registers (the buffers), not the HBM response wires.
// A sector landed twice in one job, or a beat outside the 2,176-sector window, is a fault.
//
// Job.  `job_v` (one cycle, while not busy) opens a job: rows [first, first + count) of user `user`,
// count <= 128; all sector-landed bits clear.  Row R is readable when first <= R < first + count, its 17
// sectors have landed in this job, and the request names the job's user (the row-tag / user checks of the
// as-built prefetch are made once, at job start, by the source's tag mirror).  `all_rows` = every job row
// readable.  Bytes are moved, never transformed.
// ---------------------------------------------------------------------------
module ot_dsrom_window_la_stage #(
    parameter integer POS_W = 21,
    parameter integer USER_W = 10,
    parameter integer NPC = 32,
    parameter integer WTAGW = 13,
    parameter integer BEATW = 4,
    parameter integer MAX_CONTEXT = 1048576
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   job_v,
    input  wire [USER_W-1:0]      job_user,
    input  wire [POS_W-1:0]       job_first,
    input  wire [7:0]             job_count,
    output wire                   all_rows,
    output reg  [11:0]            sectors_landed,
    output reg                    fault,
    // HBM responses (client port of ot_dsrom_hbm_wmux)
    input  wire [NPC-1:0]         in_v,
    output wire [NPC-1:0]         in_rdy,
    input  wire [NPC*WTAGW-1:0]   in_tag,
    input  wire [NPC*BEATW-1:0]   in_beat,
    input  wire [NPC*256-1:0]     in_data,
    // accepted beats (to the stream engine's accounting)
    output wire [NPC-1:0]         acc_v,
    output wire [NPC*WTAGW-1:0]   acc_tag,
    output wire [NPC*BEATW-1:0]   acc_beat,
    output wire [NPC*256-1:0]     acc_data,
    // four-row read port (ot_chip_v41x_window_stage4 protocol)
    input  wire                   req_v,
    output wire                   req_ready,
    input  wire [USER_W-1:0]      req_user,
    input  wire [POS_W-1:0]       req_first_row,
    input  wire [3:0]             req_mask,
    output reg                    rsp_v,
    output reg  [USER_W-1:0]      rsp_user,
    output reg  [POS_W-1:0]       rsp_first_row,
    output reg  [3:0]             rsp_mask,
    output reg  [3:0]             rsp_valid_mask,
    output reg  [4*4224-1:0]      rsp_rows,
    output reg                    rsp_fault
);
    localparam integer ROWB = 4224, PITCH = 17, NSECT = 128 * PITCH;
    assign req_ready = 1'b1;
    // ---------------- job ----------------
    reg [USER_W-1:0] j_user;
    reg [POS_W-1:0]  j_first;
    reg [7:0]        j_count;
    reg [127:0]      in_job;                 // slot belongs to a job row
    reg [NSECT-1:0]  landed;                 // sector landed in this job
    wire [127:0]     slot_done;
    genvar s;
    generate for (s = 0; s < 128; s = s + 1) begin : g_slot
        assign slot_done[s] = &landed[s*PITCH +: PITCH];
    end endgenerate
    assign all_rows = &(slot_done | ~in_job);
    // ---------------- landing buffers ----------------
    reg  [NPC-1:0]       bf;                 // buffer full
    reg  [WTAGW-1:0]     b_tag  [0:NPC-1];
    reg  [BEATW-1:0]     b_beat [0:NPC-1];
    reg  [255:0]         b_data [0:NPC-1];
    reg  [11:0]          b_sec  [0:NPC-1];
    reg  [6:0]           b_slot [0:NPC-1];
    reg  [4:0]           b_col  [0:NPC-1];
    reg  [NPC-1:0]       b_bad;              // outside the window
    reg  [NPC-1:0]       acc;
    function automatic [11:0] sec_of(input [WTAGW-1:0] t, input [BEATW-1:0] j);
        sec_of = {t, 2'b00} + j;
    endfunction
    // slot = sec / 17 exactly for sec < 2,176: (sec * 3,856) >> 16
    function automatic [6:0] slot_of(input [11:0] x);
        reg [27:0] m;
        begin m = {16'd0, x} * 28'd3856; slot_of = m[22:16]; end
    endfunction
    // arbitration: lowest pseudo-channel wins a (bank, column)
    integer ap, aq;
    reg lose;
    always @* begin
        for (ap = 0; ap < NPC; ap = ap + 1) begin
            lose = 1'b0;
            for (aq = 0; aq < ap; aq = aq + 1)
                if (bf[aq] && !b_bad[aq] && b_slot[aq][1:0] == b_slot[ap][1:0] && b_col[aq] == b_col[ap]) lose = 1'b1;
            acc[ap] = bf[ap] && !b_bad[ap] && !lose;
        end
    end
    assign in_rdy = ~bf | acc;
    genvar g;
    generate for (g = 0; g < NPC; g = g + 1) begin : g_acc
        assign acc_v[g] = acc[g];
        assign acc_tag[g*WTAGW +: WTAGW] = b_tag[g];
        assign acc_beat[g*BEATW +: BEATW] = b_beat[g];
        assign acc_data[g*256 +: 256] = b_data[g];
    end endgenerate
    // ---------------- banks: 4 x 17 columns x 32 entries ----------------
    wire [ROWB-1:0] bank_q [0:3];
    reg  [3:0] bank_qv;
    reg  v1, bad1;
    reg  [USER_W-1:0] user1;
    reg  [POS_W-1:0] first1;
    reg  [3:0] mask1;
    wire prefix_mask = req_mask == 4'b0001 || req_mask == 4'b0011 ||
                       req_mask == 4'b0111 || req_mask == 4'b1111;
    generate for (genvar b = 0; b < 4; b = b + 1) begin : g_bank
        wire [1:0] lane = 2'(b) - req_first_row[1:0];
        wire [POS_W:0] wanted = {1'b0, req_first_row} + (POS_W+1)'(lane);
        wire [4:0] raddr = wanted[6:2];
        wire [POS_W:0] rel = wanted - {1'b0, j_first};
        wire ok = wanted < (POS_W+1)'(MAX_CONTEXT) && wanted >= {1'b0, j_first} &&
                  rel < (POS_W+1)'(j_count) && req_user == j_user && slot_done[wanted[6:0]];
        for (genvar k = 0; k < PITCH; k = k + 1) begin : g_col
            localparam integer CWID = (k < 16) ? 256 : 128;
            reg [CWID-1:0] mem [0:31];
            reg [CWID-1:0] q;
            // the column's writer: the accepted beat (at most one) targeting (b, k)
            reg we; reg [4:0] wa; reg [CWID-1:0] wd;
            always @* begin
                we = 1'b0; wa = '0; wd = '0;
                for (integer p = 0; p < NPC; p = p + 1)
                    if (acc[p] && b_slot[p][1:0] == 2'(b) && b_col[p] == 5'(k)) begin
                        we = 1'b1; wa = b_slot[p][6:2]; wd = b_data[p][CWID-1:0];
                    end
            end
            always @(posedge clk) begin
                if (we) mem[wa] <= wd;
                if (req_v) q <= mem[raddr];
            end
            if (k < 16) begin : g_c
                assign bank_q[b][256*k +: 256] = q;
            end else begin : g_s
                assign bank_q[b][4096 +: 128] = q;
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) bank_qv[b] <= 1'b0;
            else if (req_v) bank_qv[b] <= ok;
    end endgenerate
    // lanes (stage4's second register: bank order -> chronological lanes)
    wire [3:0] lane_ok;
    generate for (genvar l = 0; l < 4; l = l + 1) begin : g_lane
        wire [1:0] bank = first1[1:0] + 2'(l);
        assign lane_ok[l] = mask1[l] && bank_qv[bank];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rsp_rows[l*ROWB +: ROWB] <= '0; rsp_valid_mask[l] <= 1'b0; end
            else begin
                rsp_rows[l*ROWB +: ROWB] <= lane_ok[l] ? bank_q[bank] : '0;
                rsp_valid_mask[l] <= lane_ok[l];
            end
    end endgenerate
    // ---------------- control ----------------
    integer lp, jt;
    reg [11:0] nl, sc;
    reg [6:0] sl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            j_user <= 0; j_first <= 0; j_count <= 0; in_job <= 0; landed <= 0; sectors_landed <= 0; fault <= 0;
            bf <= 0; b_bad <= 0;
            v1 <= 0; bad1 <= 0; user1 <= 0; first1 <= 0; mask1 <= 0;
            rsp_v <= 0; rsp_user <= 0; rsp_first_row <= 0; rsp_mask <= 0; rsp_fault <= 0;
        end else begin
            nl = job_v ? 12'd0 : sectors_landed;
            if (job_v) begin
                j_user <= job_user; j_first <= job_first; j_count <= job_count; landed <= 0;
                for (jt = 0; jt < 128; jt = jt + 1)
                    in_job[job_first[6:0] + jt[6:0]] <= jt < job_count;
            end
            for (lp = 0; lp < NPC; lp = lp + 1) begin
                if (acc[lp]) begin
                    if (!job_v) begin
                        if (landed[b_sec[lp]]) fault <= 1'b1;
                        landed[b_sec[lp]] <= 1'b1;
                    end
                    nl = nl + 1'b1;
                end
                if (bf[lp] && b_bad[lp]) fault <= 1'b1;
                if (in_v[lp] && in_rdy[lp]) begin
                    sc = sec_of(in_tag[lp*WTAGW +: WTAGW], in_beat[lp*BEATW +: BEATW]);
                    sl = slot_of(sc);
                    bf[lp] <= 1'b1;
                    b_tag[lp] <= in_tag[lp*WTAGW +: WTAGW]; b_beat[lp] <= in_beat[lp*BEATW +: BEATW];
                    b_data[lp] <= in_data[lp*256 +: 256];
                    b_sec[lp] <= sc; b_slot[lp] <= sl; b_col[lp] <= sc - sl * 12'd17;
                    b_bad[lp] <= ({in_tag[lp*WTAGW +: WTAGW], 2'b00} + in_beat[lp*BEATW +: BEATW]) >= NSECT;
                end else if (acc[lp]) bf[lp] <= 1'b0;
            end
            sectors_landed <= nl;
            // read path (stage4)
            v1 <= req_v;
            if (req_v) begin
                user1 <= req_user; first1 <= req_first_row; mask1 <= req_mask;
                bad1 <= !prefix_mask ||
                    ({1'b0, req_first_row} + (POS_W+1)'(req_mask[3] ? 3 : req_mask[2] ? 2 : req_mask[1] ? 1 : 0)) >=
                    (POS_W+1)'(MAX_CONTEXT);
            end
            rsp_v <= v1; rsp_user <= user1; rsp_first_row <= first1; rsp_mask <= mask1;
            rsp_fault <= v1 && (bad1 || ((mask1 & ~lane_ok) != 0));
        end
    end
`ifndef SYNTHESIS
    initial if (POS_W < 21 || USER_W < 10 || MAX_CONTEXT != 1048576 || WTAGW < 10)
        $fatal(1, "ot_dsrom_window_la_stage parameter contract failed");
`endif
endmodule
