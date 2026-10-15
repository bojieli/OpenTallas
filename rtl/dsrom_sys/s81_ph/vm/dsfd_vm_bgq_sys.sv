`ifdef OT_SPVM_RESET_ACK
`include "dsfd_vm_reset_ack.svh"
`endif
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_bgq (SYSTOLIC successor) -- redesign-ds 2026-10-09, OWNER rule "structural alternatives from established
// accelerators" (TPU systolic dataflow, Tensix/Cerebras abutted registered tiles).  Opt-in: this file is a separate
// top source for the closure loop; the default tile rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bg.sv is untouched.
//
// Why: every dsfd_vm_bgq / bgh / bg route died in global route (GRT markers pinned at the 20000 cap, best 1,184 after
// 20 extra iterations; vm_bg 17 h).  The tile carried FIVE vertical copies of the port traffic through a 253.8 um
// column whose M1-M4 are blocked by 8 stacked 174-um macros: the pin request bundle, NG = 4 kept stage-A copies of it
// (each 1,170 b, "<= 32 loads a bit"), a separate forward register bundle f_* (1,170 b), the upstream read chain
// r_* -> o_* (1,039 b), and a CENTRAL 32:1 read-select (8 ports x 128 b fed by 8 banks x 4 due slots = 4,096 b
// converging on one output stage).  ~13 k vertical nets against ~4.6 k usable vertical tracks.
//
// Structure (same ports, same pin plan contract_vmh, same banks / queues / macros / exact order):
//   * ONE request bus.  The pin register rb[0] is the only copy; it runs N -> S past every bank row (each bank taps
//     it), optionally re-registered every NBL/NSTG rows (rb[s]); its last register rb[NSTG] IS the forward output
//     f_* (no separate forward bundle).
//   * ONE read-return bus, flowing the SAME way: rt[s] <= rt[s-1] | (the due data of stage s's banks).  Its input is
//     the upstream tile's merged read data (pin register q_*), its last register drives o_* directly.  The central
//     32:1 mux becomes, per bank, a 4:1 select of its own due slots ANDed with "this port's due read is mine", ORed
//     into the passing bus (an AND-OR column, the TPU partial-sum pattern).
//   * Requests and read data move in lockstep (stage s sees a request s cycles after the pins, and its due data
//     joins the return bus exactly when that bus carries the same issue cycle), so the read latency stays FIXED and
//     every bank still sees every op in (issue cycle, port) order: the exact semantics are unchanged.
//   * Per-stage read history (h_v / h_b) and due-slot index (jc) are replicated in each stage (384 flops a stage)
//     instead of being broadcast from one place.
// Latency: request hop per tile NSTG + 1 (was 2); chain read latency (4 tiles) = 4*NSTG + QD + 8 cycles
// (NSTG 1: 16, NSTG 2: 20; dsfd_vm_bg chain: QD + 14 = 18).  Status (fault / code / max_occ): one registered merge.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_bgq #(
    parameter integer NP = 8,
    parameter integer NB = 32,
    parameter integer NBL = 8,
    parameter integer QD = 4,
    parameter integer RQ = 8,
    parameter integer MACRO = 1,
    parameter integer DW = 128,
    parameter integer NSTG = 1,        // register stages of the two buses inside the tile (1, 2, 4, 8; divides NBL)
    // s81-vm-1011 (opt-in): ports NPR .. NP-1 are WRITE-ONLY (the VM master's capture landing ports): no read history,
    // no read-return lane (r_* / o_* carry ports 0 .. NPR-1 only).  A read op on such a port is a schedule violation
    // -> sticky fault (code bit 0, with the queue faults).  Default NPR = NP: the closed tile, unchanged.
    parameter integer NPR = NP,
    // el1011-ds-vm/bgq28 (opt-in): ENQUEUE PIPELINE.  EP 0 = the closed single-cycle enqueue (default, unchanged).
    // EP >= 1: the per-bank NP-port enqueue (bank match -> port-order prefix count -> NP:1 slot select -> queue write,
    // ~2.1 ns placed at NP 28) is cut into registered rungs: E1 bank-match vector (per-bank replicated group id),
    // E2 prefix count -> one-hot slot selects + saturated count, E3 NP-input AND-OR slot data select fused with the
    // 4-slot queue write (EP 1) or registered first (EP 2).  Every op of every bank moves ED = EP + 1 cycles later,
    // and so does the read history (HL), so (issue cycle, port) order and the fixed read latency hold (+ED cycles).
    parameter integer EP = 0
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rs,
    input  wire [$clog2(NB/NBL)-1:0] grp,
    input  wire [NP-1:0]       i_v,
    input  wire [NP-1:0]       i_we,
    input  wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*(DW/32)-1:0] i_mask,
    input  wire [NP*DW-1:0]    i_d,
    output wire [NP-1:0]       f_v,
    output wire [NP-1:0]       f_we,
    output wire [NP*($clog2(NB)+9)-1:0] f_row,
    output wire [NP*(DW/32)-1:0] f_mask,
    output wire [NP*DW-1:0]    f_d,
    input  wire [NPR-1:0]       r_v,
    input  wire [NPR*DW-1:0]    r_d,
    input  wire [3:0]          r_f,
    input  wire [$clog2(QD):0] r_o,
    output wire [NPR-1:0]       o_v,
    output wire [NPR*DW-1:0]    o_d,
    output reg  [3:0]          o_f,
    output reg  [$clog2(QD):0] o_o
);
    localparam integer GW = $clog2(NB / NBL);
    localparam integer BB = $clog2(NB);
    localparam integer RA = BB + 9;
    localparam integer PW = (NP > 1) ? $clog2(NP) : 1;
    localparam integer QW = $clog2(QD);
    localparam integer RW = $clog2(RQ);
    localparam integer KQ = (NP < QD) ? NP : QD;
    localparam integer KW = (KQ > 1) ? $clog2(KQ) : 1;
    localparam integer LB = $clog2(NBL);
    localparam integer ED = (EP == 0) ? 0 : EP + 1; // enqueue pipeline cycles added
    localparam integer HL = QD + 4 + ED;           // = ot_s81ph_vm_mem L - 2 (+ ED)
    localparam integer MW = DW / 32, NC = DW / 128;
    localparam integer SR = NBL / NSTG;            // bank rows per bus stage
    localparam integer OW = $clog2(QD) + 1;
    localparam [NP-1:0] RMASK = {NP{1'b1}} >> (NP - NPR);   // read-capable ports
    wire clk = ck[0];

    // ------------------------------------------------------------------ reset: async assert, 2-flop release
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_i = rst_s[1];
    reg [GW-1:0] grp_q;
    always @(posedge clk) grp_q <= grp;

    // ------------------------------------------------------------------ request bus: rb[0] = pin register .. rb[NSTG] = f_*
    reg [NP-1:0]    rb_v  [0:NSTG];
    reg [NP-1:0]    rb_we [0:NSTG];
    reg [NP*RA-1:0] rb_row[0:NSTG];
    reg [NP*MW-1:0] rb_m  [0:NSTG];
    reg [NP*DW-1:0] rb_d  [0:NSTG];
    integer s;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) for (s = 0; s <= NSTG; s = s + 1) rb_v[s] <= {NP{1'b0}};
        else begin
            rb_v[0] <= i_v;
            for (s = 1; s <= NSTG; s = s + 1) rb_v[s] <= rb_v[s-1];
        end
    always @(posedge clk) begin : p_l102 integer s;
        rb_we[0] <= i_we; rb_row[0] <= i_row; rb_m[0] <= i_mask; rb_d[0] <= i_d;
        for (s = 1; s <= NSTG; s = s + 1) begin
            rb_we[s] <= rb_we[s-1]; rb_row[s] <= rb_row[s-1]; rb_m[s] <= rb_m[s-1]; rb_d[s] <= rb_d[s-1];
        end
    end
`ifdef OT_VM_SYS_MUT_SKEW
    // MUTANT: the forward output skips the last bus stage (the next tile sees its requests one cycle early)
    localparam integer FS = (NSTG > 0) ? NSTG - 1 : 0;
`else
    localparam integer FS = NSTG;
`endif
    wire wo_rd_any;                                          // a read on a write-only port (any stage sees it first at rb[0])
    assign wo_rd_any = |(rb_v[0] & ~rb_we[0] & ~RMASK);
    assign f_v = rb_v[FS]; assign f_we = rb_we[FS]; assign f_row = rb_row[FS]; assign f_mask = rb_m[FS]; assign f_d = rb_d[FS];

    // ------------------------------------------------------------------ read-return bus input: pin registers
    reg [NPR-1:0]    q_v;
    reg [NPR*DW-1:0] q_d;
    reg [3:0]       q_f;
    reg [OW-1:0]    q_o;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin q_v <= {NPR{1'b0}}; q_f <= 4'd0; q_o <= {OW{1'b0}}; end
        else begin q_v <= r_v; q_f <= r_f; q_o <= r_o; end
    always @(posedge clk) q_d <= r_d;

    // the return bus registers live in each stage block (g_s[s].rt_v / rt_d); the last stage drives the pins
    assign o_v = g_s[NSTG-1].rt_v;
    assign o_d = g_s[NSTG-1].rt_d;

    wire [NSTG-1:0] st_f;                 // per-stage sticky faults (ovf | und | port-id mismatch)
    wire [3*NSTG-1:0] st_c;
    wire [OW*NSTG-1:0] st_o;

    genvar gs, gb, gc;
    generate for (gs = 0; gs < NSTG; gs = gs + 1) begin : g_s
        // ---- this stage's view of the request bus
        wire [NP-1:0] a_v = rb_v[gs], a_we = rb_we[gs];
        wire [NP*RA-1:0] a_row = rb_row[gs];
        wire [NP*MW-1:0] a_m = rb_m[gs];
        wire [NP*DW-1:0] a_d = rb_d[gs];
        // ---- (EP >= 1) per-stage group-id copy (a register chain, so synthesis cannot merge the replicas back into
        // one high-fanout flop) and the request fields the E3 slot select reads, delayed 2 cycles (E1, E2)
        reg [GW-1:0] sg;
        if (gs == 0) begin : g_sg0
            always @(posedge clk) sg <= grp_q;
        end else begin : g_sgn
            always @(posedge clk) sg <= g_s[gs-1].sg;
        end
        wire [GW-1:0] grp_s = (EP == 0) ? grp_q : sg;
        reg [NP-1:0]    x1_we, x2_we;
        reg [NP*9-1:0]  x1_r, x2_r;
        reg [NP*MW-1:0] x1_m, x2_m;
        reg [NP*DW-1:0] x1_d, x2_d;
        if (EP > 0) begin : g_x
            integer xp;
            // x1 data fields load only on a valid port beat (clock-enabled, per port).  Besides the power saving this
            // keeps them STRUCTURALLY distinct from the next bus relay rb_*[gs+1] <= rb_*[gs]: as plain copies yosys
            // opt_merge folded them into the relays (keep does not stop it), so the bus relays / f_* output flops were
            // placed by the bank logic -- f_d 358 um from its S pin, zero-wire relay pairs (4a2c66fb7-pd35 hold class).
            // Consumers only read x1/x2 data of valid beats, so holding the old value on an idle port is exact.
            always @(posedge clk) begin
                x1_we <= a_we;
                for (xp = 0; xp < NP; xp = xp + 1) if (a_v[xp]) begin
                    x1_m[xp*MW +: MW] <= a_m[xp*MW +: MW]; x1_d[xp*DW +: DW] <= a_d[xp*DW +: DW];
                    x1_r[xp*9 +: 9] <= a_row[xp*RA + BB +: 9];
                end
                x2_we <= x1_we; x2_r <= x1_r; x2_m <= x1_m; x2_d <= x1_d;
            end
        end
        // ---- read history (per stage): (read issued, bank) per port; position HL-1 is due at the slot stage
        reg [NP-1:0] h_v [0:HL-1];
        reg [BB-1:0] h_b [0:HL-1][0:NP-1];
        integer hh, p, q, k;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) for (hh = 0; hh < HL; hh = hh + 1) h_v[hh] <= {NP{1'b0}};
            else begin
                h_v[0] <= a_v & ~a_we & RMASK;
                for (hh = 1; hh < HL; hh = hh + 1) h_v[hh] <= h_v[hh-1];
            end
        always @(posedge clk) begin
            for (p = 0; p < NP; p = p + 1) h_b[0][p] <= a_row[p*RA +: BB];
            for (hh = 1; hh < HL; hh = hh + 1) for (p = 0; p < NP; p = p + 1) h_b[hh][p] <= h_b[hh-1][p];
        end
        reg [NPR-1:0] d_v;
        reg [BB-1:0] d_b [0:NPR-1];
        reg [KW-1:0] d_j [0:NPR-1];
        reg [KW-1:0] jc [0:NPR-1];
        always @* begin
            for (p = 0; p < NPR; p = p + 1) begin
                jc[p] = {KW{1'b0}};
                for (q = 0; q < p; q = q + 1)
                    if (h_v[HL-1][q] && h_b[HL-1][q] == h_b[HL-1][p]) jc[p] = jc[p] + 1'b1;
            end
        end
        always @(posedge clk or negedge rst_i)
            if (!rst_i) d_v <= {NPR{1'b0}};
            else d_v <= h_v[HL-1][NPR-1:0];
        always @(posedge clk)
            for (p = 0; p < NPR; p = p + 1) begin
                d_b[p] <= h_b[HL-1][p];
`ifdef OT_S81PH_VM_MUT_J0
                d_j[p] <= {KW{1'b0}};                              // MUTANT: every port takes the first due slot
`else
                d_j[p] <= jc[p];
`endif
            end

        // ---- this stage's banks (local index gs*SR .. gs*SR + SR - 1)
        wire [SR-1:0] b_ovf, b_und;
        wire [QW:0]   b_occ [0:SR-1];
        wire [DW*KQ-1:0] b_ds [0:SR-1];
        wire [PW*KQ-1:0] b_dp [0:SR-1];
        for (gb = 0; gb < SR; gb = gb + 1) begin : g_bank
            localparam integer LBI = gs * SR + gb;              // local bank index in the tile
            wire [BB+GW:0] gidw = grp_s * NBL + LBI;
            wire [BB-1:0] gid = gidw[BB-1:0];
            // (EP >= 1) per-bank group-id replica (chain: bank gb copies bank gb-1, bank 0 copies the stage copy)
            reg [GW-1:0] gq;
            if (gb == 0) begin : g_gq0
                always @(posedge clk) gq <= sg;
            end else begin : g_gqn
                always @(posedge clk) gq <= g_bank[gb-1].gq;
            end
            wire [BB+GW:0] gqw = gq * NBL + LBI;
            wire [BB-1:0] gidq = gqw[BB-1:0];
            reg [NP-1:0] hit;
            reg [QW:0]   pref [0:NP-1];
            reg [QW+PW:0] cnt;
            integer pp;
            always @* begin
                cnt = 0;
                for (pp = 0; pp < NP; pp = pp + 1) hit[pp] = a_v[pp] && a_row[pp*RA +: BB] == gid;
`ifdef OT_S81PH_VM_MUT_ORDER
                for (pp = NP - 1; pp >= 0; pp = pp - 1) begin   // MUTANT: same-cycle ops queued in reverse port order
`else
                for (pp = 0; pp < NP; pp = pp + 1) begin
`endif
                    pref[pp] = cnt[QW:0];
                    if (hit[pp]) cnt = cnt + 1'b1;
                end
            end
            reg [QD-1:0] q_we;
            reg [PW-1:0] q_p [0:QD-1];
            reg [8:0]    q_r [0:QD-1];
            reg [MW-1:0] q_m [0:QD-1];
            reg [DW-1:0] q_dd [0:QD-1];
            reg [QW-1:0] qh, qt;
            reg [QW:0]   occ;
            reg          ovf;
            wire         serve = occ != 0;
            // the count the queue state applies this cycle: EP 0 = this cycle's, EP >= 1 = the pipelined e_cnt
            wire [QW+PW:0] cnt_a;
            wire [QW+PW+1:0] need = occ - serve + cnt_a;
            integer ps;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin qh <= 0; qt <= 0; occ <= 0; ovf <= 1'b0; end
                else begin
                    if (need > QD) begin
                        ovf <= 1'b1;
                        qt <= qt + (QD - (occ - serve));
                        occ <= QD;
                    end else begin
                        qt <= qt + cnt_a;
                        occ <= need;
                    end
                    if (serve) qh <= qh + 1'b1;
                end
            // (EP >= 1) queue-pointer replicas, one per 32-bit data word: each updates from its OWN state (so synthesis
            // cannot merge them) by the same rule as qt / qh, so they are equal to qt / qh every cycle; each drives
            // only its word's 4-slot write rotate / serve select (~32 x 4 loads instead of ~600 on one net)
            localparam integer NW = DW / 32;
            reg [QW-1:0] qtr [0:NW-1];
            reg [QW-1:0] qhr [0:NW-1];
            integer wr;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) for (wr = 0; wr < NW; wr = wr + 1) begin qtr[wr] <= 0; qhr[wr] <= 0; end
                else for (wr = 0; wr < NW; wr = wr + 1) begin
                    if (need > QD) qtr[wr] <= qtr[wr] + (QD - (occ - serve));
                    else qtr[wr] <= qtr[wr] + cnt_a;
                    if (serve) qhr[wr] <= qhr[wr] + 1'b1;
                end
            if (EP == 0) begin : g_e0
                assign cnt_a = cnt;
                always @(posedge clk)
                    for (ps = 0; ps < NP; ps = ps + 1)
                        if (hit[ps] && occ - serve + pref[ps] < QD) begin
                            q_we[(qt + pref[ps]) & (QD-1)] <= a_we[ps];
                            q_p [(qt + pref[ps]) & (QD-1)] <= ps;
                            q_r [(qt + pref[ps]) & (QD-1)] <= a_row[ps*RA + BB +: 9];
                            q_m [(qt + pref[ps]) & (QD-1)] <= a_m[ps*MW +: MW];
                            q_dd[(qt + pref[ps]) & (QD-1)] <= a_d[ps*DW +: DW];
                        end
            end else begin : g_ep
                // ---- E1: bank-match vector (registered; the group id is this bank's own replica)
                reg [NP-1:0] e_hit;
                integer i1;
                always @(posedge clk or negedge rst_i)
                    if (!rst_i) e_hit <= {NP{1'b0}};
                    else for (i1 = 0; i1 < NP; i1 = i1 + 1) e_hit[i1] <= a_v[i1] && a_row[i1*RA +: BB] == gidq;
                // ---- E2: port-order prefix count in 4 groups (local ripple <= 6 + group offsets), one-hot slot
                // selects e_sel[j][p] = "p is the j-th hit port" (j < QD), count saturated at QD + 1 (need > QD is
                // exact: with no overflow the count is <= QD)
                localparam integer NG = 4, GZ = (NP + NG - 1) / NG, CW = $clog2(NP + 1);
                reg [NP-1:0] ho;                         // hits in queue order (MUT_ORDER: reverse port order)
                reg [CW-1:0] lpre [0:NP-1];
                reg [CW-1:0] gt [0:NG-1];
                reg [CW-1:0] goff [0:NG-1];
                reg [CW-1:0] opre [0:NP-1];
                reg [CW-1:0] tot;
                reg [NP-1:0] sel_c [0:QD-1];
                integer g2, i2, j2;
                always @* begin
                    for (i2 = 0; i2 < NP; i2 = i2 + 1)
`ifdef OT_S81PH_VM_MUT_ORDER
                        ho[i2] = e_hit[NP-1-i2];                 // MUTANT: same-cycle ops queued in reverse port order
`else
                        ho[i2] = e_hit[i2];
`endif
                    for (g2 = 0; g2 < NG; g2 = g2 + 1) begin
                        gt[g2] = {CW{1'b0}};
                        for (i2 = g2 * GZ; i2 < (g2 + 1) * GZ && i2 < NP; i2 = i2 + 1) begin
                            lpre[i2] = gt[g2];
                            gt[g2] = gt[g2] + ho[i2];
                        end
                    end
                    goff[0] = {CW{1'b0}};
                    for (g2 = 1; g2 < NG; g2 = g2 + 1) goff[g2] = goff[g2-1] + gt[g2-1];
                    tot = goff[NG-1] + gt[NG-1];
                    for (i2 = 0; i2 < NP; i2 = i2 + 1) opre[i2] = goff[i2 / GZ] + lpre[i2];
                    for (j2 = 0; j2 < QD; j2 = j2 + 1)
                        for (i2 = 0; i2 < NP; i2 = i2 + 1)
`ifdef OT_S81PH_VM_MUT_ORDER
                            sel_c[j2][NP-1-i2] = ho[i2] && opre[i2] == j2;
`else
                            sel_c[j2][i2] = ho[i2] && opre[i2] == j2;
`endif
                end
                reg [NP-1:0] e_sel [0:QD-1];
                reg [QW+PW:0] e_cnt;
                integer j3;
                always @(posedge clk or negedge rst_i)
                    if (!rst_i) begin
                        e_cnt <= 0;
                        for (j3 = 0; j3 < QD; j3 = j3 + 1) e_sel[j3] <= {NP{1'b0}};
                    end else begin
                        e_cnt <= (tot > QD) ? QD + 1 : tot;
                        for (j3 = 0; j3 < QD; j3 = j3 + 1) e_sel[j3] <= sel_c[j3];
                    end
                // ---- E3: slot data select (NP-input AND-OR per slot; the selects are one-hot)
                reg [QD-1:0] w_v, w_we;
                reg [PW-1:0] w_p [0:QD-1];
                reg [8:0]    w_r [0:QD-1];
                reg [MW-1:0] w_m [0:QD-1];
                reg [DW-1:0] w_d [0:QD-1];
                integer j4, p4;
                always @* for (j4 = 0; j4 < QD; j4 = j4 + 1) begin
                    w_v[j4] = |e_sel[j4];
                    w_we[j4] = |(e_sel[j4] & x2_we);
                    w_p[j4] = {PW{1'b0}}; w_r[j4] = 9'd0; w_m[j4] = {MW{1'b0}}; w_d[j4] = {DW{1'b0}};
                    for (p4 = 0; p4 < NP; p4 = p4 + 1) begin
                        if (e_sel[j4][p4]) w_p[j4] = w_p[j4] | p4;   // one-hot: at most one port per slot
                        w_r[j4] = w_r[j4] | ({9{e_sel[j4][p4]}} & x2_r[p4*9 +: 9]);
                        w_m[j4] = w_m[j4] | ({MW{e_sel[j4][p4]}} & x2_m[p4*MW +: MW]);
                        w_d[j4] = w_d[j4] | ({DW{e_sel[j4][p4]}} & x2_d[p4*DW +: DW]);
                    end
                end
                // the slot words the queue write takes: EP 1 = w_* (fused), EP 2 = w_* registered (+1 cycle)
                wire [QD-1:0] k_v, k_we;
                wire [PW-1:0] k_p [0:QD-1];
                wire [8:0]    k_r [0:QD-1];
                wire [MW-1:0] k_m [0:QD-1];
                wire [DW-1:0] k_d [0:QD-1];
                if (EP == 1) begin : g_k1
                    assign k_v = w_v; assign k_we = w_we; assign cnt_a = e_cnt;
                    for (gc = 0; gc < QD; gc = gc + 1) begin : g_kw
                        assign k_p[gc] = w_p[gc]; assign k_r[gc] = w_r[gc]; assign k_m[gc] = w_m[gc]; assign k_d[gc] = w_d[gc];
                    end
                end else begin : g_k2
                    reg [QD-1:0] y_v, y_we;
                    reg [PW-1:0] y_p [0:QD-1];
                    reg [8:0]    y_r [0:QD-1];
                    reg [MW-1:0] y_m [0:QD-1];
                    reg [DW-1:0] y_d [0:QD-1];
                    reg [QW+PW:0] y_cnt;
                    integer j5;
                    always @(posedge clk or negedge rst_i)
                        if (!rst_i) begin y_v <= {QD{1'b0}}; y_cnt <= 0; end
                        else begin y_v <= w_v; y_cnt <= e_cnt; end
                    always @(posedge clk) begin
                        y_we <= w_we;
                        for (j5 = 0; j5 < QD; j5 = j5 + 1) begin
                            y_p[j5] <= w_p[j5]; y_r[j5] <= w_r[j5]; y_m[j5] <= w_m[j5]; y_d[j5] <= w_d[j5];
                        end
                    end
                    assign k_v = y_v; assign k_we = y_we; assign cnt_a = y_cnt;
                    for (gc = 0; gc < QD; gc = gc + 1) begin : g_kw
                        assign k_p[gc] = y_p[gc]; assign k_r[gc] = y_r[gc]; assign k_m[gc] = y_m[gc]; assign k_d[gc] = y_d[gc];
                    end
                end
                // ---- queue write: slot word j lands at (qt + j) if it fits (same rule as EP 0 with pref = j)
                integer j6, j7;
                always @(posedge clk)
                    for (j6 = 0; j6 < QD; j6 = j6 + 1)
                        if (k_v[j6] && occ - serve + j6 < QD) begin
                            q_we[(qt + j6) & (QD-1)] <= k_we[j6];
                            q_p [(qt + j6) & (QD-1)] <= k_p[j6];
                            q_r [(qt + j6) & (QD-1)] <= k_r[j6];
                            q_m [(qt + j6) & (QD-1)] <= k_m[j6];
                            for (j7 = 0; j7 < NW; j7 = j7 + 1)
                                q_dd[(qtr[j7] + j6) & (QD-1)][32*j7 +: 32] <= k_d[j6][32*j7 +: 32];
                        end
            end
            assign b_ovf[gb] = ovf;
            assign b_occ[gb] = occ;
            // serve register: drives the macro pins (no logic between flop and macro pin)
            reg          s_we, s_re;
            reg [PW-1:0] s_p;
            reg [8:0]    s_r;
            reg [DW-1:0] s_dd, s_bm;
            integer e;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin s_we <= 1'b0; s_re <= 1'b0; end
                else begin s_we <= serve & q_we[qh]; s_re <= serve & ~q_we[qh]; end
            always @(posedge clk) begin
                s_p <= q_p[qh]; s_r <= q_r[qh];
                if (EP == 0) s_dd <= q_dd[qh];
                else for (e = 0; e < NW; e = e + 1) s_dd[32*e +: 32] <= q_dd[qhr[e]][32*e +: 32];
                for (e = 0; e < MW; e = e + 1)
`ifdef OT_S81PH_VM_MUT_MASK
                    s_bm[32*e +: 32] <= {32{1'b1}};                    // MUTANT: element write mask ignored
`else
                    s_bm[32*e +: 32] <= {32{q_m[qh][e]}};
`endif
            end
            wire [DW-1:0] rd;
            for (gc = 0; gc < NC; gc = gc + 1) begin : g_m
                if (MACRO) begin : g_sram
                    (* keep = 1 *) ot_sram_1r1w_512x128_m4_r2c2 u_m (
                        .clk(clk), .r_ce_in(s_re), .r_addr_in(s_r), .rd_out(rd[128*gc +: 128]),
                        .w_ce_in(s_we), .w_addr_in(s_r), .wd_in(s_dd[128*gc +: 128]), .w_mask_in(s_bm[128*gc +: 128]),
                        .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(14'd0));
                end else begin : g_flop
                    reg [127:0] mem [0:511];
                    reg [127:0] r_q;
                    integer bi;
                    always @(posedge clk) begin
                        if (s_re) r_q <= mem[s_r];
                        if (s_we) for (bi = 0; bi < 128; bi = bi + 1)
                            if (s_bm[128*gc + bi]) mem[s_r][bi] <= s_dd[128*gc + bi];
                    end
                    assign rd[128*gc +: 128] = r_q;
                end
            end
            // read data capture (first flop after the macro) and return FIFO
            reg          m_v, r_vv;
            reg [PW-1:0] m_p, r_p;
            reg [DW-1:0] r_dd;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin m_v <= 1'b0; r_vv <= 1'b0; end
                else begin m_v <= s_re; r_vv <= m_v; end
            always @(posedge clk) begin m_p <= s_p; r_p <= m_p; r_dd <= rd; end
            reg [DW-1:0] f_dd [0:RQ-1];
            reg [PW-1:0] f_p [0:RQ-1];
            reg [RW-1:0] fh, ft;
            reg [RW-1:0] fhr [0:NW-1];                  // (EP >= 1) per-word replicas of fh (own-state update)
            integer wf, wf2;
            reg [RW:0]   fn;
            reg          und;
            reg [PW:0] dcnt;
            integer pd;
            always @* begin
                dcnt = 0;
                for (pd = 0; pd < NP; pd = pd + 1) if (h_v[HL-1][pd] && h_b[HL-1][pd] == ((EP == 0) ? gid : gidq)) dcnt = dcnt + 1'b1;
            end
            reg [DW-1:0] ds [0:KQ-1];
            reg [PW-1:0] dsp [0:KQ-1];
            integer kk;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin fh <= 0; ft <= 0; fn <= 0; und <= 1'b0; for (wf = 0; wf < NW; wf = wf + 1) fhr[wf] <= 0; end
                else begin
                    if (r_vv) ft <= ft + 1'b1;
                    fh <= fh + dcnt;
                    for (wf = 0; wf < NW; wf = wf + 1) fhr[wf] <= fhr[wf] + dcnt;
                    fn <= fn + r_vv - dcnt;
                    if (dcnt > fn) und <= 1'b1;
                end
            always @(posedge clk) begin
                if (r_vv) begin f_dd[ft] <= r_dd; f_p[ft] <= r_p; end
                for (kk = 0; kk < KQ; kk = kk + 1) begin
                    if (EP == 0) ds[kk] <= f_dd[(fh + kk) & (RQ-1)];
                    else for (wf2 = 0; wf2 < NW; wf2 = wf2 + 1)      // (EP >= 1) per-word read-pointer replica
                        ds[kk][32*wf2 +: 32] <= f_dd[(fhr[wf2] + kk) & (RQ-1)][32*wf2 +: 32];
                    dsp[kk] <= f_p[(fh + kk) & (RQ-1)];
                end
            end
            for (gc = 0; gc < KQ; gc = gc + 1) begin : g_ds
                assign b_ds[gb][DW*gc +: DW] = ds[gc];
                assign b_dp[gb][PW*gc +: PW] = dsp[gc];
            end
            assign b_und[gb] = und;
        end

        // ---- this stage's contribution to the return bus: per bank, AND-OR of its own due slots
        // own[p]: port p's due read is in this tile's group AND in this stage's rows
        reg [NPR-1:0] own;
        reg [LB-1:0] lb [0:NPR-1];
        always @* for (p = 0; p < NPR; p = p + 1) begin
            lb[p] = d_b[p][LB-1:0];
            own[p] = d_v[p] && (d_b[p] >> LB) == grp_s && (lb[p] / SR) == gs;
        end
        reg [NPR*DW-1:0] part;
        integer bb2;
        always @* begin
            part = {NPR*DW{1'b0}};
            for (p = 0; p < NPR; p = p + 1)
                for (bb2 = 0; bb2 < SR; bb2 = bb2 + 1)
                    if (own[p] && (lb[p] % SR) == bb2) part[p*DW +: DW] = part[p*DW +: DW] | b_ds[bb2][DW*d_j[p] +: DW];
        end
        wire [NPR-1:0]    in_v;
        wire [NPR*DW-1:0] in_d;
        if (gs == 0) begin : g_in0
            assign in_v = q_v | d_v;
            assign in_d = q_d;
        end else begin : g_inn
            assign in_v = g_s[gs-1].rt_v;
            assign in_d = g_s[gs-1].rt_d;
        end
        reg [NPR-1:0]    rt_v;
        reg [NPR*DW-1:0] rt_d;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) rt_v <= {NPR{1'b0}};
            else rt_v <= in_v;
        always @(posedge clk) rt_d <= in_d | part;
        // ---- stage status: sticky (queue overflow, return underflow, due-slot port-id mismatch)
        reg mis_r, stf;
        reg [2:0] stc;
        reg [OW-1:0] sto;
        integer bo;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin mis_r <= 1'b0; stf <= 1'b0; stc <= 3'd0; sto <= {OW{1'b0}}; end
            else begin
                for (p = 0; p < NPR; p = p + 1)
                    if (own[p] && b_dp[lb[p] % SR][PW*d_j[p] +: PW] != p) mis_r <= 1'b1;
                stc <= stc | {|b_und, mis_r, |b_ovf | (gs == 0 && wo_rd_any)};
                stf <= stf | |b_und | mis_r | |b_ovf | (gs == 0 && wo_rd_any);
                for (bo = 0; bo < SR; bo = bo + 1) if (b_occ[bo] > sto) sto <= b_occ[bo];
            end
        assign st_f[gs] = stf;
        assign st_c[3*gs +: 3] = stc;
        assign st_o[OW*gs +: OW] = sto;
    end endgenerate

    // ------------------------------------------------------------------ status merge (registered)
    reg [3:0] fm; reg [OW-1:0] om; integer t;
    always @* begin
        fm = q_f; om = q_o;
        for (t = 0; t < NSTG; t = t + 1) begin
            fm = fm | {st_f[t], st_c[3*t +: 3]};
            if (st_o[OW*t +: OW] > om) om = st_o[OW*t +: OW];
        end
    end
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin o_f <= 4'd0; o_o <= {OW{1'b0}}; end
        else begin o_f <= fm; o_o <= om; end
endmodule

// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_bgr (el1011-ds-vm/bgq28 v4, 2026-10-12): the dsfd_vm_bgq bank tile re-planned from its CUT ANALYSIS
// (log el1011-ds-vm.log 2026-10-12 "CUT ANALYSIS + PHYSICAL SPEC").  dsfd_vm_bgq EP 2 kept TWO vertical copies of the
// 28-port request bundle in the tile: the forward relay bus rb_* and, per bus stage, the x1 / x2 enqueue-alignment
// copies broadcast to the stage's 4 banks over ~250 um (4,144 + 3,976 + return 1,290 bits per horizontal cut = 0.79
// of the ~12.5k derated vertical tracks before any crossbar wiring; every 96996fa45 / 803dc8b3a route overflowed GRT,
// median usage 1.11).  Here there is ONE request bus and NO copies:
//   * CONTROL LEAD.  The bus is re-registered once per bank PAIR (NSTG stages of SR banks) and carries 2 extra lead
//     stages: rb[0] (pin flops) .. rb[NSTG+1] (= f_*).  Stage k's enqueue control (E1 bank match, E2 port-order prefix
//     -> one-hot slot selects) reads the bus at rb[k]; its E3 slot data select reads the SAME op 2 cycles later at
//     rb[k+2], where the bus itself has carried it (the bus moves one stage a cycle).  So the 2-cycle alignment that
//     x1 / x2 provided comes free from the bus; only the small selects (QD x NP + count a bank) travel 2 stages.
//   * READ HISTORY once.  Stage k's history is stage 0's delayed k cycles (its requests are), so the due vector at
//     the history tail is computed once (at rb[0]) and relayed one stage a cycle (hz[k]), instead of NSTG copies of
//     the HL-deep history.
//   * RETURN BUS per stage, in lockstep, plus one exit relay (the request hop is NSTG + 2 = one more than the return
//     bus's NSTG + 1 stages).  The tile's o_* -> f_* skew stays HL + 1, so the master's MD is unchanged.
// Every bank behaves exactly as a dsfd_vm_bgq EP >= 1 stage-gs bank with gs = k (same ED = EP + 1, same queue / serve /
// return FIFO / due-slot logic), so every bank sees every op in (issue cycle, port) order.  Tile hop: NSTG + 2 cycles
// (dsfd_vm_bgq: NSTG + 1).  Requires EP >= 1 (the lead is the E1 + E2 rungs).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_bgr #(
    parameter integer WCOMMIT = 0,
    parameter integer NP = 28,
    parameter integer NB = 32,
    parameter integer NBL = 8,
    parameter integer QD = 4,
    parameter integer RQ = 8,
    parameter integer MACRO = 1,
    parameter integer DW = 128,
    parameter integer NSTG = 4,        // bank stages (SR = NBL / NSTG banks each); bus relays rb[0 .. NSTG+1]
    parameter integer NPR = NP,
    parameter integer EP = 2           // 1: E3 fused with the queue write, 2: E3 registered (dsfd_vm_bgq EP)
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rs,
    input  wire [$clog2(NB/NBL)-1:0] grp,
    input wire [15:0] i_wtag, output wire [15:0] f_wtag,
    output wire [NBL*28-1:0] write_commit,
    input  wire [NP-1:0]       i_v,
    input  wire [NP-1:0]       i_we,
    input  wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*(DW/32)-1:0] i_mask,
    input  wire [NP*DW-1:0]    i_d,
    output wire [NP-1:0]       f_v,
    output wire [NP-1:0]       f_we,
    output wire [NP*($clog2(NB)+9)-1:0] f_row,
    output wire [NP*(DW/32)-1:0] f_mask,
    output wire [NP*DW-1:0]    f_d,
    input  wire [NPR-1:0]       r_v,
    input  wire [NPR*DW-1:0]    r_d,
    input  wire [3:0]          r_f,
    input  wire [$clog2(QD):0] r_o,
    output wire [NPR-1:0]       o_v,
    output wire [NPR*DW-1:0]    o_d,
    output reg  [3:0]          o_f,
    output reg  [$clog2(QD):0] o_o
`ifdef OT_SPVM_RESET_ACK
    ,output wire reset_ack
`endif
);
    localparam integer GW = $clog2(NB / NBL);
    localparam integer BB = $clog2(NB);
    localparam integer RA = BB + 9;
    localparam integer PW = (NP > 1) ? $clog2(NP) : 1;
    localparam integer QW = $clog2(QD);
    localparam integer RW = $clog2(RQ);
    localparam integer KQ = (NP < QD) ? NP : QD;
    localparam integer KW = (KQ > 1) ? $clog2(KQ) : 1;
    localparam integer LB = $clog2(NBL);
    localparam integer ED = EP + 1;
    localparam integer HL = QD + 4 + ED;
    localparam integer MW = DW / 32, NC = DW / 128, NW = DW / 32;
    localparam integer SR = NBL / NSTG;
    localparam integer OW = $clog2(QD) + 1;
    localparam integer NR = NSTG + 2;              // request relays rb[0 .. NR-1]; f_* = rb[NR-1]
    localparam [NP-1:0] RMASK = {NP{1'b1}} >> (NP - NPR);
    initial if (EP < 1 || EP > 2 || NBL % NSTG != 0) $error("dsfd_vm_bgr: EP 1 or 2, NSTG divides NBL");
    wire clk = ck[0];

    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_i = rst_s[1];
`ifdef OT_SPVM_RESET_ACK
    dsfd_vm_reset_ack u_ack (.clk(clk), .request_n(rs[0]), .local_release(rst_i), .consumer_live(rst_i), .ack(reset_ack));
`endif

    reg [GW-1:0] grp_q;
    always @(posedge clk) grp_q <= grp;

    // ------------------------------------------------------------------ the request bus (one copy)
    reg [NP-1:0]    rb_v  [0:NR-1];
    reg [NP-1:0]    rb_we [0:NR-1];
    reg [NP*RA-1:0] rb_row[0:NR-1];
    reg [NP*MW-1:0] rb_m  [0:NR-1];
    reg [15:0] rb_tag [0:NR-1];
    assign f_wtag=rb_tag[FS];
    reg [NP*DW-1:0] rb_d  [0:NR-1];
    integer s;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) for (s = 0; s < NR; s = s + 1) rb_v[s] <= {NP{1'b0}};
        else begin
            rb_v[0] <= i_v;
            for (s = 1; s < NR; s = s + 1) rb_v[s] <= rb_v[s-1];
        end
    always @(posedge clk) begin : p_rb integer s;
        rb_tag[0] <= WCOMMIT ? i_wtag : 16'd0;
        rb_we[0] <= i_we; rb_row[0] <= i_row; rb_m[0] <= i_mask; rb_d[0] <= i_d;
        for (s = 1; s < NR; s = s + 1) begin
            rb_tag[s] <= rb_tag[s-1];
            rb_we[s] <= rb_we[s-1]; rb_row[s] <= rb_row[s-1]; rb_m[s] <= rb_m[s-1]; rb_d[s] <= rb_d[s-1];
        end
    end
`ifdef OT_VM_SYS_MUT_SKEW
    localparam integer FS = NR - 2;                // MUTANT: the forward output skips the last relay
`else
    localparam integer FS = NR - 1;
`endif
    wire wo_rd_any = |(rb_v[0] & ~rb_we[0] & ~RMASK);
    assign f_v = rb_v[FS]; assign f_we = rb_we[FS]; assign f_row = rb_row[FS]; assign f_mask = rb_m[FS]; assign f_d = rb_d[FS];

    // ------------------------------------------------------------------ read history, ONCE (stage 0's view rb[0])
    reg [NP-1:0] h_v [0:HL-1];
    reg [BB-1:0] h_b [0:HL-1][0:NP-1];
    integer hh, hp;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) for (hh = 0; hh < HL; hh = hh + 1) h_v[hh] <= {NP{1'b0}};
        else begin
            h_v[0] <= rb_v[0] & ~rb_we[0] & RMASK;
            for (hh = 1; hh < HL; hh = hh + 1) h_v[hh] <= h_v[hh-1];
        end
    always @(posedge clk) begin
        for (hp = 0; hp < NP; hp = hp + 1) h_b[0][hp] <= rb_row[0][hp*RA +: BB];
        for (hh = 1; hh < HL; hh = hh + 1) for (hp = 0; hp < NP; hp = hp + 1) h_b[hh][hp] <= h_b[hh-1][hp];
    end

    // ------------------------------------------------------------------ read-return input pin registers
    reg [NPR-1:0]    q_v;
    reg [NPR*DW-1:0] q_d;
    reg [3:0]        q_f;
    reg [OW-1:0]     q_o;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin q_v <= {NPR{1'b0}}; q_f <= 4'd0; q_o <= {OW{1'b0}}; end
        else begin q_v <= r_v; q_f <= r_f; q_o <= r_o; end
    always @(posedge clk) q_d <= r_d;

    // return-bus exit relay (lockstep with the NSTG + 2 request hop)
    reg [NPR-1:0]    x_v;
    reg [NPR*DW-1:0] x_d;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) x_v <= {NPR{1'b0}};
        else x_v <= g_s[NSTG-1].rt_v;
    always @(posedge clk) x_d <= g_s[NSTG-1].rt_d;
    assign o_v = x_v;
    assign o_d = x_d;

    wire [NSTG-1:0] st_f;
    wire [3*NSTG-1:0] st_c;
    wire [OW*NSTG-1:0] st_o;

    genvar gs, gb, gc;
    generate for (gs = 0; gs < NSTG; gs = gs + 1) begin : g_s
        // ---- control view (E1 / E2 / history) and data view (E3: the same op 2 cycles later, 2 relays on)
        wire [NP-1:0] a_v = rb_v[gs];
        wire [NP*RA-1:0] a_row = rb_row[gs];
        wire [NP-1:0] z_we = rb_we[gs+2];
        wire [NP*RA-1:0] z_row = rb_row[gs+2];
        wire [NP*MW-1:0] z_m = rb_m[gs+2];
        wire [NP*DW-1:0] z_d = rb_d[gs+2];
        wire [15:0] z_tag=rb_tag[gs+2];
        // per-stage group-id copy (register chain)
        reg [GW-1:0] sg;
        if (gs == 0) begin : g_sg0
            always @(posedge clk) sg <= grp_q;
        end else begin : g_sgn
            always @(posedge clk) sg <= g_s[gs-1].sg;
        end
        // ---- the history tail of this stage: stage 0's, relayed gs cycles
        reg [NP-1:0] hz_v;
        reg [NP*BB-1:0] hz_b;               // flat (hierarchical refs across generate scopes)
        integer p, q;
        if (gs == 0) begin : g_hz0
            always @* begin
                hz_v = h_v[HL-1];
                for (p = 0; p < NP; p = p + 1) hz_b[p*BB +: BB] = h_b[HL-1][p];
            end
        end else begin : g_hzn
            always @(posedge clk or negedge rst_i)
                if (!rst_i) hz_v <= {NP{1'b0}};
                else hz_v <= g_s[gs-1].hz_v;
            always @(posedge clk) hz_b <= g_s[gs-1].hz_b;
        end
        reg [NPR-1:0] d_v;
        reg [BB-1:0] d_b [0:NPR-1];
        reg [KW-1:0] d_j [0:NPR-1];
        reg [KW-1:0] jc [0:NPR-1];
        always @* begin
            for (p = 0; p < NPR; p = p + 1) begin
                jc[p] = {KW{1'b0}};
                for (q = 0; q < p; q = q + 1)
                    if (hz_v[q] && hz_b[q*BB +: BB] == hz_b[p*BB +: BB]) jc[p] = jc[p] + 1'b1;
            end
        end
        always @(posedge clk or negedge rst_i)
            if (!rst_i) d_v <= {NPR{1'b0}};
            else d_v <= hz_v[NPR-1:0];
        always @(posedge clk)
            for (p = 0; p < NPR; p = p + 1) begin
                d_b[p] <= hz_b[p*BB +: BB];
`ifdef OT_S81PH_VM_MUT_J0
                d_j[p] <= {KW{1'b0}};
`else
                d_j[p] <= jc[p];
`endif
            end

        wire [SR-1:0] b_ovf, b_und;
        wire [QW:0]   b_occ [0:SR-1];
        wire [DW*KQ-1:0] b_ds [0:SR-1];
        wire [PW*KQ-1:0] b_dp [0:SR-1];
        for (gb = 0; gb < SR; gb = gb + 1) begin : g_bank
            localparam integer LBI = gs * SR + gb;
            reg [GW-1:0] gq;
            if (gb == 0) begin : g_gq0
                always @(posedge clk) gq <= sg;
            end else begin : g_gqn
                always @(posedge clk) gq <= g_bank[gb-1].gq;
            end
            wire [BB+GW:0] gqw = gq * NBL + LBI;
            wire [BB-1:0] gidq = gqw[BB-1:0];
            reg [QD-1:0] q_we;
            reg [7:0] q_tag [0:QD-1];
            reg [PW-1:0] q_p [0:QD-1];
            reg [8:0]    q_r [0:QD-1];
            reg [MW-1:0] q_m [0:QD-1];
            reg [DW-1:0] q_dd [0:QD-1];
            reg [QW-1:0] qh, qt;
            reg [QW:0]   occ;
            reg          ovf;
            wire         serve = occ != 0;
            wire [QW+PW:0] cnt_a;
            wire [QW+PW+1:0] need = occ - serve + cnt_a;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin qh <= 0; qt <= 0; occ <= 0; ovf <= 1'b0; end
                else begin
                    if (need > QD) begin
                        ovf <= 1'b1;
                        qt <= qt + (QD - (occ - serve));
                        occ <= QD;
                    end else begin
                        qt <= qt + cnt_a;
                        occ <= need;
                    end
                    if (serve) qh <= qh + 1'b1;
                end
            reg [QW-1:0] qtr [0:NW-1];
            reg [QW-1:0] qhr [0:NW-1];
            integer wr;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) for (wr = 0; wr < NW; wr = wr + 1) begin qtr[wr] <= 0; qhr[wr] <= 0; end
                else for (wr = 0; wr < NW; wr = wr + 1) begin
                    if (need > QD) qtr[wr] <= qtr[wr] + (QD - (occ - serve));
                    else qtr[wr] <= qtr[wr] + cnt_a;
                    if (serve) qhr[wr] <= qhr[wr] + 1'b1;
                end
            // ---- E1: bank-match vector on the control view
            reg [NP-1:0] e_hit;
            integer i1;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) e_hit <= {NP{1'b0}};
                else for (i1 = 0; i1 < NP; i1 = i1 + 1) e_hit[i1] <= a_v[i1] && a_row[i1*RA +: BB] == gidq;
            // ---- E2: port-order prefix count (4 groups), one-hot slot selects, saturated count
            localparam integer NG = 4, GZ = (NP + NG - 1) / NG, CW = $clog2(NP + 1);
            reg [NP-1:0] ho;
            reg [CW-1:0] lpre [0:NP-1];
            reg [CW-1:0] gt [0:NG-1];
            reg [CW-1:0] goff [0:NG-1];
            reg [CW-1:0] opre [0:NP-1];
            reg [CW-1:0] tot;
            reg [NP-1:0] sel_c [0:QD-1];
            integer g2, i2, j2;
            always @* begin
                for (i2 = 0; i2 < NP; i2 = i2 + 1)
`ifdef OT_S81PH_VM_MUT_ORDER
                    ho[i2] = e_hit[NP-1-i2];
`else
                    ho[i2] = e_hit[i2];
`endif
                for (g2 = 0; g2 < NG; g2 = g2 + 1) begin
                    gt[g2] = {CW{1'b0}};
                    for (i2 = g2 * GZ; i2 < (g2 + 1) * GZ && i2 < NP; i2 = i2 + 1) begin
                        lpre[i2] = gt[g2];
                        gt[g2] = gt[g2] + ho[i2];
                    end
                end
                goff[0] = {CW{1'b0}};
                for (g2 = 1; g2 < NG; g2 = g2 + 1) goff[g2] = goff[g2-1] + gt[g2-1];
                tot = goff[NG-1] + gt[NG-1];
                for (i2 = 0; i2 < NP; i2 = i2 + 1) opre[i2] = goff[i2 / GZ] + lpre[i2];
                for (j2 = 0; j2 < QD; j2 = j2 + 1)
                    for (i2 = 0; i2 < NP; i2 = i2 + 1)
`ifdef OT_S81PH_VM_MUT_ORDER
                        sel_c[j2][NP-1-i2] = ho[i2] && opre[i2] == j2;
`else
                        sel_c[j2][i2] = ho[i2] && opre[i2] == j2;
`endif
            end
            reg [NP-1:0] e_sel [0:QD-1];
            reg [QW+PW:0] e_cnt;
            integer j3;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin
                    e_cnt <= 0;
                    for (j3 = 0; j3 < QD; j3 = j3 + 1) e_sel[j3] <= {NP{1'b0}};
                end else begin
                    e_cnt <= (tot > QD) ? QD + 1 : tot;
                    for (j3 = 0; j3 < QD; j3 = j3 + 1) e_sel[j3] <= sel_c[j3];
                end
            // ---- E3: slot data select straight off the bus data view (one-hot NP-input AND-OR a slot)
            reg [QD-1:0] w_v, w_we;
            reg [PW-1:0] w_p [0:QD-1];
            reg [8:0]    w_r [0:QD-1];
            reg [MW-1:0] w_m [0:QD-1];
            reg [DW-1:0] w_d [0:QD-1];
            integer j4, p4;
            always @* for (j4 = 0; j4 < QD; j4 = j4 + 1) begin
                w_v[j4] = |e_sel[j4];
                w_we[j4] = |(e_sel[j4] & z_we);
                w_p[j4] = {PW{1'b0}}; w_r[j4] = 9'd0; w_m[j4] = {MW{1'b0}}; w_d[j4] = {DW{1'b0}};
                for (p4 = 0; p4 < NP; p4 = p4 + 1) begin
                    if (e_sel[j4][p4]) w_p[j4] = w_p[j4] | p4;
                    w_r[j4] = w_r[j4] | ({9{e_sel[j4][p4]}} & z_row[p4*RA + BB +: 9]);
                    w_m[j4] = w_m[j4] | ({MW{e_sel[j4][p4]}} & z_m[p4*MW +: MW]);
                    w_d[j4] = w_d[j4] | ({DW{e_sel[j4][p4]}} & z_d[p4*DW +: DW]);
                end
            end
            wire [7:0] k_tag[0:QD-1];
            wire [QD-1:0] k_v, k_we;
            wire [PW-1:0] k_p [0:QD-1];
            wire [8:0]    k_r [0:QD-1];
            wire [MW-1:0] k_m [0:QD-1];
            wire [DW-1:0] k_d [0:QD-1];
            if (EP == 1) begin : g_k1
                assign k_v = w_v; assign k_we = w_we; assign cnt_a = e_cnt;
                for (gc = 0; gc < QD; gc = gc + 1) begin : g_kw
                    assign k_tag[gc]=w_p[gc]==3 ? z_tag[7:0] : w_p[gc]==4 ? z_tag[15:8] : 8'd0;
                    assign k_p[gc] = w_p[gc]; assign k_r[gc] = w_r[gc]; assign k_m[gc] = w_m[gc]; assign k_d[gc] = w_d[gc];
                end
            end else begin : g_k2
                reg [7:0] y_tag[0:QD-1];
                reg [QD-1:0] y_v, y_we;
                reg [PW-1:0] y_p [0:QD-1];
                reg [8:0]    y_r [0:QD-1];
                reg [MW-1:0] y_m [0:QD-1];
                reg [DW-1:0] y_d [0:QD-1];
                reg [QW+PW:0] y_cnt;
                integer j5;
                always @(posedge clk or negedge rst_i)
                    if (!rst_i) begin y_v <= {QD{1'b0}}; y_cnt <= 0; end
                    else begin y_v <= w_v; y_cnt <= e_cnt; end
                always @(posedge clk) begin
                    y_we <= w_we;
                    for (j5 = 0; j5 < QD; j5 = j5 + 1) begin
                        y_tag[j5]<=w_p[j5]==3 ? z_tag[7:0] : w_p[j5]==4 ? z_tag[15:8] : 8'd0;
                        y_p[j5] <= w_p[j5]; y_r[j5] <= w_r[j5]; y_m[j5] <= w_m[j5]; y_d[j5] <= w_d[j5];
                    end
                end
                assign k_v = y_v; assign k_we = y_we; assign cnt_a = y_cnt;
                for (gc = 0; gc < QD; gc = gc + 1) begin : g_kw
                    assign k_tag[gc]=y_tag[gc];
                    assign k_p[gc] = y_p[gc]; assign k_r[gc] = y_r[gc]; assign k_m[gc] = y_m[gc]; assign k_d[gc] = y_d[gc];
                end
            end
            integer j6, j7;
            always @(posedge clk)
                for (j6 = 0; j6 < QD; j6 = j6 + 1)
                    if (k_v[j6] && occ - serve + j6 < QD) begin
                        q_tag[(qt + j6) & (QD-1)] <= k_tag[j6];
                        q_we[(qt + j6) & (QD-1)] <= k_we[j6];
                        q_p [(qt + j6) & (QD-1)] <= k_p[j6];
                        q_r [(qt + j6) & (QD-1)] <= k_r[j6];
                        q_m [(qt + j6) & (QD-1)] <= k_m[j6];
                        for (j7 = 0; j7 < NW; j7 = j7 + 1)
                            q_dd[(qtr[j7] + j6) & (QD-1)][32*j7 +: 32] <= k_d[j6][32*j7 +: 32];
                    end
            assign b_ovf[gb] = ovf;
            assign b_occ[gb] = occ;
            // serve register -> macro pins
            reg          s_we, s_re;
            reg [7:0] s_tag;
            reg [PW-1:0] s_p;
            reg [8:0]    s_r;
            reg [DW-1:0] s_dd, s_bm;
            integer e;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin s_we <= 1'b0; s_re <= 1'b0; end
                else begin s_we <= serve & q_we[qh]; s_re <= serve & ~q_we[qh]; end
            always @(posedge clk) begin
                s_tag<=q_tag[qh];
                s_p <= q_p[qh]; s_r <= q_r[qh];
                for (e = 0; e < NW; e = e + 1) s_dd[32*e +: 32] <= q_dd[qhr[e]][32*e +: 32];
                for (e = 0; e < MW; e = e + 1)
`ifdef OT_S81PH_VM_MUT_MASK
                    s_bm[32*e +: 32] <= {32{1'b1}};
`else
                    s_bm[32*e +: 32] <= {32{q_m[qh][e]}};
`endif
            end
            // Registered event samples the very edge that writes the actual SRAM.
            // No timing prediction or queue-admission token substitutes for this edge.
            reg [27:0] commit_q;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) commit_q<=0;
                else commit_q <= {WCOMMIT && s_we && (s_p==3 || s_p==4), s_p==4,
                                  s_bm[96],s_bm[64],s_bm[32],s_bm[0],s_r,gidq,s_tag};
            assign write_commit[28*LBI+:28]=commit_q;
            wire [DW-1:0] rd;
            for (gc = 0; gc < NC; gc = gc + 1) begin : g_m
                if (MACRO) begin : g_sram
                    (* keep = 1 *) ot_sram_1r1w_512x128_m4_r2c2 u_m (
                        .clk(clk), .r_ce_in(s_re), .r_addr_in(s_r), .rd_out(rd[128*gc +: 128]),
                        .w_ce_in(s_we), .w_addr_in(s_r), .wd_in(s_dd[128*gc +: 128]), .w_mask_in(s_bm[128*gc +: 128]),
                        .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(14'd0));
                end else begin : g_flop
                    reg [127:0] mem [0:511];
                    reg [127:0] r_q;
                    integer bi;
                    always @(posedge clk) begin
                        if (s_re) r_q <= mem[s_r];
                        if (s_we) for (bi = 0; bi < 128; bi = bi + 1)
                            if (s_bm[128*gc + bi]) mem[s_r][bi] <= s_dd[128*gc + bi];
                    end
                    assign rd[128*gc +: 128] = r_q;
                end
            end
            reg          m_v, r_vv;
            reg [PW-1:0] m_p, r_p;
            reg [DW-1:0] r_dd;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin m_v <= 1'b0; r_vv <= 1'b0; end
                else begin m_v <= s_re; r_vv <= m_v; end
            always @(posedge clk) begin m_p <= s_p; r_p <= m_p; r_dd <= rd; end
            reg [DW-1:0] f_dd [0:RQ-1];
            reg [PW-1:0] f_p [0:RQ-1];
            reg [RW-1:0] fh, ft;
            reg [RW-1:0] fhr [0:NW-1];
            integer wf, wf2;
            reg [RW:0]   fn;
            reg          und;
            reg [PW:0] dcnt;
            integer pd;
            always @* begin
                dcnt = 0;
                for (pd = 0; pd < NP; pd = pd + 1) if (hz_v[pd] && hz_b[pd*BB +: BB] == gidq) dcnt = dcnt + 1'b1;
            end
            reg [DW-1:0] ds [0:KQ-1];
            reg [PW-1:0] dsp [0:KQ-1];
            integer kk;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin fh <= 0; ft <= 0; fn <= 0; und <= 1'b0; for (wf = 0; wf < NW; wf = wf + 1) fhr[wf] <= 0; end
                else begin
                    if (r_vv) ft <= ft + 1'b1;
                    fh <= fh + dcnt;
                    for (wf = 0; wf < NW; wf = wf + 1) fhr[wf] <= fhr[wf] + dcnt;
                    fn <= fn + r_vv - dcnt;
                    if (dcnt > fn) und <= 1'b1;
                end
            always @(posedge clk) begin
                if (r_vv) begin f_dd[ft] <= r_dd; f_p[ft] <= r_p; end
                for (kk = 0; kk < KQ; kk = kk + 1) begin
                    for (wf2 = 0; wf2 < NW; wf2 = wf2 + 1)
                        ds[kk][32*wf2 +: 32] <= f_dd[(fhr[wf2] + kk) & (RQ-1)][32*wf2 +: 32];
                    dsp[kk] <= f_p[(fh + kk) & (RQ-1)];
                end
            end
            for (gc = 0; gc < KQ; gc = gc + 1) begin : g_ds
                assign b_ds[gb][DW*gc +: DW] = ds[gc];
                assign b_dp[gb][PW*gc +: PW] = dsp[gc];
            end
            assign b_und[gb] = und;
        end

        // ---- this stage's contribution to the return bus
        reg [NPR-1:0] own;
        reg [LB-1:0] lb [0:NPR-1];
        always @* for (p = 0; p < NPR; p = p + 1) begin
            lb[p] = d_b[p][LB-1:0];
            own[p] = d_v[p] && (d_b[p] >> LB) == sg && (lb[p] / SR) == gs;
        end
        reg [NPR*DW-1:0] part;
        integer bb2;
        always @* begin
            part = {NPR*DW{1'b0}};
            for (p = 0; p < NPR; p = p + 1)
                for (bb2 = 0; bb2 < SR; bb2 = bb2 + 1)
                    if (own[p] && (lb[p] % SR) == bb2) part[p*DW +: DW] = part[p*DW +: DW] | b_ds[bb2][DW*d_j[p] +: DW];
        end
        wire [NPR-1:0]    in_v;
        wire [NPR*DW-1:0] in_d;
        if (gs == 0) begin : g_in0
            assign in_v = q_v | d_v;
            assign in_d = q_d;
        end else begin : g_inn
            assign in_v = g_s[gs-1].rt_v;
            assign in_d = g_s[gs-1].rt_d;
        end
        reg [NPR-1:0]    rt_v;
        reg [NPR*DW-1:0] rt_d;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) rt_v <= {NPR{1'b0}};
            else rt_v <= in_v;
        always @(posedge clk) rt_d <= in_d | part;
        reg mis_r, stf;
        reg [2:0] stc;
        reg [OW-1:0] sto;
        integer bo;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin mis_r <= 1'b0; stf <= 1'b0; stc <= 3'd0; sto <= {OW{1'b0}}; end
            else begin
                for (p = 0; p < NPR; p = p + 1)
                    if (own[p] && b_dp[lb[p] % SR][PW*d_j[p] +: PW] != p) mis_r <= 1'b1;
                stc <= stc | {|b_und, mis_r, |b_ovf | (gs == 0 && wo_rd_any)};
                stf <= stf | |b_und | mis_r | |b_ovf | (gs == 0 && wo_rd_any);
                for (bo = 0; bo < SR; bo = bo + 1) if (b_occ[bo] > sto) sto <= b_occ[bo];
            end
        assign st_f[gs] = stf;
        assign st_c[3*gs +: 3] = stc;
        assign st_o[OW*gs +: OW] = sto;
    end endgenerate

    reg [3:0] fm; reg [OW-1:0] om; integer t;
    always @* begin
        fm = q_f; om = q_o;
        for (t = 0; t < NSTG; t = t + 1) begin
            fm = fm | {st_f[t], st_c[3*t +: 3]};
            if (st_o[OW*t +: OW] > om) om = st_o[OW*t +: OW];
        end
    end
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin o_f <= 4'd0; o_o <= {OW{1'b0}}; end
        else begin o_f <= fm; o_o <= om; end
endmodule

// dsfd_vm_mem_sys: NS bit-sliced chains of 4 systolic tiles (bench target; same ports as dsfd_vm_mem)
module dsfd_vm_mem_sys #(parameter integer NS = 4, parameter integer NP = 8, parameter integer NB = 32,
                         parameter integer QD = 4, parameter integer RQ = 8, parameter integer MACRO = 1,
                         parameter integer NSTG = 1) (
    input  wire clk, input wire rst_n,
    input  wire [NP-1:0] i_v, input wire [NP-1:0] i_we, input wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*16-1:0] i_mask, input wire [NP*512-1:0] i_d,
    output wire [NP-1:0] o_v, output wire [NP*512-1:0] o_d, output wire fault, output wire [2:0] fault_code,
    output wire [$clog2(QD):0] max_occ,
    output wire slice_mismatch
);
    localparam integer NT = 4, NBL = NB / NT, RA = $clog2(NB) + 9, OW = $clog2(QD) + 1, SW = 512 / NS, SM = 16 / NS;
    wire [NP-1:0] ovh [0:NS-1]; wire [3:0] ofh [0:NS-1]; wire [OW-1:0] ooh [0:NS-1]; wire [NP*SW-1:0] odh [0:NS-1];
    genvar h, t, pp;
    generate for (h = 0; h < NS; h = h + 1) begin : g_h
        wire [NP*SM-1:0] mk; wire [NP*SW-1:0] dh;
        for (pp = 0; pp < NP; pp = pp + 1) begin : g_p
            assign mk[SM*pp +: SM] = i_mask[16*pp + SM*h +: SM];
            assign dh[SW*pp +: SW] = i_d[512*pp + SW*h +: SW];
            assign o_d[512*pp + SW*h +: SW] = odh[h][SW*pp +: SW];
        end
        wire [NP-1:0] cv [0:NT], cwe [0:NT], ov [0:NT];
        wire [NP*RA-1:0] crow [0:NT]; wire [NP*SM-1:0] cmask [0:NT]; wire [NP*SW-1:0] cd [0:NT], od [0:NT];
        wire [3:0] of [0:NT]; wire [OW-1:0] oo [0:NT];
        assign cv[0] = i_v; assign cwe[0] = i_we; assign crow[0] = i_row; assign cmask[0] = mk; assign cd[0] = dh;
        assign ov[0] = 0; assign od[0] = 0; assign of[0] = 0; assign oo[0] = 0;
        for (t = 0; t < NT; t = t + 1) begin : g_t
            wire [$clog2(NT)-1:0] gid = t;
            dsfd_vm_bgq #(.NP(NP), .NB(NB), .NBL(NBL), .QD(QD), .RQ(RQ), .MACRO(MACRO), .DW(SW), .NSTG(NSTG)) u_bg (
                .ck(clk), .rs(rst_n), .grp(gid),
                .i_v(cv[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cmask[t]), .i_d(cd[t]),
                .f_v(cv[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cmask[t+1]), .f_d(cd[t+1]),
                .r_v(ov[t]), .r_d(od[t]), .r_f(of[t]), .r_o(oo[t]), .o_v(ov[t+1]), .o_d(od[t+1]), .o_f(of[t+1]), .o_o(oo[t+1]));
        end
        assign ovh[h] = ov[NT]; assign ofh[h] = of[NT]; assign ooh[h] = oo[NT]; assign odh[h] = od[NT];
    end endgenerate
    reg mism; reg [3:0] fo; integer k;
    always @* begin
        mism = 1'b0; fo = 4'd0;
        for (k = 0; k < NS; k = k + 1) begin
            fo = fo | ofh[k];
            if (ovh[k] != ovh[0] || ofh[k] != ofh[0] || ooh[k] != ooh[0]) mism = 1'b1;
        end
    end
    assign o_v = ovh[0]; assign fault = fo[3]; assign fault_code = fo[2:0]; assign max_occ = ooh[0];
    assign slice_mismatch = mism;
endmodule

// dsfd_vm_bgq28 (s81-vm-1011, 2026-10-11): the hard tile of the VM master dsfd_sp_vm v3 = dsfd_vm_bgq at NP 28 (ports
// 0 .. 9 read / write, 10 .. 27 write-only: 2 landing drains + 16 capture lanes: NPR 10), NSTG 2, DW 128 (one bit
// slice), 8 banks / 8 macros, 345.6 x 500.04 (contract_vm28: N / S pins on M5 + M7).  A separate master name so the closed
// NP 8 view (dsfd_vm_bgq, contract_vmh) stays valid.
module dsfd_vm_bgq28 (
    input  wire [0:0]        ck,
    input  wire [0:0]        rs,
    input  wire [1:0]        grp,
    input  wire [27:0]       i_v,
    input  wire [27:0]       i_we,
    input  wire [28*14-1:0]  i_row,
    input  wire [28*4-1:0]   i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0]       f_v,
    output wire [27:0]       f_we,
    output wire [28*14-1:0]  f_row,
    output wire [28*4-1:0]   f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0]        r_v,
    input  wire [10*128-1:0] r_d,
    input  wire [3:0]        r_f,
    input  wire [2:0]        r_o,
    output wire [9:0]        o_v,
    output wire [10*128-1:0] o_d,
    output wire [3:0]        o_f,
    output wire [2:0]        o_o
);
    // el1011-ds-vm/bgq28: EP 2 (enqueue pipeline, +3 cycles on every op; the master's MD follows).  OT_VM28_EP1 selects
    // the fused-select EP 1 (+2) for a route variant.
`ifdef OT_VM28_EP1
    localparam integer EP = 1;
`else
    localparam integer EP = 2;
`endif
    // v4 (2026-10-12, cut analysis): dsfd_vm_bgr -- one request bus with a 2-stage control lead, relays per bank pair
    // (NSTG 4), no enqueue-alignment copies; hop 6 cycles (was 3), o_* -> f_* skew (MD) unchanged.
    dsfd_vm_bgr #(.NP(28), .NPR(10), .NB(32), .NBL(8), .QD(4), .RQ(8), .MACRO(1), .DW(128), .NSTG(4), .EP(EP)) u (
        .ck(ck), .rs(rs), .grp(grp), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_mask), .i_d(i_d),
        .f_v(f_v), .f_we(f_we), .f_row(f_row), .f_mask(f_mask), .f_d(f_d), .r_v(r_v), .r_d(r_d), .r_f(r_f), .r_o(r_o),
        .o_v(o_v), .o_d(o_d), .o_f(o_f), .o_o(o_o));
endmodule
