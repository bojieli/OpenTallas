`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_delay_hc: fixed delay line q = d delayed D edges (same function and edge count as ot_hdc_delay #(W, D),
// RESET 0), built so that NO storage hop is a bare flop->flop path on the same clock edge.
//
// Why: a W x D shift line is W*D back-to-back flop->flop hops with no logic.  Under the 25 ps FF hold uncertainty
// plus the 30 ps route repair margin every such hop needs ~2 hold buffers: in hcoll_gq_issue_1018 (two 1,024 x 9
// quantiser lines) the CTS gate inserted 64,598 hold buffers (+15% area, 1 h 50 min of repair) on 23,749 endpoints,
// almost all ot_hbm_xp_aq_tree13 u_x line registers.
//
// Structure (B = D - 1 banks, written in rotation, read through a one-hot AND-OR):
//   xn       negative-edge register of d                      d (posedge reg) -> xn : half-cycle path, hold ~T/2
//   bank[i]  W flops on a gated clock (ot_hdc_cg, one ICG per bank, enabled on the edge the pointer is at i)
//                                                             xn (negedge) -> bank : half-cycle path, hold ~T/2
//   r        output register = OR_i (bank[i] & wp[i])         bank -> AND-OR -> r : >= 3 logic levels
//   wp       one-hot write/read pointer (reset to bank 0), rotates every edge
// Edge n writes bank[wp] with xn = d after edge n-1 and r reads the same bank's old contents (written B edges ago),
// so q after edge n = d after edge n-D.  Data registers carry no reset, as in ot_hdc_delay; q is undefined for the
// first D edges after reset (validity travels on a separate reset line, as before).
// Requirement: d must settle within half a cycle of the rising edge (it is a register output in every user).
// Storage = W*(D+1) flops (one extra W-bit negedge register) + B ICGs; no recirculating enable muxes (the ICGs do
// the enabling), so the banks have no self-loop hold paths either.
// MUT (bench mutant): 1 = one bank too few (delay D-1).
// GATED (HBM-GQISSUE2 10-19): 1 (default, as before) = banks on ICG-gated clocks. 0 = banks on the plain clock with a
// load enable (bk <= wp[i] ? xn : bk). Routed hcoll_gq_issue_1018-r2-a481cc848 (GATED 1): the 16 gated bank sub-trees
// (cg_pushdown x32 ICG copies each) arrived ~70 ps EARLIER than the ungated read register r at FF (gated bank 240 ps,
// r 310 ps), so bank -> AND-OR -> r failed hold by up to -27.7 ps (1,445 endpoints), and the ICG enables (wp, ~rst_n)
// failed setup by up to -72 ps against the ICG's early clock pin. With GATED 0 bank and r share one tree (no
// insertion step), the self-load loop is a same-flop path (skew 0) and wp -> bank is a full-cycle mux select.
// Function and edge count identical (same wp rotation, same xn half-cycle hop).
// ---------------------------------------------------------------------------
module ot_hdc_delay_hc #(
    parameter integer W = 32,
    parameter integer D = 9,           // >= 3
    parameter integer MUT = 0,
    parameter integer GATED = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer B = D - 1 - ((MUT == 1) ? 1 : 0);
    reg [W-1:0] xn;
    always @(negedge clk) xn <= d;
    reg [B-1:0] wp;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) wp <= {{(B-1){1'b0}}, 1'b1};
        else wp <= {wp[B-2:0], wp[B-1]};
    wire [B-1:0]   gk;
    wire [W*B-1:0] bank;               // bank i = bank[i*W +: W] (separate registers, no memory inference)
    genvar i;
    generate
        for (i = 0; i < B; i = i + 1) begin : g_bank
            reg [W-1:0] bk;
            if (GATED != 0) begin : g_icg
                ot_hdc_cg u_cg (.clk(clk), .en(wp[i] | ~rst_n), .gclk(gk[i]));
                always @(posedge gk[i]) bk <= xn;
            end else begin : g_en
                assign gk[i] = 1'b0;
                always @(posedge clk) if (wp[i]) bk <= xn;      // plain clock: no reset clocking needed
            end
            assign bank[i*W +: W] = bk;
        end
    endgenerate
    reg [W-1:0] r, sel;
    always @(*) begin
        sel = {W{1'b0}};
        for (integer k = 0; k < B; k = k + 1) sel = sel | (bank[k*W +: W] & {W{wp[k]}});
    end
    always @(posedge clk) r <= sel;
    assign q = r;
endmodule
