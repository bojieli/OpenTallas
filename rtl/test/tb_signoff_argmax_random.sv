`timescale 1ns/1ps
// Sign-off calibration bench (tools/signoff_analysis.py, configs/signoff/rom_fabric.json):
// random logits and flags into ot_rom_argmax_reduce for 2,000 cycles, simulated
// once gate-level on the routed netlist and once as RTL, so the error of
// RTL-name activity mapping plus OpenSTA propagation is measured against
// gate-level activity on the same stimulus.
module tb_signoff_argmax_random (input wire clk);
    reg rst_n = 0;
    reg [31:0] cyc = 0;
    reg [511:0] lg_data, up_data;
    reg lg_valid, lg_last, up_valid, up_last, dn_ready;
    reg [15:0] lg_mask; reg [31:0] lg_base; reg [7:0] lg_tag;
    wire lg_ready, up_ready, dn_valid, dn_last, fault;
    wire [511:0] dn_data; wire [31:0] tokens_out;
    ot_rom_argmax_reduce dut (.clk(clk), .rst_n(rst_n), .lg_valid(lg_valid), .lg_ready(lg_ready),
        .lg_data(lg_data), .lg_mask(lg_mask), .lg_base(lg_base), .lg_tag(lg_tag), .lg_last(lg_last),
        .up_valid(up_valid), .up_ready(up_ready), .up_data(up_data), .up_last(up_last),
        .dn_valid(dn_valid), .dn_ready(dn_ready), .dn_data(dn_data), .dn_last(dn_last),
        .tokens_out(tokens_out), .fault(fault));
    integer i;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1;
        for (i = 0; i < 16; i = i + 1) lg_data[32*i +: 32] <= $random;
        for (i = 0; i < 16; i = i + 1) up_data[32*i +: 32] <= $random;
        lg_valid <= $random; lg_last <= $random; up_valid <= 0; up_last <= $random; dn_ready <= 1;
        lg_mask <= $random; lg_base <= $random; lg_tag <= $random;
        if (cyc == 2000) begin $display("done tokens=%0d fault=%0d", tokens_out, fault); $finish; end
    end
endmodule
