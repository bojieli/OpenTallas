`timescale 1ns/1ps
// KV-SRAM-D2D 2026-10-19: slot-store bank equivalence + storage scoreboard.
//   ref : ot_qkvd_llr_replay_sram_leaf_sf  (as built: 64x512 macro, 137 of 512 columns used)
//   dut : ot_qkvd_llr_replay_sram_leaf_sfm #(.SRAMV(SRAMV_V), .MUTW(MUTW_V))  (right-sized d2d_sram 64x137)
// Same inputs every edge; dout compared every edge from edge 3 (both macros power up as the generator's model: zero, or X
// with OT_MEM_NO_INIT -- X === X).  Phases:
//   A 0..99,999      random writes / reads, half the addresses from {0..3} so same-edge (age 0) and one-edge-old (age 1)
//                    write / read collisions are frequent; all 137 data bits random
//   B 100,000..      lifetime: write every slot 0..63 once with a random word, idle 500 edges, read every slot back; each
//                    read word must equal the word written (scoreboard, independent of the reference)
// Coverage asserted: >= 1,000 age-0 hits, >= 1,000 age-1 hits, >= 10,000 macro reads, 64 scoreboard reads.
// Prints LEAF_EQ_PASS or LEAF_EQ_FAIL.
module tb;
`ifndef SRAMV_V
`define SRAMV_V 1
`endif
`ifndef MUTW_V
`define MUTW_V 0
`endif
reg ck = 0; always #5 ck = ~ck;
reg we = 0; reg [5:0] wa = 0, ra = 0; reg [136:0] din = 0;
wire [136:0] r_dout, d_dout;
ot_qkvd_llr_replay_sram_leaf_sf  #(.W(137)) ref_leaf (.ck(ck), .we(we), .wa(wa), .ra(ra), .din(din), .dout(r_dout));
ot_qkvd_llr_replay_sram_leaf_sfm #(.W(137), .SRAMV(`SRAMV_V), .MUTW(`MUTW_V)) dut (.ck(ck), .we(we), .wa(wa), .ra(ra), .din(din), .dout(d_dout));
integer cyc, i, mism = 0, h0 = 0, h1 = 0, mr = 0, sb = 0, nz136 = 0;
reg [136:0] gold [0:63];
reg [5:0] ra_d1, ra_d2; reg chk_d1 = 0, chk_d2 = 0;
function [136:0] rnd137(input integer dummy);
    rnd137 = {$random, $random, $random, $random, $random};
endfunction
initial begin
    for (cyc = 0; cyc < 100000 + 64 + 500 + 64 + 4; cyc = cyc + 1) begin
        @(negedge ck);
        if (cyc < 100000) begin
            we = $random; din = rnd137(0);
            wa = ($random & 1) ? ($random & 3) : $random; ra = ($random & 1) ? ($random & 3) : $random;
            chk_d1 = 0;
        end else if (cyc < 100064) begin
            we = 1; wa = cyc - 100000; din = rnd137(0); gold[cyc - 100000] = din; ra = (cyc - 99990) & 63; chk_d1 = 0;
        end else if (cyc < 100564) begin
            we = 0; ra = $random; chk_d1 = 0;
        end else if (cyc < 100628) begin
            we = 0; ra = cyc - 100564; chk_d1 = 1;
        end else begin we = 0; chk_d1 = 0; end
        @(posedge ck); #1;
        // scoreboard: dout after edge t+1 is the word read at edge t
        if (chk_d2) begin
            sb = sb + 1;
            if (d_dout !== gold[ra_d2]) begin
                $display("LEAF_EQ_FAIL scoreboard slot %0d", ra_d2); $fatal(1); end
            if (d_dout[136]) nz136 = nz136 + 1;
        end
        chk_d2 = chk_d1; ra_d2 = ra;
        if (cyc >= 3 && d_dout !== r_dout) begin
            mism = mism + 1;
            if (mism <= 3) $display("MISMATCH cycle %0d ref %h dut %h", cyc, r_dout, d_dout);
            if (mism == 3) begin $display("LEAF_EQ_FAIL mismatches"); $fatal(1); end
        end
        if (ref_leaf.s_dq[0]) h0 = h0 + 1;
        if (ref_leaf.s_dqq[0]) h1 = h1 + 1;
        if (ref_leaf.s_mr[0]) mr = mr + 1;
    end
    if (h0 < 1000 || h1 < 1000 || mr < 10000 || sb != 64 || nz136 < 8) begin
        $display("LEAF_EQ_FAIL coverage age0 %0d age1 %0d macro %0d scoreboard %0d bit136 %0d", h0, h1, mr, sb, nz136); $fatal(1); end
    $display("LEAF_EQ_PASS sramv=%0d edges=%0d age0_hits=%0d age1_hits=%0d macro_reads=%0d scoreboard=%0d bit136_ones=%0d",
             `SRAMV_V, cyc, h0, h1, mr, sb, nz136);
    $finish;
end
endmodule
