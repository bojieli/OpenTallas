`undef OT_HARD_CHILDREN
`define OT_HB_PINCOPY
module hist_mut #(
    parameter integer MUT = 0          // 1: every bank counts its neighbour's bins (witness); 2: bank 3 never clears (witness)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    clr,            // per-bank copies of the clear (identical values, distinct nets)
    input  wire          i_v,
    input  wire [15:0]   i_en,
    input  wire [127:0]  i_dg,
    input  wire [8*4-1:0] gsel_d,        // per-bank copies of the command input whose register is the original gsel
    output wire [239:0]  gsum,
    output wire [175:0]  gbin,
    output wire          busy
);
    // exact original busy: HPIPE 1 recurrence of ot_s81ph_native_sel_hist, shadowed from the bank inputs
    reg sx_v, sx_clr, s_v1, s_v2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sx_v <= 1'b0; sx_clr <= 1'b0; s_v1 <= 1'b0; s_v2 <= 1'b0; end
        else begin sx_v <= i_v; sx_clr <= clr[0]; s_v1 <= sx_v && !sx_clr; s_v2 <= s_v1 && !sx_clr; end
    assign busy = sx_v || s_v1 || s_v2;
    wire [8*176-1:0] bk_out;
    wire [7:0] bb_unused;
    genvar b, l;
    generate for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [127:0] nd;
        for (l = 0; l < 16; l = l + 1) begin : g_d
            assign nd[8*l +: 8] = i_dg[8*l +: 8] ^ (8'((MUT == 1) ? (b ^ 1) : b) << 5);
        end
        wire [3:0] ng = gsel_d[4*b +: 4] ^ (4'(b) << 1);
        wire       nc = (MUT == 2 && b == 3) ? 1'b0 : clr[b];
`ifdef OT_HARD_CHILDREN
        ot_s81ph_native_sel_hist_bank_copy u_bank (
`else
        ot_s81ph_native_sel_hist_bank_copy #(.W(16), .CB(11), .BANK(0), .NB(32), .HPIPE(1)) u_bank (
`endif
`ifdef OT_HB_PINCOPY
            // one bank pin per kept capture flop (KITS-SPARE-2/HB 10-25): the bank's copy registers are fed in parallel
            .clk(clk), .rst_n(rst_n), .clr({17{nc}}), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel({{15{ng}}, (ng ^ 4'h1)}),
`else
            .clk(clk), .rst_n(rst_n), .clr(nc), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel(ng),
`endif
            .gsum(gsum[30*b +: 30]), .gbin(bk_out[176*b +: 176]), .busy(bb_unused[b]));
    end endgenerate
    reg [175:0] j;
    integer k;
    always @(*) begin j = 176'd0; for (k = 0; k < 8; k = k + 1) j = j | bk_out[176*k +: 176]; end
    assign gbin = j;
endmodule
`undef OT_HB_PINCOPY
