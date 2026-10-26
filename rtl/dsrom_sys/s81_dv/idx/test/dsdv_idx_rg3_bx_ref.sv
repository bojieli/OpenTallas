`timescale 1ns/1ps
// STW-S81c-TOK4-BAND 10-22: the flat X band of 2e189d817 (ONE hard tile), kept as the reference of tb_dsdv_idx_rg3_bx_lsw
module dsdv_idx_rg3_bx_ref #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer RH = 1
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [1087:0] rri,           // 4 x 272-b response lanes {data 256, tag10, beat 4, pop, v}
    input  wire [17:0]   sx_i,          // R's S stage {gatk[1], s_v x4 (one copy a landing unit), s_it[34:25], s_it[2:0]}
    output wire [67:0]   xr_o,          // {rkc[3:0], rrr[3][15:0], .., rrr[0][15:0]}
    output wire [543:0]  kq_o           // key word, one edge after the K stage (= the old kr[0])
);
    // reset: same forest depth as dsdv_idx_rg3 (rs 2 + u_r0 3 + u_r1 3 edges) -> same release edge
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire       r0;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r0 (.clk(ck), .rst_n_in(rs[1]), .rst_n(r0));
    wire [2:0] rl;                                  // [0] rrr valid / pop (rg3 rl[1]), [1] lw_v (rl[22]), [2] c_v (rl[25])
    ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r1 (.clk(ck), .rst_n_in(r0), .rst_n(rl));
    // response relay hops (rh[0] = the N pin flops) and the landing-side lane register
    wire [1087:0] rrh;
    generate if (RH == 0) begin : g_khrz
        assign rrh = rri;
    end else begin : g_khrp
        (* keep = "true" *) reg [1087:0] rh [0:RH-1];
        always @(posedge ck) begin
            rh[0] <= rri;
            for (int k = 1; k < RH; k++) rh[k] <= rh[k - 1];
        end
        assign rrh = rh[RH - 1];
    end endgenerate
    reg [3:0][271:0] rrr;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin rrr[0][1:0] <= 2'd0; rrr[1][1:0] <= 2'd0; rrr[2][1:0] <= 2'd0; rrr[3][1:0] <= 2'd0; end
        else begin
            rrr[0][1:0] <= rrh[1:0]; rrr[1][1:0] <= rrh[273:272]; rrr[2][1:0] <= rrh[545:544]; rrr[3][1:0] <= rrh[817:816];
        end
    always @(posedge ck) begin
        rrr[0][271:2] <= rrh[271:2]; rrr[1][271:2] <= rrh[543:274]; rrr[2][271:2] <= rrh[815:546]; rrr[3][271:2] <= rrh[1087:818];
    end
    (* keep = "true" *) reg [3:0] rkc;
    always @(posedge ck) rkc <= {rrh[817], rrh[545], rrh[273], rrh[1]};
    assign xr_o = {rkc, rrr[3][15:0], rrr[2][15:0], rrr[1][15:0], rrr[0][15:0]};
    // landing writes (registered one edge after rrr; the same functions of rrr as R's slot-count copy)
    wire [3:0][16:0] rt;
    wire [3:0][3:0]  rb;
    wire [3:0]       mine;
    genvar gu;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_rdw
        assign rt[gu] = {2'b11, rrr[gu][15:6], 5'd0};
        assign rb[gu] = rrr[gu][5:2];
        assign mine[gu] = rrr[gu][0] && !(MUT == 5 && rt[gu][7]);
    end endgenerate
    reg  [3:0]  lw_v, lw_h1;
    reg  [3:0][9:0] lw_a;
    reg  [3:0][255:0] lw_d;
    integer u;
    always @(posedge ck) for (u = 0; u < 4; u = u + 1) begin : g_rsp
        reg g; reg [3:0] s_; reg [3:0] cl; reg sc; reg [3:0] bt;
        g = rt[u][14]; s_ = {rt[u][5], rt[u][13:11]}; cl = rt[u][10:7]; sc = rt[u][6]; bt = rb[u];
        lw_d[u] <= rrr[u][271:16];
        lw_h1[u] <= !sc && bt[0];
        if (!sc) lw_a[u] <= {2'b00, s_, g ? cl : cl + {3'd0, bt[1]}};
        else if (!g) lw_a[u] <= {5'b01000, s_, bt[0]};
        else lw_a[u] <= {2'b10, s_, cl};
    end
    always @(posedge ck or negedge rl[1]) if (!rl[1]) lw_v <= 4'd0; else lw_v <= mine;
    // read side: R's S stage, the C stage copy, the landing SRAMs, scale / key selects (as dsdv_idx_rg3)
    wire        gatk1 = sx_i[17];
    wire [3:0]  s_vx  = sx_i[16:13];
    wire [34:25] s_hi = sx_i[12:3];
    wire [2:0]  s_lo  = sx_i[2:0];
    reg         c_v;
    reg  [34:25] c_hi;
    always @(posedge ck or negedge rl[2]) if (!rl[2]) c_v <= 1'b0; else c_v <= s_vx[0];
    always @(posedge ck) c_hi <= s_hi;
    wire [1:0]  su_b = s_hi[34:33];                 // == R's su_a / su_b (registered from ih[34:33] with s_it)
    wire [1:0]  c_u  = c_hi[34:33];
    wire [9:0]  s_row = gatk1 ? {2'b10, s_hi[32:29], s_hi[28:25]} : {5'b01000, s_hi[32:29], s_hi[28]};
    wire [9:0]  c_row = {2'b00, c_hi[32:29], c_hi[28:25]};
    wire [3:0][255:0] h0q, h1q;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_land
        wire rs0 = s_vx[gu] && su_b == 2'(gu);
        wire rc  = c_v && c_u == 2'(gu);
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_h0 (
            .ck(ck), .re(rs0 || rc), .ra(rs0 ? s_row : c_row), .rd(h0q[gu]),
            .we(lw_v[gu] && !lw_h1[gu]), .wa(lw_a[gu]), .wd(lw_d[gu]));
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_h1 (
            .ck(ck), .re(rc), .ra(c_row), .rd(h1q[gu]),
            .we(lw_v[gu] && lw_h1[gu]), .wa(lw_a[gu]), .wd(lw_d[gu]));
    end endgenerate
    (* keep = "true" *) reg [31:0] ssel;
    always @(posedge ck) begin : g_ss
        integer a_;
        for (a_ = 0; a_ < 32; a_ = a_ + 1) ssel[a_] <= su_b == 2'(a_ / 8) && s_lo == 3'(a_ % 8);
    end
    reg [31:0] k_sc;
    always @(posedge ck) begin : g_sc
        reg [31:0] x; integer a_;
        x = 32'd0;
        for (a_ = 0; a_ < 32; a_ = a_ + 1) x = x | ({32{ssel[a_]}} & h0q[a_ / 8][32 * (a_ % 8) +: 32]);
        k_sc <= x;
    end
    (* keep = "true" *) reg [1:0] cu_a, cu_b;
    (* keep = "true" *) reg [31:0] ks0, ks1, ks2, ks3;
    always @(posedge ck) begin
        cu_a <= s_hi[34:33]; cu_b <= s_hi[34:33];
        ks0 <= {{16{cu_b == 2'd0}}, {16{cu_a == 2'd0}}}; ks1 <= {{16{cu_b == 2'd1}}, {16{cu_a == 2'd1}}};
        ks2 <= {{16{cu_b == 2'd2}}, {16{cu_a == 2'd2}}}; ks3 <= {{16{cu_b == 2'd3}}, {16{cu_a == 2'd3}}};
    end
    wire [543:0] k_key;
    genvar gk;
    generate for (gk = 0; gk < 32; gk = gk + 1) begin : g_km
        localparam integer H = gk / 16, O = 16 * (gk % 16);
        wire [15:0] d0_ = ({16{ks0[gk]}} & (H ? h1q[0][O +: 16] : h0q[0][O +: 16])) | ({16{ks1[gk]}} & (H ? h1q[1][O +: 16] : h0q[1][O +: 16])) |
                          ({16{ks2[gk]}} & (H ? h1q[2][O +: 16] : h0q[2][O +: 16])) | ({16{ks3[gk]}} & (H ? h1q[3][O +: 16] : h0q[3][O +: 16]));
        assign k_key[256 * H + O +: 16] = d0_;
    end endgenerate
    assign k_key[543:512] = k_sc;
    (* keep = "true" *) reg [543:0] kq;            // the old kr[0] of every column, one copy (S face)
    always @(posedge ck) kq <= k_key;
    assign kq_o = kq;
endmodule

