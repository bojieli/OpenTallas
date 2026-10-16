`timescale 1ns/1ps
// q14 r9 (2026-10-14): die-port contract bench of the NODE-LESS tile qfd_tile_nl (the 48 block-last tiles); model as
// tb_qfd_tile_nk_slot (copied from q14 r8: contract bench of qfd_tile_nk (rtl/physical/qfd_tile_nk_slot.sv) -- the die bundle
// mapping {tap, t_out / n_a / n_b / n_y = {fault, valid, 512}, tile_id} onto the REAL ot_qwen_rom_tile_nk wrapper.  As
// tb_qwen_rom_tile_nk_boundary.sv, the inner ROM tile core is a transparent contract model (the datapath exactness of
// ot_qwen_rom_tile_w12 is gated by its own benches); every output bit is checked every cycle against the field it must
// carry, so a swapped / shifted field fails.  +define+OT_QFD_TILE_NL_MUT (go from the wrong end of the tap) must FAIL.
module ot_qwen_rom_tile_w12 #(parameter ROM_TILE=-1, NW=18,GT=6144,SMIN=7,CODE_BANKS=5,KV_VB=131072,KV_NH=2,MEM_EXTRA=1,ACC_LAT=7,
    FAST_ISSUE=1,KV_PREP=4,MUL_LAT=8,TREE_LAT=7,ROM_PIPE=1,ROM_ARELAY=2,ROM_CAP2=1,ROM_CAPX=2,LRST=3,ARPB=1,MPR=1,HIER=2,
    HIER_HARD=1,TOREG=1,TIDR=1,LRR=1,XTX=2,ANR=1,BAW=12,KV_SLICE=1,RPH=0,RQR=0,NDH=0,BMUT=0,NODE=1,CHILD_CLOCKS=0) (
    input [CODE_BANKS-1:0] ck_rpair, input [2*CODE_BANKS-1:0] ck_rom, input [7:0] ck_lsl, input ck_node,
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
    wire thi, tlo;
    always @(posedge ck) if (rst_n && (thi !== 1'b1 || tlo !== 1'b0)) $fatal(1, "strap tie outputs wrong: tie_hi %b tie_lo %b", thi, tlo);
    qfd_tile_nl dut (.ck(ck), .ck_rp0(ck), .ck_rp1(ck), .ck_rp2(ck), .ck_rp3(ck), .ck_rp4(ck), .ck_lsl0(ck), .ck_lsl1(ck), .ck_lsl2(ck), .ck_lsl3(ck), .ck_lsl4(ck), .ck_lsl5(ck), .ck_lsl6(ck), .ck_lsl7(ck), .rst_n(rst_n), .tile_id(tid), .tie_hi(thi), .tie_lo(tlo), .tap(tap), .t_out(to));
    integer i, bad = 0, checks = 0;
    reg pf = 0;
    // Native boundary (Codex d6ce2ed5f): one input pin-register edge (tap, tile_id, reset) and one output launch
    // edge; same independent edge model as tb_qfd_tile_nk_slot (expected values from the previously captured pins).
    reg [507:0] tap_history = 0;
    reg [15:0]  tid_history = 0;
    reg         reset_history = 0;
    reg [511:0] expected_to;
    reg         expected_tv, expected_tf;
    initial begin
        repeat (3) @(negedge ck);
        rst_n = 1;
        for (i = 0; i < 4000; i = i + 1) begin
            @(posedge ck);
            expected_to = {4{tap_history[507:380]}} ^ {32{tid_history}};
            expected_tv = reset_history & tap_history[0];
            expected_tf = reset_history & pf;
            if (reset_history) pf = (^tap_history[379:1]) ^ (^tid_history); else pf = 0;
            tap_history = tap; tid_history = tid; reset_history = rst_n;
            @(negedge ck);
            tap = {$random, $random, $random, $random, $random, $random, $random, $random, $random, $random, $random,
                   $random, $random, $random, $random, $random};
            tid = $random;
            #0.01;
            checks = checks + 1;
            if (to[511:0] !== expected_to) bad = bad + 1;   // data + xl field (+ tile_id, n_* = 0)
            if (to[512] !== expected_tv) bad = bad + 1;     // valid = go
            if (to[513] !== expected_tf) bad = bad + 1;     // tile fault (flop-launched)
        end
        if (bad == 0) $display("PASS qfd_tile_nl_slot checks=%0d", checks);
        else $display("FAIL qfd_tile_nl_slot checks=%0d mismatches=%0d", checks, bad);
        $finish;
    end
endmodule
