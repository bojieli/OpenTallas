`timescale 1ns/1ps
`default_nettype none
// HBM-HCROOT6 10-20 (RELEASE_TREE H.STA.BLK.1): ot_hbm_hc_tail_child_static -- the HC Sinkhorn tail as ONE hardened child
// tile, instanced twice in the HC root (ot_hbm_hc_root_static TAILC 1).  Function and calendar = ot_hbm_hc_tail_unit_static
// (sigmoid pre/post + exp + Sinkhorn ITERS 20 on the /SDIV sink clock, fixed launch -> result latency) + 2 edges:
//   PINS     every input lands in a pin flop (launch, 24 mixes, 24 bases, 3 scales = 1,633 flops), then one more
//            free-running stage so the launch can fan out to the 1,632 capture enables through a 2-level KEPT copy tree
//            (pin flop -> launch_s copies, the copies made at gate level by the bounded-fanout cloner) with the data
//            beside it: the inner tail launches 2 edges after the pin.  result / result_v are flops of the inner tail
//            (output pin registers, no added edge); fault is registered (sticky, +1).
//   RESET    own regional relay (ot_rst_relay, 2-stage synchronous release, 3 kept region roots; the gate-level cloner replicates a root that drives > 24 pins): the root's rst_tail
//            port drives only the relay.
//   CLOCK    own CTS root (core clk) plus the generated /SDIV sink clock (one flop, sclk) for the Sinkhorn: the child is
//            a separate tile; the root lands result / result_v / fault in its own flops (reg -> reg crossing).
//   DATAPATH ot_hgi_hc_tail_os_static (registered one-hot operand selects and write-backs, no delay lines).
// Latency: result_v at launch + L + 2 (L = 198 + SDIV + CAP + 2 = 496 at SDIV 7, CAP 289); the root delays its tail-side
// emit by the same 2 edges (TAILC 1: HC_MIX + 2 over the SAFE 1 root).  No ready, busy or response signal moves an event.
// MUT (bench): 1 = inner p3 row-max operand off by one group (ot_hgi_hc_tail_os_static MUT 1).
module ot_hbm_hc_tail_child_static #(
    parameter integer SDIV = 7,
    parameter integer CAP  = 41 * SDIV + 2,            // 2 ITERS + 1 = 41 Sinkhorn steps + 2 (289 at SDIV 7)
    parameter integer MUT_PRE = 0,
    parameter integer MUT = 0,
    // HBM-HCROOT8 10-20: SKCE 1 (default) = the Sinkhorn on the core clock with the sclk flop as its step ENABLE (one clock
    // root, no derived clock; kit SDC: declared multicycle SDIV between the Sinkhorn's own registers).  Calendar and
    // result edges unchanged.  0 = the derived /SDIV step clock of 22ea15f97 (k1/k1b: CTS left sclk untreed).
    parameter integer SKCE = 1,
    // FAM-HBM-B/HCTAIL 10-21 (k2b STA: Sinkhorn step 7.53 ns > the 5.83 ns MCP 7 budget, ~2,100 single-period tail paths
    // ~38 levels / -417 ps): TPIPE 1 = the pipelined tail calendar of ot_hgi_hc_tail_os_static (EREADY 197 -> 270, the
    // sink launch window opens at TR = EREADY + 1); SKP 1 = the Sinkhorn step in registered stages (ot_hdc_sinkhorn_cp,
    // needs SDIV >= 16, no multicycle path).  Kits: k3 = TPIPE 1 SKP 1 SDIV 16 (L 947, +451 edges over L 496);
    // k3b = TPIPE 1 SKP 0 SDIV 12 + MCP 12 (L 779, +283 edges).  Defaults = the k2 form (L 496).
    parameter integer TPIPE = 0,
    parameter integer SKP = 0,
    parameter integer TR = TPIPE ? 271 : 198,          // os EREADY + 1 (ot_hgi_hc_tail_os_static calendar)
    parameter integer L = TR + SDIV + CAP + 2
)(
    input  wire          clk, rst_n,
    input  wire          launch,
    input  wire [767:0]  mixes, bases,
    input  wire [95:0]   scales,
    output reg           result_v,
    output wire [767:0]  result,
    output reg           fault
);
    // ---------------------------------------------------------------- regional reset (2-stage landing + kept roots)
    // HBM-HC7 10-20: the relay roots are async-reset by the port, so the gate-level cloner's copies of a relay root
    // loaded rst_n (37 > 32, BFC frontier).  A second KEPT leaf stage per region is async-reset by its region root
    // (assertion still ripples asynchronously, release +1 clk edge, boot only): the cloner now replicates the leaves
    // (loading rn[r], <= 32) and rst_n drives only the 2 sync flops + 3 region roots.
    wire [2:0] rn;
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    (* keep = "true", dont_touch = "true" *) reg [2:0] rl;
    genvar gr;
    generate for (gr = 0; gr < 3; gr = gr + 1) begin : g_rleaf
        always @(posedge clk or negedge rn[gr]) if (!rn[gr]) rl[gr] <= 1'b0; else rl[gr] <= 1'b1;
    end endgenerate
    wire rst_pin = rl[0], rst_ctl = rl[1], rst_core = rl[2];
    // ---------------------------------------------------------------- pin flops + second (fanout) stage
    reg launch_p, launch_s; reg [1631:0] d_p, d_s;
    always @(posedge clk or negedge rst_pin)
        if (!rst_pin) begin launch_p <= 1'b0; launch_s <= 1'b0; end
        else begin launch_p <= launch; launch_s <= launch_p; end
    always @(posedge clk) begin d_p <= {scales, bases, mixes}; d_s <= d_p; end
    wire [767:0] i_mixes = d_s[767:0], i_bases = d_s[1535:768];
    wire [95:0]  i_scales = d_s[1631:1536];
    // ---------------------------------------------------------------- tail unit (ot_hbm_hc_tail_unit_static calendar)
    localparam integer CW = $clog2(SDIV);
    reg [CW-1:0] cnt; reg sclk;
    always @(posedge clk or negedge rst_ctl)
        if (!rst_ctl) begin cnt <= 0; sclk <= 1'b0; end
        else begin cnt <= (cnt == SDIV - 1) ? {CW{1'b0}} : cnt + 1'b1; sclk <= (cnt == SDIV - 1); end
    wire wrap = (cnt == SDIV - 1);
    reg active, sl, armed; reg [9:0] age, sage;
    wire tv, tf, e_rdy;
    reg capture_q;
    ot_hgi_hc_tail_os_static #(.MUT_PRE(MUT_PRE), .MUT(MUT), .SKCE(SKCE), .SKP(SKP), .TPIPE(TPIPE)) u_tail (.clk(clk), .sink_clk(sclk), .rst_n(rst_core),
        .launch(launch_s), .mixes(i_mixes), .bases(i_bases), .scales(i_scales), .sink_launch(sl), .sink_capture(capture_q),
        .e_ready(e_rdy), .result_v(tv), .result(result), .fault(tf));
    reg own_fault, captured;
    always @(posedge clk or negedge rst_ctl) begin
        if (!rst_ctl) begin active <= 0; sl <= 0; armed <= 0; age <= 0; sage <= 0; capture_q <= 0; result_v <= 0;
                            own_fault <= 0; captured <= 0; fault <= 0; end
        else begin
            capture_q <= 1'b0; result_v <= 1'b0;
            fault <= own_fault | tf;
            if (active) age <= age + 1'b1;
            if (launch_s) begin
                if (active) own_fault <= 1'b1;
                active <= 1'b1; age <= 10'd1; armed <= 1'b0; captured <= 1'b0;
            end
            if (e_rdy && age != 10'(TR - 1)) own_fault <= 1'b1;     // HCTAIL: TR must equal the os calendar's EREADY + 1
            if (active && !armed && age >= 10'(TR) && wrap) begin sl <= 1'b1; armed <= 1'b1; sage <= 10'd1; end
            else if (sl && wrap) sl <= 1'b0;
            if (armed && !captured) begin
                sage <= sage + 1'b1;
                if (sage == 10'(CAP)) begin capture_q <= 1'b1; captured <= 1'b1; end
            end
            if (active && age == 10'(L - 1)) begin
                result_v <= 1'b1; active <= 1'b0;
                if (!captured) own_fault <= 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
