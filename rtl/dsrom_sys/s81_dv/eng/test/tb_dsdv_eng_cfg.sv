`timescale 1ns/1ps
// S81/PORTFIX-CFG 10-25: unit bench of dsdv_eng_cfg (the eng die master's soft config register + 1-bit sticky fault).
// Checks: reset state {en, layer, rank} = 0; a CTL cfg op beat (kind 0, slice mask 0, op bit p[20] 1, uid 0xE6) on
// either rung input loads {en, layer, rank} 3 edges after its vi pin edge; decoys do not load (another uid, op bit 0, a
// slice mask bit set, kind 4 with the same payload, the continuation fragments of an XQ / XB train that look like a cfg
// beat); fault == OR of the sticky st inputs one edge later, on every edge, for each st bit; an f_ks start before any
// cfg write, and cfg beats on both inputs in one cycle, raise fault; reset clears everything.  TB_ENG_CFG PASS / FAIL.
// Mutants (must FAIL): MUT 1 rank bits swapped, 2 decode on kind only, 3 no continuation tracking, 4 st[2] dropped from
// the fold, 5 en reset to 1.
module tb_dsdv_eng_cfg;
    parameter integer MUT = 0;
    reg ck = 0, rst = 0;
    always #0.5 ck = ~ck;
    reg [275:0] vi_s = 0, vi_n = 0; reg ks = 0; reg [3:0] st = 0;
    wire en, ly, fault; wire [1:0] rk;
    dsdv_eng_cfg #(.MUT(MUT)) dut (.ck(ck), .rst_n(rst), .vi_s(vi_s), .vi_n(vi_n), .ks_v(ks), .st(st), .cfg_en(en),
        .cfg_layer(ly), .cfg_rank(rk), .fault(fault));
    integer nerr = 0, cyc = 0;
    // the cfg op beat (results/s81_portfix_1024/cfg_formats.md): p = beat[21 +: 186]
    function automatic [275:0] beat(input [2:0] kind, input [7:0] uid, input op, input [15:0] smask, input e, input l,
                                    input [1:0] r, input [31:0] junk);
        reg [185:0] p;
        p = '0; p[185:29] = 157'({5{junk}}); p[28:21] = uid; p[20] = op; p[19:18] = r; p[17] = l; p[16] = e; p[15:0] = smask;
        beat = {69'd0, p, junk[7:0], 4'h4, 5'd0, kind, 1'b1};
    endfunction
    // continuous fault check: fault(t) == fault(t-1) | |st(t-1) while chk (no configuration events expected)
    reg chk = 0, fo = 0;
    always @(posedge ck) begin
        #0.1;
        if (chk && fault !== fo) begin nerr++; if (nerr < 8) $display("TB_ENG_CFG fault %b exp %b cyc %0d", fault, fo, cyc); end
        cyc++;
    end
    always @(posedge ck) if (!chk) fo <= 0; else fo <= fo | |st;
    task automatic put_s(input [275:0] b); @(negedge ck); vi_s = b; @(negedge ck); vi_s = 0; endtask
    task automatic put_n(input [275:0] b); @(negedge ck); vi_n = b; @(negedge ck); vi_n = 0; endtask
    task automatic expect_cfg(input e, input l, input [1:0] r, input string what);
        repeat (3) @(negedge ck);
        if ({en, ly, rk} !== {e, l, r}) begin nerr++; $display("TB_ENG_CFG %s: cfg %b%b%b exp %b%b%b", what, en, ly, rk, e, l, r); end
    endtask
    task automatic do_reset;
        @(negedge ck); chk = 0; rst = 0; st = 0; repeat (3) @(negedge ck); rst = 1; repeat (5) @(negedge ck); chk = 1;
    endtask
    initial begin : run
        integer b, k;
        reg [275:0] h, c;
        repeat (3) @(negedge ck);
        do_reset;
        expect_cfg(0, 0, 0, "reset");
        // XQ (kind 1) and XB (kind 2) trains on vi_s whose 3 continuation fragments look like cfg beats: not decoded
        for (k = 1; k <= 2; k = k + 1) begin
            c = beat(3'd0, 8'hE6, 1'b1, 16'd0, 1'b1, 1'b1, 2'd3, 32'h1111_0000 + k);
            @(negedge ck); vi_s = beat(3'(k), 8'h00, 1'b0, 16'hFFFF, 1'b0, 1'b0, 2'd0, 32'h2222_0000);
            @(negedge ck); vi_s = c; @(negedge ck); vi_s = c; @(negedge ck); vi_s = c; @(negedge ck); vi_s = 0;
            expect_cfg(0, 0, 0, "train continuation");
        end
        // the cfg op on vi_n: en 1, layer 0, rank 2
        put_n(beat(3'd0, 8'hE6, 1'b1, 16'd0, 1'b1, 1'b0, 2'd2, 32'hCAFE_0001));
        expect_cfg(1, 0, 2, "cfg vi_n");
        // decoys: another uid, op bit 0, a slice mask bit, kind 4 (RD) with the cfg payload
        put_s(beat(3'd0, 8'hE7, 1'b1, 16'd0, 1'b0, 1'b1, 2'd1, 32'h0BAD_0001)); expect_cfg(1, 0, 2, "decoy uid");
        put_n(beat(3'd0, 8'hE6, 1'b0, 16'd0, 1'b0, 1'b1, 2'd1, 32'h0BAD_0002)); expect_cfg(1, 0, 2, "decoy op");
        put_s(beat(3'd0, 8'hE6, 1'b1, 16'h8000, 1'b0, 1'b1, 2'd1, 32'h0BAD_0003)); expect_cfg(1, 0, 2, "decoy mask");
        put_n(beat(3'd4, 8'hE6, 1'b1, 16'd0, 1'b0, 1'b1, 2'd1, 32'h0BAD_0004)); expect_cfg(1, 0, 2, "decoy kind");
        // a trailing single beat right after a train is a header again: the cfg op on vi_s after an XQ train
        @(negedge ck); vi_s = beat(3'd1, 8'h00, 1'b0, 16'd0, 1'b0, 1'b0, 2'd0, 32'h3333_0000);
        repeat (3) begin @(negedge ck); vi_s = 276'h5; end
        @(negedge ck); vi_s = beat(3'd0, 8'hE6, 1'b1, 16'd0, 1'b0, 1'b1, 2'd1, 32'hCAFE_0002);
        @(negedge ck); vi_s = 0;
        expect_cfg(0, 1, 1, "cfg vi_s after a train");
        // an f_ks start after configuration: no fault (checked continuously)
        @(negedge ck); ks = 1; @(negedge ck); ks = 0; repeat (4) @(negedge ck);
        // fault = OR of each sticky st bit (one edge later, every edge)
        for (b = 0; b < 4; b = b + 1) begin
            do_reset;
            put_s(beat(3'd0, 8'hE6, 1'b1, 16'd0, 1'b1, 1'b1, 2'd3, 32'hCAFE_0003));
            expect_cfg(1, 1, 3, "cfg per st bit");
            repeat (3) @(negedge ck);
            if (fault !== 1'b0) begin nerr++; $display("TB_ENG_CFG fault before st[%0d]", b); end
            st[b] = 1'b1; repeat (4) @(negedge ck);
            if (fault !== 1'b1) begin nerr++; $display("TB_ENG_CFG st[%0d] not folded", b); end
        end
        // reset clears; an f_ks start before any cfg write -> fault
        do_reset; chk = 0;
        expect_cfg(0, 0, 0, "reset after config");
        if (fault !== 1'b0) begin nerr++; $display("TB_ENG_CFG fault not cleared by reset"); end
        @(negedge ck); ks = 1; @(negedge ck); ks = 0; repeat (3) @(negedge ck);
        if (fault !== 1'b1) begin nerr++; $display("TB_ENG_CFG unconfigured start not flagged"); end
        // cfg beats on both inputs in one cycle -> fault, vi_s wins
        do_reset; chk = 0;
        @(negedge ck); vi_s = beat(3'd0, 8'hE6, 1'b1, 16'd0, 1'b1, 1'b0, 2'd1, 32'hCAFE_0004);
                      vi_n = beat(3'd0, 8'hE6, 1'b1, 16'd0, 1'b0, 1'b1, 2'd2, 32'hCAFE_0005);
        @(negedge ck); vi_s = 0; vi_n = 0;
        expect_cfg(1, 0, 1, "dual cfg");
        if (fault !== 1'b1) begin nerr++; $display("TB_ENG_CFG dual cfg not flagged"); end
        $display("TB_ENG_CFG_STATS mut %0d nerr %0d", MUT, nerr);
        if (nerr) $display("TB_ENG_CFG FAIL"); else $display("TB_ENG_CFG PASS");
        $finish;
    end
endmodule
