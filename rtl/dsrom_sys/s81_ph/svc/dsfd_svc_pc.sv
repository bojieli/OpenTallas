`timescale 1ns/1ps
// dsfd_svc_pc -- the scan service's per-PC HBM interface TILE ("rd group", CLAUDE S81-PH svc, 2026-10-06).
// 32 instances in a row along the svc's S face, instance p at x = p * 265.584 um directly above the ctrl tile
// dsfd_ctrl_pc of the same pseudo-channel (S face pins at exactly the ctrl tile's N face x: abutted, 0-um hops);
// the N face carries the same signals at the same x to the quadrant above (quadrant q = PCs 8q .. 8q + 7).
//   request  qrq (quadrant, 341 b {wdata, wstrb, tag, len, addr, we, v}) -> one register -> rq (ctrl), credit flow
//            unchanged (the quadrant holds the ctrl's DQ credits; rk pulses come back through this tile)
//   response rd {rv, r_beat, r_tag, r_data} (ctrl, valid-only) -> one register -> qrd (quadrant)
//   rk / wd  pulses -> one register each
// One register per direction: every pin of the tile is one flop away from its partner pin (43 um), valids reset.
// Cost: +1 cks on each direction (credit round trip +2).
module dsfd_svc_pc (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,          // async die reset (active low), synchronised here
    input  wire [340:0] qrq,          // from the quadrant (N)
    output reg  [340:0] rq,           // to the ctrl PC tile (S)
    input  wire [0:0]   rk,           // credit pulse from the ctrl (S)
    output reg  [0:0]   qrk,          // to the quadrant (N)
    input  wire [0:0]   wd,
    output reg  [0:0]   qwd,
    input  wire [0:0]   rv,           // response from the ctrl (S)
    input  wire [255:0] r_data,
    input  wire [16:0]  r_tag,
    input  wire [3:0]   r_beat,
    output reg  [0:0]   qrv,          // to the quadrant (N)
    output reg  [255:0] qr_data,
    output reg  [16:0]  qr_tag,
    output reg  [3:0]   qr_beat
);
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rn = rst_s[1];
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin rq[0] <= 1'b0; qrk <= 1'b0; qwd <= 1'b0; qrv <= 1'b0; end
        else begin
            rq[0] <= qrq[0]; qrk <= rk; qwd <= wd;
`ifdef S81PH_SVCPC_MUT_DROP
            qrv <= rv & ~r_tag[0];                  // mutant: responses with tag bit 0 set are lost
`else
            qrv <= rv;
`endif
        end
    always @(posedge ck[0]) begin
        rq[340:1] <= qrq[340:1];
        qr_data <= r_data; qr_tag <= r_tag; qr_beat <= r_beat;
    end
endmodule
