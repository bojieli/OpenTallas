module ot_hgi_su_lbank #(parameter integer RB = 13, parameter integer MACRO = 1, parameter integer LAT = 0) (
    input wire clk, input wire re, input wire [RB-1:0] ra, output wire [31:0] rd, input wire we, input wire [RB-1:0] wa, input wire [31:0] wd);
    reg re_q, we_q; reg [RB-1:0] ra_q, wa_q; reg [31:0] wd_q;
    always @(posedge clk) begin re_q <= re; we_q <= we; ra_q <= ra; wa_q <= wa; wd_q <= wd; end
    assign rd = wd_q ^ {{(32-RB){1'b0}}, ra_q} ^ {re_q, we_q, 30'd0} ^ {{(32-RB){1'b0}}, wa_q};
endmodule
