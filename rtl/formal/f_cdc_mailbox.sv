`timescale 1ns/1ps
module f_cdc_mailbox;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg src_valid;
    (* anyseq *) reg [7:0] src_data;
    (* anyseq *) reg dst_ready;
    (* anyseq *) reg [2:0] dst_response;
    wire src_ready, src_done;
    wire [2:0] src_response;
    wire dst_valid;
    wire [7:0] dst_data;

    reg model_outstanding;
    reg model_delivered;
    reg [7:0] model_payload;
    reg [2:0] model_response;
    reg [2:0] accepted_count;
    reg [2:0] delivered_count;
    reg [2:0] done_count;

    ot_cdc_mailbox #(.WIDTH(8),.RESPONSE_W(3)) dut (
        .src_clk(clk), .src_rst_n(rst_n), .src_valid(src_valid),
        .src_ready(src_ready), .src_data(src_data), .src_done(src_done),
        .src_response(src_response), .dst_clk(clk), .dst_rst_n(rst_n),
        .dst_valid(dst_valid), .dst_ready(dst_ready), .dst_data(dst_data),
        .dst_response(dst_response));

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (!rst_n) begin
            model_outstanding <= 1'b0;
            model_delivered <= 1'b0;
            model_payload <= 8'b0;
            model_response <= 3'b0;
            accepted_count <= 3'b0;
            delivered_count <= 3'b0;
            done_count <= 3'b0;
        end else begin
            // Standard source ready/valid stability assumption.
            if (f_past_valid && $past(rst_n && src_valid && !src_ready)) begin
                assume(src_valid);
                assume(src_data == $past(src_data));
            end

            assert(delivered_count <= accepted_count);
            assert(done_count <= delivered_count);
            assert(accepted_count - done_count <= 1);
            if (src_ready)
                assert(!model_outstanding);

            if (src_valid && src_ready) begin
                assert(!model_outstanding);
                model_outstanding <= 1'b1;
                model_delivered <= 1'b0;
                model_payload <= src_data;
                accepted_count <= accepted_count + 1'b1;
            end

            if (dst_valid) begin
                assert(model_outstanding);
                assert(!model_delivered);
                assert(dst_data == model_payload);
            end
            if (f_past_valid && $past(rst_n && dst_valid && !dst_ready)) begin
                assert(dst_valid);
                assert(dst_data == $past(dst_data));
            end
            if (dst_valid && dst_ready) begin
                assert(model_outstanding && !model_delivered);
                model_delivered <= 1'b1;
                model_response <= dst_response;
                delivered_count <= delivered_count + 1'b1;
            end

            if (src_done) begin
                assert(model_outstanding && model_delivered);
                assert(src_response == model_response);
                model_outstanding <= 1'b0;
                model_delivered <= 1'b0;
                done_count <= done_count + 1'b1;
            end
            if (f_past_valid && $past(src_done))
                assert(!src_done);

            cover(dst_valid && !dst_ready);
            cover(src_done && (src_response == 3'b101));
            cover(done_count >= 2);
        end
    end
endmodule
