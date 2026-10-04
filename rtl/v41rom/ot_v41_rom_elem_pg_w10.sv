`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rom_elem_pg_w10 -- the V4.1 ROM-array element (ot_v41_rom_elem_w10) as a power-gated domain.
//
// PG = 0 (default): the element, unchanged; every PG port is ignored and pg_ready = 1.
// PG = 1: the element sits behind a header switch ring.  The always-on (AO) side keeps
//   * the stage scheduler + W18 power controller (ot_v41_stage_pg_sched; shared by a whole domain in the die,
//     one per element only in this vehicle): staggered ring wake, reset, isolation, clock enable, pre-wake from
//     the static token schedule;
//   * output isolation: every element output is clamped to 0 while iso_n = 0 (AND clamps);
//   * retention of the configuration, the only element state that must survive a sleep (the element is a
//     stateless consumer between tokens: walkers, FIFOs, chains and trees all restart at `go`; the ROM is a
//     mask ROM).  Retention is an AO shadow of exactly the bits the element decodes (676 for NSEG = 8, NB = 2),
//     written on the host's configuration writes through a write-enabled AO clock gate (no idle clock), and
//     replayed into the element, one entry a cycle, after every wake.  Host writes while the domain is asleep or
//     restoring update only the shadow and are replayed.
//   * the domain clock gate (clk_en from the controller).
// pg_ready rises when the domain is powered, reset, de-isolated and restored.  A `go` that arrives before
// pg_ready is a schedule miss: it is not delivered and pg_late latches (fail closed; the static pre-wake makes
// it unreachable when cfg_lead covers the wake).
// ---------------------------------------------------------------------------
module ot_v41_rom_elem_pg_w10 #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 5,
    parameter integer BF16 = 0,
    parameter integer NCHB = 8,
    parameter integer NB = 1,
    parameter integer MTP = 0,
    parameter integer EARLY = 0,
    parameter integer CG = 1,
    parameter integer DRAIN = 127,
    parameter integer FAST = 0,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer PP = 0,
    parameter integer FRONT_PAR = 0,
    parameter integer BP = 0,
    parameter INSTANCE = "",
    parameter integer PG = 0,          // 1: power-gated domain (opt-in)
    parameter integer NSUB = 4,        // header-ring segments of this element's domain
    parameter integer TW = 24
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         go_bf,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    input  wire [2:0]   xb_pos,
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault,
    // power gating (PG = 1)
    input  wire         pg_en,
    input  wire         sched_v,
    input  wire [TW-1:0] sched_gap,
    input  wire [TW-1:0] pg_lead,
    input  wire [TW-1:0] pg_bet,
    input  wire [7:0]   pg_idle,
    input  wire [15:0]  pg_step,
    input  wire [7:0]   pg_rst,
    input  wire [15:0]  pg_ack_to,
    output wire [NSUB-1:0] sw_en,
    input  wire [NSUB-1:0] sw_ack,
    output wire         pg_ready,
    output wire         pg_late,
    output wire         pg_fault
);
    // retained width of configuration entry a (see g_pg)
    function integer ew(input integer a);
        ew = (a < NSEG) ? 43 : (a < 2 * NSEG) ? 23 : (a == 2 * NSEG) ? 20 : 16;
    endfunction

    // element-side nets
    wire         e_clk, e_rst_n, e_cfg_v, e_go;
    wire [4:0]   e_cfg_a;
    wire [47:0]  e_cfg_d;
    wire [NB-1:0]    e_pv, e_perr;
    wire [32*NB-1:0] e_pval;
    wire [16*NB-1:0] e_prow;
    wire [5*NB-1:0]  e_pseg, e_pnseg;
    wire [3*NB-1:0]  e_ppos;
    wire e_busy, e_fault;

    ot_v41_rom_elem_w10 #(.NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NCHB(NCHB), .NB(NB), .MTP(MTP),
        .EARLY(EARLY), .CG(CG), .DRAIN(DRAIN), .FAST(FAST), .CUT(CUT), .PP(PP), .FRONT_PAR(FRONT_PAR), .BP(BP),
        .INSTANCE(INSTANCE)) u_elem (
        .clk(e_clk), .rst_n(e_rst_n), .cfg_v(e_cfg_v), .cfg_a(e_cfg_a), .cfg_d(e_cfg_d), .go(e_go), .go_bf(go_bf),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1),
        .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv), .xb_u(xb_u),
        .xb_d(xb_d), .pv(e_pv), .pval(e_pval), .prow(e_prow), .pseg(e_pseg), .pnseg(e_pnseg), .perr(e_perr),
        .ppos(e_ppos), .busy(e_busy), .fault(e_fault));

    if (PG == 0) begin : g_off
        assign e_clk = clk; assign e_rst_n = rst_n; assign e_cfg_v = cfg_v; assign e_cfg_a = cfg_a;
        assign e_cfg_d = cfg_d; assign e_go = go;
        assign pv = e_pv; assign pval = e_pval; assign prow = e_prow; assign pseg = e_pseg; assign pnseg = e_pnseg;
        assign perr = e_perr; assign ppos = e_ppos; assign busy = e_busy; assign fault = e_fault;
        assign sw_en = {NSUB{1'b1}}; assign pg_ready = 1'b1; assign pg_late = 1'b0; assign pg_fault = 1'b0;
    end else begin : g_pg
        // ------------- retention shadow: the decoded configuration bits, per address class -------------
        // a < NSEG: segment [42:0]; NSEG <= a < 2NSEG: class [19+SW-1:0] with bit 22 (BF16 family);
        // a = 2NSEG: [19:0]; 2NSEG < a <= 3NSEG (NB = 2): second-macro row [15:0]
        localparam integer NA = (NB == 2) ? 3 * NSEG + 1 : 2 * NSEG + 1;
        localparam integer AW = 5;
        if (NSEG != 8) begin : g_bad
            initial $error("ot_v41_rom_elem_pg_w10: the retention map is written for NSEG = 8");
        end

        wire iso_n, dom_rst_n, clk_en, pwr_good, ctl_fault;
        reg  ready, late, restoring;
        reg  [NA-1:0] valid, dirty;
        wire host_wr = cfg_v && ({27'd0, cfg_a} < NA);

        // the shadow is clocked only on a host write (AO ICG); idle, it costs leakage only
        wire sh_clk;
        ot_hdc_cg u_sh_cg (.clk(clk), .en(cfg_v | !rst_n), .gclk(sh_clk));
        wire [47:0] sh_q [0:NA-1];
        genvar ga;
        for (ga = 0; ga < NA; ga = ga + 1) begin : g_sh
            localparam integer W = ew(ga);
            reg [W-1:0] r;
            always @(posedge sh_clk) if (cfg_v && cfg_a == ga[AW-1:0]) r <= cfg_d[W-1:0];
            assign sh_q[ga] = {{(48 - W){1'b0}}, r};
        end

        // restore: lowest dirty entry first, one a cycle, once powered and before ready
        reg [AW-1:0] ridx; reg rhit;
        integer k;
        always @* begin
            ridx = {AW{1'b0}}; rhit = 1'b0;
            for (k = NA - 1; k >= 0; k = k - 1) if (dirty[k]) begin ridx = k[AW-1:0]; rhit = 1'b1; end
        end
        wire rst_wr = pwr_good && !ready && rhit;
        reg pg_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin valid <= {NA{1'b0}}; dirty <= {NA{1'b0}}; ready <= 1'b0; late <= 1'b0; pg_q <= 1'b0; end
            else begin
                pg_q <= pwr_good;
                if (pg_q && !pwr_good) begin ready <= 1'b0; dirty <= valid; end       // power lost: replay all
                else begin
                    if (rst_wr) dirty[ridx] <= 1'b0;
                    if (host_wr) begin
                        valid[cfg_a] <= 1'b1;
                        if (!ready) dirty[cfg_a] <= 1'b1;                              // replayed after wake
                    end
                    if (pwr_good && !ready && !rhit && !(host_wr)) ready <= 1'b1;
                end
                if (go && !ready) late <= 1'b1;
            end

        // configuration port of the element: the host while ready, the replay while restoring
        assign e_cfg_v = ready ? cfg_v : rst_wr;
        assign e_cfg_a = ready ? cfg_a : ridx;
        assign e_cfg_d = ready ? cfg_d : sh_q[ridx];
        assign e_go    = go && ready;
        assign e_rst_n = rst_n && dom_rst_n;
        ot_hdc_cg u_dom_cg (.clk(clk), .en(clk_en | !rst_n), .gclk(e_clk));

        // output isolation (clamp to 0)
        assign pv    = e_pv    & {NB{iso_n}};
        assign pval  = e_pval  & {32*NB{iso_n}};
        assign prow  = e_prow  & {16*NB{iso_n}};
        assign pseg  = e_pseg  & {5*NB{iso_n}};
        assign pnseg = e_pnseg & {5*NB{iso_n}};
        assign perr  = e_perr  & {NB{iso_n}};
        assign ppos  = e_ppos  & {3*NB{iso_n}};
        assign busy  = e_busy  & iso_n;
        assign fault = (e_fault & iso_n) | late | ctl_fault;

        wire dom_busy = go || busy || (|pv) || (pwr_good && !ready) || (|dirty && pwr_good);
        wire req_on;
        ot_v41_stage_pg_sched #(.NSUB(NSUB), .TW(TW)) u_sched (
            .clk(clk), .rst_n(rst_n), .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap), .cfg_lead(pg_lead),
            .cfg_bet(pg_bet), .cfg_idle(pg_idle), .cfg_step(pg_step), .cfg_rst(pg_rst), .cfg_ack_to(pg_ack_to),
            .dom_busy(dom_busy), .sw_en(sw_en), .sw_ack(sw_ack), .iso_n(iso_n), .dom_rst_n(dom_rst_n),
            .clk_en(clk_en), .pwr_good(pwr_good), .fault(ctl_fault), .req_on(req_on));
        assign pg_ready = ready;
        assign pg_late  = late;
        assign pg_fault = ctl_fault;
    end
endmodule
