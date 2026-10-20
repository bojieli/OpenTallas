`timescale 1ns/1ps
`default_nettype none
// L2H-PAD l21 bench: ot_hbm_host_static_ingress_obs + an ot_hbm_obs_leaf ring (3 leaves: N=95 LID 4 with SYNC bits,
// N=209 LID 0, N=32 LID 2), with registered relay stations between hops (as the die relay planner inserts them).
// Checks, over random static observation values and single-cycle pulses:
//  page 0 (live) word == the observed bits (SYNC bits after their extra flop), page 1 (sticky) holds a 1-cycle pulse
//  and is cleared by its own read; non-window reads unchanged (0xf30 status, 0x800 -> ffffffff); every word of every
//  leaf, the zero padding above N, and a LID with no leaf (returns 0).
// LMUT (define) is the MUT of the middle leaf: 1 no clear, 2 obs[N-1] dropped, 3 page select swapped -> must FAIL.
`ifndef LMUT
`define LMUT 0
`endif
module tb_hbm_obs_ring;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    localparam integer NA = 95, NB = 209, NC = 32;
    localparam [511:0] SMA = 512'h7000_0000_0000_0000_0000_0003;   // bits 0,1 and 92..94 sync (serial / async sources)
    reg [NA-1:0] oa; reg [NB-1:0] ob; reg [NC-1:0] oc;
    // AXI-lite host side
    reg arv = 0; reg [11:0] ara = 0; wire arr; wire rv; reg rr = 0; wire [31:0] rd;
    wire awr, wr, bv; wire [1:0] br;
    wire cfg_v, desc_v, launch_v, fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    wire q_v; wire [7:0] q_i; wire [31:0] q_d;
    wire r_v; wire [7:0] r_i; wire [31:0] r_d;
    ot_hbm_host_static_ingress_obs ing (.clk(clk), .rst_n(rst_n),
        .s_awvalid(1'b0), .s_awready(awr), .s_awaddr(12'd0), .s_wvalid(1'b0), .s_wready(wr), .s_wdata(32'd0), .s_wstrb(4'd0),
        .s_bvalid(bv), .s_bready(1'b1), .s_bresp(br), .s_arvalid(arv), .s_arready(arr), .s_araddr(ara),
        .s_rvalid(rv), .s_rready(rr), .s_rdata(rd), .block_ready(1'b1), .program_active(1'b0), .program_fault(1'b0),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .fault(fault),
        .obs_q_v(q_v), .obs_q_idx(q_i), .obs_q_d(q_d), .obs_r_v(r_v), .obs_r_idx(r_i), .obs_r_d(r_d));
    // relay station = one register on {v, idx, d}
    reg s0v, s1v, s2v; reg [7:0] s0i, s1i, s2i; reg [31:0] s0d, s1d, s2d;
    wire av, bv2, cv; wire [7:0] ai, bi, ci; wire [31:0] ad, bd, cd;
    always @(posedge clk) begin
        s0v <= rst_n & q_v; s0i <= q_i; s0d <= q_d;
        s1v <= rst_n & av;  s1i <= ai;  s1d <= ad;
        s2v <= rst_n & bv2; s2i <= bi;  s2d <= bd;
    end
    ot_hbm_obs_leaf #(.N(NA), .LID(4), .SYNC_MASK(SMA)) la (.clk(clk), .rst_n(rst_n), .obs(oa),
        .q_v(s0v), .q_idx(s0i), .q_d(s0d), .r_v(av), .r_idx(ai), .r_d(ad));
    ot_hbm_obs_leaf #(.N(NB), .LID(0), .MUT(`LMUT)) lb (.clk(clk), .rst_n(rst_n), .obs(ob),
        .q_v(s1v), .q_idx(s1i), .q_d(s1d), .r_v(bv2), .r_idx(bi), .r_d(bd));
    ot_hbm_obs_leaf #(.N(NC), .LID(2)) lc (.clk(clk), .rst_n(rst_n), .obs(oc),
        .q_v(s2v), .q_idx(s2i), .q_d(s2d), .r_v(r_v), .r_idx(r_i), .r_d(r_d));

    integer errors = 0, reads = 0, lat = 0, maxlat = 0;
    reg [31:0] got;
    task automatic axi_read(input [11:0] a);
        integer t;
        begin
            @(negedge clk); arv = 1; ara = a;
            t = 0;
            while (!(arr === 1'b1)) begin @(negedge clk); t = t + 1; if (t > 200) begin $display("FAIL ar timeout %h", a); $finish; end end
            @(negedge clk); arv = 0; rr = 1;
            t = 0;
            while (!(rv === 1'b1)) begin @(negedge clk); t = t + 1; if (t > 500) begin $display("FAIL r timeout %h", a); $finish; end end
            got = rd; reads = reads + 1; if (t > maxlat) maxlat = t;
            @(negedge clk); rr = 0;
        end
    endtask
    function automatic [31:0] wsel(input integer lid, input integer w);
        reg [511:0] v;
        begin
            v = 512'd0;
            if (lid == 4) v[NA-1:0] = oa; else if (lid == 0) v[NB-1:0] = ob; else if (lid == 2) v[NC-1:0] = oc;
            wsel = v[w * 32 +: 32];
        end
    endfunction
    task automatic check(input [11:0] a, input [31:0] exp, input [8*24-1:0] what);
        begin
            axi_read(a);
            if (got !== exp) begin
                errors = errors + 1;
                if (errors < 12) $display("FAIL %0s addr %h got %h exp %h", what, a, got, exp);
            end
        end
    endtask
    function automatic [11:0] adr(input integer lid, input integer page, input integer w);
        adr = {2'b00, lid[2:0], page[0], w[3:0], 2'b00};
    endfunction
    integer it, w, lid, b, nw;
    initial begin
        oa = 0; ob = 0; oc = 0;
        repeat (6) @(negedge clk); rst_n = 1; repeat (12) @(negedge clk);
        // clear stickies of power-up X/0 state
        for (lid = 0; lid < 8; lid = lid + 1) for (w = 0; w < 16; w = w + 1) axi_read(adr(lid, 1, w));
        for (it = 0; it < 24; it = it + 1) begin
            oa = {$random, $random, $random}; ob = {$random, $random, $random, $random, $random, $random, $random};
            oc = $random;
            repeat (4) @(negedge clk);
            // drain stickies (they hold the new static value), then check live + sticky == static value
            for (lid = 0; lid < 5; lid = lid + 2) for (w = 0; w < 16; w = w + 1) axi_read(adr(lid, 1, w));
            for (lid = 0; lid < 8; lid = lid + 1) begin
                nw = (lid == 4) ? 3 : (lid == 0) ? 7 : (lid == 2) ? 1 : 0;
                for (w = 0; w < 16; w = w + 1) begin
                    check(adr(lid, 0, w), (w < nw) ? wsel(lid, w) : 32'd0, "live");
                    check(adr(lid, 1, w), (w < nw) ? wsel(lid, w) : 32'd0, "sticky_static");
                end
            end
            // single-cycle pulse on a bit that is 0 in the static value: sticky must hold it, its read clears it
            b = (it * 37) % NB;
            ob[b] = 1'b0; repeat (4) @(negedge clk); axi_read(adr(0, 1, b / 32));
            @(negedge clk); ob[b] = 1'b1; @(negedge clk); ob[b] = 1'b0; repeat (4) @(negedge clk);
            check(adr(0, 0, b / 32), wsel(0, b / 32), "live_after_pulse");
            check(adr(0, 1, b / 32), wsel(0, b / 32) | (32'd1 << (b % 32)), "sticky_pulse");
            check(adr(0, 1, b / 32), wsel(0, b / 32), "sticky_cleared");
            // the top bit of leaf B (N-1) toggles
            ob[NB-1] = ~ob[NB-1]; repeat (4) @(negedge clk);
            check(adr(0, 0, (NB - 1) / 32), wsel(0, (NB - 1) / 32), "top_bit");
        end
        // non-window reads are the unchanged ingress map
        check(12'hf30, {26'd0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 1'b0}, "f30_status");
        check(12'h800, 32'hffffffff, "non_window");
        check(12'hffc, 32'hffffffff, "non_window2");
        if (fault !== 1'b0) begin errors = errors + 1; $display("FAIL ingress fault raised by reads"); end
        if (errors == 0) $display("OBS RING BENCH PASS reads=%0d max_r_wait=%0d LMUT=%0d", reads, maxlat, `LMUT);
        else $display("OBS RING BENCH FAIL errors=%0d reads=%0d LMUT=%0d", errors, reads, `LMUT);
        $finish;
    end
endmodule
`default_nettype wire
