`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_tile (s81-suhc-hier-1011, 2026-10-11): one hardened engine tile of the hierarchical SU slab dsfd_sp_su_h.
// TK selects the function, TI / NT the tile's lane group among NT tiles of that function:
//   TK 0 QN  q RMSNorm -> FP8 (ot_dsrom_su_norm N QN_N) + the QN gain sets (GQ jobs)       one tile
//   TK 1 KV  kv RMSNorm -> RoPE -> FP8 QDQ (N KV_N, RD 64) + the KV gain sets (GK jobs)     one tile
//   TK 2 QB  act-quant bank, QB_NB / NT blocks (blocks are independent)                     NT tiles
//   TK 3 SW  SwiGLU x route weight -> FP8, SW_W / NT lanes (lanes and 32-blocks independent) NT tiles
//   TK 4 SM  softmax SE / SO, SM_H / NT heads (every reduction is within a head)             NT tiles
// The cross-lane reductions (RMSNorm sum of squares, softmax max / sum) stay inside one unit in the golden's order;
// lane groups are split only where the golden has no cross-lane step, so every value is bit-identical.
// Boundaries (every one registered: pin flops on the down-spine tap, registered write slots / status out; the
// spines' relay registers are slab-level stations, one at each tile stop):
//   down spine tap (the relay register at this stop):
//     dn_st announces a job {kind, gain set, FP4, job id}; parameter rows (ph 0) of its own jobs land in prow; operand
//     rows (ph 1) of its own lane group land in the local beat buffer; a full beat strobes the unit;
//   unit results -> a two-entry result row staging (rows {VM row, word mask, data}) -> up to WS rows a cycle out of
//     registered output slots; the slab merges them into the tile's window (TI * WS) of the S_WR write slots of the up
//     spine at the tile's stop (only the active function's tiles drive slots);
//   reset: a two-flop regional relay (asynchronous assert, synchronous release) from the slab's reset spine;
//     datapath registers (beat, staging data, parameters, gain sets) carry no reset.
// MUT: 3 the softmax unit's one-cycle reset at SO parameter load (behaviour-equivalent: recorded); 4 the norm gain
// set index ignored; 5 the softmax lanes' den loads on the first SE only (stale den).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_tile #(
    parameter integer TK = 0, TI = 0, NT = 1,
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, MUT = 0,
    parameter integer WSP = S_WR / NT                        // write slots of this tile (its window of the S_WR)
) (
    input  wire                   clk,
    input  wire                   rst_in,         // from the slab's reset relay at this tile's spine stop
    // down spine tap (the slab's relay register at this stop)
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire                   dn_fp4_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    // norm lane-group seams (TK 0 / 1, through the slab's registered rung): group partial to the head, rstd back
    input  wire                   x_pp_v_i,
    input  wire [7:0]             x_pp_i_i,
    input  wire [31:0]            x_pp_d_i,
    input  wire                   x_rb_v_i,
    input  wire [31:0]            x_rb_d_i,
    output reg                    x_pp_v_o,
    output reg  [7:0]             x_pp_i_o,
    output reg  [31:0]            x_pp_d_o,
    output reg                    x_rb_v_o,
    output reg  [31:0]            x_rb_d_o,
    // this tile's write slots (registered) and status, merged into the up spine at this stop
    output reg  [WSP-1:0]         o_v,
    output reg  [WSP*14-1:0]      o_a,
    output reg  [WSP*16-1:0]      o_m,
    output reg  [WSP*512-1:0]     o_d,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer DQ = 1280, DK = 512, NVQ = DQ / QN_N;
    localparam integer SMW = SM_H * SM_LPH;
    localparam integer RQN = QN_N / 16, RKV = KV_N / 16, RQB = 2 * QB_NB, RSW = SW_W / 16, RSM = SMW / 16;
    localparam [3:0] K_QN = 0, K_KV = 1, K_QB = 2, K_SW = 3, K_SE = 4, K_SO = 5, K_GQ = 6, K_GK = 7;
    localparam integer MAXP = 8;
    // lane group of this tile
    localparam integer NBT = QB_NB / NT;                          // QB blocks
    localparam integer WT  = SW_W / NT;                           // SW lanes
    localparam integer HPT = SM_H / NT;                           // SM heads
    localparam integer LT  = HPT * SM_LPH;                        // SM lanes
    // operand rows: rows a beat (whole function), this tile's segment(s) [A0, A0 + L) (+ [B0, B0 + L) for SW's u)
    localparam integer RPB = (TK == 0) ? RQN : (TK == 1) ? RKV : (TK == 2) ? RQB : (TK == 3) ? 2 * RSW : RSM;
    localparam integer L   = (TK == 0) ? RQN / NT : (TK == 1) ? RKV / NT : (TK == 2) ? 2 * NBT : (TK == 3) ? WT / 16 : LT / 16;
    localparam integer A0  = TI * L;
    localparam integer B0  = RSW + TI * L;
    localparam integer NBR = (TK == 3) ? 2 * L : L;               // rows of this tile's beat
    // results: rows an event, write slots
    localparam integer R_QNF = QN_N / 64 + 1;                     // rows a q vector (every lane tile's codes + exps)
    localparam integer R_QN = QN_N / NT / 64 + 1, R_KV = KV_N / NT / 64 + 1 + KV_N / NT / 32, R_QB = NBT / 2 + 1 + NBT;
    localparam integer R_SW = WT / 64 + 1 + WT / 32, R_SE = LT / 16, R_SO = LT / 32;
    localparam integer R = (TK == 0) ? R_QN : (TK == 1) ? R_KV : (TK == 2) ? R_QB : (TK == 3) ? R_SW :
                           (R_SE > R_SO ? R_SE : R_SO);
    localparam integer WS = S_WR / NT;                            // write slots of this tile
    localparam integer W0 = TI * WS;                              // its window
    localparam integer RW = 14 + 16 + 512;                        // staged row {row, mask, data}
`ifndef SYNTHESIS
    initial begin
        if (RPB & (RPB - 1)) $fatal(1, "ot_s81_su_tile: rows a beat a power of two");
        if (TK >= 2 && (S_WR % NT || WS == 0)) $fatal(1, "ot_s81_su_tile: write slots split evenly");
        if (TK == 2 && (NBT % 2)) $fatal(1, "ot_s81_su_tile: QB tile an even block count");
        if (TK == 3 && (WT % 64)) $fatal(1, "ot_s81_su_tile: SW tile a multiple of 64 lanes");
        if (TK == 4 && (LT % 32)) $fatal(1, "ot_s81_su_tile: SM tile a multiple of 32 lanes");
    end
`endif

    // ------------------------------------------------------------------ regional reset relay
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;

    // ------------------------------------------------------------------ pin flops (the down-spine tap)
    reg                dq_st, dq_fp4;
    reg  [3:0]         dq_kind;
    reg  [1:0]         dq_gsel;
    reg  [7:0]         dq_jid;
    reg  [S_RD-1:0]    dq_v;
    reg  [S_RD*512-1:0] dq_d;
    always @(posedge clk) begin
        dq_kind <= dn_kind_i; dq_gsel <= dn_gsel_i; dq_fp4 <= dn_fp4_i; dq_jid <= dn_jid_i;
        dq_d <= dn_d_i;
        xq_pp_i <= x_pp_i_i; xq_pp_d <= x_pp_d_i; xq_rb_d <= x_rb_d_i;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; end
                                           else begin dq_st <= dn_st_i; dq_v <= dn_v_i; end
    reg                xq_pp_v, xq_rb_v;
    reg  [7:0]         xq_pp_i;
    reg  [31:0]        xq_pp_d, xq_rb_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin xq_pp_v <= 1'b0; xq_rb_v <= 1'b0; end
                                           else begin xq_pp_v <= x_pp_v_i; xq_rb_v <= x_rb_v_i; end

    function automatic mine_k(input [3:0] k);
        case (TK)
            0: mine_k = (k == K_QN || k == K_GQ);
            1: mine_k = (k == K_KV || k == K_GK);
            2: mine_k = (k == K_QB);
            3: mine_k = (k == K_SW);
            default: mine_k = (k == K_SE || k == K_SO);
        endcase
    endfunction
    function automatic [3:0] nparams(input [3:0] k);
        nparams = (k == K_KV || k == K_SO) ? 5 : (k == K_SE) ? 1 + (SM_H + 15) / 16 : 1;
    endfunction

    // ------------------------------------------------------------------ job context, parameters, operand beats
    reg  [3:0]  jkind;
    reg  [1:0]  gsel;
    reg         fp4, mine;
    reg  [7:0]  jid;
    reg  [511:0] prow [0:MAXP-1];
    reg  [3:0]  pc;
    reg         pdone;                                // parameter rows of this tile's job all in (a pulse)
    reg  [512*NBR-1:0] bb, bq;
    reg         beat_v;
    reg  [15:0] bc, bi;                               // beats of the job / index of the strobed beat
    wire [1:0]  gs = (MUT == 4) ? 2'd0 : gsel;
    wire [13:0] obase = prow[0][13:0];
    wire [31:0] w3 = prow[0][96 +: 32];
    integer s, q, g;
    // row numbering (from the job announce): the VM responses of a job arrive in order, a prefix of the slots a
    // cycle; the first nparams(kind) rows are the descriptor + parameter rows (phase 0), the rest the operand rows
    reg  [15:0]        rcnt;
    reg  [S_RD-1:0]    sph;                           // slot s: an operand row
    reg  [S_RD*16-1:0] six;                           // slot s: its index within its phase
    always @(*) begin : numb
        integer i;
        reg [15:0] gi, npj;
        npj = {12'd0, nparams(jkind)};
        for (i = 0; i < S_RD; i = i + 1) begin
            gi = rcnt + i;
            sph[i] = (gi >= npj);
            six[16 * i +: 16] = (gi >= npj) ? gi - npj : gi;
        end
    end
    always @(posedge clk or negedge rst_n) begin : rcntb
        integer i;
        reg [15:0] c;
        if (!rst_n) rcnt <= 0;
        else if (dq_st) rcnt <= 0;
        else begin
            c = rcnt;
            for (i = 0; i < S_RD; i = i + 1) if (dq_v[i]) c = c + 1;
            rcnt <= c;
        end
    end
    always @(posedge clk) begin                       // parameter rows / beat data: no reset
        for (s = 0; s < S_RD; s = s + 1)
            if (dq_v[s] && !sph[s] && mine && six[16 * s +: 16] < MAXP) prow[six[16 * s +: 16]] <= dq_d[512 * s +: 512];
        begin : asm
            reg [15:0] r;
            for (s = 0; s < S_RD; s = s + 1)
                if (dq_v[s] && sph[s] && mine) begin
                    r = six[16 * s +: 16] & (RPB - 1);
                    if (r >= A0 && r < A0 + L) bb[512 * (r - A0) +: 512] = dq_d[512 * s +: 512];
                    else if (TK == 3 && r >= B0 && r < B0 + L) bb[512 * (L + r - B0) +: 512] = dq_d[512 * s +: 512];
                end
        end
        if (cmp) bq <= bb;                            // the assembled beat (same block: bb is blocking)
    end
    // completion: the slot carrying this tile's last beat row
    reg cmp;
    always @(*) begin : cmpb
        integer i;
        cmp = 1'b0;
        for (i = 0; i < S_RD; i = i + 1)
            if (dq_v[i] && sph[i] && mine && ((six[16 * i +: 16] & (RPB - 1)) == ((TK == 3) ? B0 + L - 1 : A0 + L - 1)))
                cmp = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            jkind <= 0; gsel <= 0; fp4 <= 0; mine <= 0; jid <= 0; pc <= 0; pdone <= 0; beat_v <= 0; bc <= 0; bi <= 0;
        end else begin
            pdone <= 1'b0; beat_v <= 1'b0;
            if (dq_st) begin
                jkind <= dq_kind; gsel <= dq_gsel; fp4 <= dq_fp4; jid <= dq_jid; mine <= mine_k(dq_kind);
                pc <= 0; bc <= 0;
            end else begin
                begin : pcnt
                    reg [3:0] c;
                    c = pc;
                    for (s = 0; s < S_RD; s = s + 1) if (dq_v[s] && !sph[s] && mine) c = c + 1;
                    pc <= c;
                    if (mine && c == nparams(jkind) && pc != c) pdone <= 1'b1;
                end
                if (cmp) begin beat_v <= 1'b1; bi <= bc; bc <= bc + 1; end
            end
        end
    end

    // ------------------------------------------------------------------ unit + result events
    reg              ev;                               // result rows this cycle (combinational from the unit)
    reg  [7:0]       ev_n;
    reg  [RW*R-1:0]  ev_r;
    reg              u_f;                              // the unit's fault
    reg              den_ok;                           // SM: this SE job's den reached the lanes
    reg              rdy_p;                            // QN / KV: go issued (a pulse)
    reg  [15:0]      oc;                               // result events of the job (rows / beats / vectors)

    function automatic [RW-1:0] mkrow(input [13:0] a, input [15:0] m, input [511:0] d);
        mkrow = {a, m, d};
    endfunction

    generate
    if (TK <= 1) begin : g_nm
        // a lane group of the q (TK 0) / kv (TK 1) RMSNorm: G lanes from L0; the group sums of squares meet in the
        // head tile (TI 0) through the slab's registered rung (x_pp_*), its rstd comes back over x_rb_*
        localparam integer NN = (TK == 0) ? QN_N : KV_N, GG = NN / NT, NVN = (TK == 0) ? NVQ : 1;
        localparam integer DD = (TK == 0) ? DQ : DK, RFULL = (TK == 0) ? R_QNF : 0;
        reg [GG*32-1:0] gn [0:4*NVN-1];
        reg n_go, n_wl, gon; reg [7:0] n_wi; reg [GG*32-1:0] n_wd; reg [15:0] gp;
        wire n_yv, n_qv, n_rov, n_f; wire [7:0] n_yi, n_qi; wire [GG*32-1:0] n_y, n_ro;
        wire [(GG/32)*256-1:0] n_qc; wire [(GG/32)*10-1:0] n_qe; wire [(GG/32)*512-1:0] n_qy;
        wire ps_v; wire [7:0] ps_i; wire [31:0] ps_d; wire rb_v; wire [31:0] rb_d;
        ot_s81_su_norm_lg #(.N(NN), .G(GG), .L0(TI * GG), .T(NT), .HEAD(TI == 0), .D(DD), .RD(TK == 1 ? 64 : 0),
                            .QUANT(1), .LM(LM), .LA(LA)) u_n (
            .clk(clk), .rst_n(rst_n), .go(n_go), .in_v(beat_v && jkind == (TK == 0 ? K_QN : K_KV)), .in_x(bq[0 +: GG * 32]),
            .n_f(TK == 0 ? 32'h44A00000 : 32'h44000000), .eps(w3), .wl_v(n_wl), .wl_i(n_wi), .wl_d(n_wd),
            .cos_t(TK == 1 ? {prow[2], prow[1]} : 1024'd0), .sin_t(TK == 1 ? {prow[4], prow[3]} : 1024'd0),
            .ps_v(ps_v), .ps_i(ps_i), .ps_d(ps_d), .pp_v(xq_pp_v), .pp_i(xq_pp_i), .pp_d(xq_pp_d),
            .rb_o_v(rb_v), .rb_o_d(rb_d), .rb_i_v(xq_rb_v), .rb_i_d(xq_rb_d),
            .y_v(n_yv), .y_i(n_yi), .y(n_y), .q_v(n_qv), .q_i(n_qi), .q_codes(n_qc), .q_e(n_qe), .q_y(n_qy),
            .ro_v(n_rov), .ro(n_ro), .fault(n_f));
        always @(*) begin x_pp_v_o = ps_v; x_pp_i_o = ps_i; x_pp_d_o = ps_d; x_rb_v_o = rb_v; x_rb_d_o = rb_d; end
        always @(posedge clk) begin
            if (beat_v && jkind == (TK == 0 ? K_GQ : K_GK)) gn[gsel * NVN + bi] <= bq[0 +: GG * 32];
            n_wd <= gn[gs * NVN + gp];
        end
        // gain vectors -> go -> ready (the head reports it), after the job's parameters (eps) are in
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin n_go <= 0; n_wl <= 0; n_wi <= 0; gp <= 0; gon <= 0; rdy_p <= 0; end
            else begin
                n_go <= 0; n_wl <= 0; rdy_p <= 0;
                if (pdone && jkind == (TK == 0 ? K_QN : K_KV)) begin gon <= 1; gp <= 0; end
                if (gon) begin
                    if (gp < NVN) begin n_wl <= 1; n_wi <= gp[7:0]; gp <= gp + 1; end
                    else begin n_go <= 1; rdy_p <= (TI == 0); gon <= 0; end
                end
            end
        end
        always @(*) begin : evb
            integer q, g;
            reg [13:0] base; reg [511:0] row; reg [15:0] m;
            ev = n_qv; ev_n = R; ev_r = 0; u_f = n_f; den_ok = 1'b1;
            base = obase + oc * RFULL;
            for (q = 0; q < GG / 64; q = q + 1)
                ev_r[RW * q +: RW] = mkrow(base + TI * (GG / 64) + q, 16'hFFFF, n_qc[512 * q +: 512]);
            row = 0; m = 0;
            for (g = 0; g < GG / 32; g = g + 1) row[16 * (TI * (GG / 32) + g) +: 16] = {6'd0, n_qe[10 * g +: 10]};
            for (g = 0; g < 16; g = g + 1) m[g] = (g >= TI * (GG / 64)) && (TI == NT - 1 || g < (TI + 1) * (GG / 64));
            ev_r[RW * (GG / 64) +: RW] = mkrow(base + NN / 64, m, row);
            if (TK == 1)
                for (q = 0; q < GG / 32; q = q + 1)
                    ev_r[RW * (GG / 64 + 1 + q) +: RW] = mkrow(base + NN / 64 + 1 + TI * (GG / 32) + q, 16'hFFFF,
                                                               n_qy[512 * q +: 512]);
        end
    end else if (TK == 2) begin : g_qb
        wire qb_vo, qb_f; wire [256*NBT-1:0] qb_q; wire [10*NBT-1:0] qb_e; wire [512*NBT-1:0] qb_y;
        ot_dsrom_su_qbank #(.NB(NBT), .NIN(1), .NOUT(1), .ROPE(0), .LM(LM), .LA(LA)) u_qb (
            .clk(clk), .rst_n(rst_n), .v(beat_v), .fp4(fp4), .x(bq[0 +: 1024 * NBT]), .cs(2048'd0), .vo(qb_vo), .q(qb_q),
            .e(qb_e), .y(qb_y), .fault(qb_f));
        always @(*) begin : evb
            integer q, g;
            ev = qb_vo; ev_n = R_QB; ev_r = 0; u_f = qb_f; den_ok = 1'b1; rdy_p = 1'b0;
            begin : ex
                reg [13:0] base; reg [511:0] row; reg [15:0] m;
                base = obase + oc * (QB_NB / 2 + 1 + QB_NB);
                for (q = 0; q < NBT / 2; q = q + 1)
                    ev_r[RW * q +: RW] = mkrow(base + TI * (NBT / 2) + q, 16'hFFFF, qb_q[512 * q +: 512]);
                row = 0; m = 0;
                for (g = 0; g < NBT; g = g + 1) row[16 * (TI * NBT + g) +: 16] = {6'd0, qb_e[10 * g +: 10]};
                for (g = 0; g < 16; g = g + 1) m[g] = (32 * g >= 16 * TI * NBT) && (TI == NT - 1 || 32 * g < 16 * (TI + 1) * NBT);
                ev_r[RW * (NBT / 2) +: RW] = mkrow(base + QB_NB / 2, m, row);
                for (q = 0; q < NBT; q = q + 1)
                    ev_r[RW * (NBT / 2 + 1 + q) +: RW] = mkrow(base + QB_NB / 2 + 1 + TI * NBT + q, 16'hFFFF, qb_y[512 * q +: 512]);
            end
        end
    end else if (TK == 3) begin : g_sw
        reg [32*WT-1:0] sw_w;
        wire sw_vo, sw_f; wire [8*WT-1:0] sw_q; wire [10*WT/32-1:0] sw_e; wire [16*WT-1:0] sw_y;
        always @(posedge clk) if (cmp) for (g = 0; g < WT; g = g + 1) sw_w[32 * g +: 32] <= prow[0][32 * (5 + bc) +: 32];
        ot_dsrom_su_swiglu #(.W(WT), .NIN(1), .NOUT(1), .ROUTED(1), .LM(LM), .LA(LA)) u_sw (
            .clk(clk), .rst_n(rst_n), .v(beat_v), .g(bq[0 +: 32 * WT]), .u(bq[32 * WT +: 32 * WT]), .w(sw_w), .lim(w3),
            .vo(sw_vo), .q(sw_q), .e(sw_e), .y(sw_y), .fault(sw_f));
        always @(*) begin : evb
            integer q, g;
            ev = sw_vo; ev_n = R_SW; ev_r = 0; u_f = sw_f; den_ok = 1'b1; rdy_p = 1'b0;
            begin : ex
                reg [13:0] base; reg [511:0] row; reg [15:0] m;
                base = obase + oc * (SW_W / 64 + 1 + SW_W / 32);
                for (q = 0; q < WT / 64; q = q + 1)
                    ev_r[RW * q +: RW] = mkrow(base + TI * (WT / 64) + q, 16'hFFFF, sw_q[512 * q +: 512]);
                row = 0; m = 0;
                for (g = 0; g < WT / 32; g = g + 1) row[16 * (TI * (WT / 32) + g) +: 16] = {6'd0, sw_e[10 * g +: 10]};
                for (g = 0; g < 16; g = g + 1)
                    m[g] = (32 * g >= 16 * TI * (WT / 32)) && (TI == NT - 1 || 32 * g < 16 * (TI + 1) * (WT / 32));
                ev_r[RW * (WT / 64) +: RW] = mkrow(base + SW_W / 64, m, row);
                for (q = 0; q < WT / 32; q = q + 1)
                    ev_r[RW * (WT / 64 + 1 + q) +: RW] = mkrow(base + SW_W / 64 + 1 + TI * (WT / 32) + q, 16'hFFFF, sw_y[512 * q +: 512]);
            end
        end
    end else begin : g_sm
        reg [6:0] sm_nv; reg [2:0] sm_lt; reg [31:0] sm_scale; reg [HPT*32-1:0] sm_sink;
        reg [16*64-1:0] sm_cos, sm_sin;
        reg sm_rst_n, dn;
        wire sm_ev, sm_mxv, sm_esv, sm_denv, sm_ov, sm_f;
        wire [LT*32-1:0] sm_ed; wire [HPT*32-1:0] sm_mx, sm_es, sm_den; wire [LT*16-1:0] sm_od;
        always @(posedge clk) if (pdone) begin
            if (jkind == K_SE) begin
                sm_nv <= prow[0][64 +: 7]; sm_lt <= prow[0][128 +: 3]; sm_scale <= prow[0][96 +: 32];
                sm_sink <= prow[1][32 * TI * HPT +: HPT * 32];
            end
            if (jkind == K_SO) begin
                sm_cos <= {prow[2][0 +: 512], prow[1][0 +: 512]};
                sm_sin <= {prow[4][0 +: 512], prow[3][0 +: 512]};
            end
        end
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin sm_rst_n <= 1'b1; dn <= 1'b0; end
            else begin
                sm_rst_n <= !(MUT == 3 && pdone && jkind == K_SO);
                if (dq_st) dn <= 1'b0; else if (sm_denv) dn <= 1'b1;
            end
        end
        ot_dsrom_su_softmax #(.H(HPT), .LPH(SM_LPH), .NVMAX(SM_NVMAX), .DIN(1), .DOUT(1), .RWU(1), .RWD(1), .LM(LM),
                              .LA(LA), .STALEDEN(MUT == 5)) u_sm (
            .clk(clk), .rst_n(rst_n && sm_rst_n), .nv(sm_nv), .lt(sm_lt), .scale(sm_scale), .sink(sm_sink),
            .cosv(sm_cos), .sinv(sm_sin), .s_v(beat_v && jkind == K_SE), .s_d(bq[0 +: LT * 32]), .e_v(sm_ev),
            .e_d(sm_ed), .mx_v(sm_mxv), .mx_d(sm_mx), .es_v(sm_esv), .es_d(sm_es), .den_v(sm_denv), .den_d(sm_den),
            .pv_v(beat_v && jkind == K_SO), .pv_d(bq[0 +: LT * 32]), .o_v(sm_ov), .o_d(sm_od), .fault(sm_f));
        always @(*) begin : evb
            integer q, g;
            ev = 1'b0; ev_n = 0; ev_r = 0; u_f = sm_f; den_ok = dn; rdy_p = 1'b0;
            if (sm_ev && jkind == K_SE) begin
                ev = 1'b1; ev_n = R_SE;
                for (q = 0; q < R_SE; q = q + 1)
                    ev_r[RW * q +: RW] = mkrow(obase + oc * RSM + TI * R_SE + q, 16'hFFFF, sm_ed[512 * q +: 512]);
            end
            if (sm_ov) begin
                ev = 1'b1; ev_n = R_SO;
                for (q = 0; q < R_SO; q = q + 1)
                    ev_r[RW * q +: RW] = mkrow(obase + oc * (SMW / 32) + TI * R_SO + q, 16'hFFFF, sm_od[512 * q +: 512]);
            end
        end
    end
    endgenerate

    generate if (TK >= 2) begin : g_nx
        always @(*) begin x_pp_v_o = 1'b0; x_pp_i_o = 8'd0; x_pp_d_o = 32'd0; x_rb_v_o = 1'b0; x_rb_d_o = 32'd0; end
    end endgenerate

    // ------------------------------------------------------------------ result staging: head + tail buffers
    reg [RW-1:0] hb [0:R-1];
    reg [RW-1:0] tb [0:R-1];
    reg [7:0]    hn, tn;
    reg          ovf, ufs;
    wire [7:0]   k = (hn < WS) ? hn : 8'd0 + WS;
    wire [7:0]   hrem = hn - k;
    always @(posedge clk) begin                       // staged rows: no reset
        for (q = 0; q < R; q = q + 1) begin
            if (hrem == 0) begin
                if (tn != 0) hb[q] <= tb[q];
                else if (ev) hb[q] <= ev_r[RW * q +: RW];
            end else if (q + WS < R) hb[q] <= hb[q + WS];
            if ((hrem == 0 && tn != 0 && ev) || (hrem != 0 && ev && tn == 0)) tb[q] <= ev_r[RW * q +: RW];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hn <= 0; tn <= 0; ovf <= 0; ufs <= 0; oc <= 0; end
        else begin
            if (u_f) ufs <= 1'b1;
            if (hrem == 0) begin
                if (tn != 0) begin hn <= tn; tn <= ev ? ev_n : 8'd0; end
                else hn <= ev ? ev_n : 8'd0;
            end else begin
                hn <= hrem;
                if (ev) begin if (tn != 0) ovf <= 1'b1; else tn <= ev_n; end
            end
            if (dq_st) oc <= 0; else if (ev) oc <= oc + 1;
        end
    end
    // QN events count rows (QN_N / 64 + 1 a vector) in the result row offset
    // (oc counts events; the QN tile's offset is oc * R_QN: see below)

    // ------------------------------------------------------------------ registered outputs (the tile's write slots)
    always @(posedge clk) begin
        for (s = 0; s < WS; s = s + 1) begin
            o_a[14 * s +: 14] <= hb[s][RW - 1 -: 14];
            o_m[16 * s +: 16] <= hb[s][512 +: 16];
            o_d[512 * s +: 512] <= hb[s][0 +: 512];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_v <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; end
        else begin
            for (s = 0; s < WS; s = s + 1) o_v[s] <= (s < k);
            o_fu <= ufs; o_fo <= ovf; o_alive <= 1'b1; o_den <= den_ok; o_rdy <= rdy_p; o_rjid <= jid;
        end
    end
endmodule
