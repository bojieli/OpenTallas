// Physical fixture (not a design block): one forwarded-clock link HOP of rtl/common/ot_fwd_link_stage.sv.
// Stage A at the west edge launches data on the falling edge of fclk_i and forwards fclk_o = ~fclk_i; stage B at
// the east edge (>= 430.56 um away, fwd_hop2_fences.tcl) is clocked ONLY by that forwarded clock, which travels the
// span beside the data bus through placed repeaters (B's own CTS subtree is rooted at the last one), and captures on its falling edge.  So the
// A -> B register-to-register arc is the hop as a chain of link stages sees it: no output-delay placeholder, and
// the forwarded clock's real wire/buffer delay is in the capture path.  B's synchronous reset is tied inactive
// (a chain carries reset as a pipelined static control, not on this hop's timing).
module ot_fwd_link_hop2 #(parameter integer W = 512, parameter bit ENABLE = 1) (
    input  wire         fclk_i,
    input  wire         rst_n,
    input  wire         i_v,
    input  wire [W-1:0] i_d,
    output wire         fclk_o,
    output wire         o_v,
    output wire [W-1:0] o_d
);
    wire         fa;
    wire         va;
    wire [W-1:0] da;
    ot_fwd_link_stage #(.W(W), .ENABLE(ENABLE)) u_a (.fclk_i(fclk_i), .rst_n(rst_n), .i_v(i_v), .i_d(i_d),
                                                     .fclk_o(fa), .o_v(va), .o_d(da));
    // The forwarded clock's span: six repeaters (kept inverter cells; even count keeps the polarity) that
    // fwd_hop2_fences.tcl places at even pitch along the bus, as the data wire's repeaters are; the last one roots
    // stage B's subtree (fwd_hop2.sdc fwd_a).  Explicit names (no generate brackets) for the SDC.
    wire [6:0] fc;
    assign fc[0] = fa;
    ot_fwd_clk_inv u_rep0 (.a(fc[0]), .y(fc[1]));
    ot_fwd_clk_inv u_rep1 (.a(fc[1]), .y(fc[2]));
    ot_fwd_clk_inv u_rep2 (.a(fc[2]), .y(fc[3]));
    ot_fwd_clk_inv u_rep3 (.a(fc[3]), .y(fc[4]));
    ot_fwd_clk_inv u_rep4 (.a(fc[4]), .y(fc[5]));
    ot_fwd_clk_inv u_rep5 (.a(fc[5]), .y(fc[6]));
    ot_fwd_link_stage #(.W(W), .ENABLE(ENABLE)) u_b (.fclk_i(fc[6]), .rst_n(1'b1), .i_v(va), .i_d(da),
                                                     .fclk_o(fclk_o), .o_v(o_v), .o_d(o_d));
endmodule
