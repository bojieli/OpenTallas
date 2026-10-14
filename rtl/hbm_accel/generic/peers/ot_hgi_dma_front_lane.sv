`timescale 1ns/1ps
`default_nettype none
// Extracted production lane: one SRAM and its FIFO/skid/out-buffer state, one clock root.
// This source preserves predecessor cycle behavior. Grant/config pins and lane_sector
// mux are explicit physical seam defects; the module is NOT a die-qualified hard leaf.
module ot_hgi_dma_front_lane #(parameter integer NB=32, LD=16)(
 input wire clk, lr,
 input wire [269:0] dd,
 input wire [287:0] tag_sectors,
 input wire [1:0] ks,
 input wire [2:0] sf,
 input wire [3:0] kmask, slot_grant,
 input wire [NB-1:0] bank_grant,
 output wire beat_valid,
 output wire [3:0] beat_tag,
 output wire lane_fault,
 output wire [3:0] active_slots,
 output wire [17:0] active_sector,
 output wire [276:0] lane_sector,
 output wire credit,
 output wire [NB-1:0] request_banks
);
 localparam integer LW=$clog2(LD), BW=$clog2(NB);
    function automatic [NB-1:0] bmask(input [17:0] sv, input [3:0] km);
        bmask = '0;
        for (integer j = 0; j < 4; j = j + 1) if (km[j]) bmask[BW'(sv[BW-1:0] + BW'(j))] = 1'b1;
    endfunction
        reg dv; reg [269:0] dd_q;                             // pin flop
        reg [LW-1:0] h, t; reg [LW:0] n;                      // lane FIFO
        reg [17:0] qs [0:LD-1];                               // its entries' VM sectors
        reg rv; reg [17:0] rs; wire [255:0] rd;               // read in flight
        reg [1:0] sh, st, sn; reg [273:0] sk [0:2];           // skid
        reg ap, pa; reg [273:0] bf [0:1]; reg [2:0] bff [0:1];                     // out buffers
        reg [3:0] ov; reg [17:0] ob; reg cr;
        reg [NB-1:0] rqv; reg [NB-1:0] skm [0:2];             // XP: the active buffer's requested banks; a skid entry's
        reg [NB-1:0] gb;                                      //     the banks that granted this lane this cycle
        always @* gb = bank_grant;
        assign request_banks = rqv;
        wire rdi  = n != '0 && ({1'b0, sn} + {2'd0, rv}) < 3'd3;
        wire full = n == (LW+1)'(LD) && !rdi;
        wire ok   = dv && !full;
        wire fin  = (ov & ~slot_grant) == 4'd0;
        wire ld   = fin && sn != 2'd0;
        assign beat_valid = dv; assign beat_tag = dd_q[267:264];
        assign lane_fault = dv && (dd_q[268] || full);
        assign active_slots = ov; assign active_sector = ob;
        assign lane_sector = {bff[pa], bf[pa]};
        assign credit = cr;
        ot_sram_1r1w_128x256_m1_r2c2 u_q (.clk(clk), .r_ce_in(rdi), .r_addr_in(7'(h)), .rd_out(rd),
            .w_ce_in(ok), .w_addr_in(7'(t)), .wd_in(dd_q[255:0]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        always @(posedge clk) begin                           // data: no reset
            dd_q <= dd;
            if (ok) qs[t] <= tag_sectors[dd_q[267:264]*18 +: 18] + (18'(dd_q[263:256]) << ks);
            if (rdi) rs <= qs[h];
            if (rv) begin sk[st] <= {rs, rd}; skm[st] <= bmask(rs, kmask); end
            if (ld) begin bf[!ap] <= sk[sh]; bff[!ap] <= sf; ob <= sk[sh][273:256]; end
        end
        always @(posedge clk or negedge lr) begin
            if (!lr) begin
                dv <= 1'b0; h <= '0; t <= '0; n <= '0; rv <= 1'b0; sh <= 2'd0; st <= 2'd0; sn <= 2'd0;
                ap <= 1'b0; pa <= 1'b0; ov <= 4'd0; cr <= 1'b0; rqv <= '0;
            end else begin
                dv <= dd[269];
                if (ok) t <= t + 1'b1;
                if (rdi) h <= h + 1'b1;
                n <= n + (LW+1)'(ok) - (LW+1)'(rdi);
                cr <= rdi;
                rv <= rdi;
                if (rv) st <= (st == 2'd2) ? 2'd0 : st + 2'd1;
                if (ld) sh <= (sh == 2'd2) ? 2'd0 : sh + 2'd1;
                sn <= sn + 2'(rv) - 2'(ld);
                pa <= ap;
                if (ld) begin ap <= !ap; ov <= kmask; rqv <= skm[sh]; end
                else begin ov <= ov & ~slot_grant; rqv <= rqv & ~gb; end
            end
        end
endmodule
`default_nettype wire
