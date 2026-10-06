`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_vm_mem -- banked vector-memory subsystem of the S81 hub VM slab (dsfd_sp_vm), CLAUDE S81-PH 2026-10-06.
//
// Replaces the S81 parent's behavioural many-port VM (rtl/dsrom_sys/s81_capture_parent/ot_chip_v41x_tile.sv `vm`,
// "NOT a 128-port SRAM fit claim") by real 1R1W SRAM macros (ot_sram_1r1w_512x128_m4_r2c2, 64 Kb) at the die-bus
// granularity: a ROW is 512 b = 16 FP32 elements (one 512-b hub lane beat; a 1024-b hub bus is two ports).
//
// Ports: NP request ports, each one op a cycle: {v, we, row[RA], mask[16] (element write mask), d[512]}.  Reads
// return on o_v / o_d of the SAME port exactly L = QD + 6 cycles after the request is presented (fixed latency, in
// order, never stalls).  Banks: NB banks interleaved by the low row bits (bank = row[BB-1:0]), each 4 macros wide
// (512 rows x 512 b); capacity NB x 512 rows (NB = 32: 16,384 rows = 262,144 elements = 8 Mb, 128 macros).
//
// Semantics (exact, = a behavioural array): ops take effect in the global order (issue cycle, then port index):
// a read returns the row as written by every earlier op, including lower-indexed ports' writes of the same cycle.
// Mechanism: every op is pushed, in port order, into its bank's in-order queue (QD entries); each bank performs
// its queue head once a cycle (macro 1R1W used as 1 op/cycle, so RAW/WAR order is the queue order); a read's
// data waits in the bank's return FIFO until its fixed deadline, then the port takes it (two-stage select).
// Stall-free contract: a bank may receive more ops than it drains only up to QD outstanding; a push beyond that is
// a schedule violation of the issuing sequencer -> sticky fault (code bit 0), the op is dropped (fail closed).
//
// Margin-first boundary: request inputs are captured at the pins (stage A), outputs launched from flops; the
// macro inputs are driven from the per-bank serve register (no logic between flop and macro pin except the
// macro's own read/write enable), and macro read data is captured in a register before any mux.
// Self-checks: the return FIFO entry taken by a port must carry that port's id (code bit 1) and exist (bit 2).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_vm_mem #(
    parameter integer NP = 8,            // request ports
    parameter integer NB = 32,           // banks (power of 2)
    parameter integer QD = 4,            // bank queue depth (power of 2)
    parameter integer RQ = 8,            // bank return FIFO depth (power of 2, >= QD + 2)
    parameter integer MACRO = 1          // 1: ot_sram_1r1w_512x128_m4_r2c2 macros; 0: flop array (debug only)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NP-1:0]     i_v,
    input  wire [NP-1:0]     i_we,
    input  wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*16-1:0]  i_mask,
    input  wire [NP*512-1:0] i_d,
    output reg  [NP-1:0]     o_v,
    output reg  [NP*512-1:0] o_d,
    output reg               fault,
    output reg  [2:0]        fault_code,
    output reg  [$clog2(QD):0] max_occ
);
    localparam integer BB = $clog2(NB);
    localparam integer RA = BB + 9;
    localparam integer PW = (NP > 1) ? $clog2(NP) : 1;
    localparam integer QW = $clog2(QD);
    localparam integer RW = $clog2(RQ);
    localparam integer KQ = (NP < QD) ? NP : QD;   // reads of one issue cycle that one bank can hold
    localparam integer KW = (KQ > 1) ? $clog2(KQ) : 1;
    localparam integer L  = QD + 6;                // fixed read latency (cycles from request to o_v)
    localparam integer HL = L - 2;                 // read history depth (request -> due-slot stage)

    integer p, q, b, k;
    // ------------------------------------------------------------------ reset synchroniser (rst_s[1]: 2-cycle release)
    reg [1:0] rst_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_i = rst_s[1];
    // ------------------------------------------------------------------ stage A: pin registers
    // (the request word is captured NG times at the pin, kept, so each copy drives NB/NG banks: <= 32 loads a bit)
    localparam integer NG = (NB >= 4) ? 4 : 1;
    (* keep = 1 *) reg [511:0] a_dg [0:NG-1][0:NP-1];
    (* keep = 1 *) reg [15:0]  a_mg [0:NG-1][0:NP-1];
    (* keep = 1 *) reg [RA-1:0] a_rg [0:NG-1][0:NP-1];
    (* keep = 1 *) reg [NP-1:0] a_vg [0:NG-1], a_wg [0:NG-1];
    integer g;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) for (g = 0; g < NG; g = g + 1) begin a_vg[g] <= {NP{1'b0}}; a_wg[g] <= {NP{1'b0}}; end
        else for (g = 0; g < NG; g = g + 1) begin a_vg[g] <= i_v; a_wg[g] <= i_we; end
    always @(posedge clk)
        for (g = 0; g < NG; g = g + 1) for (p = 0; p < NP; p = p + 1) begin
            a_rg[g][p] <= i_row[p*RA +: RA]; a_mg[g][p] <= i_mask[p*16 +: 16]; a_dg[g][p] <= i_d[p*512 +: 512];
        end
    reg [NP-1:0] a_v, a_we;
    reg [RA-1:0] a_row [0:NP-1];
    always @* begin
        a_v = a_vg[0]; a_we = a_wg[0];
        for (p = 0; p < NP; p = p + 1) a_row[p] = a_rg[0][p];
    end

    // read history: (read issued, bank) per port, shifted every cycle; position HL-1 is due at the slot stage
    reg [NP-1:0] h_v [0:HL-1];
    reg [BB-1:0] h_b [0:HL-1][0:NP-1];
    integer hh;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) for (hh = 0; hh < HL; hh = hh + 1) h_v[hh] <= {NP{1'b0}};
        else begin
            h_v[0] <= a_v & ~a_we;
            for (hh = 1; hh < HL; hh = hh + 1) h_v[hh] <= h_v[hh-1];
        end
    always @(posedge clk) begin
        for (p = 0; p < NP; p = p + 1) h_b[0][p] <= a_row[p][BB-1:0];
        for (hh = 1; hh < HL; hh = hh + 1) for (p = 0; p < NP; p = p + 1) h_b[hh][p] <= h_b[hh-1][p];
    end

    // ------------------------------------------------------------------ banks
    wire [NB-1:0] b_ovf, b_mis, b_und;
    wire [QW:0]   b_occ [0:NB-1];
    wire [512*KQ-1:0] b_ds [0:NB-1];     // registered due slots: return FIFO head .. head+KQ-1
    wire [PW*KQ-1:0]  b_dp [0:NB-1];

    // per port: due-slot stage selection (bank, index among same-bank reads of its issue cycle)
    reg [NP-1:0] d_v;
    (* keep = 1 *) reg [BB-1:0] d_b [0:3][0:NP-1];     // kept copy per 128-b output slice (select fanout)
    (* keep = 1 *) reg [KW-1:0] d_j [0:3][0:NP-1];
    always @(posedge clk or negedge rst_i)
        if (!rst_i) d_v <= {NP{1'b0}};
        else d_v <= h_v[HL-1];
    reg [KW-1:0] jc [0:NP-1];
    always @* begin
        for (p = 0; p < NP; p = p + 1) begin
            jc[p] = {KW{1'b0}};
            for (q = 0; q < p; q = q + 1)
                if (h_v[HL-1][q] && h_b[HL-1][q] == h_b[HL-1][p]) jc[p] = jc[p] + 1'b1;
        end
    end
    always @(posedge clk)
        for (p = 0; p < NP; p = p + 1) begin
            for (k = 0; k < 4; k = k + 1) begin
                d_b[k][p] <= h_b[HL-1][p];
`ifdef OT_S81PH_VM_MUT_J0
                d_j[k][p] <= {KW{1'b0}};                           // MUTANT: every port takes the first due slot
`else
                d_j[k][p] <= jc[p];
`endif
            end
        end

    genvar gb;
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_bank
        localparam integer GI = gb / (NB / NG);
        // ---- pushes of this cycle (stage A regs, this bank group's copy), in port order
        reg [NP-1:0] hit;
        reg [QW:0]   pref [0:NP-1];
        reg [QW+PW:0] cnt;
        integer pp;
        always @* begin
            cnt = 0;
            for (pp = 0; pp < NP; pp = pp + 1) hit[pp] = a_vg[GI][pp] && a_rg[GI][pp][BB-1:0] == gb;
`ifdef OT_S81PH_VM_MUT_ORDER
            for (pp = NP - 1; pp >= 0; pp = pp - 1) begin   // MUTANT: same-cycle ops queued in reverse port order
`else
            for (pp = 0; pp < NP; pp = pp + 1) begin
`endif
                pref[pp] = cnt[QW:0];
                if (hit[pp]) cnt = cnt + 1'b1;
            end
        end
        // ---- request queue
        reg [QD-1:0] q_we;
        reg [PW-1:0] q_p [0:QD-1];
        reg [8:0]    q_r [0:QD-1];
        reg [15:0]   q_m [0:QD-1];
        reg [511:0]  q_d [0:QD-1];
        reg [QW-1:0] qh, qt;
        reg [QW:0]   occ;
        reg          ovf;
        wire         serve = occ != 0;
        wire [QW+PW+1:0] need = occ - serve + cnt;
        integer ss, ps;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin qh <= 0; qt <= 0; occ <= 0; ovf <= 1'b0; end
            else begin
                if (need > QD) begin                       // schedule violation: keep what fits, flag
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
                    q_we[(qt + pref[ps]) & (QD-1)] <= a_wg[GI][ps];
                    q_p [(qt + pref[ps]) & (QD-1)] <= ps;
                    q_r [(qt + pref[ps]) & (QD-1)] <= a_rg[GI][ps][RA-1:BB];
                    q_m [(qt + pref[ps]) & (QD-1)] <= a_mg[GI][ps];
                    q_d [(qt + pref[ps]) & (QD-1)] <= a_dg[GI][ps];
                end
        assign b_ovf[gb] = ovf;
        assign b_occ[gb] = occ;
        // ---- serve register (drives the macro pins)
        reg          s_v, s_we, s_re;     // s_re: the macro read enable straight from a flop (no gate before the pin)
        reg [PW-1:0] s_p;
        reg [8:0]    s_r;
        reg [511:0]  s_d, s_bm;
        integer e;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin s_v <= 1'b0; s_we <= 1'b0; s_re <= 1'b0; end
            else begin s_v <= serve; s_we <= serve & q_we[qh]; s_re <= serve & ~q_we[qh]; end
        always @(posedge clk) begin
            s_p <= q_p[qh]; s_r <= q_r[qh]; s_d <= q_d[qh];
            for (e = 0; e < 16; e = e + 1)
`ifdef OT_S81PH_VM_MUT_MASK
                s_bm[32*e +: 32] <= {32{1'b1}};                    // MUTANT: element write mask ignored
`else
                s_bm[32*e +: 32] <= {32{q_m[qh][e]}};
`endif
        end
        // ---- macros: 4 x 128 b
        wire [511:0] rd;
        genvar gc;
        for (gc = 0; gc < 4; gc = gc + 1) begin : g_m
            if (MACRO) begin : g_sram
                // kept, NOT dont_touch: the resizer must be free to buffer the nets that drive the macro pins
                // (route m1 failed RSZ-3006 at place_gp: dont_touch forbids a buffer before r_ce_in)
                (* keep = 1 *) ot_sram_1r1w_512x128_m4_r2c2 u_m (
                    .clk(clk), .r_ce_in(s_re), .r_addr_in(s_r), .rd_out(rd[128*gc +: 128]),
                    .w_ce_in(s_we), .w_addr_in(s_r), .wd_in(s_d[128*gc +: 128]), .w_mask_in(s_bm[128*gc +: 128]),
                    .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(14'd0));
            end else begin : g_flop
                reg [127:0] mem [0:511];
                reg [127:0] r_q;
                integer bi;
                always @(posedge clk) begin
                    if (s_re) r_q <= mem[s_r];
                    if (s_we) for (bi = 0; bi < 128; bi = bi + 1)
                        if (s_bm[128*gc + bi]) mem[s_r][bi] <= s_d[128*gc + bi];
                end
                assign rd[128*gc +: 128] = r_q;
            end
        end
        // ---- read data capture (first flop after the macro) and return FIFO
        reg          m_v, r_v;
        reg [PW-1:0] m_p, r_p;
        reg [511:0]  r_d;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin m_v <= 1'b0; r_v <= 1'b0; end
            else begin m_v <= s_re; r_v <= m_v; end
        always @(posedge clk) begin m_p <= s_p; r_p <= m_p; r_d <= rd; end
        reg [511:0]  f_d [0:RQ-1];
        reg [PW-1:0] f_p [0:RQ-1];
        reg [RW-1:0] fh, ft;
        reg [RW:0]   fn;
        reg          und;
        // reads of this bank due at the slot stage (history position HL-1)
        reg [PW:0] dcnt;
        integer pd;
        always @* begin
            dcnt = 0;
            for (pd = 0; pd < NP; pd = pd + 1) if (h_v[HL-1][pd] && h_b[HL-1][pd] == gb) dcnt = dcnt + 1'b1;
        end
        reg [511:0]  ds [0:KQ-1];
        reg [PW-1:0] dsp [0:KQ-1];
        integer kk;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin fh <= 0; ft <= 0; fn <= 0; und <= 1'b0; end
            else begin
                if (r_v) ft <= ft + 1'b1;
                fh <= fh + dcnt;
                fn <= fn + r_v - dcnt;
                if (dcnt > fn) und <= 1'b1;
            end
        always @(posedge clk) begin
            if (r_v) begin f_d[ft] <= r_d; f_p[ft] <= r_p; end
            for (kk = 0; kk < KQ; kk = kk + 1) begin
                ds[kk] <= f_d[(fh + kk) & (RQ-1)];
                dsp[kk] <= f_p[(fh + kk) & (RQ-1)];
            end
        end
        for (gc = 0; gc < KQ; gc = gc + 1) begin : g_ds
            assign b_ds[gb][512*gc +: 512] = ds[gc];
            assign b_dp[gb][PW*gc +: PW] = dsp[gc];
        end
        assign b_und[gb] = und;
    end endgenerate

    // ------------------------------------------------------------------ output stage
    reg mis_r;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin o_v <= {NP{1'b0}}; mis_r <= 1'b0; end
        else begin
            o_v <= d_v;
            for (p = 0; p < NP; p = p + 1)
                if (d_v[p] && b_dp[d_b[0][p]][PW*d_j[0][p] +: PW] != p) mis_r <= 1'b1;
        end
    always @(posedge clk)
        for (p = 0; p < NP; p = p + 1) for (k = 0; k < 4; k = k + 1)
            o_d[p*512 + 128*k +: 128] <= b_ds[d_b[k][p]][512*d_j[k][p] + 128*k +: 128];

    // ------------------------------------------------------------------ status
    integer bo;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin fault <= 1'b0; fault_code <= 3'd0; max_occ <= 0; end
        else begin
            fault_code <= fault_code | {|b_und, mis_r, |b_ovf};
            fault <= fault | |b_und | mis_r | |b_ovf;
            for (bo = 0; bo < NB; bo = bo + 1) if (b_occ[bo] > max_occ) max_occ <= b_occ[bo];
        end
endmodule
