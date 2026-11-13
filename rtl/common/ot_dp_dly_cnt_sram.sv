// Static-count reset-less delay using the existing one-cycle ASAP7 SRAM.
// BASE fixed stages and min(strap_cnt, DMAX) selected stages are fused into
// one age; no additional data/control cycle. Count is a STATIC parent strap.
// Every binary five-bit write-pointer state is valid modulo32; its arbitrary
// initial address cancels in wp-rp. The complete word is defined after D writes.
// Warm reset elsewhere cannot restart this pointer or discard data history.
// No payload/epoch bit is masked as invalid: every W bit has the same delay.
(* keep_hierarchy = 1 *)
module ot_dp_dly_cnt_sram #(
    parameter integer W = 291,
    parameter integer DMAX = 24,
    parameter integer BASE = 2,
    parameter integer CW = 5
) (
    input wire clk,
    input wire [CW-1:0] strap_cnt,
    input wire [W-1:0] d,
    output wire [W-1:0] q
);
    // Synthesis must fail too for an impossible memory/count declaration;
    // this deliberately unresolved diagnostic cell is never in a legal form.
    generate if (W < 1 || BASE < 0 || DMAX < 0 || BASE+DMAX > 32 ||
                 CW < 1 || CW > 6 || DMAX >= (1 << CW)) begin : g_bad_shape
        (* keep = 1 *) OT_DP_DLY_CNT_SRAM_REQUIRES_LEGAL_32_WORD_SHAPE bad_shape();
    end endgenerate
    localparam integer NB = (W + 63) / 64;
`ifdef OT_DP_DLY_SRAM_COUNT_TRUNC_MUT
    wire [CW-1:0] selected_count = CW'(strap_cnt & CW'(15));
`else
    wire [CW-1:0] selected_count = strap_cnt;
`endif
    wire [5:0] selected = (selected_count > CW'(DMAX)) ? 6'(DMAX) : 6'(selected_count);
    wire [5:0] depth = 6'(BASE) + selected;
    (* keep = 1 *) reg [W-1:0] short_1, short_2;
    always @(posedge clk) begin
        short_1 <= d;
        short_2 <= short_1;
    end
    generate if (BASE + DMAX >= 3) begin : g_ring
        (* keep = 1 *) reg [4:0] wp;
        always @(posedge clk) wp <= wp + 5'd1;
        // Macro output is registered, then captured once at the bank edge.
        // For depth D, rp=wp-(D-2) therefore gives the D-stage word.
`ifdef OT_DP_DLY_SRAM_AGE_MUT
        wire [4:0] rp = wp - (5'(depth) - 5'd3);
`else
        wire [4:0] rp = wp - (5'(depth) - 5'd2);
`endif
        wire [NB*64-1:0] di = {{(NB*64-W){1'b0}}, d};
        wire [NB*64-1:0] qo;
        for (genvar b = 0; b < NB; b = b + 1) begin : g_bank
            localparam integer USED = (W - 64*b < 64) ? W - 64*b : 64;
            wire [63:0] raw;
            // No unused short-age read collision; writes preserve all history.
            ot_sram_1r1w_32x64_m1 u_mem (
                .clk(clk), .r_ce_in(depth >= 6'd3), .r_addr_in(rp), .rd_out(raw),
                .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(di[64*b +: 64]),
                .w_mask_in(64'hffffffffffffffff >> (64-USED)));
            (* keep = 1 *) reg [USED-1:0] edge_q;
            always @(posedge clk) edge_q <= raw[USED-1:0];
            assign qo[64*b +: 64] = {{(64-USED){1'b0}}, edge_q};
        end
        assign q = depth == 6'd0 ? d : depth == 6'd1 ? short_1 :
                   depth == 6'd2 ? short_2 : qo[W-1:0];
    end else begin : g_short
        assign q = depth == 6'd0 ? d : depth == 6'd1 ? short_1 : short_2;
    end endgenerate
`ifndef SYNTHESIS
    initial begin
        if (W < 1 || BASE < 0 || DMAX < 0 || BASE+DMAX > 32 || CW < 1 || CW > 6 || DMAX >= (1 << CW))
            $fatal(1,"ot_dp_dly_cnt_sram unsupported W=%0d BASE=%0d DMAX=%0d CW=%0d",W,BASE,DMAX,CW);
    end
`endif
endmodule
