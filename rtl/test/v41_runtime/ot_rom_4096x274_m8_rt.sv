`timescale 1ns/1ps
// Simulation-only PP adapter. Host images stay logical 8192-word banks.
// The element owns the PP capture registers; this macro retains one-edge read/hold.
module ot_rom_4096x274_m8 #(parameter string VIAMAP = "", parameter string INSTANCE = "") (
    input wire clk,
    input wire ce_in,
    input wire [11:0] addr_in,
    output reg [273:0] rd_out
);
    import "DPI-C" context function void v41rt_rom_register(input string inst);
    import "DPI-C" context function void v41rt_rom_read(input int addr, output bit [273:0] q);
    string logical_instance;
    integer parity;
    bit [273:0] w;
    initial begin
        if (INSTANCE.len() < 2 || INSTANCE[INSTANCE.len()-2] != "_" ||
            (INSTANCE[INSTANCE.len()-1] != "0" && INSTANCE[INSTANCE.len()-1] != "1"))
            $fatal(1, "PP INSTANCE must end in _0 or _1");
        parity = (INSTANCE[INSTANCE.len()-1] == "1");
        logical_instance = INSTANCE.len() == 2 ? "" : INSTANCE.substr(0, INSTANCE.len()-3);
        v41rt_rom_register(logical_instance);
    end
    always @(posedge clk)
        if (ce_in) begin
            v41rt_rom_read(2 * int'(addr_in) + parity, w);
            rd_out <= w;
        end
endmodule
