`timescale 1ns/1ps
// CORE-S81-SVC (10-23): lockstep of the S81 attention tile as 16 one-head hard cores (ot_s81c_attn_tile_hc) against
// ot_hdc_v41x_attn_tile_s at the S81 engine parameters (default HG 4, PCOLP 0): every output (ov, oy, oflt) every
// cycle from the first cycle after reset.  Random load stream (normal / p-mode, both p-words via ld_w2v, all banks,
// every group index incl. out-of-range) interleaved with a random operand stream (random 18-bit elements: pads,
// formats, codes, scales).  Driven by tb_s81c_hcore.cpp (clock); +seed=<n>, +cycles=<n>.
// Mutants: -DOT_S81C_HCORE_MUT (head g reads head g+1's p-word-1 column) must FAIL.
module tb_s81c_hgrp #(parameter integer GID = 1) (input wire clk);
    localparam integer H = 16, TD = 32, BW = 3;
    reg rst_n = 1'b0;
    // S81-CORES2/EH 10-25: DUT reset pin (-DOT_S81C_HCORE_RSTE releases 2 cycles later inside the core, so the bench
    // releases the DUT pin 2 cycles earlier) and DUT control (-DOT_S81C_HCORE_CTLA: ld_grp / ld_w2v one cycle ahead;
    // negative control -DOT_TB_CTLA_MUT feeds them on time and must FAIL)
    reg rst_n_d = 1'b0;
    reg [7:0] nx_grp = 8'd0;
    reg nx_w2v = 1'b0;
    wire [7:0] d_grp;
    wire d_w2v;
`ifdef OT_S81C_HCORE_CTLA
`ifdef OT_TB_CTLA_MUT
    assign d_grp = ld_grp; assign d_w2v = ld_w2v;
`else
    assign d_grp = nx_grp; assign d_w2v = nx_w2v;
`endif
`else
    assign d_grp = ld_grp; assign d_w2v = ld_w2v;
`endif
    reg ld_v, ld_mode, ld_w2v, iv;
    reg [BW-1:0] ld_bank, ibank;
    reg [7:0] ld_grp;
    reg [1023:0] ld_w;
    reg [575:0] ib;
    reg raw_v=0,raw_mode=0;reg[2:0]raw_bank=0;reg[1023:0]raw_w=0;
    wire st_v,st_mode,st_w2v;wire[2:0]st_bank;wire[7:0]st_grp;wire[1023:0]st_w;
    ot_s81c_hcore_load_stage u_sender(.clk(clk),.rst_n(rst_n_d),
      .ld_v(raw_v),.ld_mode(raw_mode),.ld_bank(raw_bank),.ld_grp(nx_grp),.ld_w(raw_w),.ld_w2v(nx_w2v),
      .out_v(st_v),.out_mode(st_mode),.out_bank(st_bank),.out_grp(st_grp),.out_w(st_w),.out_w2v(st_w2v));
    integer rst_pin_edge=-1,rst_core_edge=-1,stage_bad=0,load_words=0,reset_bad=0;
`ifdef OT_TB_RST_TIMED
    reg rst_history=0;
    // Independent two sampled-edge reference; exercise assertion during active traffic.
    always @(posedge clk) begin
      rst_history<=rst_n_d;rst_n<=rst_history;
      if(cyc==1)rst_n_d<=1; // Published boot edge, measured at the following falling edge.
    end
    always @(negedge clk) begin
      if(cyc==5006 || cyc==10006)rst_n_d<=1;
      if(cyc==5002 || cyc==10002)rst_n_d<=0;
    end
`endif
    always @(negedge clk) begin
      if(rst_n_d && rst_pin_edge<0)rst_pin_edge=cyc;
      if(g_h[0].u_c.rst_core_n && rst_core_edge<0)rst_core_edge=cyc;
      if(cyc>5)begin
        if({st_v,st_mode,st_bank,st_w}!=={ld_v,ld_mode,ld_bank,ld_w})stage_bad=stage_bad+1;
        if(st_v)load_words=load_words+1;
      end
    end
    wire r_ov, d_ov;
    wire [127:0] r_oy, d_oy;
    wire [3:0] r_of, d_of;
    // Connected real sender stage; legacy reference gets the complete load word one edge later.
    // reduced vehicle: ONE head group (gid GID) of the tile -- ref ot_hdc_v41x_attn_hgrp_s (HG 4, PCOLP 0, the
    // tile_s default) vs the 4 one-head cores the tile_hc builds for heads 4 GID .. 4 GID + 3 (same wp wiring)
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(4), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1),
                              .PCOLP(0)) u_ref (
        .clk(clk), .rst_n(rst_n), .gid(GID[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_wp(256'd0), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(r_ov), .oy(r_oy), .oflt(r_of));
    wire [3:0] hov;
    genvar gh, gw, gj;
    generate for (gh = 0; gh < 4; gh = gh + 1) begin : g_h
        localparam integer G = GID * 4 + gh;
        wire [63:0] wp;
        for (gw = 0; gw < 2; gw = gw + 1) begin : g_ww
            for (gj = 0; gj < 2; gj = gj + 1) begin : g_wj
`ifdef OT_S81C_HCORE_MUT
                assign wp[(gw*2 + gj)*16 +: 16] = st_w[gw*512 + (gj*16 + ((gw == 1) ? ((G + 1) % 16) : G))*16 +: 16];
`else
                assign wp[(gw*2 + gj)*16 +: 16] = st_w[gw*512 + (gj*16 + G)*16 +: 16];
`endif
            end
        end
        wire [7:0] gidh = G;
        ot_s81c_attn_hcore u_c (.clk(clk), .rst_n(rst_n_d), .gid(gidh), .ld_v(st_v), .ld_mode(st_mode), .ld_bank(st_bank),
            .ld_grp(st_grp), .ld_w(st_w[511:0]), .ld_wp(wp), .ld_w2v(st_w2v), .iv(iv), .ibank(ibank), .ib(ib),
            .ov(hov[gh]), .oy(d_oy[gh*32 +: 32]), .oflt(d_of[gh]));
    end endgenerate
    assign d_ov = hov[0];
    integer cyc = 0, mism = 0, nov = 0, seed = 1, ncyc = 20000, i, nz = 0;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", ncyc)) ncyc = 20000;
        xs = 32'h9e3779b9 ^ (seed * 32'h85ebca6b);
        ld_v = 0; ld_mode = 0; ld_w2v = 0; iv = 0; ld_bank = 0; ibank = 0; ld_grp = 0; ld_w = 0; ib = 0;
    end
    // xorshift32 stimulus generator (seeded by +seed)
    reg [31:0] xs;
    // xs is initialized once, after parsing +seed, in the stimulus initial block.
    function [31:0] rnd; input integer dummy; reg [31:0] x; begin
        x = xs; x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); xs = x; rnd = x; end endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
`ifndef OT_TB_RST_TIMED
        if (cyc == 3) rst_n <= 1'b1;
`ifdef OT_S81C_HCORE_RSTE
        if (cyc == 1) rst_n_d <= 1'b1;
`else
        if (cyc == 3) rst_n_d <= 1'b1;
`endif
`endif
`ifdef OT_TB_RST_TIMED
        if(cyc>4 && g_h[0].u_c.rst_core_n!==rst_n)reset_bad=reset_bad+1;
`endif
        `ifdef OT_TB_RST_TIMED
        ld_v<=rst_n_d ? raw_v : 1'b0;
`else
        ld_v<=raw_v;
`endif
        ld_mode<=raw_mode;ld_bank<=raw_bank;ld_w<=raw_w;
        // stimulus: phase A (cycles < 400) mostly loads; then mixed
        raw_v <= (cyc < 400) ? (rnd(0) % 8 != 0) : (rnd(0) % 4 == 0);
        raw_mode <= rnd(0) % 3 == 0;
        nx_w2v <= rnd(0) % 2;
        ld_w2v <= nx_w2v;
        raw_bank <= rnd(0) % 6;                      // 5 = no bank (writes nothing)
        ld_grp <= nx_grp;
        nx_grp <= (rnd(0) % 16 == 0) ? (rnd(0) % 256) : (rnd(0) % 3 == 0) ? (GID * 4 + rnd(0) % 4) : (rnd(0) % 17);
        for (i = 0; i < 32; i = i + 1) raw_w[i*32 +: 32] <= rnd(0);
        iv <= (cyc < 300) ? 1'b0 : (rnd(0) % 4 != 0);
        ibank <= rnd(0) % 5;
        for (i = 0; i < 18; i = i + 1) ib[i*32 +: 32] <= rnd(0);
        if (cyc > 4) begin
            if (r_ov !== d_ov || r_oy !== d_oy || r_of !== d_of) begin
                mism = mism + 1;
                if (mism <= 5) $display("MISMATCH cyc=%0d ov %b/%b oy %h / %h oflt %h/%h", cyc, r_ov, d_ov,
                                        r_oy, d_oy, r_of, d_of);
            end
            if (r_ov) begin nov = nov + 1; if (r_oy != 0) nz = nz + 1; end
        end
        if (cyc == ncyc) begin
            $display("S81C_LOAD_PROFILE load_transport=1 reset_release=%0d stage_bad=%0d load_words=%0d reset_bad=%0d",rst_core_edge-rst_pin_edge,stage_bad,load_words,reset_bad);
            if (mism == 0 && nov > 1000 && nz > 100 && stage_bad==0 && reset_bad==0 && rst_core_edge-rst_pin_edge==2)
                $display("S81C_HGRP_BENCH PASS gid=%0d seed=%0d cycles=%0d mismatches=0 ov=%0d ov_nonzero=%0d", GID, seed, ncyc, nov, nz);
            else
                $display("S81C_HGRP_BENCH FAIL gid=%0d seed=%0d cycles=%0d mismatches=%0d ov=%0d ov_nonzero=%0d", GID, seed, ncyc, mism, nov, nz);
            $finish;
        end
    end
endmodule
