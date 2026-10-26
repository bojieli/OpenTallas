// LEC stubs (S81-CORE-LAT-R2/LV): the ICG cell as its function (GCLK = CLK & (ENA | SE); latch omitted -- the same
// model on both sides, the gated clock is itself a compared signal), the ROM macros as black boxes (equiv_struct
// merges the old / new macro cells once their input pins are proved equal: input pins = compare points, output pins =
// shared free inputs, as tools/die_plan/lec.py does).
module ICGx1_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK);
  assign GCLK = CLK & (ENA | SE);
endmodule
(* blackbox *)
module ot_rom_4096x274_m8 #(parameter INSTANCE = "") (input clk, input ce_in, input [11:0] addr_in, output [273:0] rd_out);
endmodule
(* blackbox *)
module ot_rom_8192x274_m8 #(parameter INSTANCE = "") (input clk, input ce_in, input [12:0] addr_in, output [273:0] rd_out);
endmodule
