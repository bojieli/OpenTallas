`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_stage_pg_sched -- static-schedule pre-wake for one power-gated ROM stage domain (always-on island).
//
// One per gated domain (a die region of many elements share it; the single-element vehicle instantiates one).
// The stage's static token schedule is known: whenever the hub issues a token to the stage it also announces
// the number of cycles until the NEXT arrival (`sched_v`, `sched_gap`; AR batch 1: the token period; MTP / the
// wavefront: the position spacing).  The countdown requests power `lead + bet` cycles before that arrival
// (`lead` >= switch-ring wake + domain reset + retention restore; `bet` = break-even margin) and releases it
// once the domain has been idle `idle_min` consecutive cycles and the next arrival is farther than that.
//
// The power sequence itself (staggered header-ring enable, reset, isolation release, power-down order, dead
// ring fault) is the W18 controller ot_chip_v41_pg_ctrl, instantiated unchanged.
//
// pg_en = 0 holds the domain powered (req_on = 1): gating is opt-in at run time as well as by parameter.
// ---------------------------------------------------------------------------
module ot_v41_stage_pg_sched #(
    parameter integer NSUB = 4,           // header-ring segments of the domain
    parameter integer TW   = 24           // schedule counter width (AR period at 1.2 GHz is ~486k cycles)
) (
    input  wire            clk,           // always-on clock
    input  wire            rst_n,         // always-on reset
    input  wire            pg_en,
    input  wire            sched_v,       // the hub announces the next arrival
    input  wire [TW-1:0]   sched_gap,     // cycles from now until that arrival
    input  wire [TW-1:0]   cfg_lead,      // wake lead: ring wake + reset + restore
    input  wire [TW-1:0]   cfg_bet,       // break-even margin: never sleep for a shorter gap
    input  wire [7:0]      cfg_idle,      // idle cycles before the domain may sleep (>= the element drain)
    input  wire [15:0]     cfg_step,
    input  wire [7:0]      cfg_rst,
    input  wire [15:0]     cfg_ack_to,
    input  wire            dom_busy,      // the domain has work in flight (element busy, partials, restore)
    output wire [NSUB-1:0] sw_en,
    input  wire [NSUB-1:0] sw_ack,
    output wire            iso_n,
    output wire            dom_rst_n,
    output wire            clk_en,
    output wire            pwr_good,
    output wire            fault,
    output wire            req_on
);
    reg [TW-1:0] cnt;
    reg          cnt_v;
    reg [7:0]    idle;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cnt <= {TW{1'b0}}; cnt_v <= 1'b0; idle <= 8'd0; end
        else begin
            if (sched_v) begin cnt <= sched_gap; cnt_v <= 1'b1; end
            else if (cnt_v && cnt != {TW{1'b0}}) cnt <= cnt - 1'b1;
            else cnt_v <= 1'b0;                               // the announced arrival has passed
            if (dom_busy) idle <= 8'd0;
            else if (idle != 8'hff) idle <= idle + 8'd1;
        end
    reg  [TW:0] th;                                           // lead + bet, registered (static configuration)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) th <= {(TW+1){1'b0}};
        else th <= {1'b0, cfg_lead} + {1'b0, cfg_bet};
    wire        near = cnt_v && ({1'b0, cnt} <= th);
    wire        idle_long = !dom_busy && idle >= cfg_idle;
    assign req_on = !pg_en || !idle_long || near;

    ot_chip_v41_pg_ctrl #(.NSUB(NSUB), .CW(16)) u_pg (
        .clk(clk), .rst_n(rst_n), .req_on(req_on), .cfg_step(cfg_step), .cfg_rst(cfg_rst),
        .cfg_ack_to(cfg_ack_to), .sw_en(sw_en), .sw_ack(sw_ack), .iso_n(iso_n), .dom_rst_n(dom_rst_n),
        .clk_en(clk_en), .pwr_good(pwr_good), .fault(fault));
endmodule
