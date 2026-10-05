`timescale 1ns/1ps
module f_async_fifo;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg wr_valid;
    (* anyseq *) reg [3:0] wr_data;
    (* anyseq *) reg rd_ready;
    wire wr_ready, rd_valid;
    wire [3:0] rd_data;
    wire wr_overflow, rd_underflow;
    wire push = wr_valid && wr_ready;
    wire pop = rd_valid && rd_ready;

    reg [3:0] model_mem0, model_mem1, model_mem2, model_mem3;
    reg [1:0] model_wr, model_rd;
    reg [2:0] model_count;
    reg [3:0] expected_head;

    ot_async_fifo #(.WIDTH(4), .DEPTH(4)) dut (
        .wr_clk(clk), .wr_rst_n(rst_n), .wr_valid(wr_valid),
        .wr_ready(wr_ready), .wr_data(wr_data), .wr_overflow(wr_overflow),
        .rd_clk(clk), .rd_rst_n(rst_n), .rd_valid(rd_valid),
        .rd_ready(rd_ready), .rd_data(rd_data), .rd_underflow(rd_underflow)
    );

    always @* begin
        case (model_rd)
            2'd0: expected_head = model_mem0;
            2'd1: expected_head = model_mem1;
            2'd2: expected_head = model_mem2;
            default: expected_head = model_mem3;
        endcase
    end

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (!rst_n) begin
            model_mem0 <= 0;
            model_mem1 <= 0;
            model_mem2 <= 0;
            model_mem3 <= 0;
            model_wr <= 0;
            model_rd <= 0;
            model_count <= 0;
        end else begin
            if (f_past_valid && $past(rst_n && wr_valid && !wr_ready)) begin
                assume(wr_valid);
                assume(wr_data == $past(wr_data));
            end
            assert(model_count <= 4);
            assert(!wr_overflow && !rd_underflow);
            if (rd_valid) begin
                assert(model_count != 0);
                assert(rd_data == expected_head);
            end
            if (f_past_valid && $past(rd_valid && !rd_ready)) begin
                assert(rd_valid);
                assert(rd_data == $past(rd_data));
            end
            if (push) begin
                assert(model_count < 4);
                case (model_wr)
                    2'd0: model_mem0 <= wr_data;
                    2'd1: model_mem1 <= wr_data;
                    2'd2: model_mem2 <= wr_data;
                    default: model_mem3 <= wr_data;
                endcase
                model_wr <= model_wr + 1'b1;
            end
            if (pop) begin
                assert(model_count != 0);
                model_rd <= model_rd + 1'b1;
            end
            case ({push,pop})
                2'b10: model_count <= model_count + 1'b1;
                2'b01: model_count <= model_count - 1'b1;
                default: model_count <= model_count;
            endcase
            cover(!wr_ready && wr_valid);
            cover(rd_valid && !rd_ready);
            cover(push && pop);
        end
    end
endmodule
