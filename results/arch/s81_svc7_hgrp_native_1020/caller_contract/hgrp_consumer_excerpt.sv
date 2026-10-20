
// rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv:210
                assign we_q = we_r; assign wd_q = wd_r; assign wb_q = wb_r;
            end
            wire [31:0] y;
            wire f;
            ot_hdc_v41x_attn_hdp_s #(.TD(TD), .NBANK(NBANK), .BW(BW), .FPL(FPL), .FML(BML), .F12(F12)) u_hdp (
                .clk(clk), .rst_n(rst_n), .we(we_q), .wbank(wb_q), .wd(wd_q), .sk_bank(sk_bank), .sk_b(sk_b),
                .y(y), .f(f));
            always @(posedge clk) begin
                oy[gh*32 +: 32] <= y;
                oflt[gh] <= f;
            end
        end
    endgenerate

    wire v_core;
    ot_hdc_v41x_vdly #(.D(LAT_CORE)) u_v (.clk(clk), .rst_n(rst_n), .d(d1_v), .q(v_core));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0;
        else ov <= v_core;
    end
endmodule


// rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv:283
            // S81 hard head group (SVC3 10-19): parameter-free element rtl/hdc/v41x/ot_hdc_v41x_attn_hgrp_s81.sv,
            // hardened once (kit physical/ref_tile/s81svc_attn_hgrp); only the S81 engine parameters are legal here
            if (H != 16 || HG != 4 || TD != 32 || NBANK != 5 || BW != 3 || PWORDS != 2 || FPL != 4 || FML != 6 ||
                F12 != 1) begin : g_bad_hard
                initial $error("ot_hdc_v41x_attn_tile_s: OT_ATTN_HGRP_HARD needs the S81 engine parameters");
            end
            ot_hdc_v41x_attn_hgrp_s81 u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_wp(wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*HG*32 +: HG*32]), .oflt(oflt[g*HG +: HG]));
`else
            ot_hdc_v41x_attn_hgrp_s #(.H(H), .HG(HG), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL),
                                      .FML(FML), .F12(F12), .PCOLP(PCOLP)) u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_wp(wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*HG*32 +: HG*32]), .oflt(oflt[g*HG +: HG]));
`endif
        end
    endgenerate
    assign ov = gov[0];
endmodule

// ---------------------------------------------------------------------------
