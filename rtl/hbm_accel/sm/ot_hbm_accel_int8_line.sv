// Opt-in registered line adapter. Signed INT8 has an exact BF16 representation.
// 128 packed codes become two consecutive 64-lane BF16 beats, low half first.
// Sidecars are zero for fmt3: row scales are applied by SU after the FP32 sum.
// Mode must remain stable until the operation's issued beats have drained.
module ot_hbm_accel_int8_line (
    input wire clk, rst_n, int8_mode,
    input wire s_valid,
    output wire s_ready,
    input wire [1087:0] s_data,
    output reg m_valid,
    input wire m_ready,
    output reg [1087:0] m_data
);
    reg pending;
    reg [511:0] high_codes;
    wire capacity = !m_valid || m_ready;
    assign s_ready = capacity && !pending;
    wire [511:0] codes = pending ? high_codes : s_data[511:0];
    function automatic [15:0] to_bf16(input [7:0] code);
        reg [7:0] mag, shifted;
        reg [7:0] exponent;
        integer bit_index, top;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            top = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) top = bit_index;
            exponent = 8'd127 + top;
            shifted = mag << (7 - top);
            to_bf16 = (mag == 0) ? 16'd0 : {code[7], exponent, shifted[6:0]};
        end
    endfunction
    wire [1023:0] widened;
    genvar lane;
    generate for (lane = 0; lane < 64; lane = lane + 1) begin : g_lane
`ifdef OT_INT8_MUT_SIGN
        assign widened[16*lane +: 16] = to_bf16(codes[8*lane +: 8] & 8'h7f);
`else
        assign widened[16*lane +: 16] = to_bf16(codes[8*lane +: 8]);
`endif
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m_valid <= 1'b0; pending <= 1'b0; end
        else if (capacity) begin
            m_valid <= pending || s_valid;
            if (pending) begin
                m_data <= {64'd0, widened};
                pending <= 1'b0;
            end else if (s_valid) begin
                if (int8_mode) begin
                    m_data <= {64'd0, widened};
                    high_codes <= s_data[1023:512];
                    pending <= 1'b1;
                end else m_data <= s_data;
            end
        end
    end
endmodule
