`timescale 1ns/1ps
`default_nettype none
// tb_hnx_att4_scl: LOCKSTEP + publication bench of the HNEXT.ATT4 cluster-leaf successor ot_hnx_att4_scl (two leaves,
// claude/hnx-att4-leaf-1020) against the flat tile ot_hnx_att4_spvm (MUT 0) on the SAME pin stimulus as tb_hnx_att4_pub
// (tools/hbm_next/att4_pub_bench.py --top scl).  The cluster's published streams are printed as PUB lines (the driver
// checks them bit for bit against the golden csum8 pairwise tree); every cycle after reset the cluster's outputs must
// equal the flat tile's LAG = 3 edges earlier (inputs +1 edge, outputs +2 edges; see ot_hnx_att4_sleaf.sv): pub_v and
// fault always, pub_data / pub_word / pub_out_slot / pub_out_lane / pub_tag whenever pub_v.  Any difference prints
// LOCKSTEP_MISMATCH and fails the run.  MUT drives the cluster only (1..6 core mutants, 7..9 seam mutants).
module tb_hnx_att4_scl;
    parameter integer MUT = 0;
    parameter integer NL = 3;
    localparam integer RB = 32 + 8 + 8 + 64 + 2048;
    localparam integer LAG = 3;
    localparam integer OW = 1 + 32 + 4 + 3 + 2 + 16 + 1;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [RB-1:0] stim [0:65535];
    integer n, last, idx, c, nw, mism, cyc, i;
    string sf;
    reg [3:0] ev = 0; reg [2047:0] sm = 0; reg [63:0] tg = 0;
    reg ps = 0; reg [1:0] pl = 0; reg [2:0] psl = 0;
    wire pub_v, fault; wire [31:0] pub_data; wire [3:0] pub_word; wire [2:0] pub_out_slot; wire [1:0] pub_out_lane;
    wire [15:0] pub_tag;
    wire r_v, r_f; wire [31:0] r_d; wire [3:0] r_w; wire [2:0] r_s; wire [1:0] r_l; wire [15:0] r_t;
    ot_hnx_att4_scl #(.NL(NL), .LV(3), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .ev(ev[NL-1:0]), .sum_lo(sm[1023:0]),
        .tag_lo(tg[31:0]), .sum_hi(sm[512*NL-1:1024]), .tag_hi(tg[16*NL-1:32]), .pub_start(ps), .pub_lane(pl),
        .pub_slot(psl), .pub_v(pub_v), .pub_data(pub_data), .pub_word(pub_word), .pub_out_slot(pub_out_slot),
        .pub_out_lane(pub_out_lane), .pub_tag(pub_tag), .fault(fault));
    ot_hnx_att4_spvm #(.NL(NL), .LV(3), .MUT(0)) ref0 (.clk(clk), .rst_n(rst_n), .ev(ev[NL-1:0]), .sum_lo(sm[1023:0]),
        .tag_lo(tg[31:0]), .sum_hi(sm[512*NL-1:1024]), .tag_hi(tg[16*NL-1:32]), .pub_start(ps), .pub_lane(pl),
        .pub_slot(psl), .pub_v(r_v), .pub_data(r_d), .pub_word(r_w), .pub_out_slot(r_s), .pub_out_lane(r_l),
        .pub_tag(r_t), .fault(r_f));
    reg [OW-1:0] rh [0:LAG-1];
    wire [OW-1:0] rnow = {r_v, r_d, r_w, r_s, r_l, r_t, r_f};
    wire [OW-1:0] rl = rh[LAG-1];
    always @(posedge clk) begin
        for (i = LAG - 1; i > 0; i = i - 1) rh[i] <= rh[i-1];
        rh[0] <= rnow;
        cyc <= cyc + 1;
        if (cyc > 24) begin
            if (pub_v !== rl[OW-1] || fault !== rl[0] ||
                (pub_v && {pub_data, pub_word, pub_out_slot, pub_out_lane, pub_tag} !== rl[OW-2:1])) begin
                mism = mism + 1;
                if (mism <= 8)
                    $display("LOCKSTEP_MISMATCH cyc=%0d scl v=%b f=%b d=%08h w=%0d s=%0d l=%0d t=%04h | flat-%0d v=%b f=%b d=%08h w=%0d s=%0d l=%0d t=%04h",
                             cyc, pub_v, fault, pub_data, pub_word, pub_out_slot, pub_out_lane, pub_tag, LAG,
                             rl[OW-1], rl[0], rl[OW-2 -: 32], rl[OW-34 -: 4], rl[OW-38 -: 3], rl[OW-41 -: 2],
                             rl[OW-43 -: 16]);
            end
        end
        if (pub_v) begin
            $display("PUB %0d %0d %0d %04h %08h", pub_out_lane, pub_out_slot, pub_word, pub_tag, pub_data);
            nw = nw + 1;
        end
        if (fault) begin $display("FAULT scl"); $fatal(1, "fault"); end
    end
    initial begin
        nw = 0; mism = 0; cyc = 0;
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
        $display("LOCKSTEP lag=%0d mismatches=%0d", LAG, mism);
        if (mism != 0) $fatal(1, "LOCKSTEP_MISMATCH total %0d", mism);
        $display("DONE words=%0d", nw);
        $finish;
    end
endmodule
`default_nettype wire
