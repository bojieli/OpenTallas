`timescale 1ns/1ps
`default_nettype none
// Extracted production lane: one SRAM and its FIFO/skid/out-buffer state, one clock root.
// This source preserves predecessor cycle behavior. Grant/config pins and lane_sector
// mux are explicit physical seam defects; the module is NOT a die-qualified hard leaf.
module ot_hgi_dma_front_lane2 #(parameter integer NB=32, LD=16)(
 input wire clk, rst_n,
 input wire [269:0] dd,
 input wire [287:0] tag_sectors,
 input wire [1:0] ks,
 input wire [2:0] sf,
 input wire [1:0] ack_epoch,
 output reg [1:0] epoch,
 output wire beat_valid,
 output wire [3:0] beat_tag,
 output reg lane_fault,
 output wire [553:0] lane_sector,
 output wire credit,
 output wire [2*NB-1:0] request_banks
);
 wire [0:0] local_reset;
 ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk),.rst_n_in(rst_n),.rst_n(local_reset));
 wire lr=local_reset[0];
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
        reg [276:0] packet [0:1]; // launch register held until matching acknowledged epoch
        reg [3:0] ov [0:1]; reg cr;
        reg [NB-1:0] rqv [0:1]; reg [NB-1:0] skm [0:2];             // XP: the active buffer's requested banks; a skid entry's
        reg [1:0] ack_q; reg [287:0] tags_q; reg [1:0] ks_q; reg [2:0] sf_q;
        wire [3:0] kmask_q = ks_q == 0 ? 4'b0001 : ks_q == 1 ? 4'b0011 : 4'b1111;
        always @(posedge clk) begin
            tags_q <= tag_sectors; ks_q <= ks; sf_q <= sf;
        end
        always @(posedge clk or negedge lr)
            if (!lr) ack_q <= 2'b00; else ack_q <= ack_epoch;
        assign request_banks = {rqv[1],rqv[0]};
        wire rdi  = n != '0 && ({1'b0, sn} + {2'd0, rv}) < 3'd3;
        wire full = n == (LW+1)'(LD) && !rdi;
        wire ok   = dv && !full;
        wire [1:0] free_slot = {ov[1] == 4'd0 || ack_q[1] == epoch[1], ov[0] == 4'd0 || ack_q[0] == epoch[0]};
        wire alloc = !free_slot[0];
        wire ld = free_slot != 2'b00 && sn != 2'd0;
        assign beat_valid = dv; assign beat_tag = dd_q[267:264];

        assign lane_sector = {packet[1],packet[0]};
        assign credit = cr;
        ot_sram_1r1w_128x256_m1_r2c2 u_q (.clk(clk), .r_ce_in(rdi), .r_addr_in(7'(h)), .rd_out(rd),
            .w_ce_in(ok), .w_addr_in(7'(t)), .wd_in(dd_q[255:0]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        always @(posedge clk) begin                           // data: no reset
            dd_q <= dd;
            if (ok) qs[t] <= tags_q[dd_q[267:264]*18 +: 18] + (18'(dd_q[263:256]) << ks_q);
            if (rdi) rs <= qs[h];
            if (rv) begin sk[st] <= {rs, rd}; skm[st] <= bmask(rs, kmask_q); end
            if (ld) packet[alloc] <= {sf_q, sk[sh]};
        end
        always @(posedge clk or negedge lr) begin
            if (!lr) begin
                dv <= 1'b0; h <= '0; t <= '0; n <= '0; rv <= 1'b0; sh <= 2'd0; st <= 2'd0; sn <= 2'd0;
                epoch <= '0; cr <= 1'b0; lane_fault <= 1'b0;
                for (integer os=0;os<2;os=os+1) begin ov[os] <= '0; rqv[os] <= '0; end
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
                lane_fault <= dv && (dd_q[268] || full);
                for (integer os=0;os<2;os=os+1) if (free_slot[os]) begin ov[os] <= '0; rqv[os] <= '0; end
                if (ld) begin epoch[alloc] <= !epoch[alloc]; ov[alloc] <= kmask_q; rqv[alloc] <= skm[sh]; end
            end
        end
endmodule
`default_nettype wire
