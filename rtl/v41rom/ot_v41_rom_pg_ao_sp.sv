`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rom_pg_ao_sp -- ot_v41_rom_pg_ao (the ALWAYS-ON side of one power-gated V4.1 ROM element domain) plus the
// GATED STAGE CLOCK SPINE (2026-10-04, opt-in SPINE = 1; SPINE = 0 is ot_v41_rom_pg_ao with aon_clk unused).
//
// Measured on ot_v41_rom_pg_ao (route R3, results/rtl/rom_stage_power_gating_20261004): a sleeping domain still burns
// 0.889 mW per element in its clock tree, because the always-on sinks (scheduler, controller, AO clock gates) hang on
// the same clock net as the domain and clock-tree synthesis delay-balances that branch against the domain's deep
// tree; those balancing buffers toggle while the domain is off (residual 35.4% of clock-gated idle).
//
// SPINE = 1 splits the element's clock in two, as the die does:
//   * aon_clk  -- the always-on island's own branch (tapped before the spine gate; in the die the hub AO island,
//                 one controller per stage): scheduler + W18 controller, retention shadow ICG, AO state ICG;
//   * clk      -- the stage clock spine root; it reaches the domain only through u_spine_cg, whose enable is
//                 spine_on, a register on aon_clk that is 1 while a header-ring segment acknowledges (is powered)
//                 and the ring is not being switched off (some sw_en still high).  Wake order: sw_en[0] -> first ring ack -> spine_on (next cycle) -> remaining segments
//                 ((NSUB-1) x cfg_step cycles) -> domain reset with clock edges (cfg_rst) -> isolation release ->
//                 retention replay -> ready.  The domain is held in reset and isolated the whole time the spine
//                 starts, so the first (possibly partial) edges reach only reset flops.
//                 Sleep order: clock enable off -> isolate -> reset + switches off (spine_on = 0 the next cycle,
//                 before the ring's acks fall) -> acks low.  So the spine runs only while the domain is powered and
//                 stops while the domain is isolated, in reset and still powered.
//   The spine gate is the platform latch ICG (glitch-free); its enable is a flop, so no combinational port path.
// ---------------------------------------------------------------------------
module ot_v41_rom_pg_ao_sp #(
    parameter integer NSEG = 8,
    parameter integer NB = 2,
    parameter integer NSUB = 4,
    parameter integer TW = 24,
    parameter integer DOM_CG = 0,    // 1: a domain clock gate in series with the element's own (adds clock insertion delay)
    parameter integer SPINE = 0      // 1: gated stage clock spine (aon_clk feeds the always-on side; clk is the spine)
) (
    input  wire         clk,
    input  wire         aon_clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    // element side
    output wire         e_clk,
    output wire         e_rst_n,
    output wire         e_cfg_v,
    output wire [4:0]   e_cfg_a,
    output wire [47:0]  e_cfg_d,
    output wire         e_go,
    input  wire [NB-1:0]    e_pv,
    input  wire [32*NB-1:0] e_pval,
    input  wire [16*NB-1:0] e_prow,
    input  wire [5*NB-1:0]  e_pseg,
    input  wire [5*NB-1:0]  e_pnseg,
    input  wire [NB-1:0]    e_perr,
    input  wire [3*NB-1:0]  e_ppos,
    input  wire         e_busy,
    input  wire         e_fault,
    // isolated outputs
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault,
    // power control
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
    // retained width of configuration entry a: a < NSEG segment [42:0]; NSEG <= a < 2NSEG class [22:0];
    // a = 2NSEG [19:0]; 2NSEG < a <= 3NSEG (NB = 2) second-macro row [15:0]
    function integer ew(input integer a);
        ew = (a < NSEG) ? 43 : (a < 2 * NSEG) ? 23 : (a == 2 * NSEG) ? 20 : 16;
    endfunction
    // ------------- retention shadow: the decoded configuration bits, per address class -------------
    // a < NSEG: segment [42:0]; NSEG <= a < 2NSEG: class [19+SW-1:0] with bit 22 (BF16 family);
    // a = 2NSEG: [19:0]; 2NSEG < a <= 3NSEG (NB = 2): second-macro row [15:0]
    localparam integer NA = (NB == 2) ? 3 * NSEG + 1 : 2 * NSEG + 1;
    localparam integer AW = 5;
    if (NSEG != 8) begin : g_bad
        initial $error("ot_v41_rom_pg_ao: the retention map is written for NSEG = 8");
    end

    wire iso_n, dom_rst_n, clk_en, pwr_good, ctl_fault;
    reg  ready, late;
    reg  [NA-1:0] valid, dirty;
    wire host_wr = cfg_v && ({27'd0, cfg_a} < NA);

    // the shadow is clocked only on a host write (AO ICG); idle, it costs leakage only
    wire a_clk;                 // the always-on side's clock: its own branch with SPINE = 1
    if (SPINE != 0) begin : g_aclk
        assign a_clk = aon_clk;
    end else begin : g_nclk
        assign a_clk = clk;
    end
    wire sh_clk;
    ot_hdc_cg u_sh_cg (.clk(a_clk), .en(cfg_v | !rst_n), .gclk(sh_clk));
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
    // the replay write is registered (dirty -> priority select -> 25:1 shadow mux would otherwise reach the element's
    // configuration port combinationally: -403 ps at 0.833 ns WC in the AO-only route A1)
    // the element-side state (valid / dirty / ready / late / replay) changes only on a host write, a `go`, a power
    // transition or while restoring: it runs on its own clock gate, so a sleeping (or idle, ready) domain's AO side
    // costs leakage and one ICG clock pin (route R1 measured ~0.13 mW of free-running AO state + its clock tree)
    wire ao_clk;
    reg  pg_q;
    wire ao_en = cfg_v | go | (pwr_good ^ pg_q) | (pwr_good & !ready) | rp_v;
    ot_hdc_cg u_ao_cg (.clk(a_clk), .en(ao_en | !rst_n), .gclk(ao_clk));
    reg            rp_v;
    reg [AW-1:0]   rp_a;
    reg [47:0]     rp_d;
    always @(posedge ao_clk or negedge rst_n)
        if (!rst_n) rp_v <= 1'b0;
        else rp_v <= rst_wr;
    always @(posedge ao_clk) if (rst_wr) begin rp_a <= ridx; rp_d <= sh_q[ridx]; end
    always @(posedge ao_clk or negedge rst_n)
        if (!rst_n) begin valid <= {NA{1'b0}}; dirty <= {NA{1'b0}}; ready <= 1'b0; late <= 1'b0; pg_q <= 1'b0; end
        else begin
            pg_q <= pwr_good;
            if (pg_q && !pwr_good) begin ready <= 1'b0; dirty <= valid; end      // power lost: replay all
            else begin
                if (rst_wr) dirty[ridx] <= 1'b0;
                if (host_wr) begin
                    valid[cfg_a] <= 1'b1;
                    if (!ready) dirty[cfg_a] <= 1'b1;                             // replayed after wake
                end
                if (pwr_good && !ready && !rhit && !rp_v && !(host_wr)) ready <= 1'b1;
            end
            if (go && !ready) late <= 1'b1;
        end

    // configuration port of the element: the host while ready, the replay while restoring
    assign e_cfg_v = ready ? cfg_v : rp_v;
    assign e_cfg_a = ready ? cfg_a : rp_a;
    assign e_cfg_d = ready ? cfg_d : rp_d;
    assign e_go    = go && ready;
    assign e_rst_n = rst_n && dom_rst_n;
    // DOM_CG = 0 (default): the AO clock reaches the domain ungated.  An off domain's clock tree is unpowered, the
    // stage clock spine gate stops the clock wire to an idle stage, and the element's own ICG (enable ORs !rst_n)
    // runs its clock through the wake reset; a series gate only added ~200 ps of insertion delay (route R1).
    wire s_clk;                 // the domain's clock: the spine through its gate (SPINE = 1), else clk
    if (SPINE != 0) begin : g_spine
        reg spine_on;
        always @(posedge a_clk or negedge rst_n)
            if (!rst_n) spine_on <= 1'b0;
`ifdef PG_MUTANT_SPINE_LATE
            else spine_on <= pwr_good;             // mutant: the spine starts only at isolation release
`else
            else spine_on <= (|sw_en) & (|sw_ack); // a segment powered and the ring not being switched off
`endif
        ot_hdc_cg u_spine_cg (.clk(clk), .en(spine_on | !rst_n), .gclk(s_clk));
    end else begin : g_nspine
        assign s_clk = clk;
    end
    if (DOM_CG != 0) begin : g_dcg
        ot_hdc_cg u_dom_cg (.clk(s_clk), .en(clk_en | !rst_n), .gclk(e_clk));
    end else begin : g_ndcg
        assign e_clk = s_clk;
    end

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

    wire dom_busy = go || busy || (|pv) || (pwr_good && !ready) || (|dirty && pwr_good) || rp_v;
    wire req_on;
    ot_v41_stage_pg_sched #(.NSUB(NSUB), .TW(TW)) u_sched (
        .clk(a_clk), .rst_n(rst_n), .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap), .cfg_lead(pg_lead),
        .cfg_bet(pg_bet), .cfg_idle(pg_idle), .cfg_step(pg_step), .cfg_rst(pg_rst), .cfg_ack_to(pg_ack_to),
        .dom_busy(dom_busy), .sw_en(sw_en), .sw_ack(sw_ack), .iso_n(iso_n), .dom_rst_n(dom_rst_n),
        .clk_en(clk_en), .pwr_good(pwr_good), .fault(ctl_fault), .req_on(req_on));
    assign pg_ready = ready;
    assign pg_late  = late;
    assign pg_fault = ctl_fault;
endmodule
