`timescale 1ns/1ps
// tb_dsfd_capt_status_x43 (S-VM-CAPT-STATUS 2026-10-16): the capture status transfer dsfd_capt_status_dual (wrapper of
// dsfd_capt_status_x43_t / _s) against its sample rule, with COINCIDENT epoch edges as on the die (stream period 6,
// serial 8, both rising at 24k + 3; 1 time unit = 1/2 VCO tick).  A fresh random 64-bit f_sn every stream cycle.
//   +mode=0  resets released on the epoch (contract): t_st after serial edge j must equal f_sn as presented at stream
//            index 2 (j = 0, previous epoch), 3 (j = 1, previous epoch), 0 (j = 2, same epoch); 0 for the first two
//            serial edges.  Every serial edge checked.            -> TB_STX43 PASS mode 0 words <n>
//   +mode=1  stream reset released one stream cycle late; +mode=2 serial reset one serial cycle late;
//   +mode=3  stream reset one epoch + one stream cycle late:  the slip must raise the sticky fault on t_st[3]
//            (f_sn[3] driven 0 in these modes)                   -> TB_STX43 PASS mode <m> fault
module tb_dsfd_capt_status_x43;
    reg ck = 1'b0, ckv = 1'b0;
    initial forever begin #3 ck = 1'b1; #3 ck = 1'b0; end
    initial begin #3 forever begin ckv = 1'b1; #4 ckv = 1'b0; #4; end end
    reg rst = 1'b0, rsv = 1'b0;
    reg [63:0] f_sn = 64'd0;
    wire [63:0] t_st;
    dsfd_capt_status_dual u (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_sn(f_sn), .t_st(t_st));
    integer mode = 0, bad = 0, words = 0, ns = 0, nt = 0, seen_fault = 0;
    reg [63:0] m0 = 0, m2 = 0, m3 = 0, ex = 0;
    reg on_t = 1'b0, on_s = 1'b0;
    // reference model of the sample rule (indices counted from the epoch-aligned release)
    always @(posedge ck) if (on_t) begin
        case (nt % 4) 0: m0 <= f_sn; 2: m2 <= f_sn; 3: m3 <= f_sn; default: ; endcase
        nt <= nt + 1;
    end
    always @(posedge ckv) if (on_s) begin
        if (ns >= 2) case (ns % 3) 0: ex <= m2; 1: ex <= m3; default: ex <= m0; endcase
        ns <= ns + 1;
    end
    // stimulus: new word at every stream negedge
    always @(negedge ck) f_sn <= (mode == 0) ? {$random, $random} : ({$random, $random} & ~64'd8);
    // check at every serial negedge
    always @(negedge ckv) if (on_s && mode == 0 && rsv) begin
        if (t_st !== ex) begin bad = bad + 1; if (bad < 6) $display("TB_STX43 MISMATCH t=%0t ns=%0d got %h exp %h", $time, ns, t_st, ex); end
        else if (ns > 2) words = words + 1;
    end
    always @(negedge ckv) if (mode != 0 && rsv && rst && t_st[3]) seen_fault = 1;
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        // release just before the coincident edge at 24 * 4 + 3 = 99
        #98;
        case (mode)
            0: begin rst = 1; rsv = 1; on_t = 1; on_s = 1; end
            1: begin rsv = 1; on_s = 1; #6 rst = 1; end
            2: begin rst = 1; on_t = 1; #8 rsv = 1; end
            default: begin rsv = 1; #30 rst = 1; end
        endcase
        #(24 * 400);
        if (mode == 0) begin
            if (bad == 0 && words > 1000) $display("TB_STX43 PASS mode 0 words %0d", words);
            else $display("TB_STX43 FAIL mode 0 mismatches %0d words %0d", bad, words);
        end else begin
            if (seen_fault) $display("TB_STX43 PASS mode %0d fault", mode);
            else $display("TB_STX43 FAIL mode %0d no fault on a slipped epoch", mode);
        end
        $finish;
    end
endmodule
