`timescale 1ns/1ps
// TYPE-CONS-2 SWQ: cycle-identical form of qfd_dv_s8s_sram_delay with a flop on the read data.
// Same q on every clock (q(t) = warm(t) ? d(t-D) : 0), one SRAM read latency moved behind a register, so the
// 252-ps macro read + wire leaves the following logic cone. No pin cycle, no schedule change. D >= 4.
module qfd_dv_s8s_sram_delay_oq #(parameter integer W = 514, parameter integer D = 14, parameter integer MUT = 0, parameter integer G = 12) (
    input wire ck, rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    reg [4:0] wp;
    reg [D-2:0] valid;
    wire mask_reset;
    (* keep_hierarchy = "yes" *) qfd_dv_kept_valid #(.ID(2048)) u_mask_reset (.ck(ck),.rst_n(rst_n),.d(1'b1),.q(mask_reset));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin wp <= 0; valid <= 0; end
        else begin wp <= wp + 1'b1; valid <= {valid[D-3:0], 1'b1}; end
    wire [4:0] ra = wp - (D-2) + ((MUT == 1) ? 5'd1 : 5'd0);
    wire [W-1:0] mq;
    qfd_dv_sram_bank64 #(.W(W)) u_m (.clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mq),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(d), .w_mask_in({W{1'b1}}));
    reg [W-1:0] q_r;
    genvar g;
    generate for (g = 0; g < (W+G-1)/G; g = g + 1) begin : g_out
        localparam integer B = ((W-G*g) < G) ? W-G*g : G;
        wire warm_q;
        (* keep_hierarchy = "yes" *) qfd_dv_kept_valid #(.ID(g)) u_v (.ck(ck), .rst_n(mask_reset), .d(valid[(MUT == 2) ? D-2 : D-3]), .q(warm_q));
        always @(posedge ck) q_r[G*g +: B] <= warm_q ? mq[G*g +: B] : {B{1'b0}};
    end endgenerate
    assign q = q_r;
`ifndef SYNTHESIS
    initial if (D < 4 || D > 27 || W > 546) $fatal(1, "SRAM_DELAY_OQ_CONFIG");
`endif
endmodule
