`timescale 1ns/1ps
module f_credit_manager;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg reserve_valid;
    (* anyseq *) reg [2:0] reserve_mask;
    (* anyseq *) reg release_valid;
    (* anyseq *) reg [2:0] release_mask;
    wire reserve_ready;
    wire [8:0] free_count;
    wire overflow_error, underflow_error, conservation_error;
    reg [2:0] outstanding [0:2];
    integer i;
    reg [3:0] next_outstanding;
    wire reserve_fire = reserve_valid && reserve_ready;

    ot_credit_manager #(.SINKS(3),.DEPTH(4),.CREDIT_W(3)) dut (
        .clk(clk),.rst_n(rst_n),.reserve_valid(reserve_valid),
        .reserve_ready(reserve_ready),.reserve_mask(reserve_mask),
        .release_valid(release_valid),.release_mask(release_mask),
        .free_count(free_count),.overflow_error(overflow_error),
        .underflow_error(underflow_error),.conservation_error(conservation_error));

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (!rst_n) begin
            for (i=0;i<3;i=i+1)
                outstanding[i] <= 0;
        end else begin
            // The environment may only release transactions it owns.
            for (i=0;i<3;i=i+1)
                if (release_valid && release_mask[i])
                    assume(outstanding[i] != 0);
            for (i=0;i<3;i=i+1) begin
                assert(outstanding[i] <= 4);
                assert(free_count[i*3 +: 3] + outstanding[i] == 4);
                next_outstanding = outstanding[i];
                if (release_valid && release_mask[i])
                    next_outstanding = next_outstanding - 1'b1;
                if (reserve_fire && reserve_mask[i])
                    next_outstanding = next_outstanding + 1'b1;
                outstanding[i] <= next_outstanding[2:0];
            end
            assert(!overflow_error && !underflow_error && !conservation_error);
            cover((outstanding[0] == 4) && release_valid && release_mask[0] &&
                  reserve_fire && reserve_mask[0]);
        end
    end
endmodule
