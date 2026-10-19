`timescale 1ns/1ps
// =====================================================================================================================
// qfd_sys_face_mu_dhuser -- the user of every stage start on the compute die, WITHOUT touching the closed system face
// (MU-QWEN item R3, MU-ADOPT-SLICE 2026-10-19).  Supersedes, for adoption, the class-7 USER prefix event
// (qfd_sys_face_mu_user + adopt_sys_face.patch): that encoding has to change the closed qfd_sys_face (its T calendar
// and the class check t_bad live inside the face, so a class-7 T event faults there today).
//
// What it does: the face's T calendar is a static, periodic image, so the k-th stage start (seq_dh h_start) of every
// calendar period always belongs to the same user.  This leaf holds that compiled per-period list and names the user
// of each h_start on the same edge the h_start leaves the face:
//   dh_user = USER_SEQ[k] in the cycle seq_dh[42] (h_start) is high; it holds the last user between h_starts.
//   k counts the h_starts of the period, 0 .. NS-1, and wraps to 0 after NS-1 (NS = h_starts per period).
// The compiled list carries each entry's stage number too (STG_SEQ[k]); an h_start whose stage (seq_dh[41:36])
// differs from STG_SEQ[k] raises the sticky mu_fault: the two compiler images (the face's T calendar and this list)
// cannot drift apart unnoticed (the same rule as the face's own T-vs-D2D-sequencer check).  RES_SEQ[k] marks the
// h_start that carries the RESULT capture (STAGE arg[8]); res_user = that h_start's user, held.
// Static schedule: no handshake, no stall; it only observes seq_dh.  Zero added edges: dh_user is valid with the
// h_start it names (k is a register; the lookup is combinational from it).
// Placement: next to the consumer of seq_dh -- inside the qfd_tt_ctlm_dv cluster at its dh input (MU-ADOPT-CTLM, R1/R2),
// or at the die top beside qfd_sys_face; either way the closed qfd_sys_face view is untouched.
// seq_dh field map (qfd_sys_face.sv: seq_dh = {dh_prog, dh_run}; dh_run = {kv_write_drained, h_start, stage6,
// tp_token18, tp_pos18}): h_start = seq_dh[42], stage = seq_dh[41:36].
// NU = 1 (default): dh_user = res_user = 0, mu_fault = 0 (constants: today).
// MUT (bench only): 1 user of entry k+1 (off by one); 2 stage check dropped; 3 dh_user one edge late.
//
// OPSEG (MU-QW-B1 2026-10-19, coordinator B1 = option 2; opt-in, 0 = the leaf above, unchanged): the OP-START LEAF.  The
// face's T calendar carries the latency user's (user 0's) stage starts only; the fillers' op-granular segment starts
// come from this leaf: a ROM (ot_rom_4096x72_m8, image tools/qwen_static_schedule/mu_opcal.py rom_words / via_map) of
// compiled entries {t_rom, user, stage, first, cnt, FIRST}, played against a frame counter.  dh_user = res_user = 0
// (the face carries user 0 only).
//   ROM word 0 = header {magic 16'h4F50 [71:56], H 22 [55:34] (frame period, edges), nent 12 [33:22], T 22 [21:0]
//   (latency-user token period)}; word k = 1..nent = entry k, sorted by t_rom: {FIRST [71], 2'b0, cnt 10 [68:59],
//   first 10 [58:49], stage 6 [48:43], user 2 [42:41], t_rom 22 [40:19], 19'b0}.
//   Frame counter fc (period H) and token counter tc (period T): ANCHORED on the first h_start with stage 1 seen after
//   the header is good (calendar time 0 = the latency user's L0 start; the anchor edge has fc = tc = 0).
//   Entry fire: on the edge fc == t_rom the leaf consumes the entry and presents a REGISTERED op start (op_v + fields)
//   in the next cycle, i.e. qfd_dv_cmd_cal_mu starts the user's playhead on edge t_rom + 1 = S (the compiled start).
//   Prefetch: one entry register; the consuming edge issues the ROM read of the next entry (1-edge read), captured the
//   edge after: compiler rule t_rom gap >= 2 (mu_opcal.LEAF_MIN_GAP), the frame wrap included (after entry nent the
//   leaf reads entry 1 for the next frame).
//   FIRST: a filler's first entry of the frame (its first token's L0 start).  The entries of user u before its FIRST
//   entry are tails of tokens that began in the previous frame; in the first frame after the anchor they have no
//   beginning, so the leaf consumes them WITHOUT a start until it has seen u's FIRST entry (then every frame plays all).
//   Sticky faults (op_fcode, never a stall; mu_fault = |op_fcode):
//     [0] bad header (magic, H / T / nent zero, T > H, nent > 4095): the leaf never anchors;
//     [1] anchor drift: after the anchor every stage-1 h_start must land on tc == 0 (a multiple of T) and every tc == 0
//         edge must carry one (none missing); fc must wrap with tc;
//     [2] missed / late entry: an entry captured with t_rom <= fc (its edge passed) or an entry of the frame still
//         unconsumed when fc wraps;
//     [3] bad entry: user 0 or >= NU, stage > LAST_STAGE, cnt 0, first not 4-aligned, t_rom >= H, or t_rom not >= 2
//         after the previous entry.
//   MUT (bench only): 4 entry consumed one edge late (fc == t_rom + 1); 5 the counters re-anchor on EVERY stage-1 h_start
//   (fc restarts each latency token: anchor drift into the wrong frame entries); 6 drift / missing check dropped.
//
// PINREG (MU-LEAF-KIT 2026-10-19, opt-in, OPSEG only; 0 = unchanged): the hardened-leaf form, every used pin registered.
//   dh_run[42:36] (h_start, stage) land in a pin flop dh_q7, so the leaf sees each h_start one edge after the parent
//   launched it.  The counters compensate exactly: the anchor edge (one edge after calendar time 0) loads fc = tc = 1
//   and the drift check expects the (delayed) stage-1 h_start on tc == 1, so every entry still fires on calendar edge
//   t_rom and op_v / op_* are cycle-identical to PINREG 0 (lockstep bench tb_dhuser_pinreg.sv).  Compiler rule: t_rom
//   >= 1 (an entry on calendar edge 0 of the first frame is reported missed, op_fcode[2]); F16 minimum 1,721.
//   Faults: op_fcode[1] (drift, from dh_run) is raised one edge later than at PINREG 0; [0] / [2] / [3] on the same edge;
//   mu_fault becomes a flop (|op_fcode one edge later; sticky, observability only).  dh_user / res_user are constant 0.
//   dh_run[43] and [35:0] stay unused (the parent may leave them unconnected).
//   MUT 7 (bench only): PINREG without the anchor compensation (fc anchors at 0): every op start one edge late.
//   ROM capture register (MU-LEAF-KIT2 2026-10-19, PINREG 1 only): rd_out lands in rq (72 flops) before any decode, so
//   no path runs ROM rd_out -> header / entry decode -> registers or -> the ROM address (the gate's TT -134 ps).  Every
//   read is decoded one edge later: the header takes one more edge (hw), and the prefetch is a 2-stage pipe (rd_p: data
//   in the ROM, rd_p2: data in rq).  The fire edge (fc == t_rom) and the registered op start are UNCHANGED, so op_v /
//   op_* stay cycle-identical to PINREG 0; only the earliest next consume moves from e + 2 to e + 3.  Compiler rule:
//   consecutive t_rom (and the frame wrap) >= 3 (mu_opcal.LEAF_MIN_GAP 3; the F16 image's minimum gap is 7).  The bad-
//   entry check [3] tests gap >= 3 at PINREG 1.
// =====================================================================================================================
module qfd_sys_face_mu_dhuser #(
    parameter integer NU = 1,
    parameter integer NS = 1,                      // h_starts per T calendar period (1..64)
    parameter [64*2-1:0] USER_SEQ = '0,            // entry k = bits [2k+1:2k]: user of the k-th h_start of the period
    parameter [64*6-1:0] STG_SEQ = '0,             // entry k = bits [6k+5:6k]: its stage number (alignment check)
    parameter [63:0]     RES_SEQ = '0,             // bit k: the k-th h_start carries the RESULT capture
    parameter integer MUT = 0,
    parameter integer OPSEG = 0,                   // 1: the op-start leaf (NU 2..4), see the header
    parameter integer LAST_STAGE = 37,
    parameter         VIAMAP = "",                 // OPSEG: ot_rom_4096x72_m8 via-mask image ($readmemh)
    parameter         INSTANCE = "",               // OPSEG: ROM instance name (+OT_ROM_DIR=<dir>/<INSTANCE>.viamap.hex)
    parameter integer PINREG = 0                   // OPSEG: 1 = pin flop on dh_run[42:36], compensated (see the header)
) (
    input  wire        ck,
    input  wire        rst_n,
    input  wire [43:0] dh_run,                     // seq_dh[43:0] (the face's dh_run)
    output wire [1:0]  dh_user,                    // user of the h_start on this edge (holds between h_starts)
    output wire [1:0]  res_user,                   // user of the latest RESULT h_start (holds)
    output wire        mu_fault,                   // sticky: stage mismatch against the compiled list (OPSEG: |op_fcode)
    // ---------------- OPSEG op start (registered; all 0 at OPSEG 0)
    output reg         op_v,                       // a filler op start this cycle (qfd_dv_cmd_cal_mu start, explicit range)
    output reg  [1:0]  op_user,
    output reg  [5:0]  op_stage,
    output reg  [9:0]  op_first,                   // absolute entry index of the DV calendar image (4-aligned)
    output reg  [9:0]  op_cnt,
    output reg         op_ff,                      // the entry's FIRST flag (observability)
    output reg  [3:0]  op_fcode                    // sticky leaf faults (see the header)
);
    generate if (OPSEG != 0) begin : g_op
        // ------------------------------------------------------------ ROM + header / prefetch
        reg         rom_ce; reg [11:0] rom_a; wire [71:0] rom_q;
`ifdef SYNTHESIS
        // OpenROAD's netlist reader rejects instance parameters; the hard macro is content-independent
        ot_rom_4096x72_m8 u_rom (.clk(ck), .ce_in(rom_ce), .addr_in(rom_a), .rd_out(rom_q));
`else
        ot_rom_4096x72_m8 #(.VIAMAP(VIAMAP), .INSTANCE(INSTANCE)) u_rom (.clk(ck), .ce_in(rom_ce), .addr_in(rom_a),
            .rd_out(rom_q));
`endif
        localparam integer PR = (PINREG != 0) ? 1 : 0;
        localparam [21:0] A0 = (PINREG != 0 && MUT != 7) ? 22'd1 : 22'd0;   // counter value on the anchor edge
        reg  [6:0]  dh_q7;                         // PINREG: {h_start, stage} pin flop
        reg         mu_q;                          // PINREG: registered mu_fault
        reg  [71:0] rq;                            // PINREG: ROM rd_out capture register
        reg         hw;                            // PINREG: header in rq (decode edge)
        reg         rd_p2, rd_nf2;                 // PINREG: the read's data sits in rq (captured into nx this edge)
        reg  [1:0]  bst;                           // 0 read header, 1 header in flight, 2 running, 3 bad header (idle)
        reg  [21:0] hm1, tm1;                      // H - 1, T - 1
        reg  [11:0] nent, ptr;                     // ptr = index of the entry in flight / in the prefetch register
        reg         rd_p, rd_nf;                   // a read in flight (captured next edge); it is next frame's entry
        reg         nx_v, nx_nf, nx_f;
        reg  [21:0] nx_t, prev_t;
        reg  [1:0]  nx_u; reg [5:0] nx_s; reg [9:0] nx_first, nx_cnt;
        reg         anch;
        reg  [21:0] fc, tc;
        reg  [3:0]  seen;
        wire        hs = PR ? dh_q7[6] : dh_run[42];
        wire [5:0]  stg = PR ? dh_q7[5:0] : dh_run[41:36];
        wire        l0 = hs && stg == 6'd1;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) begin dh_q7 <= 7'd0; mu_q <= 1'b0; end
            else begin dh_q7 <= dh_run[42:36]; mu_q <= |op_fcode; end
        // decoded word: rd_out (PINREG 0) or its capture register (PINREG 1)
        wire [71:0] rw = PR ? rq : rom_q;
        wire        hdec = bst == 2'd1 && (!PR || hw);                    // the header is decoded on this edge
        wire        rd_c = PR ? rd_p2 : rd_p;                             // an entry is captured into nx on this edge
        wire        rd_cnf = PR ? rd_nf2 : rd_nf;
        wire [21:0] gapm = PR ? 22'd3 : 22'd2;                            // minimum t_rom spacing
        wire [15:0] h_magic = rw[71:56];
        wire [21:0] h_H = rw[55:34], h_T = rw[21:0];
        wire [11:0] h_n = rw[33:22];
        wire        h_good = h_magic == 16'h4F50 && h_H != 22'd0 && h_T != 22'd0 && h_T <= h_H && h_n != 12'd0 &&
                             h_n != 12'hFFF;
        wire        e_ff = rw[71]; wire [9:0] e_cnt = rw[68:59], e_first = rw[58:49];
        wire [5:0]  e_s = rw[48:43]; wire [1:0] e_u = rw[42:41]; wire [21:0] e_t = rw[40:19];
        wire        anchor_now = bst == 2'd2 && !anch && l0;
        wire        act = anch || anchor_now;
        wire [21:0] fc_now = anch ? fc : A0, tc_now = anch ? tc : A0;
        wire        wrap = act && fc_now == hm1;
        wire [21:0] t_hit = (MUT == 4) ? nx_t + 22'd1 : nx_t;
        wire        fire = act && nx_v && fc_now == t_hit;
        wire [11:0] nptr = (ptr == nent) ? 12'd1 : ptr + 12'd1;
        if (PINREG != 0) begin : g_rq
            always @(posedge ck) rq <= rom_q;                                 // data only: no reset needed
            always @(posedge ck or negedge rst_n)
                if (!rst_n) begin hw <= 1'b0; rd_p2 <= 1'b0; rd_nf2 <= 1'b0; end
                else begin hw <= bst == 2'd1 && !hw; rd_p2 <= rd_p; rd_nf2 <= rd_nf && !wrap; end
        end else begin : g_norq
            always @* begin rq = 72'd0; hw = 1'b0; rd_p2 = 1'b0; rd_nf2 = 1'b0; end
        end
        always @* begin
            rom_ce = 1'b0; rom_a = 12'd0;
            if (bst == 2'd0) rom_ce = 1'b1;                                   // header
            else if (hdec && h_good) begin rom_ce = 1'b1; rom_a = 12'd1; end          // entry 1
            else if (fire) begin rom_ce = 1'b1; rom_a = nptr; end
        end
        always @(posedge ck or negedge rst_n)
            if (!rst_n) begin
                bst <= 2'd0; hm1 <= 22'd0; tm1 <= 22'd0; nent <= 12'd0; ptr <= 12'd0; rd_p <= 1'b0; rd_nf <= 1'b0;
                nx_v <= 1'b0; nx_nf <= 1'b0; nx_f <= 1'b0; nx_t <= 22'd0; prev_t <= 22'd0; nx_u <= 2'd0; nx_s <= 6'd0;
                nx_first <= 10'd0; nx_cnt <= 10'd0; anch <= 1'b0; fc <= 22'd0; tc <= 22'd0; seen <= 4'd0;
                op_v <= 1'b0; op_user <= 2'd0; op_stage <= 6'd0; op_first <= 10'd0; op_cnt <= 10'd0; op_ff <= 1'b0;
                op_fcode <= 4'd0;
            end else begin
                op_v <= 1'b0;
                // ---------------- header
                if (bst == 2'd0) bst <= 2'd1;
                else if (hdec) begin
                    if (h_good) begin
                        bst <= 2'd2; hm1 <= h_H - 22'd1; tm1 <= h_T - 22'd1; nent <= h_n; ptr <= 12'd1;
                        rd_p <= 1'b1; rd_nf <= 1'b0;
                    end else begin bst <= 2'd3; op_fcode[0] <= 1'b1; end
                end
                // ---------------- frame / token counters (anchored on the latency user's L0 start)
                if (act) begin
                    anch <= 1'b1;
                    fc <= wrap ? 22'd0 : fc_now + 22'd1;
                    tc <= (tc_now == tm1) ? 22'd0 : tc_now + 22'd1;
                    if (MUT == 5 && l0) begin fc <= A0 + 22'd1; tc <= A0 + 22'd1; end
                    if (MUT != 6) begin
                        if (l0 != (tc_now == A0)) op_fcode[1] <= 1'b1;               // drift / missing L0 start
                        if (wrap && tc_now != tm1) op_fcode[1] <= 1'b1;               // H not a multiple of T
                    end
                end
                // ---------------- prefetch capture
                if (rd_p) rd_p <= 1'b0;
                if (rd_c) begin
                    nx_v <= 1'b1; nx_nf <= rd_cnf && !wrap; nx_f <= e_ff; nx_t <= e_t; nx_u <= e_u; nx_s <= e_s;
                    nx_first <= e_first; nx_cnt <= e_cnt; prev_t <= e_t;
                    if (e_u == 2'd0 || {1'b0, e_u} >= 3'(NU) || e_s > LAST_STAGE[5:0] || e_cnt == 10'd0 ||
                        e_first[1:0] != 2'd0 || e_t > hm1 || (ptr != 12'd1 && e_t < prev_t + gapm))
                        op_fcode[3] <= 1'b1;
                    if (act && !rd_cnf && e_t <= fc_now) op_fcode[2] <= 1'b1;         // its edge has passed
                end
                // ---------------- consume (fire) + next read
                if (fire) begin
                    nx_v <= 1'b0;
                    ptr <= nptr; rd_p <= 1'b1; rd_nf <= (ptr == nent) && !wrap;
                    if (nx_f || seen[nx_u]) begin
                        op_v <= 1'b1; op_user <= nx_u; op_stage <= nx_s; op_first <= nx_first; op_cnt <= nx_cnt;
                        op_ff <= nx_f;
                    end
                    if (nx_f) seen[nx_u] <= 1'b1;
                end
                // ---------------- frame wrap: every entry of the frame consumed; next frame's entries become current
                if (wrap) begin
                    if ((nx_v && !nx_nf && !fire) || (rd_p && !rd_nf) || (rd_p2 && !rd_nf2)) op_fcode[2] <= 1'b1;
                    if (!rd_c) nx_nf <= 1'b0;
                    if (!fire) rd_nf <= 1'b0;
                end
            end
        assign dh_user = 2'd0;
        assign res_user = 2'd0;
        assign mu_fault = PR ? mu_q : |op_fcode;
    end else if (NU == 1) begin : g_one
        assign dh_user = 2'd0;
        assign res_user = 2'd0;
        assign mu_fault = 1'b0;
    end else begin : g_mu
        wire       hs = dh_run[42];
        wire [5:0] stg = dh_run[41:36];
        reg  [5:0] k;
        reg  [1:0] hold_u, res_q, late_u;
        reg        fault_q;
        wire [5:0] kk = (MUT == 1) ? ((k == 6'(NS - 1)) ? 6'd0 : k + 6'd1) : k;
        wire [1:0] u_k = USER_SEQ[2*kk +: 2];
        wire [5:0] s_k = STG_SEQ[6*k +: 6];
        always @(posedge ck or negedge rst_n)
            if (!rst_n) begin k <= 6'd0; hold_u <= 2'd0; res_q <= 2'd0; late_u <= 2'd0; fault_q <= 1'b0; end
            else begin
                late_u <= hs ? u_k : hold_u;
                if (hs) begin
                    k <= (k == 6'(NS - 1)) ? 6'd0 : k + 6'd1;
                    hold_u <= u_k;
                    if (RES_SEQ[k]) res_q <= u_k;
                    if (stg != s_k && MUT != 2) fault_q <= 1'b1;
                end
            end
        assign dh_user = (MUT == 3) ? late_u : hs ? u_k : hold_u;
        assign res_user = res_q;
        assign mu_fault = fault_q;
    end endgenerate
    generate if (OPSEG == 0) begin : g_no_op
        always @* begin op_v = 1'b0; op_user = 2'd0; op_stage = 6'd0; op_first = 10'd0; op_cnt = 10'd0; op_ff = 1'b0;
                        op_fcode = 4'd0; end
    end endgenerate
    integer q;
    initial begin
        if (NU < 1 || NU > 4) $fatal(1, "qfd_sys_face_mu_dhuser: NU %0d outside 1..4", NU);
        if (NS < 1 || NS > 64) $fatal(1, "qfd_sys_face_mu_dhuser: NS %0d outside 1..64", NS);
        if (MUT < 0 || MUT > 7) $fatal(1, "qfd_sys_face_mu_dhuser: MUT %0d undefined", MUT);
        if (PINREG != 0 && OPSEG == 0) $fatal(1, "qfd_sys_face_mu_dhuser: PINREG needs OPSEG 1");
        if (OPSEG != 0 && (NU < 2 || NU > 4)) $fatal(1, "qfd_sys_face_mu_dhuser: OPSEG needs NU 2..4");
        for (q = 0; q < NS; q = q + 1)
            if (NU > 1 && USER_SEQ[2*q +: 2] >= NU) $fatal(1, "qfd_sys_face_mu_dhuser: entry %0d user >= NU", q);
    end
endmodule
