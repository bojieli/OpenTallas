`timescale 1ns/1ps
// KV-DCAL2 10-19: ot_qkh_ktree_lk bench.  Phase 1: 4,000 lockstep edges (random partials, bursty valid, rare lane gf) ->
// sc_d / sc_f / g_f of ot_qkh_ktree_lk == ot_qkh_ktree (kpv_in = lane 0) every edge.  Phase 2: for each lane t = 0..15 a
// one-edge-late kpv and (separately) a lone kpv on lane t only -> the lk tile's g_f must rise on the edge after gf_r latches it
// while the reference stays quiet.  -DKLK_MUT=1 builds the tile with lanes ignored (old kpv_in[0]-only wiring): must FAIL.
`ifndef KLK_MUT
`define KLK_MUT 0
`endif
// KVG3-CORES 10-24: -DKLK_PR=1 builds the tile with PORT_REGS=1 (kpv / gf face flops, lanes compared registered): sc_d /
// sc_f must still equal the reference every edge and g_f must equal the reference g_f ONE EDGE LATER (priced fault +1).
`ifndef KLK_PR
`define KLK_PR 0
`endif
module tb_qkh_ktree_lk;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg [511:0] kp; reg [15:0] kpv, gf;
    wire [31:0] sc_r, sc_l; wire sf_r, sf_l, gf_r, gf_l;
    ot_qkh_ktree    u_ref (.clk(clk), .rst_n(rst_n), .kp_in(kp), .kpv_in(kpv[0]), .gf_in(gf), .sc_d(sc_r), .sc_f(sf_r), .g_f(gf_r));
    ot_qkh_ktree_lk #(.MUT(`KLK_MUT), .PORT_REGS(`KLK_PR)) u_lk (.clk(clk), .rst_n(rst_n), .kp_in(kp), .kpv_in(kpv), .gf_in(gf),
                                              .sc_d(sc_l), .sc_f(sf_l), .g_f(gf_l));
    reg gf_rd = 1'b0;                          // reference g_f one edge later (the PORT_REGS=1 fault latency)
    always @(posedge clk) gf_rd <= gf_r;
    wire gf_exp = (`KLK_PR != 0) ? gf_rd : gf_r;
    integer i, t, k, mism = 0, det = 0, falsepos = 0, edges = 0;
    reg v;
    task drive_rand(input bit with_gf);
        begin
            for (k = 0; k < 16; k = k + 1) kp[32*k +: 32] = {$urandom} & 32'hBF7FFFFF;   // finite fp32 partials
            v = ($urandom % 4) != 0;
            kpv = {16{v}};
            gf = (with_gf && ($urandom % 97) == 0) ? (16'h1 << ($urandom % 16)) : 16'h0;
        end
    endtask
    task check_eq;
        begin
            edges = edges + 1;
            if (sc_r !== sc_l || sf_r !== sf_l || gf_exp !== gf_l) begin
                mism = mism + 1;
                if (mism < 6) $display("MISMATCH edge %0d sc %h/%h sf %b/%b gf %b/%b", edges, sc_r, sc_l, sf_r, sf_l, gf_r, gf_l);
            end
        end
    endtask
    initial begin
        kp = 0; kpv = 0; gf = 0;
        repeat (6) @(posedge clk);
        #0.1 rst_n = 1;
        // reset-release window: the lk tile lands rst_n 2 edges later than ot_qkh_ktree (rst_l0/rst_l1); idle (kp 0, kpv 0)
        // for the full K pipe depth (4 x ADD 7 + MUL 6 + regs < 64) so both unreset data pipes hold the same words
        repeat (64) @(posedge clk);
        // phase 1: lockstep miter
        for (i = 0; i < 4000; i = i + 1) begin
            #0.1 drive_rand(1);
            @(posedge clk); #0.05 check_eq();
        end
        // drain
        for (i = 0; i < 60; i = i + 1) begin #0.1 kpv = 0; gf = 0; @(posedge clk); #0.05 check_eq(); end
        // phase 2: per-lane skew / drop injection (gf held 0, so any g_f is the lockstep check)
        for (t = 0; t < 16; t = t + 1) begin
            for (k = 0; k < 2; k = k + 1) begin
                #0.1 kpv = 16'h0; gf = 0;
                @(posedge clk);
                #0.1 kpv = 16'hFFFF; kpv[t] = (k == 0) ? 1'b0 : 1'b1;        // k0: lane t late / dropped this edge
                if (k == 1) kpv = 16'h0;                                     // k1: lane t valid with no partner (duplicate)
                if (k == 1) kpv[t] = 1'b1;
                if (k == 1 && t == 0) kpv = 16'hFFFE;                        // lane 0 itself diverging from 1..15
                @(posedge clk);
                #0.1 kpv = (k == 0) ? (16'h1 << t) : 16'h0;                  // k0: the late lane arrives one edge later
                @(posedge clk);                                                 // g_f = |gf_r of the injected edge
                if (`KLK_PR != 0) begin #0.1 kpv = 0; @(posedge clk); end        // PORT_REGS: the lane check is registered
                #0.05 if (gf_l === 1'b1) det = det + 1;
                if (gf_r !== 1'b0) falsepos = falsepos + 1;
                #0.1 kpv = 0;
                repeat (6) @(posedge clk);
            end
        end
        if (mism == 0 && det == 32 && falsepos == 0)
            $display("PASS ktree_lk lockstep_edges=%0d mismatches=0 lane_injections=32 detected=%0d", edges, det);
        else
            $display("FAIL ktree_lk lockstep_edges=%0d mismatches=%0d lane_injections=32 detected=%0d ref_false=%0d", edges, mism, det, falsepos);
        $finish;
    end
endmodule
