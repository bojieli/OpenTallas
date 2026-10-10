`timescale 1ns/1ps
// Copy of ot_dsrom_mtp_rstsync (rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv) for routes of dsfd_mtp_seq_rtt that do not
// read dsfd_mtp_tops.sv (never compile both).
module ot_dsrom_mtp_rstsync (input wire clk, input wire rst_n_async, output wire rst_n);
    reg [1:0] s;
    always @(posedge clk or negedge rst_n_async) if (!rst_n_async) s <= 2'b00; else s <= {s[0], 1'b1};
    assign rst_n = s[1];
endmodule
