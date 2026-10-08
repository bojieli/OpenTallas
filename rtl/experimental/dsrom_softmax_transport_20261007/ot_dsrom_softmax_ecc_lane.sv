// Opt-in standalone component; no production parent instantiates this module.
// A memory return is captured before syndrome logic. Corrected data emerges
// three sampled edges from r_valid. SRAM address/control protection is external.
module ot_dsrom_softmax_ecc_lane (
    input wire clk, rst_n,
    input wire w_valid,
    input wire [63:0] w_data,
    output reg w_code_valid,
    output reg [71:0] w_code,
    input wire r_valid,
    input wire [71:0] r_code,
    output wire r_data_valid,
    output reg [63:0] r_data,
    output reg corrected, uncorrectable
);
    import ot_gpu_w6_secded_pkg::*;
    import ot_hbm_accel_r5a_ecc_pkg::*;
    reg [2:0] rv;
    reg [71:0] code0, code1;
    reg [7:0] syndrome1;
    wire [65:0] decoded = finish64(code1, syndrome1);
    assign r_data_valid = rv[2];
    always @(posedge clk) begin
        if (!rst_n) begin
            w_code_valid <= 0;
            rv <= 0;
            corrected <= 0;
            uncorrectable <= 0;
        end else begin
            w_code_valid <= w_valid;
            if (w_valid) w_code <= encode64(w_data);
            rv <= {rv[1:0], r_valid};
            if (r_valid) code0 <= r_code;
            if (rv[0]) begin
                code1 <= code0;
                syndrome1 <= syndrome64(code0);
            end
            if (rv[1]) begin
`ifdef SOFTMAX_ECC_NO_CORRECTION
                r_data <= raw64(code1);
`else
                r_data <= decoded[63:0];
`endif
                corrected <= decoded[64];
                uncorrectable <= decoded[65];
            end
        end
    end
endmodule
