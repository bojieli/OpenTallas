`timescale 1ns/1ps
`define OT_HBM_RW_MACROS
module leaf_new #(
    parameter integer W = 137, QD = 64,
    parameter integer QA = $clog2(QD), MUT = 0
) (
    input wire ck, we,
    input wire [QA-1:0] wa, ra,
    input wire [W-1:0] din,
    output reg [W-1:0] dout
);
    // Real 64x512 SRAM at the native64x137 shape. Unused columns are masked;
    // all readable queue words are written before their valid reservation.
    // Capture write pins, then commit to the SRAM. Track both collision ages
    // because the macro read is synchronous and read-before-write.
    reg wq;
    reg [QA-1:0] aq;
    reg hit_age0, hit_age1;
    reg [W-1:0] dq, dqq;
    wire [511:0] mr;
    always @(posedge ck) begin
        wq <= we; aq <= wa; dq <= din;
        dqq <= dq;
        // Compare at the same edge that captures the matching write/read ages.
        // Next edge's mux sees exactly the old (wq,aq,rq)/(wqq,aqq,rq)
        // collision decisions, without a six-bit compare driving all W outputs.
`ifdef OT_QKD_REPLAY_HIT_MUT
        hit_age0 <= we && wa != ra; // negative control: corrupt current-age selection
`else
        hit_age0 <= we && wa == ra;
`endif
        hit_age1 <= wq && aq == ra;
    end
`ifdef OT_HBM_RW_MACROS
    // DIE-HBM-61/MEM 11-03 RE-FORM (macro channels, HBM kits only: the define is set by the HBM RE-FORM recipe; every
    // other build elaborates the r2c2 branch unchanged): right-width r0c0 master, one mask pin, same 1r1w cycle
    // contract (tools/mem_compiler/build_hbm_rightwidth_1103.py).  Repair pins were tied 0, mask bits above W tied 0
    // and mr[511:W] never read, so the W used bits behave identically.
    // DIE-HBM-61/RF1-BUILD 11-03: independent if-generates (no else-if chain) so the synthesized macro paths are
    // <leaf>.g_rw141.u_sram etc. as in core_macros (yosys put the else-if arms under genblk1 -> MPL-0020 on cp_rxs).
    if (QD == 64 && W <= 32) begin : g_rw32
        wire [31:0] mr_w;
        ot_sram_1r1w_64x32_m1_r0c0_g32 u_sram (
            .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr_w),
            .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(32-W){1'b0}},dq}), .w_mask_in(1'b1));
        assign mr = {480'd0, mr_w};
    end
    if (QD == 64 && W > 32 && W <= 141) begin : g_rw141
        wire [140:0] mr_w;
        ot_sram_1r1w_64x141_m1_r0c0_g141 u_sram (
            .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr_w),
            .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(141-W){1'b0}},dq}), .w_mask_in(1'b1));
        assign mr = {371'd0, mr_w};
    end
    if (QD == 64 && W == 306) begin : g_rw306
        wire [305:0] mr_w;
        ot_sram_1r1w_64x306_m1_r0c0_g306 u_sram (
            .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr_w),
            .w_ce_in(wq), .w_addr_in(aq), .wd_in(dq), .w_mask_in(1'b1));
        assign mr = {206'd0, mr_w};
    end
    if (!(QD == 64 && (W <= 141 || W == 306))) begin : g_r2c2
`endif
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}},dq}),
        .w_mask_in({{(512-W){1'b0}},{W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
`ifdef OT_HBM_RW_MACROS
    end
`endif
    always @(posedge ck)
        // A write arriving after this read reservation is forbidden by the
        // compiler ownership check. Bypass only the two captured write ages;
        // raw write pins must not feed the read-output D cones.
        dout <= (hit_age0 ? dq :
                 hit_age1 ? dqq : mr[W-1:0]) ^
            (MUT != 0 ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});

endmodule
`undef OT_HBM_RW_MACROS
