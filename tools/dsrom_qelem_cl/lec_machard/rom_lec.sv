// LEC model on both sides: one registered read, each data bit a distinct function of clock-enable and address; pin map proven through it
module ot_rom_4096x274_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [273:0] rd_out);
    integer i;
    reg [273:0] w;
    always @* for (i = 0; i < 274; i = i + 1) w[i] = addr_in[i % 12] ^ addr_in[(i / 12) % 12] ^ (i % 7 == 0);
    always @(posedge clk) if (ce_in) rd_out <= w;
endmodule
