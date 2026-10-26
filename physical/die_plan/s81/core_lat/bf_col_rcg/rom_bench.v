// bench-only ROM model: registered read of a deterministic address hash (same in both builds)
module ot_rom_4096x274_m8 #(parameter string VIAMAP = "", parameter string INSTANCE = "") (
    input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [273:0] rd_out);
    integer i; reg [31:0] h;
    always @(posedge clk) if (ce_in) begin
        h = {20'h9e377, addr_in} ^ (INSTANCE == "" ? 32'h0 : 32'h5bd1e995);
        for (i = 0; i < 274; i = i + 1) begin h = h ^ (h << 13); h = h ^ (h >> 17); h = h ^ (h << 5); rd_out[i] <= h[7]; end
    end
endmodule
