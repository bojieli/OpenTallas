// rtl/hdc/v41x/ot_hdc_v41x_attn.sv:845
    wire ln_v, ln_pv;
    wire [15:0] ln_row0;
    wire [NL-1:0] ln_mask;
    ot_hdc_v41x_vdly #(.D(3 * LS + 1)) u_lnv (.clk(clk), .rst_n(rst_n), .d(t_ov[0] && !t_pv), .q(ln_v));
    ot_hdc_v41x_dly #(.W(16 + NL), .D(3 * LS + 1)) u_lnt (.clk(clk), .d({t_row0, t_mask}), .q({ln_row0, ln_mask}));
    // (the +1 above aligns with the register below; ln_y is 3*LS after t_y)
    reg [NL*H*32-1:0] ln_yr;
// rtl/hdc/v41x/ot_hdc_v41x_attn.sv:865
    wire [NT*H-1:0]    m_f;
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_m
            if (PHYS == 0) begin : g_real
            ot_hdc_v41x_attn_merge #(.H(H), .DPT(DPT), .MLEV(MLEV)) u_m (
                .clk(clk), .rst_n(rst_n), .iv(t_ov[gk] && t_pv), .ifin(t_fin), .iblk(t_blk),
                .iy(t_y[gk*H*32 +: H*32]), .if_(t_f[gk*H +: H]), .ov(m_ov[gk]), .oy(m_y[gk*H*32 +: H*32]),
                .of_(m_f[gk*H +: H]));
            end else begin : g_phs
            ot_hdc_v41x_attn_merge_phs #(.H(H), .DPT(DPT), .MLEV(MLEV)) u_m (
                .clk(clk), .rst_n(rst_n), .iv(t_ov[gk] && t_pv), .ifin(t_fin), .iblk(t_blk),
                .iy(t_y[gk*H*32 +: H*32]), .if_(t_f[gk*H +: H]), .ov(m_ov[gk]), .oy(m_y[gk*H*32 +: H*32]),
                .of_(m_f[gk*H +: H]));
            end
