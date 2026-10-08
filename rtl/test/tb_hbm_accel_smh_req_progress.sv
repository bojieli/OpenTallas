`timescale 1ns/1ps
// A hub grants this client every other cycle. Sixteen finite requests must all
// complete under either grant phase. USE_RETRY=1 is the rejected m3c negative:
// its final request repeats forever on the denied phase (16 sent, 15 accepted).
module tb_hbm_accel_smh_req_progress;
    parameter integer USE_RETRY = 0;
    reg clk = 0, rst_n = 0, sv = 0, mr = 0;
    always #5 clk = ~clk;
    wire sr, mv;
    reg [41:0] sd = 0;
    wire [41:0] md;
    generate if (USE_RETRY) begin : g_retry
        ot_hbm_accel_smh_oreq #(.W(42)) dut
            (.clk(clk), .rst_n(rst_n), .s_valid(sv), .s_ready(sr),
             .s_data(sd), .m_valid(mv), .m_ready(mr), .m_data(md));
    end else begin : g_fifo
        ot_hbm_accel_smh_oskid #(.W(42)) dut
            (.clk(clk), .rst_n(rst_n), .s_valid(sv), .s_ready(sr),
             .s_data(sd), .m_valid(mv), .m_ready(mr), .m_data(md));
    end endgenerate
    integer i, phase, sent, received;
    reg [15:0] pending;
    initial begin
        for (phase = 0; phase < 2; phase = phase + 1) begin
            @(negedge clk); rst_n = 0; sv = 0; mr = 0;
            repeat (3) @(negedge clk);
            sent = 0; received = 0; pending = 0; rst_n = 1;
            // 256 grants is ample for 16 requests through either two/four-slot
            // queue; this is a finite directed test, not a job wall-time limit.
            for (i = 0; i < 512; i = i + 1) begin
                @(negedge clk); sv = sent < 16; sd = sent; mr = i[0] ^ phase[0];
                @(posedge clk);
                if (mv && mr) begin
                    if (md >= 16 || !pending[md]) $fatal(1, "REQ_PROGRESS duplicate/corrupt request %0d", md);
                    pending[md] = 0; received = received + 1;
                end
                if (sv && sr) begin pending[sent] = 1; sent = sent + 1; end
            end
            $display("REQ_PROGRESS retry=%0d phase=%0d sent=%0d received=%0d pending=%h",
                     USE_RETRY, phase, sent, received, pending);
            if (sent != 16 || received != 16)
                $fatal(1, "REQ_PROGRESS starvation under periodic ready");
        end
        $display("REQ_PROGRESS PASS");
        $finish;
    end
endmodule
