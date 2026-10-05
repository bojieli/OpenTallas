`timescale 1ns/1ps
// SIMULATION ONLY (W17 runtime composition, tools/v41_field_rt_gate.py): the ROM macro ot_rom_8192x274_m8 with
// the same port behaviour as the via-programmed model (a read on ce_in returns the addressed 274-bit word at the
// next edge; the output holds when ce_in is low) but its words served by the runtime host through DPI, so one
// compiled element model serves every element of the field.  The host keys each macro by the calling scope,
// registered once at time 0 with the macro's INSTANCE suffix ("" = the pair's first macro, "b" = the second).
module ot_rom_8192x274_m8 #(parameter string VIAMAP = "", parameter string INSTANCE = "") (
    input  wire clk,
    input  wire ce_in,
    input  wire [12:0] addr_in,
    output reg  [273:0] rd_out
);
    import "DPI-C" context function void v41rt_rom_register(input string inst);
    import "DPI-C" context function void v41rt_rom_read(input int addr, output bit [273:0] q);
    initial v41rt_rom_register(INSTANCE);
    bit [273:0] w;
    always @(posedge clk)
        if (ce_in) begin
            v41rt_rom_read({19'd0, addr_in}, w);
            rd_out <= w;
        end
endmodule
