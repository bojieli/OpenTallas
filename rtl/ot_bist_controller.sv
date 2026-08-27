`timescale 1ns/1ps
// Generic bounded BIST sequencer.  Macro-specific March/signature engines can
// replace the address/data callbacks while preserving ownership, timeout, and
// pass/fail semantics.
module ot_bist_controller #(
    parameter integer DEPTH = 64,
    parameter integer ADDR_W = (DEPTH <= 2) ? 1 : $clog2(DEPTH),
    parameter integer TIMEOUT = 4096
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         start,
    input  wire                         abort,
    input  wire                         resource_ready,
    input  wire                         fault_inject,
    input  wire [31:0]                  observed_word,
    input  wire [31:0]                  expected_word,
    output reg                          busy,
    output reg                          done,
    output reg                          pass,
    output reg [31:0]                   signature,
    output reg [ADDR_W-1:0]             failing_address,
    output reg                          timeout,
    output reg                          owner_test_mode
);
    localparam [1:0] S_IDLE=2'd0, S_RUN=2'd1, S_DONE=2'd2;
    reg [1:0] state;
    reg [ADDR_W-1:0] address;
    reg [31:0] timer;
    reg [31:0] lfsr;
    wire last_address = (address == DEPTH-1);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            address <= 0;
            timer <= 0;
            lfsr <= 32'h1;
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            signature <= 0;
            failing_address <= 0;
            timeout <= 1'b0;
            owner_test_mode <= 1'b0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    owner_test_mode <= 1'b0;
                    if (start && resource_ready) begin
                        state <= S_RUN;
                        busy <= 1'b1;
                        owner_test_mode <= 1'b1;
                        address <= 0;
                        timer <= 0;
                        lfsr <= 32'h1;
                        signature <= 0;
                        pass <= 1'b1;
                        timeout <= 1'b0;
                    end
                end
                S_RUN: begin
                    busy <= 1'b1;
                    owner_test_mode <= 1'b1;
                    if (abort) begin
                        pass <= 1'b0;
                        state <= S_DONE;
                    end else if (fault_inject || (observed_word !== expected_word)) begin
                        pass <= 1'b0;
                        failing_address <= address;
                        signature <= signature ^ observed_word ^ expected_word;
                    end else begin
                        signature <= signature ^ observed_word ^ lfsr;
                    end
                    lfsr <= {lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
                    if (last_address) begin
                        state <= S_DONE;
                    end else begin
                        address <= address + 1'b1;
                    end
                    if (TIMEOUT != 0) begin
                        if (timer >= TIMEOUT) begin
                            timeout <= 1'b1;
                            pass <= 1'b0;
                            state <= S_DONE;
                        end else timer <= timer + 1'b1;
                    end
                end
                S_DONE: begin
                    busy <= 1'b0;
                    owner_test_mode <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
