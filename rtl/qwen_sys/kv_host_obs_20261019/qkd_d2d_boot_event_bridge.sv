`timescale 1ns/1ps
// Exceptional boot ordering only. installed is the accepted programme/all-images predicate.
// Default legacy mode and configured-before-request edges are unchanged. HBM boot_go is untouched.
module qkd_d2d_boot_event_bridge #(parameter integer ENABLE = 0) (
    input wire ck, rst_n, request, installed,
    output wire boot_begin
);
    generate if (ENABLE == 0) begin : g_legacy
        assign boot_begin = request;
    end else begin : g_ordered
        reg pending;
        assign boot_begin = installed && (request || pending);
        always @(posedge ck or negedge rst_n)
            if (!rst_n) pending <= 1'b0;
            else if (boot_begin) pending <= 1'b0;
            else if (request) pending <= 1'b1;
    end endgenerate
endmodule
