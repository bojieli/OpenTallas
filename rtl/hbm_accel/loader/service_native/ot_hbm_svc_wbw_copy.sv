`timescale 1ns/1ps
`default_nettype none
// H-SM 2026-10-16 (d4c locality, owner neighbour-relative clocking: no broadcast beyond ~2 mm without a local copy).
// WB WINDOW COMMAND LOCAL COPY at the PC band.  d4b-r: wbk_<q>.{wbw_v, wbw_base[29:0], wbw_total[11:0]} (43 b) was ONE
// equal-age broadcast from wbk_<q> (quadrant centre) to the eight vm_kshare leaves strung ~7.5 mm along the PC band
// (hbm-domain equal-age max 50, the worst of its domain).  Now wbk_<q> drives TWO copy leaves p2p (one per half of the
// PC band, each within ~2 mm of its four kshare leaves); each leaf re-issues the command to its NS kshare leaves on
// a FIXED edge:  in pin register (+1 stream edge) -> one output register per sink (+1 stream edge).  LAT = 2 stream
// edges on every sink, identical for both leaves, so the eight kshare leaves still see the command on the SAME edge
// (die equal-age pads balance the wbk -> leaf and leaf -> kshare relay legs as before).  Compiler: the window-command
// arrival constant grows by WBW_COPY_LAT = 2 stream edges (+ the routed leg difference H-DIE reports).
// Static fixed-cycle: no ready/credit.  Only the valid bit is reset; the payload is data (no reset).
// MUT (bench only): 1 = sink 2's copy one edge late (equal-age skew), 2 = sink 3 drops the valid (lost window).
module ot_hbm_svc_wbw_copy #(
    parameter integer NS  = 4,
    parameter integer MUT = 0
) (
    input  wire                 stream_clk,
    input  wire                 stream_rst_n,
    input  wire                 wbw_v,
    input  wire [29:0]          wbw_base,
    input  wire [11:0]          wbw_total,
    output wire [NS-1:0]        o_wbw_v,
    output wire [NS*30-1:0]     o_wbw_base,
    output wire [NS*12-1:0]     o_wbw_total
);
    // pin register
    reg        pv;
    reg [29:0] pb;
    reg [11:0] pt;
    always @(posedge stream_clk or negedge stream_rst_n)
        if (!stream_rst_n) pv <= 1'b0; else pv <= wbw_v;
    always @(posedge stream_clk) begin pb <= wbw_base; pt <= wbw_total; end
    // one output register per sink (per-direction drivers, low fanout)
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_s
        (* keep *) reg        qv;
        (* keep *) reg [29:0] qb;
        (* keep *) reg [11:0] qt;
        always @(posedge stream_clk or negedge stream_rst_n)
            if (!stream_rst_n) qv <= 1'b0; else qv <= (MUT == 2 && s == 3) ? 1'b0 : pv;
        always @(posedge stream_clk) begin qb <= pb; qt <= pt; end
        if (MUT == 1 && s == 2) begin : g_skew
            reg        mv;
            reg [29:0] mb;
            reg [11:0] mt;
            always @(posedge stream_clk or negedge stream_rst_n)
                if (!stream_rst_n) mv <= 1'b0; else mv <= qv;
            always @(posedge stream_clk) begin mb <= qb; mt <= qt; end
            assign o_wbw_v[s] = mv; assign o_wbw_base[s*30 +: 30] = mb; assign o_wbw_total[s*12 +: 12] = mt;
        end else begin : g_ok
            assign o_wbw_v[s] = qv; assign o_wbw_base[s*30 +: 30] = qb; assign o_wbw_total[s*12 +: 12] = qt;
        end
    end endgenerate
endmodule
`default_nettype wire
