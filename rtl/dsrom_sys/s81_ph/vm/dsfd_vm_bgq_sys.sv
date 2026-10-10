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
    parameter integer NSTG = 1         // register stages of the two buses inside the tile (1, 2, 4, 8; divides NBL)
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
    input  wire [NP-1:0]       r_v,
    input  wire [NP*DW-1:0]    r_d,
    input  wire [3:0]          r_f,
    input  wire [$clog2(QD):0] r_o,
    output wire [NP-1:0]       o_v,
    output wire [NP*DW-1:0]    o_d,
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
    localparam integer HL = QD + 4;                // = ot_s81ph_vm_mem L - 2
    localparam integer MW = DW / 32, NC = DW / 128;
    localparam integer SR = NBL / NSTG;            // bank rows per bus stage
    localparam integer OW = $clog2(QD) + 1;
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
    always @(posedge clk) begin
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
    assign f_v = rb_v[FS]; assign f_we = rb_we[FS]; assign f_row = rb_row[FS]; assign f_mask = rb_m[FS]; assign f_d = rb_d[FS];

    // ------------------------------------------------------------------ read-return bus input: pin registers
    reg [NP-1:0]    q_v;
    reg [NP*DW-1:0] q_d;
    reg [3:0]       q_f;
    reg [OW-1:0]    q_o;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin q_v <= {NP{1'b0}}; q_f <= 4'd0; q_o <= {OW{1'b0}}; end
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
        // ---- read history (per stage): (read issued, bank) per port; position HL-1 is due at the slot stage
        reg [NP-1:0] h_v [0:HL-1];
        reg [BB-1:0] h_b [0:HL-1][0:NP-1];
        integer hh, p, q, k;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) for (hh = 0; hh < HL; hh = hh + 1) h_v[hh] <= {NP{1'b0}};
            else begin
                h_v[0] <= a_v & ~a_we;
                for (hh = 1; hh < HL; hh = hh + 1) h_v[hh] <= h_v[hh-1];
            end
        always @(posedge clk) begin
            for (p = 0; p < NP; p = p + 1) h_b[0][p] <= a_row[p*RA +: BB];
            for (hh = 1; hh < HL; hh = hh + 1) for (p = 0; p < NP; p = p + 1) h_b[hh][p] <= h_b[hh-1][p];
        end
        reg [NP-1:0] d_v;
        reg [BB-1:0] d_b [0:NP-1];
        reg [KW-1:0] d_j [0:NP-1];
        reg [KW-1:0] jc [0:NP-1];
        always @* begin
            for (p = 0; p < NP; p = p + 1) begin
                jc[p] = {KW{1'b0}};
                for (q = 0; q < p; q = q + 1)
                    if (h_v[HL-1][q] && h_b[HL-1][q] == h_b[HL-1][p]) jc[p] = jc[p] + 1'b1;
            end
        end
        always @(posedge clk or negedge rst_i)
            if (!rst_i) d_v <= {NP{1'b0}};
            else d_v <= h_v[HL-1];
        always @(posedge clk)
            for (p = 0; p < NP; p = p + 1) begin
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
            wire [BB+GW:0] gidw = grp_q * NBL + LBI;
            wire [BB-1:0] gid = gidw[BB-1:0];
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
            wire [QW+PW+1:0] need = occ - serve + cnt;
            integer ps;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin qh <= 0; qt <= 0; occ <= 0; ovf <= 1'b0; end
                else begin
                    if (need > QD) begin
                        ovf <= 1'b1;
                        qt <= qt + (QD - (occ - serve));
                        occ <= QD;
                    end else begin
                        qt <= qt + cnt;
                        occ <= need;
                    end
                    if (serve) qh <= qh + 1'b1;
                end
            always @(posedge clk)
                for (ps = 0; ps < NP; ps = ps + 1)
                    if (hit[ps] && occ - serve + pref[ps] < QD) begin
                        q_we[(qt + pref[ps]) & (QD-1)] <= a_we[ps];
                        q_p [(qt + pref[ps]) & (QD-1)] <= ps;
                        q_r [(qt + pref[ps]) & (QD-1)] <= a_row[ps*RA + BB +: 9];
                        q_m [(qt + pref[ps]) & (QD-1)] <= a_m[ps*MW +: MW];
                        q_dd[(qt + pref[ps]) & (QD-1)] <= a_d[ps*DW +: DW];
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
                s_p <= q_p[qh]; s_r <= q_r[qh]; s_dd <= q_dd[qh];
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
            reg [RW:0]   fn;
            reg          und;
            reg [PW:0] dcnt;
            integer pd;
            always @* begin
                dcnt = 0;
                for (pd = 0; pd < NP; pd = pd + 1) if (h_v[HL-1][pd] && h_b[HL-1][pd] == gid) dcnt = dcnt + 1'b1;
            end
            reg [DW-1:0] ds [0:KQ-1];
            reg [PW-1:0] dsp [0:KQ-1];
            integer kk;
            always @(posedge clk or negedge rst_i)
                if (!rst_i) begin fh <= 0; ft <= 0; fn <= 0; und <= 1'b0; end
                else begin
                    if (r_vv) ft <= ft + 1'b1;
                    fh <= fh + dcnt;
                    fn <= fn + r_vv - dcnt;
                    if (dcnt > fn) und <= 1'b1;
                end
            always @(posedge clk) begin
                if (r_vv) begin f_dd[ft] <= r_dd; f_p[ft] <= r_p; end
                for (kk = 0; kk < KQ; kk = kk + 1) begin
                    ds[kk] <= f_dd[(fh + kk) & (RQ-1)];
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
        reg [NP-1:0] own;
        reg [LB-1:0] lb [0:NP-1];
        always @* for (p = 0; p < NP; p = p + 1) begin
            lb[p] = d_b[p][LB-1:0];
            own[p] = d_v[p] && (d_b[p] >> LB) == grp_q && (lb[p] / SR) == gs;
        end
        reg [NP*DW-1:0] part;
        integer bb2;
        always @* begin
            part = {NP*DW{1'b0}};
            for (p = 0; p < NP; p = p + 1)
                for (bb2 = 0; bb2 < SR; bb2 = bb2 + 1)
                    if (own[p] && (lb[p] % SR) == bb2) part[p*DW +: DW] = part[p*DW +: DW] | b_ds[bb2][DW*d_j[p] +: DW];
        end
        wire [NP-1:0]    in_v;
        wire [NP*DW-1:0] in_d;
        if (gs == 0) begin : g_in0
            assign in_v = q_v | d_v;
            assign in_d = q_d;
        end else begin : g_inn
            assign in_v = g_s[gs-1].rt_v;
            assign in_d = g_s[gs-1].rt_d;
        end
        reg [NP-1:0]    rt_v;
        reg [NP*DW-1:0] rt_d;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) rt_v <= {NP{1'b0}};
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
                for (p = 0; p < NP; p = p + 1)
                    if (own[p] && b_dp[lb[p] % SR][PW*d_j[p] +: PW] != p) mis_r <= 1'b1;
                stc <= stc | {|b_und, mis_r, |b_ovf};
                stf <= stf | |b_und | mis_r | |b_ovf;
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
