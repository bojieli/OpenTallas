`timescale 1ns/1ps
module f_skid_buffer;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg in_valid;
    (* anyseq *) reg [3:0] in_data;
    (* anyseq *) reg out_ready;
    wire in_ready, out_valid;
    wire [3:0] out_data;
    wire overflow, underflow;
    wire [1:0] formal_count;
    reg [3:0] model_mem0, model_mem1;
    reg model_wr, model_rd;
    reg [1:0] model_count;
    wire push = in_valid && in_ready;
    wire pop = out_valid && out_ready;

    ot_skid_buffer #(.WIDTH(4),.DEPTH(2)) dut (
        .clk(clk),.rst_n(rst_n),.in_valid(in_valid),.in_ready(in_ready),
        .in_data(in_data),.out_valid(out_valid),.out_ready(out_ready),
        .out_data(out_data),.overflow(overflow),.underflow(underflow),
        .formal_count(formal_count));

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (!rst_n) begin
            model_mem0 <= 0;
            model_mem1 <= 0;
            model_wr <= 1'b0;
            model_rd <= 1'b0;
            model_count <= 2'd0;
        end else begin
            // Producer protocol assumption: a stalled item is retained.
            if (f_past_valid && $past(rst_n && in_valid && !in_ready)) begin
                assume(in_valid);
                assume(in_data == $past(in_data));
            end
            assert(model_count <= 2);
            assert(formal_count == model_count);
            assert(out_valid == (model_count != 0));
            assert(in_ready == ((model_count < 2) || (out_valid && out_ready)));
            if (out_valid)
                assert(out_data == (model_rd ? model_mem1 : model_mem0));
            assert(!overflow && !underflow);
            if (f_past_valid && $past(out_valid && !out_ready)) begin
                assert(out_valid);
                assert(out_data == $past(out_data));
            end
            if (push) begin
                if (model_wr)
                    model_mem1 <= in_data;
                else
                    model_mem0 <= in_data;
                model_wr <= ~model_wr;
            end
            if (pop)
                model_rd <= ~model_rd;
            case ({push,pop})
                2'b10: model_count <= model_count + 1'b1;
                2'b01: model_count <= model_count - 1'b1;
                default: model_count <= model_count;
            endcase
            cover(model_count == 2 && pop && push);
        end
    end
endmodule
