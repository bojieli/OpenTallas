`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81 SU act-quant function, rate-matched and split (el1011-s81su, 2026-10-12; PHYSICAL SPEC SU engines v3, QB first).
// Replaces the NQB = QB_NB / 8 QB lane tiles of ot_s81_su_tile (8 blocks each, ~200k flops on one root) by
//   one TAP sub-tile ot_s81_su_qbt at the down-spine stop and NPB = max(2, S_RD / 2) position-independent ENGINE
//   sub-tiles ot_s81_su_qbe (one ot_dsrom_actquant_f12 block each, its S0 -> E wait line in SRAM), hardened once.
// Rate match: the down spine brings S_RD rows a cycle; a QB beat is RPB = 2 QB_NB rows (32 blocks x 1,024 b), so
//   NPB physical blocks take the beat in NPS = QB_NB / NPB column passes (pass p = rows [p L, p L + L), L = 2 NPB),
//   one pass a cycle at most.  Blocks are independent (no cross-block step), so every value is that of the 32-block
//   bank; the VM rows are addressed exactly as the old tile TI = p wrote them (q rows, the exps row, y rows).
// TAP (v3b, <= 15k sinks): passes are aligned at the source (descriptor row alone, operand cycles S_RD-full from slot 0),
//   so with S_RD == L (full) spine slot j IS pass position j and a spine cycle is one pass: the tap is ONE data register
//   (8,192 b) + tags {beat, pass} + obase (~8.45k flops), no rotation, no hold; a mis-aligned arrival raises o_fo.  With
//   S_RD < L (reduced only) the pass spans L / S_RD cycles and the tap assembles it (rotation + hold, as 230a8ca0f).
//   Position 2b / 2b + 1 go to engine b over equal-depth relays (the slab), so every engine runs in lockstep.
// ENGINE b (b a registered config pin): pin flops; low half held until the high half of its pass arrives; the block;
//   writes per pass exactly two rows on its two write slots: its y row on slot 0 (at the block's output), and on slot
//   1 two cycles later the pair row it owns -- an even engine the q row {q_b+1, q_b}, an odd engine the masked exps
//   word {e_b, e_b-1}; the pair's q half / e cross between neighbours on registered pins (neighbour out reg -> pin
//   flop), the owner's own copy waits the same two cycles.  2 slots x NPB engines = S_WR: no staging, no TDM offset.
// Writes a beat: QB_NB / 2 q rows + QB_NB / 2 masked exps words + QB_NB y rows (hctl NQB = QB_NB / 2).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qbt #(
    parameter integer QB_NB = 32, S_RD = 16,
    parameter integer NPB = (S_RD / 2 > 2) ? S_RD / 2 : 2
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire                   dn_fp4_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    // to the engines: position j (row j of the current pass), its tag {beat[9:0], pass[1:0]}, the job's obase / FP4
    output reg  [2*NPB-1:0]       e_v,
    output reg  [2*NPB*512-1:0]   e_d,
    output reg  [2*NPB*12-1:0]    e_t,
    output reg  [13:0]            e_ob,
    output reg                    e_f4,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer L = 2 * NPB, NPS = QB_NB / NPB, RPB = 2 * QB_NB;
    localparam integer LL = $clog2(L), LR = $clog2(RPB);
    localparam [3:0] K_QB = 2;
`ifndef SYNTHESIS
    initial begin
        if ((1 << LL) != L || (1 << LR) != RPB) $fatal(1, "ot_s81_su_qbt: L and RPB powers of two");
        if (S_RD > L || NPS < 2 || NPS > 4 || QB_NB % NPB) $fatal(1, "ot_s81_su_qbt: S_RD <= L, 2 <= passes <= 4");
    end
`endif
    // regional reset relay
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // TAP RATE-ALIGNED (S_RD == L, the full configuration): the controller issues the descriptor row alone (slot 0 of
    // its own cycle) and then every operand cycle S_RD-full from slot 0 (ot_s81_su_hctl: ph 0 then ph 2, QB never
    // throttled, rows_in = c * RPB a multiple of S_RD), so operand row index = rcnt - 1 + s with rcnt - 1 = 0 mod L:
    // spine slot s IS pass position s and every spine cycle is exactly one pass.  No rotation, no hold: the data takes
    // a pin flop and an output flop (2 x 8,192 b); valid / tags / obase come from the pin flops of the control pins.
    // Any other arrival pattern (a partial operand cycle, a descriptor sharing its cycle) raises o_fo (fault 5).
    generate if (S_RD == L) begin : g_al
        // REGISTER AT THE PIN (owner 10-13, die timing by construction): every input pin feeds exactly one flop (q_*) and
        // nothing else; the tap logic starts from those flops.  The data therefore takes TWO registers (pin flop q_d,
        // output flop e_d) and the tap is one cycle deeper than the 10-12 version (which decided on the pins: 26
        // endpoints 4 levels behind dn_st / dn_v[0]).  The full-cycle / alignment check still runs one cycle later.
        reg q_st, q_fp4; reg [3:0] q_kind; reg [7:0] q_jid; reg [S_RD-1:0] q_v; reg [S_RD*512-1:0] q_d;
        always @(posedge clk) begin q_kind <= dn_kind_i; q_fp4 <= dn_fp4_i; q_jid <= dn_jid_i; q_d <= dn_d_i; end
        always @(posedge clk or negedge rst_n) if (!rst_n) begin q_st <= 1'b0; q_v <= 0; end
                                               else begin q_st <= dn_st_i; q_v <= dn_v_i; end
        reg mine, rnz; reg [7:0] jid; reg [15:0] rcnt, rinc;
        reg dq_m, dq_desc; reg [S_RD-1:0] dq_v;
        wire v0   = q_v[0] && !q_st;
        wire desc = mine && v0 && !rnz;                                     // the descriptor row
        wire opc  = mine && v0 && rnz;                                      // an operand cycle (one pass)
        wire [15:0] ix0 = rcnt - 16'd1;
        wire [15:0] pp  = (ix0 >> LL) % NPS;
        always @(posedge clk) begin : dreg
            integer j;
            e_d <= q_d;                                                    // the output register
            for (j = 0; j < L; j = j + 1) e_t[12 * j +: 12] <= {ix0[LR +: 10], pp[1:0]};
            if (desc) e_ob <= q_d[13:0];                                    // datapath: no reset
            if (q_st) e_f4 <= q_fp4;
        end
        always @(posedge clk or negedge rst_n) begin : creg
            integer j;
            if (!rst_n) begin
                mine <= 1'b0; rnz <= 1'b0; jid <= 8'd0; rcnt <= 16'd0; e_v <= 0; dq_m <= 1'b0; dq_desc <= 1'b0; rinc <= 16'd0;
                dq_v <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0;
            end else begin
                // rinc = rcnt + S_RD kept as state
                if (q_st) begin mine <= (q_kind == K_QB); jid <= q_jid; rcnt <= 16'd0; rnz <= 1'b0; end
                else if (desc) begin rcnt <= 16'd1; rinc <= 16'd1 + S_RD; rnz <= 1'b1; end
                else if (opc) begin rcnt <= rinc; rinc <= rinc + S_RD; end
                for (j = 0; j < L; j = j + 1) e_v[j] <= opc;
                dq_m <= mine && !q_st; dq_desc <= desc; dq_v <= q_v;
                o_fu <= 1'b0; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= jid;
                o_fo <= dq_m && (|dq_v) && (dq_desc ? (|dq_v[S_RD-1:1]) : !(&dq_v));   // not S_RD-full / aligned
            end
        end
    end else begin : g_asm
    // TAP ASSEMBLING (S_RD < L, the reduced configuration only: a pass spans L / S_RD spine cycles)
        // pin flops
        reg dq_st, dq_fp4; reg [3:0] dq_kind; reg [7:0] dq_jid; reg [S_RD-1:0] dq_v; reg [S_RD*512-1:0] dq_d;
        always @(posedge clk) begin dq_kind <= dn_kind_i; dq_fp4 <= dn_fp4_i; dq_jid <= dn_jid_i; dq_d <= dn_d_i; end
        always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; end
                                               else begin dq_st <= dn_st_i; dq_v <= dn_v_i; end
        // job context; row numbering: the first row of a QB job is its descriptor (obase), the rest operand rows
        reg mine, fp4; reg [7:0] jid; reg [13:0] ob; reg [15:0] rcnt;
        always @(posedge clk or negedge rst_n) begin : jb
            integer i; reg [15:0] c;
            if (!rst_n) begin mine <= 1'b0; fp4 <= 1'b0; jid <= 8'd0; rcnt <= 16'd0; end
            else if (dq_st) begin mine <= (dq_kind == K_QB); fp4 <= dq_fp4; jid <= dq_jid; rcnt <= 16'd0; end
            else begin
                c = rcnt;
                for (i = 0; i < S_RD; i = i + 1) if (dq_v[i]) c = c + 16'd1;
                rcnt <= c;
            end
        end
        wire          prm = mine && dq_v[0] && rcnt == 16'd0;              // the descriptor row (slot 0 of the first cycle)
        wire [13:0]   ob_n = prm ? dq_d[13:0] : ob;
        always @(posedge clk) ob <= ob_n;                                   // datapath: no reset
        // per slot: operand-row valid and tag; then a registered rotation by off = (rcnt - 1) mod L into positions
        reg  [L-1:0]      sv;
        reg  [L*512-1:0]  sd;
        reg  [L*12-1:0]   st;
        always @(*) begin : sl
            integer s; reg [15:0] ix, pp;
            sv = 0; sd = 0; st = 0;
            for (s = 0; s < S_RD; s = s + 1) begin
                ix = rcnt + s - 16'd1;
                sv[s] = mine && dq_v[s] && (rcnt != 16'd0 || s != 0);
                sd[512 * s +: 512] = dq_d[512 * s +: 512];
                pp = (ix >> LL) % NPS;
                st[12 * s +: 12] = {ix[LR +: 10], pp[1:0]};
            end
        end
        wire [LL-1:0] off = rcnt[LL-1:0] - 1'b1;
        // rotate left by off rows: position (s + off) mod L <- slot s (a log2(L)-level barrel, 1 row = 525 b)
        localparam integer RB = 512 + 12 + 1;
        reg [L*RB-1:0] rv [0:LL];
        always @(*) begin : rot
            integer s, k;
            for (s = 0; s < L; s = s + 1) rv[0][RB * s +: RB] = {sv[s], st[12 * s +: 12], sd[512 * s +: 512]};
            for (k = 0; k < LL; k = k + 1)
                for (s = 0; s < L; s = s + 1)
                    rv[k + 1][RB * s +: RB] = off[k] ? rv[k][RB * ((s - (1 << k) + L) % L) +: RB] : rv[k][RB * s +: RB];
        end
        // pass assembly: with off != 0 a pass's L rows straddle two spine cycles; the early rows wait in a hold register so
        // every position of a pass leaves in ONE cycle (the engines run in lockstep: the pair exchange and the write slots
        // depend on it). The pass completes when its last position (L - 1) arrives; rows of the next pass arriving in that
        // cycle are held.
        wire [L-1:0] iv;
        wire [L-1:0] same;
        wire [11:0]  tl = rv[LL][RB * (L - 1) + 512 +: 12];
        wire         done = iv[L - 1];
        genvar gj;
        for (gj = 0; gj < L; gj = gj + 1) begin : g_as
            assign iv[gj] = rv[LL][RB * gj + 524];
            assign same[gj] = iv[gj] && rv[LL][RB * gj + 512 +: 12] == tl;
        end
        reg [L-1:0] hv; reg [L*512-1:0] hd; reg [L*12-1:0] ht;
        always @(posedge clk) begin : oreg
            integer j;
            for (j = 0; j < L; j = j + 1) begin
                e_d[512 * j +: 512] <= same[j] ? rv[LL][RB * j +: 512] : hd[512 * j +: 512];
                e_t[12 * j +: 12] <= same[j] ? rv[LL][RB * j + 512 +: 12] : ht[12 * j +: 12];
                if (iv[j] && !(done && same[j])) begin hd[512 * j +: 512] <= rv[LL][RB * j +: 512];
                                                       ht[12 * j +: 12] <= rv[LL][RB * j + 512 +: 12]; end
            end
            e_ob <= ob_n; e_f4 <= fp4;
        end
        always @(posedge clk or negedge rst_n) begin : vreg
            integer j;
            if (!rst_n) begin e_v <= 0; hv <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; end
            else begin
                for (j = 0; j < L; j = j + 1) begin
                    e_v[j] <= done && (same[j] || hv[j]);
                    if (iv[j] && !(done && same[j])) hv[j] <= 1'b1;
                    else if (done) hv[j] <= 1'b0;
                end
                o_fu <= 1'b0; o_fo <= done && !(&(same | hv)); o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= jid;
            end
        end
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// TAP, SPLIT (el1013-s81su, 2026-10-13; structural change after the pin-registered single tap measured 16,510 sinks on
// one root, CTS insertion 774 ps / spread 130 ps: refused by the clock rule).  The rate-aligned tap (S_RD == 2 NPB, the
// full configuration) as TWO half-taps, each a kvt-shaped column (36.72 x 453.6) with its own clock root:
//   ot_s81_su_qbtl  slots 0 .. S_RD / 2 - 1 (slot 0 = the descriptor row) + the whole control (job, row counter, valid,
//                   tags, obase, FP4, status): 8,192 data flops + ~0.33k control;
//   the high half   slots S_RD / 2 .. S_RD - 1: a pure two-register data stage, which is exactly ot_s81_su_swth -- the
//                   SW high half-tap is instantiated (and hardened) once and used for both.
// Every input pin feeds exactly one flop and every output is a flop, as ot_s81_su_qbt's g_al branch, and the pair is
// that branch cycle for cycle (bench tb_s81_su_qbt_split: lockstep, no delay).  ot_s81_su_qbt stays as the assembling
// tap of the reduced shapes (S_RD < L) and as the lockstep reference.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qbtl #(
    parameter integer QB_NB = 32, S_RD = 16,
    parameter integer NPB = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer MUT = 0                      // bench negative control: 1 = the pass tag one pass early
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire                   dn_fp4_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*256-1:0]    dn_d_i,         // slots 0 .. S_RD / 2 - 1
    output reg  [2*NPB-1:0]       e_v,
    output reg  [S_RD*256-1:0]    e_d,            // pass positions 0 .. NPB - 1
    output reg  [2*NPB*12-1:0]    e_t,
    output reg  [13:0]            e_ob,
    output reg                    e_f4,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer L = 2 * NPB, NPS = QB_NB / NPB, RPB = 2 * QB_NB;
    localparam integer LL = $clog2(L), LR = $clog2(RPB);
    localparam [3:0] K_QB = 2;
`ifndef SYNTHESIS
    initial begin
        if ((1 << LL) != L || (1 << LR) != RPB) $fatal(1, "ot_s81_su_qbtl: L and RPB powers of two");
        if (S_RD != L || NPS < 2 || NPS > 4 || QB_NB % NPB) $fatal(1, "ot_s81_su_qbtl: S_RD == L (rate-aligned), 2 <= passes <= 4");
    end
`endif
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg q_st, q_fp4; reg [3:0] q_kind; reg [7:0] q_jid; reg [S_RD-1:0] q_v; reg [S_RD*256-1:0] q_d;
    always @(posedge clk) begin q_kind <= dn_kind_i; q_fp4 <= dn_fp4_i; q_jid <= dn_jid_i; q_d <= dn_d_i; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin q_st <= 1'b0; q_v <= 0; end
                                           else begin q_st <= dn_st_i; q_v <= dn_v_i; end
    reg mine, rnz; reg [7:0] jid; reg [15:0] rcnt, rinc;
    reg dq_m, dq_desc; reg [S_RD-1:0] dq_v;
    wire v0   = q_v[0] && !q_st;
    wire desc = mine && v0 && !rnz;                                     // the descriptor row
    wire opc  = mine && v0 && rnz;                                      // an operand cycle (one pass)
    wire [15:0] ix0 = rcnt - 16'd1;
    wire [15:0] pp  = (ix0 >> LL) % NPS;
    wire [1:0]  ppm = (MUT == 1) ? pp[1:0] + 2'd1 : pp[1:0];
    always @(posedge clk) begin : dreg
        integer j;
        e_d <= q_d;                                                    // the output register
        for (j = 0; j < L; j = j + 1) e_t[12 * j +: 12] <= {ix0[LR +: 10], ppm};
        if (desc) e_ob <= q_d[13:0];                                    // datapath: no reset
        if (q_st) e_f4 <= q_fp4;
    end
    always @(posedge clk or negedge rst_n) begin : creg
        integer j;
        if (!rst_n) begin
            mine <= 1'b0; rnz <= 1'b0; jid <= 8'd0; rcnt <= 16'd0; e_v <= 0; dq_m <= 1'b0; dq_desc <= 1'b0; rinc <= 16'd0;
            dq_v <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0;
        end else begin
            if (q_st) begin mine <= (q_kind == K_QB); jid <= q_jid; rcnt <= 16'd0; rnz <= 1'b0; end
            else if (desc) begin rcnt <= 16'd1; rinc <= 16'd1 + S_RD; rnz <= 1'b1; end
            else if (opc) begin rcnt <= rinc; rinc <= rinc + S_RD; end
            for (j = 0; j < L; j = j + 1) e_v[j] <= opc;
            dq_m <= mine && !q_st; dq_desc <= desc; dq_v <= q_v;
            o_fu <= 1'b0; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= jid;
            o_fo <= dq_m && (|dq_v) && (dq_desc ? (|dq_v[S_RD-1:1]) : !(&dq_v));   // not S_RD-full / aligned
        end
    end
endmodule

module ot_s81_su_qbe #(
    parameter integer QB_NB = 32, NPB = 8, MLAT = 5
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire [3:0]    cfg_b,          // block index within a pass (constant at the parent; bit 0 = pair role)
    input  wire          i_vlo, i_vhi,   // positions 2b / 2b + 1 of the tap
    input  wire [511:0]  i_lo, i_hi,
    input  wire [11:0]   i_tlo, i_thi,
    input  wire [13:0]   i_ob,
    input  wire          i_f4,
    input  wire          nx_i_v,         // the pair neighbour's q half / e (its registered nx_o_*)
    input  wire [255:0]  nx_i_q,
    input  wire [9:0]    nx_i_e,
    output reg           nx_o_v,
    output reg  [255:0]  nx_o_q,
    output reg  [9:0]    nx_o_e,
    output reg  [1:0]    o_v,
    output reg  [27:0]   o_a,
    output reg  [31:0]   o_m,
    output reg  [1023:0] o_d,
    output reg           o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]    o_rjid
);
    localparam integer LAT = 13 + MLAT;                    // ot_dsrom_actquant_f12: v -> vo
    localparam integer BW = QB_NB / 2 + 1 + QB_NB;         // VM rows a beat
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg vlo_q, vhi_q, nv_q;
    reg [511:0] lo_q, hi_q; reg [11:0] tlo_q, thi_q; reg [13:0] ob_q; reg f4_q; reg [255:0] nq_q; reg [9:0] ne_q;
    reg [3:0] cb_q;
    always @(posedge clk) begin
        lo_q <= i_lo; hi_q <= i_hi; tlo_q <= i_tlo; thi_q <= i_thi; ob_q <= i_ob; f4_q <= i_f4;
        nq_q <= nx_i_q; ne_q <= nx_i_e; cb_q <= cfg_b;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin vlo_q <= 1'b0; vhi_q <= 1'b0; nv_q <= 1'b0; end
                                           else begin vlo_q <= i_vlo; vhi_q <= i_vhi; nv_q <= nx_i_v; end
    // the low half waits for the high half of its pass (the next pass's low half may land in the same cycle)
    reg [511:0] lo_h;
    always @(posedge clk) if (vlo_q) lo_h <= lo_q;
    wire same = vlo_q && tlo_q[1:0] == thi_q[1:0];
    wire [1023:0] x = {hi_q, same ? lo_q : lo_h};
    wire vo, fault; wire [255:0] q; wire signed [9:0] e; wire [511:0] y;
    ot_dsrom_actquant_f12 #(.MLAT(MLAT), .XSRAM(1)) u_aq (.clk(clk), .rst_n(rst_n), .v(vhi_q), .fp4(f4_q), .x(x),
                                                         .vo(vo), .q(q), .e(e), .y(y), .fault(fault));
    // tag line {obase, beat, pass} aligned to vo: LAT - 2 delay, then the address rung (2 registered stages)
    wire [25:0] tg;
    ot_hdc_delay #(.W(26), .D(LAT - 2)) u_tg (.clk(clk), .rst_n(rst_n), .d({ob_q, thi_q}), .q(tg));
    reg [13:0] a_b; reg [1:0] a_p;
    reg [13:0] ay, aq, ae; reg [3:0] aw;
    always @(posedge clk) begin
        a_b <= tg[25:12] + tg[11:2] * BW; a_p <= tg[1:0];
        ay <= a_b + (QB_NB / 2 + 1) + a_p * NPB + cb_q;
        aq <= a_b + a_p * (NPB / 2) + (cb_q >> 1);
        ae <= a_b + QB_NB / 2;
        aw <= (a_p * NPB + cb_q) >> 1;
    end
`ifndef SYNTHESIS
    wire [LAT:0] vchk;
    ot_hdc_vline #(.D(LAT)) u_vc (.clk(clk), .rst_n(rst_n), .v(vhi_q), .vd(vchk));
    always @(posedge clk) if (rst_n && vo !== vchk[LAT]) $fatal(1, "ot_s81_su_qbe: block latency is not %0d", LAT);
`endif
    // the neighbour exchange and the owner's own copy, two cycles each
    reg d1v, d2v; reg [255:0] d1q, d2q; reg [9:0] d1e, d2e; reg [13:0] d1a, d2a, d1x, d2x; reg [3:0] d1w, d2w;
    always @(posedge clk) begin
        nx_o_q <= q; nx_o_e <= e;
        d1q <= q; d1e <= e; d1a <= aq; d1x <= ae; d1w <= aw;
        d2q <= d1q; d2e <= d1e; d2a <= d1a; d2x <= d1x; d2w <= d1w;
    end
    // write slots: 0 = the y row at vo; 1 = the pair row two cycles later
    always @(posedge clk) begin
        o_a[13:0] <= ay; o_m[15:0] <= 16'hFFFF; o_d[511:0] <= y;
        if (!cb_q[0]) begin
            o_a[27:14] <= d2a; o_m[31:16] <= 16'hFFFF; o_d[1023:512] <= {nq_q, d2q};
        end else begin
            o_a[27:14] <= d2x; o_m[31:16] <= 16'd1 << d2w; o_d[1023:512] <= {16{6'd0, d2e, 6'd0, ne_q}};
        end
    end
    reg fs;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            nx_o_v <= 0; d1v <= 0; d2v <= 0; o_v <= 0; fs <= 0;
            o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0;
        end else begin
            nx_o_v <= vo; d1v <= vo; d2v <= d1v; o_v <= {d2v, vo}; fs <= fs | fault;
            o_fu <= fs; o_fo <= o_fo | (d2v && !nv_q); o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= 8'd0;
        end
    end
endmodule
