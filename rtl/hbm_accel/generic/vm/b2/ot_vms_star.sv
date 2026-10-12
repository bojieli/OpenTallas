`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice COLL STAR RECEIVER (el1011-hbm-b2-vm, SPEC v0.4 F3, 2026-10-12).  The COLL broadcast is a one-hop star
// from coll to every slice: one 2,048-b data edge a slice (64 words a cycle), relayed (ot_vms_relay, W = 2130, C = 1)
// <= 500 um a stage, credit-based.  This tile terminates the edge at the slice and fans each 8-sector record into the 8
// bank COLL lanes (lane b <-> bank b, sector = {sa, b}) cut-through: a record leaves the cycle after it lands when every
// bank holds a COLL credit (no store-and-forward of a whole broadcast; no barrier).
//   vcb = {v, sa 13 (sec16[15:3]: mirror bit + 8-aligned sector), data 2,048 (8 x 256), word mask 64, epoch 4}
//   vcb_cr: one credit back a record (the source holds SD).  A lane with an all-zero word mask writes nothing.
// Reset only on control; payload flops and the FIFO have no reset.
module ot_vms_star #(
    parameter integer SD  = 2,      // record FIFO depth (the source's credits)
    parameter integer KQD = 2       // bank COLL queue depth (= ot_vms_bank KQD)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [2129:0]     vcb,
    output reg               vcb_cr,
    output wire [8*281-1:0]  kq,           // per bank {v, sec16, data 256, wmask 8}
    input  wire [7:0]        kq_cr,
    output reg  [3:0]        epoch         // epoch of the last record delivered (for the consumer's sector scoreboard)
);
    localparam integer SB = (SD > 1) ? $clog2(SD) : 1;
    // Physical structure: the record FIFO is lane-sliced (8 x {data 256, mask 8} + the {sa, epoch} chunk), each chunk
    // with its own kept copies of the write enable and pointers (no 2,129-b select / enable net); reset only on control.
    reg [2128:0] in_d; reg in_v; reg [7:0] kcr_r;
    reg [SB:0] sn; reg [2:0] kc [0:7];
    reg k_v; reg [8*281-1:0] k_d;
    wire [263:0] hl [0:7]; wire [16:0] hh;               // head chunks: lane {data, mask}; {sa 13, epoch 4}
    reg cred; always @* begin cred = 1'b1; for (integer l = 0; l < 8; l = l + 1) if (kc[l] == 3'd0) cred = 1'b0; end
    wire pop = sn != 0 && cred;
    genvar gk;
    for (gk = 0; gk < 9; gk = gk + 1) begin : g_ck
        localparam integer CW = (gk < 8) ? 264 : 17;
        (* keep = "true", dont_touch = "true" *) reg [SB-1:0] rp, wp;
        (* keep = "true", dont_touch = "true" *) reg we;
        reg [CW-1:0] m [0:SD-1];
        wire [CW-1:0] din;
        if (gk < 8) begin : g_l
            assign din = {in_d[68 + gk*256 +: 256], in_d[4 + gk*8 +: 8]};
            assign hl[gk] = m[rp];
        end else begin : g_h
            assign din = {in_d[2128:2116], in_d[3:0]};
            assign hh = m[rp];
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rp <= '0; wp <= '0; we <= 1'b0; end
            else begin
                we <= vcb[2129];
                if (we) wp <= (wp + 1'b1 == SB'(SD)) ? '0 : wp + 1'b1;
                if (pop) rp <= (rp + 1'b1 == SB'(SD)) ? '0 : rp + 1'b1;
            end
        always @(posedge clk) if (we) m[wp] <= din;
    end
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_kq
        assign kq[gk*281 +: 281] = {k_v, k_d[gk*281 +: 280]};
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            in_v <= 1'b0; kcr_r <= '0; sn <= '0; vcb_cr <= 1'b0; k_v <= 1'b0; epoch <= 4'd0;
            for (integer l = 0; l < 8; l = l + 1) kc[l] <= 3'(KQD);
        end else begin
            in_v <= vcb[2129]; kcr_r <= kq_cr;
            sn <= sn + (in_v ? 1 : 0) - (pop ? 1 : 0);
            if (pop) epoch <= hh[3:0];
            vcb_cr <= pop; k_v <= pop;
            for (integer l = 0; l < 8; l = l + 1) kc[l] <= kc[l] - (pop ? 3'd1 : 3'd0) + (kcr_r[l] ? 3'd1 : 3'd0);
        end
    always @(posedge clk) begin
        in_d <= vcb[2128:0];
        for (integer l = 0; l < 8; l = l + 1)
            k_d[l*281 +: 280] <= {hh[16:4], 3'(l), hl[l][263:8], hl[l][7:0]};
    end
endmodule
`default_nettype wire
