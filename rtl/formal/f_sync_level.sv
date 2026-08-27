`timescale 1ns/1ps
module f_sync_level;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg async_in;
    wire sync_out;
    wire formal_sync_ff2;
    wire formal_candidate;
    wire [1:0] formal_stable_count;

    ot_sync_level #(.WIDTH(1),.QUAL_CYCLES(3)) dut (
        .clk(clk), .rst_n(rst_n), .async_in(async_in),
        .sync_out(sync_out), .formal_sync_ff2(formal_sync_ff2),
        .formal_candidate(formal_candidate),
        .formal_stable_count(formal_stable_count));

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (rst_n && f_past_valid) begin
            assert(formal_stable_count <= 3);
            // Qualification is intentionally against the second synchronizer
            // stage, not the raw asynchronous pin.  A raw pin may change again
            // while an already-qualified value propagates to the output.
            if (sync_out != $past(sync_out)) begin
                assert(formal_candidate == sync_out);
                assert(formal_stable_count == 3);
            end
            cover(sync_out);
            cover($past(sync_out) && !sync_out);
        end
    end
endmodule
