`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Stage power gating with the GATED STAGE CLOCK SPINE and proper clock-domain crossings (2026-10-04, successor of
// ot_v41_rom_pg_ao_sp, whose route R5 was rejected: the gated domain's busy reached the always-on scheduler as a
// single-cycle path across two separately balanced clock trees, -535 ps).
//
// One stage = K power-gated S81 elements behind ONE shared always-on controller (scheduler + W18 power controller +
// spine gate) on the always-on branch aon_clk.  Each element keeps its own always-on part (isolation clamps,
// configuration retention shadow, replay handshake, synchronizers) and its own domain-side interface.
//
// Every signal that crosses between the always-on branch (A, aon_clk) and the gated spine (D, the domain's clock)
// is either synchronised or a quasi-static bus qualified by a synchronised toggle:
//   D -> A  busy (registered in D), domain-out-of-reset, replay ack, ready ack: each a D flop, clamped by the
//           isolation enable, captured by a 2-flop synchroniser in A;
//   A -> D  domain reset: asserted asynchronously, released through a 2-flop reset synchroniser in D;
//           replay request: a toggle, 2-flop synchronised in D; its address/data are held stable from the toggle
//           until the ack returns (quasi-static, bounded by a datapath-only max delay);
//           ready: 2-flop synchronised in D (the element accepts host configuration and `go` only once D sees it);
//   isolation: combinational clamps on every domain output (outputs to the ports and the four D -> A flops above).
// Wake: spine on (first ring ack) -> rings -> domain reset with edges -> reset released in D -> iso release ->
// D-out-of-reset seen in A -> replay (toggle/ack per entry) -> ready -> ready seen in D -> ready ack seen in A.
// ---------------------------------------------------------------------------------------------------------------------

// ---- D side of one element: in the gated domain, on the element's clock ----
module ot_v41_rom_pg_dif #(
    parameter integer NB = 2
) (
    input  wire         e_clk,
    input  wire         arst_n,        // A: rst_n & dom_rst_n (asserts asynchronously)
    input  wire         cfg_v,         // host configuration port (direct when ready)
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         rq,            // A: replay request toggle
    input  wire [4:0]   rp_a,          // A: quasi-static replay address / data
    input  wire [47:0]  rp_d,
    input  wire         ready_a,       // A: replay done
    input  wire         e_busy,        // element status
    input  wire [NB-1:0] e_pv,
    output wire         e_rst_n,
    output wire         e_cfg_v,
    output wire [4:0]   e_cfg_a,
    output wire [47:0]  e_cfg_d,
    output wire         e_go,
    output wire         dbusy,         // to A (clamped there)
    output wire         dack,
    output wire         ack,
    output wire         rdy
);
    reg cdc_dr1, cdc_dr2;
    always @(posedge e_clk or negedge arst_n)
        if (!arst_n) begin cdc_dr1 <= 1'b0; cdc_dr2 <= 1'b0; end
        else begin cdc_dr1 <= 1'b1; cdc_dr2 <= cdc_dr1; end
    assign e_rst_n = cdc_dr2;
    reg cdc_rq1, rq2, rq3, cdc_rd1, rd2, busy_q;
    always @(posedge e_clk or negedge cdc_dr2)
        if (!cdc_dr2) begin cdc_rq1 <= 1'b0; rq2 <= 1'b0; rq3 <= 1'b0; cdc_rd1 <= 1'b0; rd2 <= 1'b0; busy_q <= 1'b0; end
        else begin
            cdc_rq1 <= rq; rq2 <= cdc_rq1; rq3 <= rq2;
            cdc_rd1 <= ready_a; rd2 <= cdc_rd1;
            busy_q <= e_busy | (|e_pv);
        end
    wire wr = rq2 ^ rq3;                   // one write per request toggle
    assign e_cfg_v = wr | (rd2 & cfg_v);
    assign e_cfg_a = wr ? rp_a : cfg_a;
    assign e_cfg_d = wr ? rp_d : cfg_d;
    assign e_go    = go & rd2;
    assign dbusy = busy_q;
    assign dack  = cdc_dr2;
    assign ack   = rq3;
    assign rdy   = rd2;
endmodule

// ---- A side of one element: isolation, retention shadow, replay handshake, synchronisers (aon_clk) ----
module ot_v41_rom_pg_eao #(
    parameter integer NSEG = 8,
    parameter integer NB = 2
) (
    input  wire         a_clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         pwr_good,      // shared controller
    input  wire         iso_n,
    // D side (raw domain signals)
    input  wire [NB-1:0]    e_pv,
    input  wire [32*NB-1:0] e_pval,
    input  wire [16*NB-1:0] e_prow,
    input  wire [5*NB-1:0]  e_pseg,
    input  wire [5*NB-1:0]  e_pnseg,
    input  wire [NB-1:0]    e_perr,
    input  wire [3*NB-1:0]  e_ppos,
    input  wire         e_busy,
    input  wire         e_fault,
    input  wire         dbusy,
    input  wire         dack,
    input  wire         ack,
    input  wire         rdy,
    output reg          rq,
    output reg  [4:0]   cdc_rp_a,
    output reg  [47:0]  cdc_rp_d,
    output reg          ready,
    // isolated outputs
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault_e,
    // to the shared controller
    output wire         el_busy,       // work in flight, restore pending
    output wire         el_ready       // ready, as seen back from D
);
    function integer ew(input integer a);
        ew = (a < NSEG) ? 43 : (a < 2 * NSEG) ? 23 : (a == 2 * NSEG) ? 20 : 16;
    endfunction
    localparam integer NA = (NB == 2) ? 3 * NSEG + 1 : 2 * NSEG + 1;
    localparam integer AW = 5;
    if (NSEG != 8) begin : g_bad
        initial $error("ot_v41_rom_pg_eao: the retention map is written for NSEG = 8");
    end
    wire host_wr = cfg_v && ({27'd0, cfg_a} < NA);
    // a local copy of the shared isolation enable per element (one flop; the shared enable fanning out to K x 130
    // clamps was -65 ps at SS in route A4).  One cycle later in both directions is safe: power-down switches the
    // rings off one cycle after isolating and their acks fall >= 2 cycles after that; release only follows the
    // domain's reset.
    reg iso_q;
    always @(posedge a_clk or negedge rst_n)
        if (!rst_n) iso_q <= 1'b0;
        else iso_q <= iso_n;
    // retention shadow: clocked only on a host write
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
    reg [NA-1:0] valid, dirty;
    reg [AW-1:0] ridx; reg rhit;
    integer k;
    always @* begin
        ridx = {AW{1'b0}}; rhit = 1'b0;
        for (k = NA - 1; k >= 0; k = k - 1) if (dirty[k]) begin ridx = k[AW-1:0]; rhit = 1'b1; end
    end
    // synchronisers of the clamped domain flops
    reg cdc_bs1, bs2, cdc_rr1, rr2, cdc_ak1, ak2, cdc_ra1, ra2;
    reg pg_q, infl;
    // the priority select is registered (dirty -> 25:1 shadow mux -> replay register was -44 ps at SS in route A4);
    // a stale selection is harmless: the next request waits for the previous ack (>= 6 cycles)
    reg [AW-1:0] ridx_q; reg rhit_q, sel_v;
    wire issue = pwr_good && rr2 && sel_v && rhit_q && rhit && !infl;
    // the element-side state runs while the domain is up (and on host writes / the power-loss edge); asleep, its
    // clock gate is closed and it costs leakage only
    wire ao_clk;
    ot_hdc_cg u_ao_cg (.clk(a_clk), .en(cfg_v | pwr_good | pg_q | !rst_n), .gclk(ao_clk));
    always @(posedge ao_clk or negedge rst_n)
        if (!rst_n) begin
            valid <= {NA{1'b0}}; dirty <= {NA{1'b0}}; ready <= 1'b0; pg_q <= 1'b0; rq <= 1'b0; infl <= 1'b0;
            cdc_bs1 <= 1'b0; bs2 <= 1'b0; cdc_rr1 <= 1'b0; rr2 <= 1'b0; cdc_ak1 <= 1'b0; ak2 <= 1'b0;
            cdc_ra1 <= 1'b0; ra2 <= 1'b0;
        end else begin
            pg_q <= pwr_good;
            cdc_bs1 <= dbusy & iso_q; bs2 <= cdc_bs1;
            cdc_rr1 <= dack & iso_q;  rr2 <= cdc_rr1;
            cdc_ak1 <= ack & iso_q;   ak2 <= cdc_ak1;
            cdc_ra1 <= rdy & iso_q;   ra2 <= cdc_ra1;
            if (pg_q && !pwr_good) begin                      // power lost: replay everything on the next wake
                ready <= 1'b0; dirty <= valid; rq <= 1'b0; infl <= 1'b0;
                cdc_bs1 <= 1'b0; bs2 <= 1'b0; cdc_rr1 <= 1'b0; rr2 <= 1'b0; cdc_ak1 <= 1'b0; ak2 <= 1'b0;
                cdc_ra1 <= 1'b0; ra2 <= 1'b0;
            end else begin
                if (infl && ak2 == rq) infl <= 1'b0;
                if (issue) begin dirty[ridx_q] <= 1'b0; rq <= ~rq; infl <= 1'b1; end
                if (host_wr) begin
                    valid[cfg_a] <= 1'b1;
                    // a write D may not apply directly (not yet ready there, or racing a replay) is replayed
                    if (!ra2 || infl || issue) dirty[cfg_a] <= 1'b1;
                end
                if (pwr_good && rr2 && !rhit && !rhit_q && !infl && !issue && !host_wr) ready <= 1'b1;
            end
        end
    always @(posedge ao_clk or negedge rst_n)
        if (!rst_n) begin ridx_q <= {AW{1'b0}}; rhit_q <= 1'b0; sel_v <= 1'b0; end
        else if (issue || infl) sel_v <= 1'b0;                  // a fresh selection after every ack
        else begin ridx_q <= ridx; rhit_q <= rhit; sel_v <= 1'b1; end
    always @(posedge ao_clk) if (issue) begin cdc_rp_a <= ridx_q; cdc_rp_d <= sh_q[ridx_q]; end
    assign el_busy  = bs2 | (pwr_good & !ra2) | (pwr_good & rhit) | infl;
    assign el_ready = ra2;
    // output isolation (clamp to 0)
    assign pv    = e_pv    & {NB{iso_q}};
    assign pval  = e_pval  & {32*NB{iso_q}};
    assign prow  = e_prow  & {16*NB{iso_q}};
    assign pseg  = e_pseg  & {5*NB{iso_q}};
    assign pnseg = e_pnseg & {5*NB{iso_q}};
    assign perr  = e_perr  & {NB{iso_q}};
    assign ppos  = e_ppos  & {3*NB{iso_q}};
    assign busy  = e_busy  & iso_q;
    assign fault_e = e_fault & iso_q;
endmodule

// ---- the shared stage controller: scheduler + W18 controller + spine gate (aon_clk; the spine gate on clk) ----
module ot_v41_rom_stage_pg_ctl_sp #(
    parameter integer NSUB = 4,
    parameter integer TW = 24
) (
    input  wire         clk,           // stage spine root
    input  wire         a_clk,         // always-on branch
    input  wire         rst_n,
    input  wire         pg_en,
    input  wire         sched_v,
    input  wire [TW-1:0] sched_gap,
    input  wire [TW-1:0] pg_lead,
    input  wire [TW-1:0] pg_bet,
    input  wire [7:0]   pg_idle,
    input  wire [15:0]  pg_step,
    input  wire [7:0]   pg_rst,
    input  wire [15:0]  pg_ack_to,
    input  wire         go,
    input  wire         dom_busy,
    input  wire         all_ready,
    output wire [NSUB-1:0] sw_en,
    input  wire [NSUB-1:0] sw_ack,
    output wire         s_clk,
    output wire         iso_n,
    output wire         dom_rst_n,
    output wire         pwr_good,
    output reg          late,
    output wire         ctl_fault
);
    wire clk_en, req_on;
    ot_v41_stage_pg_sched #(.NSUB(NSUB), .TW(TW)) u_sched (
        .clk(a_clk), .rst_n(rst_n), .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap), .cfg_lead(pg_lead),
        .cfg_bet(pg_bet), .cfg_idle(pg_idle), .cfg_step(pg_step), .cfg_rst(pg_rst), .cfg_ack_to(pg_ack_to),
        .dom_busy(go | dom_busy), .sw_en(sw_en), .sw_ack(sw_ack), .iso_n(iso_n), .dom_rst_n(dom_rst_n),
        .clk_en(clk_en), .pwr_good(pwr_good), .fault(ctl_fault), .req_on(req_on));
    // spine: on while a ring segment is powered and the ring is not being switched off
    reg spine_on;
    always @(posedge a_clk or negedge rst_n)
        if (!rst_n) spine_on <= 1'b0;
`ifdef PG_MUTANT_SPINE_LATE
        else spine_on <= pwr_good;
`else
        else spine_on <= (|sw_en) & (|sw_ack);
`endif
    ot_hdc_cg u_spine_cg (.clk(clk), .en(spine_on | !rst_n), .gclk(s_clk));
    always @(posedge a_clk or negedge rst_n)
        if (!rst_n) late <= 1'b0;
        else if (go && !all_ready) late <= 1'b1;
endmodule

// ---- the always-on block of a stage: the shared controller + K element AO parts (routed alone for its leakage) ----
module ot_v41_rom_stage_pg_ao_cdc #(
    parameter integer K = 1,
    parameter integer NSEG = 8,
    parameter integer NB = 2,
    parameter integer NSUB = 4,
    parameter integer TW = 24
) (
    input  wire         clk,
    input  wire         aon_clk,
    input  wire         rst_n,
    input  wire [K-1:0] cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
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
    output wire         s_clk,
    output wire         arst_n,        // to every domain interface
    // per element, D side in
    input  wire [K*NB-1:0]    e_pv,
    input  wire [K*32*NB-1:0] e_pval,
    input  wire [K*16*NB-1:0] e_prow,
    input  wire [K*5*NB-1:0]  e_pseg,
    input  wire [K*5*NB-1:0]  e_pnseg,
    input  wire [K*NB-1:0]    e_perr,
    input  wire [K*3*NB-1:0]  e_ppos,
    input  wire [K-1:0] e_busy,
    input  wire [K-1:0] e_fault,
    input  wire [K-1:0] dbusy,
    input  wire [K-1:0] dack,
    input  wire [K-1:0] ack,
    input  wire [K-1:0] rdy,
    output wire [K-1:0] rq,
    output wire [K*5-1:0]  rp_a,
    output wire [K*48-1:0] rp_d,
    output wire [K-1:0] ready_a,
    // isolated outputs
    output wire [K*NB-1:0]    pv,
    output wire [K*32*NB-1:0] pval,
    output wire [K*16*NB-1:0] prow,
    output wire [K*5*NB-1:0]  pseg,
    output wire [K*5*NB-1:0]  pnseg,
    output wire [K*NB-1:0]    perr,
    output wire [K*3*NB-1:0]  ppos,
    output wire [K-1:0] busy,
    output wire [K-1:0] fault,
    output wire         pg_ready,
    output wire         pg_late,
    output wire         pg_fault
);
    wire iso_n, dom_rst_n, pwr_good, late, ctl_fault;
    wire [K-1:0] el_busy, el_ready, fault_e;
    assign arst_n = rst_n & dom_rst_n;
    ot_v41_rom_stage_pg_ctl_sp #(.NSUB(NSUB), .TW(TW)) u_ctl (
        .clk(clk), .a_clk(aon_clk), .rst_n(rst_n), .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap),
        .pg_lead(pg_lead), .pg_bet(pg_bet), .pg_idle(pg_idle), .pg_step(pg_step), .pg_rst(pg_rst),
        .pg_ack_to(pg_ack_to), .go(go), .dom_busy(|el_busy), .all_ready(&el_ready), .sw_en(sw_en), .sw_ack(sw_ack),
        .s_clk(s_clk), .iso_n(iso_n), .dom_rst_n(dom_rst_n), .pwr_good(pwr_good), .late(late), .ctl_fault(ctl_fault));
    genvar g;
    for (g = 0; g < K; g = g + 1) begin : g_e
        ot_v41_rom_pg_eao #(.NSEG(NSEG), .NB(NB)) u_eao (
            .a_clk(aon_clk), .rst_n(rst_n), .cfg_v(cfg_v[g]), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
            .pwr_good(pwr_good), .iso_n(iso_n),
            .e_pv(e_pv[g*NB +: NB]), .e_pval(e_pval[g*32*NB +: 32*NB]), .e_prow(e_prow[g*16*NB +: 16*NB]),
            .e_pseg(e_pseg[g*5*NB +: 5*NB]), .e_pnseg(e_pnseg[g*5*NB +: 5*NB]), .e_perr(e_perr[g*NB +: NB]),
            .e_ppos(e_ppos[g*3*NB +: 3*NB]), .e_busy(e_busy[g]), .e_fault(e_fault[g]),
            .dbusy(dbusy[g]), .dack(dack[g]), .ack(ack[g]), .rdy(rdy[g]),
            .rq(rq[g]), .cdc_rp_a(rp_a[g*5 +: 5]), .cdc_rp_d(rp_d[g*48 +: 48]), .ready(ready_a[g]),
            .pv(pv[g*NB +: NB]), .pval(pval[g*32*NB +: 32*NB]), .prow(prow[g*16*NB +: 16*NB]),
            .pseg(pseg[g*5*NB +: 5*NB]), .pnseg(pnseg[g*5*NB +: 5*NB]), .perr(perr[g*NB +: NB]),
            .ppos(ppos[g*3*NB +: 3*NB]), .busy(busy[g]), .fault_e(fault_e[g]),
            .el_busy(el_busy[g]), .el_ready(el_ready[g]));
        assign fault[g] = fault_e[g] | late | ctl_fault;
    end
    assign pg_ready = &el_ready;
    assign pg_late  = late;
    assign pg_fault = ctl_fault;
endmodule

// ---- a stage of K power-gated S81 FP8/FP4 pair elements (BF16 0, NB 2) sharing the x broadcast and `go` ----
module ot_v41_rom_stage_q_pg_cdc_w10 #(
    // Component alternative to the enclosing root publication edge. Never
    // enable both without charging two edges and testing the actual consumer.
    parameter integer PUBLICATION_CAPTURE = 0,
    parameter integer K = 1,
    parameter integer NB = 2,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 1,
    parameter integer PP = 1,
    parameter integer NSUB = 4,
    parameter integer TW = 24,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         aon_clk,
    input  wire         rst_n,
    input  wire [K-1:0] cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire [K*NB-1:0]    pv,
    output wire [K*32*NB-1:0] pval,
    output wire [K*16*NB-1:0] prow,
    output wire [K*5*NB-1:0]  pseg,
    output wire [K*5*NB-1:0]  pnseg,
    output wire [K*NB-1:0]    perr,
    output wire [K*3*NB-1:0]  ppos,
    output wire [K-1:0] busy,
    output wire [K-1:0] fault,
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
    wire s_clk, arst_n;
    localparam integer PUBW = K * (63 * NB + 2);
    wire [K*NB-1:0] raw_pv, raw_perr;
    wire [K*32*NB-1:0] raw_pval;
    wire [K*16*NB-1:0] raw_prow;
    wire [K*5*NB-1:0] raw_pseg, raw_pnseg;
    wire [K*3*NB-1:0] raw_ppos;
    wire [K-1:0] raw_busy, raw_fault;
    wire [PUBW-1:0] raw_publication = {raw_pv,raw_pval,raw_prow,
      raw_pseg,raw_pnseg,raw_perr,raw_ppos,raw_busy,raw_fault};
    wire [PUBW-1:0] publication;
    generate if (PUBLICATION_CAPTURE != 0) begin : g_publication
        // Root clk stays alive when the element spine sleeps. Only coordinated
        // cold reset clears this copy; no warm fault/idle/ACK fabrications.
        reg [PUBW-1:0] held;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) held <= '0;
            else held <= raw_publication;
        assign publication = held;
    end else begin : g_original_publication
        assign publication = raw_publication;
    end endgenerate
    assign {pv,pval,prow,pseg,pnseg,perr,ppos,busy,fault} = publication;
    wire [K*NB-1:0] e_pv, e_perr; wire [K*32*NB-1:0] e_pval; wire [K*16*NB-1:0] e_prow;
    wire [K*5*NB-1:0] e_pseg, e_pnseg; wire [K*3*NB-1:0] e_ppos;
    wire [K-1:0] e_busy, e_fault, dbusy, dack, ack, rdy, rq, ready_a;
    wire [K*5-1:0] rp_a; wire [K*48-1:0] rp_d;
    ot_v41_rom_stage_pg_ao_cdc #(.K(K), .NB(NB), .NSUB(NSUB), .TW(TW)) u_ao (
        .clk(clk), .aon_clk(aon_clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
        .pg_en(pg_en), .sched_v(sched_v), .sched_gap(sched_gap), .pg_lead(pg_lead), .pg_bet(pg_bet),
        .pg_idle(pg_idle), .pg_step(pg_step), .pg_rst(pg_rst), .pg_ack_to(pg_ack_to), .sw_en(sw_en), .sw_ack(sw_ack),
        .s_clk(s_clk), .arst_n(arst_n), .e_pv(e_pv), .e_pval(e_pval), .e_prow(e_prow), .e_pseg(e_pseg),
        .e_pnseg(e_pnseg), .e_perr(e_perr), .e_ppos(e_ppos), .e_busy(e_busy), .e_fault(e_fault), .dbusy(dbusy),
        .dack(dack), .ack(ack), .rdy(rdy), .rq(rq), .rp_a(rp_a), .rp_d(rp_d), .ready_a(ready_a),
        .pv(raw_pv), .pval(raw_pval), .prow(raw_prow), .pseg(raw_pseg), .pnseg(raw_pnseg), .perr(raw_perr), .ppos(raw_ppos), .busy(raw_busy),
        .fault(raw_fault), .pg_ready(pg_ready), .pg_late(pg_late), .pg_fault(pg_fault));
    genvar g;
    for (g = 0; g < K; g = g + 1) begin : g_el
        wire e_rst_n, e_cfg_v, e_go; wire [4:0] e_cfg_a; wire [47:0] e_cfg_d;
        ot_v41_rom_pg_dif #(.NB(NB)) u_dif (
            .e_clk(s_clk), .arst_n(arst_n), .cfg_v(cfg_v[g]), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .rq(rq[g]),
            .rp_a(rp_a[g*5 +: 5]), .rp_d(rp_d[g*48 +: 48]), .ready_a(ready_a[g]), .e_busy(e_busy[g]),
            .e_pv(e_pv[g*NB +: NB]), .e_rst_n(e_rst_n), .e_cfg_v(e_cfg_v), .e_cfg_a(e_cfg_a), .e_cfg_d(e_cfg_d),
            .e_go(e_go), .dbusy(dbusy[g]), .dack(dack[g]), .ack(ack[g]), .rdy(rdy[g]));
        ot_v41_rom_elem_w10 #(.BF16(0), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP), .FRONT_PAR(0),
            .INSTANCE(INSTANCE)) u_elem (
            .clk(s_clk), .rst_n(e_rst_n), .cfg_v(e_cfg_v), .cfg_a(e_cfg_a), .cfg_d(e_cfg_d), .go(e_go), .go_bf(1'b0),
            .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1),
            .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(3'd0), .xb_v(1'b0), .xb_b(3'd0), .xb_sv(4'd0), .xb_u(32'd0),
            .xb_d(1024'd0), .pv(e_pv[g*NB +: NB]), .pval(e_pval[g*32*NB +: 32*NB]), .prow(e_prow[g*16*NB +: 16*NB]),
            .pseg(e_pseg[g*5*NB +: 5*NB]), .pnseg(e_pnseg[g*5*NB +: 5*NB]), .perr(e_perr[g*NB +: NB]),
            .ppos(e_ppos[g*3*NB +: 3*NB]), .busy(e_busy[g]), .fault(e_fault[g]));
    end
endmodule
