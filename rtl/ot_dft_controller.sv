`timescale 1ns/1ps
// DFT/test ownership interlock.  Test clocks and scan access are granted only
// after service quiescence; ordinary service admission is forced low while a
// BIST or scan operation owns the resource.
module ot_dft_controller #(
    parameter [31:0] IDCODE = 32'h4f54_0100
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        test_request,
    input  wire        service_active,
    input  wire        service_quiesced,
    input  wire        scan_enable_request,
    input  wire        bist_start_request,
    input  wire        bist_busy,
    input  wire        bist_done,
    input  wire        bypass_select,
    output reg         test_mode,
    output reg         scan_enable,
    output reg         bist_start,
    output wire        test_access_grant,
    output wire        service_isolated,
    output wire [31:0] idcode,
    output wire        bypass_active
);
    reg [1:0] state;
    localparam [1:0] S_FUNC=2'd0, S_ARM=2'd1, S_TEST=2'd2;
    assign test_access_grant = (state == S_TEST);
    assign service_isolated = test_access_grant || bist_busy;
    assign idcode = IDCODE;
    assign bypass_active = bypass_select && !test_mode;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_FUNC;
            test_mode <= 1'b0;
            scan_enable <= 1'b0;
            bist_start <= 1'b0;
        end else begin
            bist_start <= 1'b0;
            case (state)
                S_FUNC: begin
                    test_mode <= 1'b0;
                    scan_enable <= 1'b0;
                    if (test_request && !service_active)
                        state <= S_ARM;
                end
                S_ARM: begin
                    if (service_active && !service_quiesced) begin
                        state <= S_FUNC;
                    end else begin
                        test_mode <= 1'b1;
                        state <= S_TEST;
                    end
                end
                S_TEST: begin
                    test_mode <= 1'b1;
                    scan_enable <= scan_enable_request;
                    if (bist_start_request && !bist_busy)
                        bist_start <= 1'b1;
                    if (!test_request && !bist_busy && !scan_enable_request && (bist_done || !bist_start_request)) begin
                        test_mode <= 1'b0;
                        state <= S_FUNC;
                    end
                end
                default: state <= S_FUNC;
            endcase
        end
    end
endmodule
