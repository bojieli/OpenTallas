`timescale 1ns/1ps
// tb_dsfd_wfc_hop_ep (s81-die-rtl-bind 2026-10-14, F4 hop): exact bench of the kit's stage hand-off endpoint.
// The sequencer side issues hop descriptors (c_cmd, at most 2 outstanding, random gaps, some long before and some long
// after their message); the kit side sends multi-flit messages on the link out (valid every flit, last on the final one).
// CHECK: the k-th done carries the k-th descriptor's tag {slot, op} and is not earlier than the end of the k-th message
// (and not earlier than its descriptor); every descriptor completes; no endpoint fault.  MUT 6 must FAIL.
module tb_dsfd_wfc_hop_ep;
    parameter integer MUT = 0, NJ = 300, SEED = 5;
    reg ck = 0, rst = 0; always #1 ck = ~ck;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    reg [63:0] rs = 64'hD1B54A32D192ED03 ^ SEED;
    function [31:0] rnd(input integer d); begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd = rs[31:0]; end endfunction
    reg [84:0] c_cmd = 0; wire [8:0] c_done; wire [1:0] c_st; reg lov = 0, lol = 0;
    dsfd_wfc_hop_ep #(.MUT(MUT)) dut (.ck(ck), .rst(rst), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .f_lov(lov), .f_lol(lol));
    integer ni = 0, nd = 0, nm = 0, out = 0, errors = 0, early = 0;
    reg [7:0] tag [0:NJ-1]; integer mend [0:NJ-1];
    initial begin #9 rst = 1; end
    // sequencer: descriptors, <= 2 outstanding
    always @(posedge ck) begin
        c_cmd <= 0;
        if (rst && cyc > 10 && ni < NJ && out < 2 && (rnd(0) % 23) == 0) begin
            tag[ni] = {ni[0], 7'(ni % 128)};
            c_cmd <= {1'b1, ni[0], 76'(rnd(0)), 7'(ni % 128)};
            ni = ni + 1; out = out + 1;
        end
        if (c_done[8]) begin
            if (nd >= ni || c_done[7:0] !== tag[nd]) begin errors = errors + 1; if (errors < 6) $display("ERR done %0d tag %h", nd, c_done[7:0]); end
            if (nd >= nm || cyc < mend[nd]) begin early = early + 1; if (early < 6) $display("ERR done %0d before its message end", nd); end
            nd = nd + 1; out = out - 1;
        end
    end
    // kit: messages of 1..60 flits, gaps
    integer fl = 0;
    always @(posedge ck) begin
        lov <= 0; lol <= 0;
        if (rst && cyc > 10 && nm < NJ) begin
            if (fl == 0 && (rnd(0) % 40) == 0 && nm < nd + 3) fl = 1 + rnd(0) % 60;
            if (fl > 0) begin lov <= 1; fl = fl - 1; if (fl == 0) begin lol <= 1; mend[nm] = cyc + 1; nm = nm + 1; end end
        end
    end
    initial begin
        wait (nd == NJ || cyc > 400000);
        repeat (20) @(posedge ck);
        $display("TB_DSFD_WFC_HOP_EP MUT=%0d jobs=%0d/%0d messages=%0d tag_errors=%0d early=%0d fault=%0d %s", MUT, nd, NJ, nm,
                 errors, early, c_st[0], (nd == NJ && errors == 0 && early == 0 && !c_st[0] && c_st[1]) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
