`timescale 1ns/1ps
// DIE-QC-97 11-10 (COORD): registered-read scale-wait SRAM delay for the sle_st_b_v2 station regions only.
// Hand-written next to the qfd_dv_s8s_* safe copies (their named generator gen_s8_station_safe.py is not in the tree);
// qfd_dv_s8_station_safe.sv is NOT changed.  Same ports, latency D and warm mask as qfd_dv_s8s_sram_delay, but the
// SRAM is read one edge earlier (ra = wp - (D-2), != wp for D >= 3) and rd_out lands in an unreset flop (PIN CYCLES 0;
// the form of qfd_dv_sram_delay_orq, QC-TYPES-12).  The macro keeps its instance path u_m.g_bank[0].u_m.
// Bench mutants: MUT 1 = read address off by one, MUT 2 = flop bypassed (both must fail the lock-step bench).
module qfd_dv_s8s_sram_delay_orq #(parameter integer W = 514, parameter integer D = 14, parameter integer MUT = 0, parameter integer G = 12) (
    input wire ck, rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    reg [4:0] wp;
    reg [D-2:0] valid;
    wire mask_reset;
    (* keep_hierarchy = "yes" *) qfd_dv_kept_valid #(.ID(2048)) u_mask_reset (.ck(ck),.rst_n(rst_n),.d(1'b1),.q(mask_reset));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin wp <= 0; valid <= 0; end
        else begin wp <= wp + 1'b1; valid <= {valid[D-3:0], 1'b1}; end
    wire [4:0] ra = wp - (D-2) + ((MUT == 1) ? 5'd1 : 5'd0);   // one edge earlier than qfd_dv_s8s_sram_delay
    wire [W-1:0] mq;
    qfd_dv_sram_bank64 #(.W(W)) u_m (.clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mq),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(d), .w_mask_in({W{1'b1}}));
    reg [W-1:0] mq_r;
    always @(posedge ck) mq_r <= mq;                              // unreset read-data flop
    wire [W-1:0] qd = (MUT == 2) ? mq : mq_r;
    genvar g;
    generate for (g = 0; g < (W+G-1)/G; g = g + 1) begin : g_out
        localparam integer B = ((W-G*g) < G) ? W-G*g : G;
        wire warm_q;
        (* keep_hierarchy = "yes" *) qfd_dv_kept_valid #(.ID(g)) u_v (.ck(ck), .rst_n(mask_reset), .d(valid[D-2]), .q(warm_q));
        assign q[G*g +: B] = warm_q ? qd[G*g +: B] : {B{1'b0}};
    end endgenerate
`ifndef SYNTHESIS
    initial if (D < 3 || D > 27 || W > 546) $fatal(1, "SRAM_DELAY_CONFIG");
`endif
endmodule
