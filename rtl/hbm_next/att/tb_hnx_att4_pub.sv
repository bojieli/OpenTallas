`timescale 1ns/1ps
`default_nettype none
// tb_hnx_att4_pub: PUBLICATION-PATH bench of the shared 4-lane PV merge tile ot_hnx_att4_spvm (PUBLISH = 1; HBM-NEXT-ATT4
// step 3, 2026-10-19).  Declared external stimulus at the tile pins (tools/hbm_next/att4_pub_bench.py): per pin cycle
// the 4 lanes' chunk events (ev, 16 x FP32 chunk sums, tag) and the compiler's publication requests (pub_start,
// pub_lane, pub_slot).  Every published 16-word node is printed and compared bit for bit by the driver against the
// golden csum8 pairwise tree of the run's chunk sums (tools/hgi_sim/lib.py pairwise), with its tag / lane / slot.
// plusargs: +STIM=<hex> +N=<records> +LAST=<last pin cycle>; record = {cycle 32, ev 8, pub 8 (start<<5|lane<<3|slot),
// tags 4 x 16, sums 4 x 512}.
module tb_hnx_att4_pub;
    parameter integer MUT = 0;
    localparam integer RB = 32 + 8 + 8 + 64 + 2048;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [RB-1:0] stim [0:65535];
    integer n, last, idx, c, nw;
    string sf;
    reg [3:0] ev = 0; reg [2047:0] sm = 0; reg [63:0] tg = 0;
    reg ps = 0; reg [1:0] pl = 0; reg [2:0] psl = 0;
    wire pub_v, fault; wire [31:0] pub_data; wire [3:0] pub_word; wire [2:0] pub_out_slot; wire [1:0] pub_out_lane;
    wire [15:0] pub_tag;
    ot_hnx_att4_spvm #(.LV(3), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .ev(ev), .sum_lo(sm[1023:0]), .tag_lo(tg[31:0]),
        .sum_hi(sm[2047:1024]), .tag_hi(tg[63:32]), .pub_start(ps), .pub_lane(pl), .pub_slot(psl), .pub_v(pub_v),
        .pub_data(pub_data), .pub_word(pub_word), .pub_out_slot(pub_out_slot), .pub_out_lane(pub_out_lane),
        .pub_tag(pub_tag), .fault(fault));
    always @(posedge clk) begin
        if (pub_v) begin
            $display("PUB %0d %0d %0d %04h %08h", pub_out_lane, pub_out_slot, pub_word, pub_tag, pub_data);
            nw = nw + 1;
        end
        if (fault) begin $display("FAULT spvm"); $fatal(1, "fault"); end
    end
    initial begin
        nw = 0;
        if (!$value$plusargs("STIM=%s", sf)) $fatal(1, "plusargs");
        void'($value$plusargs("N=%d", n)); void'($value$plusargs("LAST=%d", last));
        $readmemh(sf, stim, 0, n - 1);
        repeat (6) @(posedge clk); rst_n <= 1;
        repeat (8) @(posedge clk);
        idx = 0;
        for (c = 0; c <= last; c = c + 1) begin
            @(negedge clk);
            if (idx < n && stim[idx][RB-1 -: 32] == c) begin
                ev = stim[idx][RB-33 -: 4]; ps = stim[idx][RB-41 -: 3] == 3'd1; pl = stim[idx][RB-44 -: 2];
                psl = stim[idx][RB-46 -: 3]; tg = stim[idx][2048 +: 64]; sm = stim[idx][2047:0];
                idx = idx + 1;
            end else begin
                ev = 0; ps = 0;
            end
        end
        @(negedge clk); ev = 0; ps = 0;
        repeat (64) @(posedge clk);
        $display("DONE words=%0d", nw);
        $finish;
    end
endmodule
`default_nettype wire
