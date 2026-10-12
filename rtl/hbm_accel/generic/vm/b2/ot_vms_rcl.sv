`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice RING CLIENT (el1011-hbm-b2-vm, SPEC v0.4, 2026-10-12).  Replays the packet requests other slices sent
// here (PREQs ejected by the CW stop, rce0, and by the CCW stop, rce1) as hub client NC, and returns each response on
// the direction OPPOSITE to its request's (a request that came CW from its source goes back CCW: same hop count):
// rce0 responses -> the CCW stop (ri1), rce1 responses -> the CW stop (ri0).  A response slot is reserved at issue
// (outstanding + waiting PRSPs <= 4), so the hub's in-order responses always have room.
// Reset only on control; payload flops and FIFOs have no reset.
module ot_vms_rcl #(
    parameter integer EJ = 2,       // eject FIFO depth per stop (= the stop's rce credits)
    parameter integer RF = 2        // the stops' PRSP FIFO depth (this client's ri credits per stop)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [1:0]        sid,
    input  wire [287:0]      rce0,         // from the CW stop {v, src 2, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    output reg               rce0_cr,
    input  wire [287:0]      rce1,         // from the CCW stop
    output reg               rce1_cr,
    output wire [337:0]      hq,           // ring client -> hub {v, req 337}
    input  wire [273:0]      hr,           // hub -> ring client {v, rsp 273}
    output wire [265:0]      ri0,          // PRSP to the CW stop {v, dst 2, client 4, seq 2, echo, data 256}
    input  wire              ri0_cr,
    output wire [265:0]      ri1,          // PRSP to the CCW stop
    input  wire              ri1_cr
);
    localparam integer JB = (EJ > 1) ? $clog2(EJ) : 1;
    reg [286:0] r0_d, r1_d; reg r0_v, r1_v; reg [272:0] hr_d; reg hr_v; reg [1:0] ricr_r; reg [1:0] me;
    wire [287:0] r0_r = {r0_v, r0_d}, r1_r = {r1_v, r1_d}; wire [273:0] hr_r = {hr_v, hr_d};
    reg hq_v; reg [336:0] hq_d; reg [1:0] ri_v; reg [264:0] ri_d;
    assign hq = {hq_v, hq_d}; assign ri0 = {ri_v[0], ri_d}; assign ri1 = {ri_v[1], ri_d};

    reg [286:0] rf [0:1][0:EJ-1]; reg [JB-1:0] rh [0:1], rt [0:1]; reg [JB:0] rn [0:1];
    reg [9:0]   oh [0:3]; reg [1:0] ohh, oht; reg [2:0] ohn;        // {port 1, src 2, client 4, seq 2, we}
    reg [265:0] pb [0:3]; reg [1:0] pbh, pbt; reg [2:0] pbn;        // {port 1, dst 2, client 4, seq 2, echo, data 256}
    reg [2:0] ric [0:1]; reg rpick;
    wire can_iss = (ohn + pbn) < 3'd4;
    wire iss0 = can_iss && rn[0] != 0 && (!rpick || rn[1] == 0);
    wire iss1 = can_iss && rn[1] != 0 && !iss0;
    wire [265:0] ph = pb[pbh];
    wire pport = ph[265];
    wire inj = pbn != 3'd0 && ric[pport] != 3'd0;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (integer v = 0; v < 2; v = v + 1) begin rh[v] <= '0; rt[v] <= '0; rn[v] <= '0; ric[v] <= 3'(RF); end
            ohh <= '0; oht <= '0; ohn <= '0; pbh <= '0; pbt <= '0; pbn <= '0; rpick <= 1'b0;
            rce0_cr <= 1'b0; rce1_cr <= 1'b0; hq_v <= 1'b0; ri_v <= '0; r0_v <= 1'b0; r1_v <= 1'b0; hr_v <= 1'b0; ricr_r <= '0;
        end else begin
            r0_v <= rce0[287]; r1_v <= rce1[287]; hr_v <= hr[273]; ricr_r <= {ri1_cr, ri0_cr};
            if (r0_r[287]) rt[0] <= (rt[0] + 1'b1 == JB'(EJ)) ? '0 : rt[0] + 1'b1;
            if (r1_r[287]) rt[1] <= (rt[1] + 1'b1 == JB'(EJ)) ? '0 : rt[1] + 1'b1;
            rn[0] <= rn[0] + (r0_r[287] ? 1 : 0) - (iss0 ? 1 : 0);
            rn[1] <= rn[1] + (r1_r[287] ? 1 : 0) - (iss1 ? 1 : 0);
            rce0_cr <= iss0; rce1_cr <= iss1;
            if (iss0) rh[0] <= (rh[0] + 1'b1 == JB'(EJ)) ? '0 : rh[0] + 1'b1;
            if (iss1) rh[1] <= (rh[1] + 1'b1 == JB'(EJ)) ? '0 : rh[1] + 1'b1;
            if (iss0 || iss1) begin rpick <= iss0; oht <= oht + 2'd1; end
            hq_v <= iss0 || iss1;
            if (hr_r[273]) begin pbt <= pbt + 2'd1; ohh <= ohh + 2'd1; end
            ohn <= ohn + ((iss0 || iss1) ? 3'd1 : 3'd0) - (hr_r[273] ? 3'd1 : 3'd0);
            pbn <= pbn + (hr_r[273] ? 3'd1 : 3'd0) - (inj ? 3'd1 : 3'd0);
            if (inj) pbh <= pbh + 2'd1;
            ri_v <= inj ? (2'b01 << pport) : 2'b00;
            for (integer v = 0; v < 2; v = v + 1)
                ric[v] <= ric[v] - ((inj && pport == v[0]) ? 3'd1 : 3'd0) + (ricr_r[v] ? 3'd1 : 3'd0);
        end

    always @(posedge clk) begin : dat
        reg [286:0] e; reg [14:0] s; reg [31:0] bm, ad;
        r0_d <= rce0[286:0]; r1_d <= rce1[286:0]; hr_d <= hr[272:0]; me <= sid;
        if (r0_r[287]) rf[0][rt[0]] <= r0_r[286:0];
        if (r1_r[287]) rf[1][rt[1]] <= r1_r[286:0];
        // e = {src 286:285, client 284:281, seq 280:279, we 278, bank 277:275, rowm 274:264, wmask 263:256, data 255:0}
        e = iss0 ? rf[0][rh[0]] : rf[1][rh[1]];
        s = {e[274] ? 2'd0 : me, e[273:264], e[277:275]};
        ad = {11'd0, e[274], s, 5'd0};
        for (integer k = 0; k < 8; k = k + 1) bm[4*k +: 4] = {4{e[256 + k]}};
        hq_d <= {e[278], ad, e[255:0], bm, 16'd0};
        // response port: a CW-arrived request (rf 0) answers via the CCW stop (port 1), and vice versa
        if (iss0 || iss1) oh[oht] <= {iss0, e[286:285], e[284:281], e[280:279], e[278]};
        if (hr_r[273]) pb[pbt] <= {oh[ohh], hr_r[255:0]};
        ri_d <= ph[264:0];
    end
endmodule
`default_nettype wire
