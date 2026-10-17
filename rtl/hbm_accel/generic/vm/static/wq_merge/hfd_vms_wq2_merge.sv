`timescale 1ns/1ps
`default_nettype none
// H-SM 1815 (coordinator verdict 10-16): q2 (NW) VM bank write-port merge leaf.
// The NW bank was the q0 master + a third wide write port wq2 (hb_quant_NW).  q2 B/D/E/F kits all failed
// (GRT-0116 at the u_b/u_c channel mouths; F routed TT -93.6 / FF -46.5).  This leaf moves wq2 OUT of the bank:
// the NW banks become the exact q0 master (hfd_vms_bank_native_q0_faces, WG=2) and this leaf, beside each bank,
// presents wq1 (SM writer smw_NW) and wq2 (quantiser hb_quant_NW) on the bank's single wq1 port.
// STATIC, fixed-cycle: the compiler's VM calendar already grants at most ONE write source per bank per edge (the bank
// ORs valid-masked write leaves under that rule); here the two sources are merged by the same valid-masked OR, one
// two edges (pin flop + merge flop; +2 edges on both write paths, the compiler issues them two edges earlier).  The calendar addresses both as
// bank write owner 1 (q2 owner codes: 2 -> 1, k >= 3 -> k - 1: a compiler table, no hardware remap).
// Done: the bank's wq_done1 comes DONE_LAT edges after the merged write leaves this leaf; a fixed shift register of
// the source id (no FIFO, no credit) steers it to wq_done1 / wq_done2 (+1 edge).
// A cycle with both sources valid is a compiler schedule error: sticky flt (status), never arbitration.
// Regional synchronous reset: 2-flop synchroniser + 1 relay flop, synchronous clear of the control flops only.
module hfd_vms_wq2_merge #(
    parameter integer DONE_LAT = 5,
    parameter integer MUT = 0     // 1: done steering one edge late, 2: wq2 payload bit 0 dropped
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [280:0] wq1,       // SM writer (bit 280 = valid)
    input  wire [280:0] wq2,       // quantiser (bit 280 = valid)
    output wire [280:0] wq_m,      // to the q0-master bank's wq1 port
    input  wire         done_m,    // bank wq_done1
    output reg          wq_done1,
    output reg          wq_done2,
    output reg          flt
);
    (* async_reg = "true" *) reg rs1, rs2;
    reg rn;  // relay: the only sync-reset driver of the leaf
    always @(posedge clk) begin rs1 <= rst_n; rs2 <= rs1; rn <= rs2; end

    // Stage A: every input pin is captured by exactly one flop (gate 2e16db389: the raw valid pins fanned out to 283
    // mask loads each).  The valid is captured into REP replicas, one per 35-bit payload slice.
    localparam integer REP = 8, SL = 35;  // 8 x 35 = 280 payload bits
    reg [279:0] a_d, b_d;
    reg [REP-1:0] a_v, b_v;
    always @(posedge clk) begin a_d <= wq1[279:0]; b_d <= wq2[279:0]; end
    always @(posedge clk)
        if (!rn) begin a_v <= '0; b_v <= '0; end
        else begin a_v <= {REP{wq1[280]}}; b_v <= {REP{wq2[280]}}; end
    wire [279:0] p2 = (MUT == 2) ? {b_d[279:1], 1'b0} : b_d;
    // Stage B: valid-masked OR into the output flops (each replica masks one slice).
    reg [279:0] m_d;
    reg m_v, m_src;
    always @(posedge clk)
        for (integer s = 0; s < REP; s = s + 1)
            m_d[s*SL +: SL] <= ({SL{a_v[s]}} & a_d[s*SL +: SL]) | ({SL{b_v[s]}} & p2[s*SL +: SL]);
    always @(posedge clk)
        if (!rn) begin m_v <= 1'b0; m_src <= 1'b0; end
        else begin m_v <= a_v[0] | b_v[0]; m_src <= b_v[0]; end
    assign wq_m = {m_v, m_d};

    localparam integer DL = (MUT == 1) ? DONE_LAT + 1 : DONE_LAT;
    reg [DL:1] sh;
    always @(posedge clk)
        if (!rn) sh <= '0;
        else sh <= {sh[DL-1:1], m_src};
    always @(posedge clk)
        if (!rn) begin wq_done1 <= 1'b0; wq_done2 <= 1'b0; flt <= 1'b0; end
        else begin
            wq_done1 <= done_m && !sh[DL];
            wq_done2 <= done_m && sh[DL];
            if (a_v[0] && b_v[0]) flt <= 1'b1;
        end
endmodule
`default_nettype wire
