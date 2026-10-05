`timescale 1ns/1ps
// HBM model (ot_qwen_hbm_model_ack) sustained read rate: an in-order 16-sector stream of N sectors, an idle
// gap of IDLE cycles, the same stream again (the second pass meets the all-bank refreshes).  Reports both
// phases in cycles; used by tools/run_qwen_rt_realmem_standalone.py.
module tb_hbm_refresh_stream #(parameter integer NPC=32, parameter integer N=16384, parameter integer IDLE=5000, parameter integer LEN=16, parameter integer OUTS=2048) (input wire clk, input wire rst_n, output reg done, output reg [31:0] c1, output reg [31:0] c2);
    reg req_v; wire req_rdy; reg [23:0] addr; integer issued, got, cyc, phase, t0;
    wire [NPC-1:0] rsp_v;
    ot_qwen_hbm_model_ack #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(262144), .TAGW(10), .LENW(5), .BEATW(4), .CLK_PS(833), .PC_RDY(1), .WR_ACK(1)) u (
        .clk(clk), .rst_n(rst_n), .req_v(req_v), .req_rdy(req_rdy), .pc_room(), .req_we(1'b0), .req_addr(addr), .req_len(5'(LEN)),
        .req_tag(10'd0), .req_wdata(256'd0), .rsp_v(rsp_v), .rsp_rdy({NPC{1'b1}}), .rsp_tag(), .rsp_beat(), .rsp_data(), .rsp_wr());
    always @(posedge clk) begin
        if (!rst_n) begin req_v <= 0; addr <= 0; issued = 0; got = 0; cyc = 0; done <= 0; phase = 0; t0 = 0; end
        else begin
            cyc = cyc + 1;
            got = got + $countones(rsp_v);
            if (req_v && req_rdy) begin issued = issued + LEN; addr <= addr + LEN; end
            if (phase == 0 && got >= N) begin c1 <= cyc - t0; phase = 1; t0 = cyc; end
            if (phase == 1 && cyc - t0 >= IDLE) begin phase = 2; t0 = cyc; issued = 0; got = 0; addr <= 0; end
            if (phase == 2 && got >= N && !done) begin c2 <= cyc - t0; done <= 1; end
            req_v <= (phase != 1) && (issued + (req_v && req_rdy ? LEN : 0) < N) && (issued + (req_v && req_rdy ? LEN : 0) - got < OUTS);
        end
    end
endmodule
