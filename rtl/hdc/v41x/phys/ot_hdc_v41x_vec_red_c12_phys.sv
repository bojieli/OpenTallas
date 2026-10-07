`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PHYSICAL VEHICLES (HBM SU 1.2 GHz): the hardened pieces of the N = 1,024 stream-unit reducer
// (rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv) at the 1.2 GHz build (MLAT 6 / ALAT 6, RPAD 1, RSL 2, RTAP 1, ROUT 1).
// ot_hdc_v41x_vec_red #(.N(1024), .SL(64)) IS sixteen ot_hdc_v41x_vred_slice and one ot_hdc_v41x_vred_top, so
// these two fixed-parameter tops are the reducer's only distinct pieces:
//   ot_hdc_v41x_vred_slice64_c12  64 lanes: IN, square, padding (+ RPAD register), the 7-add chunk chains of
//                                 8 chunks and tree levels 1..3; every port register-direct (IN registers in,
//                                 the RSL slice-boundary registers out)
//   ot_hdc_v41x_vred_top1024_c12  the tag / valid pipeline, tree levels 4..7 on the slices' registered words,
//                                 the level taps (+ RTAP register), TIME (LV 6) and OUT (+ ROUT register); RSL 2: the slices' words
//                                 are registered again on entry, busy is one register, so every port is
//                                 register-direct (the slice keeps its single RSL register)
// Sources: this file, ot_hdc_v41x_vec_red_c12.sv, ot_hdc_fastfp_lat_c12.sv, ot_hdc_fp32_f12.sv,
// v41x/ot_dsrom_su_add6.sv, ot_hdc_fastfp.sv, ot_hdc_fp32_mul_lat.sv, ot_hdc_fp32_add_lat.sv, ot_hdc_prefix.sv,
// ot_hdc_delay.sv, ot_hdc_sfu.sv (ot_hdc_vline).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vred_slice64_c12 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire [2047:0] x_in,
    input  wire [63:0]   live_in,
    input  wire          mx_in,
    input  wire          sq_in,
    output wire [479:0]  lv_o,
    output wire          fault_o
);
    ot_hdc_v41x_vred_slice #(.SL(64), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(1)) u (.*);
endmodule

module ot_hdc_v41x_vred_top1024_c12 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
    ot_hdc_v41x_vred_top #(.N(1024), .LV(6), .AW(24), .MW(9), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(2), .RTAP(1),
                           .ROUT(1), .SL(64)) u (.*);
endmodule

// the same top with one ROUT bundle copy per 2 slot(s) (ROGS 2): the OUT select fanout of each copy is 2/4 of the above
module ot_hdc_v41x_vred_top1024_c12_g2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
    ot_hdc_v41x_vred_top #(.N(1024), .LV(6), .AW(24), .MW(9), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(2), .RTAP(1),
                           .ROUT(1), .ROGS(2), .SL(64)) u (.*);
endmodule

// the same top with one ROUT bundle copy per 1 slot(s) (ROGS 1): the OUT select fanout of each copy is 1/4 of the above
module ot_hdc_v41x_vred_top1024_c12_g1 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
    ot_hdc_v41x_vred_top #(.N(1024), .LV(6), .AW(24), .MW(9), .MLAT(6), .ALAT(6), .RPAD(1), .RSL(2), .RTAP(1),
                           .ROUT(1), .ROGS(1), .SL(64)) u (.*);
endmodule

// MARGIN VERSION (OWNER RULE 2026-10-06: SS >= +40 at 833.333 when routed at 770): every reducer op registers its
// operands (ROPI 1: op latency ALAT + 1 = 7), and the top registers the OUT address adds / BF16 roundings once more
// (ROUT 2), one OUT bundle copy per 2 slots (ROGS 2).  Depth: D_RED + 7 + 1, D_RSTEP + 1.
// The top also keeps copies of the tap-hit sources and the tap tag (RKC 1, no added cycle): tm_u30_h15 routed at 770
// signed off SS +16.36 / FF +7.88 at 833.333 on those two fanout classes.
module ot_hdc_v41x_vred_slice64_c12m (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire [2047:0] x_in,
    input  wire [63:0]   live_in,
    input  wire          mx_in,
    input  wire          sq_in,
    output wire [479:0]  lv_o,
    output wire          fault_o
);
    ot_hdc_v41x_vred_slice #(.SL(64), .MLAT(6), .ALAT(7), .RPAD(1), .RSL(1), .ROPI(1)) u (.*);
endmodule

module ot_hdc_v41x_vred_top1024_c12m (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
    ot_hdc_v41x_vred_top #(.N(1024), .LV(6), .AW(24), .MW(9), .MLAT(6), .ALAT(7), .RPAD(1), .RSL(2), .RTAP(1),
                           .ROUT(2), .ROGS(2), .SL(64), .ROPI(1), .RKC(1)) u (.*);
endmodule

// ---------------------------------------------------------------------------
// SAFE pin-register versions (owner SAFE directive 2026-10-06; default off: nothing instantiates them but the
// physical vehicles and the lockstep bench).  Every port gets a kept flop at the pin (ot_hdc_v41x_vred_pinreg is a
// kept module, placed by the flow next to its pin), so no die-wire path reaches the reducer logic.  Cost, transaction
// level (same results, order and faults; latency only): slice in +1, slice out +1, top lv_in +1, top out +1;
// the top's tag / valid inputs carry the same +3 so the slices' words still meet their tags = +4 cycles a reduction.
// busy: OR of the in-flight tag-stage valids and the core's busy, launched from a pin flop (never low while a
// reduction is in the pin stages).
// ---------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_hdc_v41x_vred_pinreg #(parameter integer W = 1, parameter integer D = 1, parameter integer RST = 0) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    genvar i;
    wire [W-1:0] s [0:D];
    assign s[0] = d;
    for (i = 0; i < D; i = i + 1) begin : g_s
        (* keep *) reg [W-1:0] r;
        if (RST) begin : g_r
            always @(posedge clk or negedge rst_n) if (!rst_n) r <= {W{1'b0}}; else r <= s[i];
        end else begin : g_n
            always @(posedge clk) r <= s[i];
        end
        assign s[i+1] = r;
    end
    assign q = s[D];
endmodule

module ot_hdc_v41x_vred_slice64_c12s (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire [2047:0] x_in,
    input  wire [63:0]   live_in,
    input  wire          mx_in,
    input  wire          sq_in,
    output wire [479:0]  lv_o,
    output wire          fault_o
);
    wire p_v, p_mx, p_sq; wire [2047:0] p_x; wire [63:0] p_live; wire [479:0] c_lv; wire c_f;
    ot_hdc_v41x_vred_pinreg #(.W(1), .D(1), .RST(1)) u_pv (.clk(clk), .rst_n(rst_n), .d(v_in), .q(p_v));
    ot_hdc_v41x_vred_pinreg #(.W(2114), .D(1)) u_pd (.clk(clk), .rst_n(rst_n), .d({x_in, live_in, mx_in, sq_in}),
        .q({p_x, p_live, p_mx, p_sq}));
    ot_hdc_v41x_vred_slice64_c12m u (.clk(clk), .rst_n(rst_n), .v_in(p_v), .x_in(p_x), .live_in(p_live), .mx_in(p_mx),
        .sq_in(p_sq), .lv_o(c_lv), .fault_o(c_f));
    ot_hdc_v41x_vred_pinreg #(.W(480), .D(1)) u_po (.clk(clk), .rst_n(rst_n), .d(c_lv), .q(lv_o));
    ot_hdc_v41x_vred_pinreg #(.W(1), .D(1), .RST(1)) u_pf (.clk(clk), .rst_n(rst_n), .d(c_f), .q(fault_o));
endmodule

module ot_hdc_v41x_vred_top1024_c12s (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
`ifdef OT_NEG_RED_PREG
    localparam integer TD = 2;           // negative control: tags one stage short of the slice words
`else
    localparam integer TD = 3;           // slice in + slice out + top lv_in
`endif
    // tag / valid: TD kept stages (the first at the pins), each stage's valid kept for busy
    wire [TD:0] tv;
    assign tv[0] = v_in;
    genvar k;
    for (k = 0; k < TD; k = k + 1) begin : g_tv
        ot_hdc_v41x_vred_pinreg #(.W(1), .D(1), .RST(1)) u (.clk(clk), .rst_n(rst_n), .d(tv[k]), .q(tv[k+1]));
    end
    wire p_mx, p_span, p_last, p_rnd; wire [3:0] p_lt; wire [2:0] p_l; wire [7:0] p_nres; wire [23:0] p_rbase;
    wire [4:0] p_rsh; wire [8:0] p_meta; wire [7679:0] p_lv; wire [15:0] p_sf;
    ot_hdc_v41x_vred_pinreg #(.W(57), .D(TD)) u_pt (.clk(clk), .rst_n(rst_n),
        .d({mx_in, lt_in, span_in, l_in, last_in, nres_in, rnd_in, rbase_in, rsh_in, meta_in}),
        .q({p_mx, p_lt, p_span, p_l, p_last, p_nres, p_rnd, p_rbase, p_rsh, p_meta}));
    ot_hdc_v41x_vred_pinreg #(.W(7680), .D(1)) u_pl (.clk(clk), .rst_n(rst_n), .d(lv_in), .q(p_lv));
    ot_hdc_v41x_vred_pinreg #(.W(16), .D(1), .RST(1)) u_ps (.clk(clk), .rst_n(rst_n), .d(sfault_in), .q(p_sf));
    wire [127:0] c_we; wire [3071:0] c_addr; wire [4095:0] c_data; wire [8:0] c_meta; wire c_ev, c_busy, c_fault;
    ot_hdc_v41x_vred_top1024_c12m u (.clk(clk), .rst_n(rst_n), .v_in(tv[TD]), .mx_in(p_mx), .lt_in(p_lt),
        .span_in(p_span), .l_in(p_l), .last_in(p_last), .nres_in(p_nres), .rnd_in(p_rnd), .rbase_in(p_rbase),
        .rsh_in(p_rsh), .meta_in(p_meta), .lv_in(p_lv), .sfault_in(p_sf), .o_we(c_we), .o_addr(c_addr),
        .o_data(c_data), .o_meta(c_meta), .o_ev(c_ev), .busy(c_busy), .fault(c_fault));
    ot_hdc_v41x_vred_pinreg #(.W(7177), .D(1)) u_po (.clk(clk), .rst_n(rst_n), .d({c_addr, c_data, c_meta}),
        .q({o_addr, o_data, o_meta}));
    ot_hdc_v41x_vred_pinreg #(.W(131), .D(1), .RST(1)) u_pv (.clk(clk), .rst_n(rst_n),
        .d({c_we, c_ev, c_fault, c_busy | (|tv[TD:1])}), .q({o_we, o_ev, fault, busy}));
endmodule

// ---------------------------------------------------------------------------
// HALF-RATE versions (Claude:hbm-su 2026-10-07, owner SAFE backstop "half-rate"; default off: only the physical
// vehicles and tb_red_half instantiate them).  The SAFE structure (a kept flop at every pin) with the pin flops AND the
// unchanged c12m core on the fast clock gated every other cycle (en flop toggling, latched while the clock is low,
// ANDed with it: the HBM loader half-rate template).  Every gclk -> gclk path (pin -> core, core -> core, core -> out
// pin, AND the die hop slice lv_o -> top lv_in, both sides gated in the same phase) gets two fast periods (SDC
// physical/hbm_su_c12/red_half_mcp.sdc: multicycle setup 2 / hold 1).  Single-cycle paths left: die -> input pin flop
// (the sender launches in the cycle that ends on a gated edge) and the event/status pin flops (fast, at the pins).
// INTERFACE CONTRACT (credit with a fixed 2-cycle return): the SU controller asserts v_in only in a fast cycle with
// ph = 1 (ph = the en flop; both blocks and the controller leave reset together), i.e. at most one reduction beat every
// two cycles, at a fixed phase.  A beat offered in a ph = 0 cycle is a contract violation and raises fault.
// Results: same values, order and faults (transaction level); o_we / o_ev pulse for one fast cycle with the data
// held stable around it.  Latency 2 x (core + 4) + 1 fast cycles (tb_red_half measures it).
// ---------------------------------------------------------------------------
// ot_hdc_v41x_vred_hgate: in rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv (shared with the RHALF reducer)

module ot_hdc_v41x_vred_slice64_c12h (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire [2047:0] x_in,
    input  wire [63:0]   live_in,
    input  wire          mx_in,
    input  wire          sq_in,
    output wire [479:0]  lv_o,
    output wire          fault_o
);
    wire gclk, ph;
    ot_hdc_v41x_vred_hgate u_g (.clk(clk), .rst_n(rst_n), .gclk(gclk), .ph(ph));
    wire p_v, p_mx, p_sq; wire [2047:0] p_x; wire [63:0] p_live; wire [479:0] c_lv; wire c_f, p_f;
    ot_hdc_v41x_vred_pinreg #(.W(1), .D(1), .RST(1)) u_pv (.clk(gclk), .rst_n(rst_n), .d(v_in), .q(p_v));
    ot_hdc_v41x_vred_pinreg #(.W(2114), .D(1)) u_pd (.clk(gclk), .rst_n(rst_n), .d({x_in, live_in, mx_in, sq_in}),
        .q({p_x, p_live, p_mx, p_sq}));
    ot_hdc_v41x_vred_slice64_c12m u (.clk(gclk), .rst_n(rst_n), .v_in(p_v), .x_in(p_x), .live_in(p_live), .mx_in(p_mx),
        .sq_in(p_sq), .lv_o(c_lv), .fault_o(c_f));
    ot_hdc_v41x_vred_pinreg #(.W(480), .D(1)) u_po (.clk(gclk), .rst_n(rst_n), .d(c_lv), .q(lv_o));
    // contract check (fast): a beat offered in a ph = 0 cycle would be dropped -> fault (sticky to the next gated edge)
    reg viol;
    always @(posedge clk or negedge rst_n) if (!rst_n) viol <= 1'b0; else viol <= (v_in & ~ph) | (viol & ~ph);
    ot_hdc_v41x_vred_pinreg #(.W(1), .D(1), .RST(1)) u_pf (.clk(gclk), .rst_n(rst_n), .d(c_f | viol), .q(fault_o));
endmodule

module ot_hdc_v41x_vred_top1024_c12h (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v_in,
    input  wire          mx_in,
    input  wire [3:0]    lt_in,
    input  wire          span_in,
    input  wire [2:0]    l_in,
    input  wire          last_in,
    input  wire [7:0]    nres_in,
    input  wire          rnd_in,
    input  wire [23:0]   rbase_in,
    input  wire [4:0]    rsh_in,
    input  wire [8:0]    meta_in,
    input  wire [7679:0] lv_in,
    input  wire [15:0]   sfault_in,
    output wire [127:0]  o_we,
    output wire [3071:0] o_addr,
    output wire [4095:0] o_data,
    output wire [8:0]    o_meta,
    output wire          o_ev,
    output wire          busy,
    output wire          fault
);
`ifdef OT_NEG_RED_HALF
    localparam integer TD = 2;           // negative control: tags one slow stage short of the slice words
`else
    localparam integer TD = 3;           // slice in + slice out + top lv_in (slow stages)
`endif
    wire gclk, ph;
    ot_hdc_v41x_vred_hgate u_g (.clk(clk), .rst_n(rst_n), .gclk(gclk), .ph(ph));
    wire [TD:0] tv;
    assign tv[0] = v_in;
    genvar k;
    for (k = 0; k < TD; k = k + 1) begin : g_tv
        ot_hdc_v41x_vred_pinreg #(.W(1), .D(1), .RST(1)) u (.clk(gclk), .rst_n(rst_n), .d(tv[k]), .q(tv[k+1]));
    end
    wire p_mx, p_span, p_last, p_rnd; wire [3:0] p_lt; wire [2:0] p_l; wire [7:0] p_nres; wire [23:0] p_rbase;
    wire [4:0] p_rsh; wire [8:0] p_meta; wire [7679:0] p_lv; wire [15:0] p_sf;
    ot_hdc_v41x_vred_pinreg #(.W(57), .D(TD)) u_pt (.clk(gclk), .rst_n(rst_n),
        .d({mx_in, lt_in, span_in, l_in, last_in, nres_in, rnd_in, rbase_in, rsh_in, meta_in}),
        .q({p_mx, p_lt, p_span, p_l, p_last, p_nres, p_rnd, p_rbase, p_rsh, p_meta}));
    ot_hdc_v41x_vred_pinreg #(.W(7680), .D(1)) u_pl (.clk(gclk), .rst_n(rst_n), .d(lv_in), .q(p_lv));
    ot_hdc_v41x_vred_pinreg #(.W(16), .D(1), .RST(1)) u_ps (.clk(gclk), .rst_n(rst_n), .d(sfault_in), .q(p_sf));
    wire [127:0] c_we; wire [3071:0] c_addr; wire [4095:0] c_data; wire [8:0] c_meta; wire c_ev, c_busy, c_fault;
    ot_hdc_v41x_vred_top1024_c12m u (.clk(gclk), .rst_n(rst_n), .v_in(tv[TD]), .mx_in(p_mx), .lt_in(p_lt),
        .span_in(p_span), .l_in(p_l), .last_in(p_last), .nres_in(p_nres), .rnd_in(p_rnd), .rbase_in(p_rbase),
        .rsh_in(p_rsh), .meta_in(p_meta), .lv_in(p_lv), .sfault_in(p_sf), .o_we(c_we), .o_addr(c_addr),
        .o_data(c_data), .o_meta(c_meta), .o_ev(c_ev), .busy(c_busy), .fault(c_fault));
    // data pins: slow flops (held over both fast cycles of the slow cycle the event pulses in)
    ot_hdc_v41x_vred_pinreg #(.W(7177), .D(1)) u_po (.clk(gclk), .rst_n(rst_n), .d({c_addr, c_data, c_meta}),
        .q({o_addr, o_data, o_meta}));
    wire [127:0] g_we; wire g_ev, g_fault, g_busy;
    ot_hdc_v41x_vred_pinreg #(.W(131), .D(1), .RST(1)) u_pg (.clk(gclk), .rst_n(rst_n),
        .d({c_we, c_ev, c_fault, c_busy | (|tv[TD:1])}), .q({g_we, g_ev, g_fault, g_busy}));
    // event / status pins: fast flops; an event pulses once, in the second fast cycle of its slow cycle (ph = 1)
    reg viol;
    always @(posedge clk or negedge rst_n) if (!rst_n) viol <= 1'b0; else viol <= v_in & ~ph;
    ot_hdc_v41x_vred_pinreg #(.W(131), .D(1), .RST(1)) u_pv (.clk(clk), .rst_n(rst_n),
        .d({g_we & {128{~ph}}, g_ev & ~ph, (g_fault & ~ph) | viol, g_busy | (|tv[TD:0])}), .q({o_we, o_ev, fault, busy}));
endmodule
