`timescale 1ns/1ps
// mtp-lead 2026-10-10: face-clocked output stations (design standard 2026-10-09 ~20:30 PT, gen_ar_fc.py).  Same
// cycle count as ot_hfd_oreg1/2/3: the core stages run on clk, the last stage (the pin flop) on its face clock tap fclk,
// and the zero-logic hop between the two roots goes through a falling-edge lockup on the core root (half a cycle on each
// side of the root crossing; tools/hbm_hub_quarter_gen.py --xroot lockup practice).
(* keep_hierarchy *)
module ot_hfd_oreg1_fc (input wire clk, input wire fclk, input wire d, output reg q);
    reg lk;
    always @(negedge clk) lk <= d;
    always @(posedge fclk) q <= lk;
endmodule
(* keep_hierarchy *)
module ot_hfd_oreg2_fc (input wire clk, input wire fclk, input wire d, output reg q);
    reg s0, lk;
    always @(posedge clk) s0 <= d;
    always @(negedge clk) lk <= s0;
    always @(posedge fclk) q <= lk;
endmodule
(* keep_hierarchy *)
module ot_hfd_oreg3_fc (input wire clk, input wire fclk, input wire d, output reg q);
    reg s0, s1, lk;
    always @(posedge clk) begin s0 <= d; s1 <= s0; end
    always @(negedge clk) lk <= s1;
    always @(posedge fclk) q <= lk;
endmodule
