`timescale 1ns/1ps
// q14 r9 (2026-10-14): die-port contract bench of the NODE-LESS tile qfd_tile_nl (the 48 block-last tiles); model as
// tb_qfd_tile_nk_slot (copied from q14 r8: contract bench of qfd_tile_nk (rtl/physical/qfd_tile_nk_slot.sv) -- the die bundle
// mapping {tap, t_out / n_a / n_b / n_y = {fault, valid, 512}, tile_id} onto the REAL ot_qwen_rom_tile_nk wrapper.  As
// tb_qwen_rom_tile_nk_boundary.sv, the inner ROM tile core is a transparent contract model (the datapath exactness of
// ot_qwen_rom_tile_w12 is gated by its own benches); every output bit is checked every cycle against the field it must
// carry, so a swapped / shifted field fails.  +define+OT_QFD_TILE_NL_MUT (go from the wrong end of the tap) must FAIL.
module ot_qwen_rom_tile_w12 #(parameter NW=18,GT=6144,SMIN=7,CODE_BANKS=5,KV_VB=131072,KV_NH=2,MEM_EXTRA=1,ACC_LAT=7,
    FAST_ISSUE=1,KV_PREP=4,MUL_LAT=8,TREE_LAT=7,ROM_PIPE=1,ROM_ARELAY=2,ROM_CAP2=1,ROM_CAPX=2,LRST=3,ARPB=1,MPR=1,HIER=2,
    HIER_HARD=1,TOREG=1,TIDR=1,LRR=1,XTX=2,ANR=1,BAW=12,KV_SLICE=1,RPH=0,RQR=0,NDH=0,BMUT=0,NODE=1) (
    input clk, rst_n, input [15:0] tile_id, input ib_go, input [3*NW+13*24+13-1:0] ib, input [127:0] xl,
    output [511:0] t_out, output t_vout, input [511:0] n_a, n_b, input n_va, output [511:0] n_y, output n_vy,
    output fault, input kvw_ce, input [6:0] kvw_addr, input [511:0] kvw_data, kvw_mask);
    assign t_out = (n_a | n_b | {511'd0, n_va}) ^ {4{xl}} ^ {32{tile_id}};   // n_* must be 0 in a node-less tile
    assign t_vout = ib_go;
    assign n_y = NODE ? n_a + n_b : 512'd0;
    assign n_vy = NODE ? n_va : 1'b0;
    assign fault = (^ib) ^ (^tile_id);
    initial if (NODE != 0 || KV_SLICE != 0 || GT != 3072 || RPH != 2 || NDH != 1 || RQR != 1 || XTX != 2 || HIER_HARD != 1 || CODE_BANKS != 5)
        $fatal(1, "qfd_tile_nl: not node-less TP8 production (NODE %0d KV_SLICE %0d GT %0d RPH %0d NDH %0d RQR %0d)",
               NODE, KV_SLICE, GT, RPH, NDH, RQR);
    always @(posedge clk) if (kvw_ce || kvw_addr || kvw_data || kvw_mask) $fatal(1, "qfd_tile_nk: KV write port driven");
endmodule

module tb_qfd_tile_nl_slot;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg  [507:0] tap = 0;
    reg  [15:0]  tid = 16'h0;
    wire [513:0] to;
    qfd_tile_nl dut (.ck(ck), .rst_n(rst_n), .tile_id(tid), .tap(tap), .t_out(to));
    integer i, bad = 0, checks = 0;
    reg pf = 0;
    initial begin
        repeat (3) @(negedge ck);
        rst_n = 1;
        for (i = 0; i < 4000; i = i + 1) begin
            @(posedge ck);
            pf = (^tap[379:1]) ^ (^tid);
            @(negedge ck);
            tap = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random,
                   $random, $random, $random, $random, $random};
            tid = $random;
            #0.01;
            checks = checks + 1;
            if (to[511:0] !== ({4{tap[507:380]}} ^ {32{tid}})) bad = bad + 1;   // data + xl field (+ tile_id, n_* = 0)
            if (to[512] !== tap[0]) bad = bad + 1;                                // valid = go
            if (to[513] !== pf) bad = bad + 1;                                    // tile fault (flop-launched)
        end
        if (bad == 0) $display("PASS qfd_tile_nl_slot checks=%0d", checks);
        else $display("FAIL qfd_tile_nl_slot checks=%0d mismatches=%0d", checks, bad);
        $finish;
    end
endmodule
