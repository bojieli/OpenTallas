`timescale 1ns/1ps
// a kept clock buffer (keep_hierarchy: the clock-output / forwarded-clock driver stays a cell)
(* keep_hierarchy *)
module ot_s81ph_ckbuf (input wire a, output wire y);
    assign y = a;
endmodule
