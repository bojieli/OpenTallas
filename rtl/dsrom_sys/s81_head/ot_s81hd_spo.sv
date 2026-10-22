`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81hd_spo (S81-HEAD HD-TILE 10-21; SPEC.md section 2): spine out node of the S81 release head die.  A registered
// 3-way forward of bus B (565 b, see ot_s81hd_tile): o (next spine level / spine U-turn), ow / oe (W / E row-pair
// chain starts).  The three output registers are KEPT identical copies that capture the input pins directly: every
// input bit drives 3 flops, every output leaves its own flop (one cycle, no combinational in -> out path).
// Reset: go / xv / rv of each copy only (datapath unreset); the 2-stage landing is the kit's.
// ---------------------------------------------------------------------------
module ot_s81hd_spo (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [564:0] i,
    output wire [564:0] o,
    output wire [564:0] ow,
    output wire [564:0] oe
);
    wire [564:0] oc [0:2];
    genvar c;
    generate for (c = 0; c < 3; c = c + 1) begin : g_c
        (* keep *) reg [2:0]   ctl_q;       // {rv, xv, go}
        (* keep *) reg [511:0] x_q;
        (* keep *) reg [49:0]  r_q;         // {flt, bits, row}
        always @(posedge ck or negedge rst_n)
            if (!rst_n) ctl_q <= 3'd0;
`ifdef OT_S81HD_MUT_SPO_OW_DROP
            else ctl_q <= (c == 1) ? {i[514:513], 1'b0} : i[514:512];   // MUTANT: ow copy drops go
`else
            else ctl_q <= i[514:512];
`endif
        always @(posedge ck) begin x_q <= i[511:0]; r_q <= i[564:515]; end
        assign oc[c] = {r_q, ctl_q, x_q};
    end endgenerate
    assign o  = oc[0];
    assign ow = oc[1];
    assign oe = oc[2];
endmodule
