`timescale 1ns/1ps
`default_nettype none
// HH-2 2026-10-19: unit bench of ot_hbm_sm_pv_merge at the production parameters (TAGW 16, LV 4, PUBLISH 1, ALAT 7),
// the smh_pvm hard tile.  Stimulus (pv_merge_golden.py gen): entry e (0..7) runs e+1 chunks of 16 FP32 lane sums; chunk j
// of entry e issues on the entry's turn (dut.bp == e) of round R0 + 5 j (compiler spacing: carry chain <= 3 turns, flush
// LV + 1).  Then one fold (0 <- 0 + 1) and the publication of slots 0, 2..7.  Every pv_v / pub_v beat is printed and
// checked bit for bit by pv_merge_golden.py check; fault must stay 0.  MUT = ot_hbm_sm_pv_merge MUT (negative controls).
// HBM-PVM-SAFE 10-19: SAFE = the dut's structural form (operand registers, ring fold tracker).  TIGHT 1 = the tight fold
// calendar from F0: (0<-0+1)@0 (2<-2+3)@2 (4<-4+5)@4 (2<-2+4)@14 (b = 4 is written back in its request cycle under SAFE),
// publication of slot 2 at the earliest legal cycle F0+25 (F0+24 with PUBEARLY: a schedule violation under SAFE -> fault),
// then slots 0, 6, 7.
module tb_pv_merge;
    parameter integer MUT = 0;
    parameter integer TURNREG = 1;                    // HH-12: the smh_pvm kit form (registered turn state)
    parameter integer SAFE = 0, TIGHT = 0, PUBEARLY = 0;
    localparam integer R0 = 4;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg ev = 0; reg [511:0] sum = 0; reg [15:0] tag_d = 0;
    reg pub_start = 0; reg [2:0] pub_slot = 0; reg fold_start = 0; reg [2:0] fold_a = 0, fold_b = 0;
    wire pv_v, pub_v, fault; wire [511:0] pv_y; wire [15:0] pv_tag, pub_tag; wire [31:0] pub_data; wire [3:0] pub_word;
    wire [2:0] pub_out_slot;
    ot_hbm_sm_pv_merge #(.TAGW(16), .LV(4), .MUT(MUT), .PUBLISH(1), .TURNREG(TURNREG), .SAFE(SAFE)) dut (.clk(clk), .rst_n(rst_n), .ev(ev), .sum(sum),
        .tag_d(tag_d), .pv_v(pv_v), .pv_y(pv_y), .pv_tag(pv_tag), .fault(fault), .pub_start(pub_start), .pub_slot(pub_slot),
        .pub_v(pub_v), .pub_data(pub_data), .pub_word(pub_word), .pub_out_slot(pub_out_slot), .pub_tag(pub_tag),
        .fold_start(fold_start), .fold_a(fold_a), .fold_b(fold_b));
    reg [511:0] chunk [0:63];                       // entry e chunk j at e*8+j
    initial $readmemh(`STIM, chunk);
    integer round = 0, cyc = 0, npv = 0, npub = 0, fault_cyc = -1;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if (dut.bp == 3'd7) round <= round + 1;
        if (pv_v) begin $display("PV %04h %0128h", pv_tag, pv_y); npv = npv + 1; end
        if (pub_v) begin $display("PUB %0d %0d %04h %08h", pub_out_slot, pub_word, pub_tag, pub_data); npub = npub + 1; end
        if (fault && fault_cyc < 0) fault_cyc = cyc;
`ifdef DBG
        if (ev || cyc < 40) $display("DBG cyc %0d bp %0d round %0d ev %0d tag %04h busy %02h fault %0d", cyc, dut.bp, round, ev, tag_d, dut.e_busy, fault);
`endif
    end
    integer e, j, k;
    // chunk issue: drive at the negedge before the posedge that sees r = bp
    always @(negedge clk) begin
        ev <= 0; tag_d <= 0;
        if (rst_n && round >= R0 && round < R0 + 40 && (round - R0) % 5 == 0) begin
            e = dut.bp; j = (round - R0) / 5;
            if (j <= e) begin
                ev <= 1; sum <= chunk[e*8+j];
                tag_d <= {1'b1, (j == 0), (j == e), 10'(e*8+j), 3'(e)};
            end
        end
    end
    task automatic tick(input integer n); for (k = 0; k < n; k = k + 1) @(negedge clk); endtask
    task automatic fold(input [2:0] a, input [2:0] b); fold_start = 1; fold_a = a; fold_b = b; @(negedge clk); fold_start = 0; endtask
    task automatic pub(input [2:0] sl); pub_start = 1; pub_slot = sl; @(negedge clk); pub_start = 0; endtask
    initial begin
        tick(3); rst_n = 1;
        wait (round == R0 + 40 + 6);                  // every run flushed (flush <= LV + 1 turns after the last chunk)
        @(negedge clk);
        if (TIGHT) begin                              // request cycles F0 + n (each task call = 1 cycle)
            fold(0, 1); tick(1); fold(2, 3); tick(1); fold(4, 5); tick(9); fold(2, 4);    // @0 @2 @4 @14
            tick(PUBEARLY ? 9 : 10); pub(2); tick(23);                                     // @25 (@24)
            pub(0); tick(23); pub(6); tick(23); pub(7); tick(23);
        end else begin
            fold(0, 1);
            tick(20);
            for (e = 0; e < 8; e = e + 1) if (e != 1) begin
                pub(3'(e)); tick(23);
            end
        end
        tick(10);
        $display("PVM DONE pv=%0d pub=%0d fault=%0d fault_cyc=%0d cycles=%0d", npv, npub, fault, fault_cyc, cyc);
        $finish;
    end
endmodule
`default_nettype wire
