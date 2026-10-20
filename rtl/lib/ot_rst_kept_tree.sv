`timescale 1ns/1ps
// Registered reset DISTRIBUTION tree with KEPT copies (LH-K9R 2026-10-19, owner SAFE-DESIGN checklist items 1 + 3:
// "reset lands in 2 registered stages at the face; no register drives > ~32 loads; kept copies verified post-Yosys").
//
// Use it AFTER the face landing (ref_tile "reset_landing": port -> rl0 -> rl1 on the landing clock, ot_pin_regs.tcl): the
// input is already a synchronous, registered reset, so this tree is two plain-D register levels (no asynchronous clear,
// no synchroniser of its own):
//   level A: NA kept identical copies ra[NA-1:0]  <= rst_n_in        (rst_n_in drives NA <= 32 D pins)
//   level B: NB kept identical copies rb[NB-1:0]  <= ra[0]           (RTL text; see below)
//   rst_n = rb[0]                                                     (RTL text; see below)
// In RTL every load hangs off copy 0 (one reset pin per consumer).  Synthesis spreads them: ot_keep_regs.tcl keeps every
// copy flop (no opt_merge fold), then ot_rst_copies.tcl / ot_rst_copies.py (spec "reset_relay_split", family regexp
// "u_fl_rst_<name>.ra|rb") PROVES the copies of each level are identical registers (same type / clock / D) and re-points
// the level-B D pins over the NA level-A copies and the consumers' reset loads over the NB level-B copies, <= max_loads
// each.  With OT_RST_COPIES_SDFF=1 the consumers' synchronous resets are first folded into $sdff SRST ports (opt_dff), so
// one coarse load = one mapped AND/NAND gate per flop bit and the split holds on the mapped netlist (census:
// textbook_lint --set hf_report=32 on 1_2_yosys.v).  Re-pointing a load between identical registers cannot change the
// function.
//
// Timing contract: assertion and release reach the consumers 2 clk edges after rst_n_in (a scheduled constant; consumers
// never count cycles from the port).  The clock must run during reset.  Instance names must be bracket-free
// (u_fl_rst_<name>, no generate index) so the copy pass can address every copy bit.
module ot_rst_kept_tree #(
    parameter integer NA = 8,
    parameter integer NB = 128
) (
    input  wire clk,
    input  wire rst_n_in,
    output wire rst_n
);
    (* keep = "true", dont_touch = "true" *) reg [NA-1:0] ra;
    (* keep = "true", dont_touch = "true" *) reg [NB-1:0] rb;
    always @(posedge clk) ra <= {NA{rst_n_in}};
    always @(posedge clk) rb <= {NB{ra[0]}};
    assign rst_n = rb[0];
`ifndef SYNTHESIS
    initial if (NA < 1 || NB < 1 || NB > 32 * NA) $error("ot_rst_kept_tree: need 1 <= NA, 1 <= NB <= 32*NA");
`endif
endmodule
