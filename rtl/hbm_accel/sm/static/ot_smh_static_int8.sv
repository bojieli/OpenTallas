// Opt-in fmt3 adapter. The compiler sends one packed line per two edges.
// Uses the actual arithmetic converter; neither issue nor valid waits on ready.
// Both halves retain the input tag. Scales are applied after reduction by SU.
module ot_smh_static_int8 (
    input wire clk, rst_n,
    input wire [1098:0] packet_in,
    output wire [1098:0] packet_out
);
    wire observed_ready, unused_busy, output_valid;
    wire [1087:0] output_data;
    reg [9:0] held_tag, classify_tag, output_tag;
    ot_hbm_accel_int8_line #(.PIPE(1)) u_actual_converter (
        .clk(clk), .rst_n(rst_n), .int8_mode(1'b1),
        .s_valid(packet_in[1098]), .s_ready(observed_ready),
        .s_data(packet_in[1087:0]), .busy(unused_busy),
        .m_valid(output_valid), .m_ready(1'b1), .m_data(output_data)
    );
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin held_tag <= 0; classify_tag <= 0; output_tag <= 0; end
        else begin
            if (packet_in[1098]) held_tag <= packet_in[1097:1088];
            classify_tag <= packet_in[1098] ? packet_in[1097:1088] : held_tag;
            output_tag <= classify_tag;
        end
    end
    assign packet_out = {output_valid, output_tag, output_data};
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && packet_in[1098] && !observed_ready)
        $fatal(1, "static INT8 compiler calendar overlapped packed lines");
`endif
endmodule
