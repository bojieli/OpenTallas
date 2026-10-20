`timescale 1ps/1fs
// KV-PC 2026-10-19: lockstep REF qkd_kv_hbm_elastic_front_mc_nc (flop storage) vs DUT qkd_kvpc_s_front (native banks).
// Legal block traffic: sectors land in order (random gaps, bursts), the issuer never lands a sector of block b before
// block b-NBLK was freed (the block credit), blk_go for block g only while gos <= freed + NBLK; early blk_go exercises
// hold.  Two resets (power-on and one mid-run, storage keeps its contents).  Every output compared every edge.
// +define+KVPC_MUT=N passes MUT N to the DUT (4 bank permutation, 5 no prefetch, 1 read +1: must FAIL).
`ifndef KVPC_MUT
`define KVPC_MUT 0
`endif
module tb_kvpc_front;
    localparam integer NBLK = 4, BLK = 8;
    reg clk = 0;
    always #512 clk = ~clk;
    reg hrst = 0;
    reg [281:0] co_in;
    reg [15:0] epoch_in;
    reg blk_go;
    wire [281:0] r_co, d_co;
    wire [15:0] r_ep, d_ep, r_st, d_st;
    wire r_put, d_put, r_fr, d_fr, r_ho, d_ho, r_id, d_id, r_fo, d_fo, r_fg, d_fg;
    wire [5:0] r_oc, d_oc;
    qkd_kv_hbm_elastic_front_mc_nc #(.NBLK(NBLK), .BLK(BLK), .STRIDE(1), .MUT(0)) u_ref (
        .pll_hbm(clk), .hrst(hrst), .pll_hbm_data({4{clk}}), .co_in(co_in), .epoch_in(epoch_in), .blk_go(blk_go),
        .co_out(r_co), .epoch_out(r_ep), .compiled_hbm_put(r_put), .blk_freed(r_fr), .hold(r_ho), .stall_edges(r_st),
        .occupancy(r_oc), .idle(r_id), .fault_overflow(r_fo), .fault_go(r_fg));
    qkd_kvpc_s_front #(.NBLK(NBLK), .BLK(BLK), .STRIDE(1), .MUT(`KVPC_MUT)) u_dut (
        .pll_hbm(clk), .hrst(hrst), .pll_hbm_data({4{clk}}), .co_in(co_in), .epoch_in(epoch_in), .blk_go(blk_go),
        .co_out(d_co), .epoch_out(d_ep), .compiled_hbm_put(d_put), .blk_freed(d_fr), .hold(d_ho), .stall_edges(d_st),
        .occupancy(d_oc), .idle(d_id), .fault_overflow(d_fo), .fault_go(d_fg));
    integer t, bad, chk, puts, holds, frees, gos, landed, freed, seed, edges, phase;
    integer rate_land, rate_go;
    task compare; begin
        chk = chk + 1;
        if ({r_co, r_ep, r_put, r_fr, r_ho, r_st, r_oc, r_id, r_fo, r_fg} !==
            {d_co, d_ep, d_put, d_fr, d_ho, d_st, d_oc, d_id, d_fo, d_fg}) begin
            bad = bad + 1;
            if (bad < 10) $display("MISMATCH t=%0d put %b/%b co %h/%h hold %b/%b occ %0d/%0d idle %b/%b fo %b/%b fg %b/%b",
                t, r_put, d_put, r_co[40:0], d_co[40:0], r_ho, d_ho, r_oc, d_oc, r_id, d_id, r_fo, d_fo, r_fg, d_fg);
        end
        if (r_put) puts = puts + 1;
        if (r_ho) holds = holds + 1;
        if (r_fr) frees = frees + 1;
    end endtask
    always @(negedge clk) if (hrst) compare;
    // issuer / sequencer model (TB truth): landed sectors, released blocks; block credit from blk_freed
    always @(posedge clk) if (hrst && r_fr) freed = freed + 1;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("edges=%d", edges)) edges = 40000;
        t = $urandom(seed);
        bad = 0; chk = 0; puts = 0; holds = 0; frees = 0; gos = 0; landed = 0; freed = 0;
        co_in = 0; epoch_in = 0; blk_go = 0;
        repeat (10) @(negedge clk);
        hrst = 1;
        for (t = 0; t < edges; t = t + 1) begin
            @(negedge clk);
            // phases: dense, sparse, go-early (hold), back-to-back
            phase = (t / 5000) % 4;
            rate_land = (phase == 0) ? 90 : (phase == 1) ? 30 : (phase == 2) ? 15 : 100;
            rate_go = (phase == 2) ? 60 : 20;
            co_in = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            epoch_in = $urandom;
            co_in[0] = 1'b0;
            if (landed < (freed + NBLK) * BLK && ($urandom % 100) < rate_land) begin
                co_in[0] = 1'b1; landed = landed + 1;
            end
            blk_go = 1'b0;
            if (gos < freed + NBLK && ($urandom % 100) < rate_go &&
                (phase == 2 || landed >= (gos + 1) * BLK)) begin
                blk_go = 1'b1; gos = gos + 1;
            end
            if (t == edges / 2) begin       // mid-run reset: both restart at wp = rp = 0 over the old storage contents
                hrst = 0; co_in[0] = 0; blk_go = 0;
                repeat (6) @(negedge clk);
                landed = 0; freed = 0; gos = 0;
                hrst = 1;
            end
        end
        if (bad == 0 && puts > 1000 && holds > 0)
            $display("KVPC_FRONT PASS edges=%0d checks=%0d puts=%0d holds=%0d freed=%0d errors=0 mut=%0d", edges, chk, puts,
                     holds, frees, `KVPC_MUT);
        else
            $display("KVPC_FRONT FAIL edges=%0d checks=%0d errors=%0d puts=%0d holds=%0d mut=%0d", edges, chk, bad, puts,
                     holds, `KVPC_MUT);
        $finish;
    end
endmodule
