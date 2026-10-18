// RTL-BUILD-KV/PVTRUNK 2026-10-18: the PV pair's 512-b registered RESULT TRUNK leaves (tools/qwen_kv_die/pv_trunk_gen.py
// --result-trunk -> qkd_pvw_die_r).  Trunk word (518 b, LSB first): data[511:0], valid[512], beat[517:513].
//
// qkd_pvr_inj -- one per block row, in the pair's CT at the row's channel crossing: ONE trunk stage that either passes the
// word from the row below (a) or injects the held y of one of the row's two column joins (ya / yb, block columns 0 / 1).
// Static schedule: the column's y_valid (yva / yvb, relayed with the y word) is registered at the pin, then a compiled
// delay dla / dlb (die-top constant of the generated pair, class compiled-slot strap) is counted down; the stage injects
// {ida, 1, y} on the edge  A + dY + 3 + dl  (A = the join's y_valid edge, dY = the column's y relay stations), which the
// generator chose so that beat b leaves the pair RES_D + b edges after column 0's y.  The join holds y until its next
// J_OUT, so the late inject reads a stable word.  No ready / credit: a pass word under an inject is a schedule error the
// pair bench excludes (every exit edge carries exactly one beat).
// Pins: a / ya / yb go through one 3:1 mux into the output flop b (the relay standards' "flop = pin register" form); the
// two y_valid pins and the reset are registered at the pin.
`default_nettype none
module qkd_pvr_inj #(
    parameter integer DW = 8                     // compiled-delay width (max delay 2^DW - 1 edges)
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [517:0]  a,
    input  wire [511:0]  ya,
    input  wire [511:0]  yb,
    input  wire          yva,
    input  wire          yvb,
    input  wire [4:0]    ida,
    input  wire [4:0]    idb,
    input  wire [DW-1:0] dla,
    input  wire [DW-1:0] dlb,
    output reg  [517:0]  b
);
    (* keep *) reg rst_q;
    always @(posedge ck) rst_q <= rst_n;
    reg yva_q, yvb_q, ra, rb;
    reg [DW-1:0] ca, cb;
    always @(posedge ck or negedge rst_q)
        if (!rst_q) begin
            yva_q <= 1'b0; yvb_q <= 1'b0; ra <= 1'b0; rb <= 1'b0; ca <= {DW{1'b0}}; cb <= {DW{1'b0}};
        end else begin
            yva_q <= yva; yvb_q <= yvb;
            if (yva_q) begin ra <= 1'b1; ca <= dla; end
            else if (ra) begin ca <= ca - 1'b1; if (ca == {DW{1'b0}}) ra <= 1'b0; end
            if (yvb_q) begin rb <= 1'b1; cb <= dlb; end
            else if (rb) begin cb <= cb - 1'b1; if (cb == {DW{1'b0}}) rb <= 1'b0; end
        end
`ifdef OT_QKD_PVR_MUT
    wire sa = ra && ca == {{(DW-1){1'b0}}, 1'b1};    // bench mutant: column a injects one edge early
`else
    wire sa = ra && ca == {DW{1'b0}};
`endif
    wire sb = rb && cb == {DW{1'b0}};
    always @(posedge ck)
        b[511:0] <= sa ? ya : sb ? yb : a[511:0];
    always @(posedge ck)
        b[517:513] <= sa ? ida : sb ? idb : a[517:513];
    always @(posedge ck or negedge rst_q)
        if (!rst_q) b[512] <= 1'b0;
        else b[512] <= sa | sb | a[512];
endmodule

// qkd_pvr_exit -- the trunk's last stage, at the strip corner facing pvfin: the 534-b pvfin p word
// {valid, beat, epoch, data}; the epoch is the pair control tile's out_epoch (relayed, static during a command), latched
// on beat 0 so a following command's start cannot relabel the beats still on the trunk.
module qkd_pvr_exit (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [517:0] t,
    input  wire [15:0]  epoch,
    output reg          p_valid,
    output reg  [4:0]   p_beat,
    output reg  [15:0]  p_epoch,
    output reg  [511:0] p_data
);
    (* keep *) reg rst_q;
    always @(posedge ck) rst_q <= rst_n;
    reg [15:0] eh;
    wire first = t[512] && t[517:513] == 5'd0;
`ifdef OT_QKD_PVR_MUT
    wire [15:0] e = epoch;                           // bench mutant: no beat-0 latch (a later start relabels the beats)
`else
    wire [15:0] e = first ? epoch : eh;
`endif
    always @(posedge ck or negedge rst_q)
        if (!rst_q) begin p_valid <= 1'b0; eh <= 16'd0; end
        else begin p_valid <= t[512]; eh <= e; end
    always @(posedge ck) begin p_beat <= t[517:513]; p_epoch <= e; p_data <= t[511:0]; end
endmodule
`default_nettype wire
