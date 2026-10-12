`timescale 1ns/1ps
// el1011-q-kvd 2026-10-11: the 12 hardened sub-tiles of ot_qwen_nearhbm_attn_hub_t (split out so the hub cluster parent
// can synthesise against their hard views via ot_nhb_tiles_bb.v).  See ot_qwen_nearhbm_attn_hub_t.sv for the design notes.
// ---- beat-store tile (one stack) ------------------------------------------------------------------------------------
module ot_nhb_pbst (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         pv,              // pi_valid[s]   (hub port)
    input  wire         pgi,             // pi_g[s]       (hub port)
    input  wire [5:0]   pbeat,           // pi_beat[6s +: 6] (hub port)
    input  wire [511:0] pdata,           // pi_data[512s +: 512] (hub port)
    input  wire [5:0]   ra,              // {pg, pp[4:0]} (parent registers)
    output reg  [511:0] sr
);
    wire [1:0] rr;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg         pv_b, pv_c;
    reg         pg_b, pg_c;
    reg [4:0]   pb_b, pb_c;
    reg [511:0] pd_b, pd_c;
    reg [5:0]   a;
    always @(posedge clk or negedge rr[0]) if (!rr[0]) begin pv_b <= 1'b0; pv_c <= 1'b0; end else begin pv_b <= pv; pv_c <= pv_b; end
    always @(posedge clk) begin
        pg_b <= pgi; pb_b <= pbeat[4:0]; pd_b <= pdata;
        pg_c <= pg_b; pb_c <= pb_b; pd_c <= pd_b;
        a <= ra;
    end
`ifdef KVD_PBMUT
    wire [5:0] ar = a ^ 6'd1;                 // bench mutant: the neighbouring beat
`else
    wire [5:0] ar = a;
`endif
    wire [255:0] q0, q1;
    ot_sram_1r1w_128x256_m1_r2c2 u_pb0 (.clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0, ar}), .rd_out(q0),
        .w_ce_in(pv_c), .w_addr_in({1'b0, pg_c, pb_c}), .wd_in(pd_c[255:0]),
        .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_128x256_m1_r2c2 u_pb1 (.clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0, ar}), .rd_out(q1),
        .w_ce_in(pv_c), .w_addr_in({1'b0, pg_c, pb_c}), .wd_in(pd_c[511:256]),
        .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk) sr <= {q1, q0};
endmodule

// ---- P.V lane-group tile (4 lanes) -----------------------------------------------------------------------------------
module ot_nhb_pvlg (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,               // pr (beat operands valid)
    input  wire [127:0] s0, s1, s2, s3,  // the 4 lanes' operands from stacks 0..3
    input  wire [31:0]  rz,              // 1/Z (aligned to the multiplier)
    output reg  [127:0] y,
    output reg  [3:0]   pf
);
    localparam integer ADD_LAT = 7, MUL_LAT = 6;
    wire [4:0] rr;
    ot_rst_relay #(.REGIONS(5), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg         v_q;
    reg [127:0] s0_q, s1_q, s2_q, s3_q;
    reg [31:0]  rz_q;
    always @(posedge clk or negedge rr[4]) if (!rr[4]) v_q <= 1'b0; else v_q <= v;
    always @(posedge clk) begin s0_q <= s0; s1_q <= s1; s2_q <= s2; s3_q <= s3; rz_q <= rz; end
    wire [127:0] y_o;
    wire [3:0]   pf_o;
    genvar gl;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_l
        wire [31:0] a01, a23, a;
        wire [1:0] e1, e2, e3, e4;
        wire v1, v2, v3, v4;
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_01 (.clk(clk), .rst_n(rr[gl]), .valid_in(v_q),
            .a(s0_q[32*gl +: 32]), .b(s1_q[32*gl +: 32]), .y(a01), .err(e1), .valid_out(v1));
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_23 (.clk(clk), .rst_n(rr[gl]), .valid_in(v_q),
            .a(s2_q[32*gl +: 32]), .b(s3_q[32*gl +: 32]), .y(a23), .err(e2), .valid_out(v2));
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_9 (.clk(clk), .rst_n(rr[gl]), .valid_in(v1), .a(a01),
            .b(a23), .y(a), .err(e3), .valid_out(v3));
        ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_m (.clk(clk), .rst_n(rr[gl]), .valid_in(v3), .a(a),
            .b(rz_q), .y(y_o[32*gl +: 32]), .err(e4), .valid_out(v4));
        assign pf_o[gl] = (v1 && e1 != 0) || (v2 && e2 != 0) || (v3 && e3 != 0) || (v4 && e4 != 0);
    end endgenerate
    always @(posedge clk) y <= y_o;
    always @(posedge clk or negedge rr[4]) if (!rr[4]) pf <= 4'd0; else pf <= pf_o;
endmodule

// ---- Z head tile (one head h: zm[g][node], g in {0,1}, node 0..63) ---------------------------------------------------
module ot_nhb_zh (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,           // start_c
    input  wire [127:0] zs_we,           // block-sum write enables of this head, index {g, k, sd}
    input  wire [127:0] sid,             // sid_c (data of stack sd = bits 32*sd)
    input  wire [3:0]   ziv,             // tree issue: lane valids (stage 0, combinational in the parent)
    input  wire         zg,
    input  wire [5:0]   zp,
    output reg  [63:0]  root,            // {g1 root, g0 root}, zv-masked
    output reg  [3:0]   zerr
);
    localparam integer ZW = 4, ADD_LAT = 7;
    integer e_, z_;
    wire [5:0] rr;
    ot_rst_relay #(.REGIONS(6), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    // pin flops (zs_we / sid / start / issue)
    reg         start_q;
    reg [127:0] zs_we_q, sid_q;
    reg [3:0]   ziv_p;
    reg         zg_p;
    reg [5:0]   zp_p;
    always @(posedge clk or negedge rr[4])
        if (!rr[4]) begin start_q <= 1'b0; zs_we_q <= 128'd0; ziv_p <= 4'd0; end
        else begin start_q <= start; zs_we_q <= zs_we; ziv_p <= ziv; end
    always @(posedge clk) begin sid_q <= sid; zg_p <= zg; zp_p <= zp; end
    // stage 0 (hub_p's issue registers, one edge later): lane valids and read addresses {g, pair}
    reg [ZW-1:0]   ziv0, ziv1;
    reg [ZW*6-1:0] zi0, zi1;
    reg            zg0, zg1;
    reg [6:0]      pz;
    always @(posedge clk or negedge rr[4]) if (!rr[4]) begin ziv0 <= 0; ziv1 <= 0; end else begin ziv0 <= ziv_p; ziv1 <= ziv0; end
    always @(posedge clk) begin
        for (z_ = 0; z_ < ZW; z_ = z_ + 1) begin pz = {1'b0, zp_p} + z_; zi0[6*z_ +: 6] <= pz[5:0]; end
        zi1 <= zi0; zg0 <= zg_p; zg1 <= zg0;
    end
    reg [32*128-1:0] zm;                          // {g, node} x 32 b
    reg [127:0]      zv;
    reg [ZW*32-1:0]  za_r, zb_r;
    wire [ZW*32-1:0] zy;
    wire [ZW-1:0]    zvo, zerr_o;
    wire [ZW*8-1:0]  zwi;
    genvar gz, gb, gf;
    generate for (gz = 0; gz < ZW; gz = gz + 1) begin : g_z
        for (gb = 0; gb < 2; gb = gb + 1) begin : g_b
            for (gf = 0; gf < 2; gf = gf + 1) begin : g_f
                wire [5:0] a;                     // {g, pair[4:0]}: one copy per (operand, 16-bit half)
                wire [5:0] pzz = {1'b0, zp_p[5:0]} + gz;
                (* keep_hierarchy *) ot_nhb_dup_a6 u_a (.clk(clk), .d({zg_p, pzz[4:0]}), .q(a));
                wire [6:0]  ix = {a[5], a[4:0], gb[0]};
                wire [15:0] rd = zv[ix] ? zm[32*ix + 16*gf +: 16] : 16'd0;
                if (gb == 0) begin : g_a
                    always @(posedge clk) za_r[32*gz + 16*gf +: 16] <= rd;
                end else begin : g_bb
                    always @(posedge clk) zb_r[32*gz + 16*gf +: 16] <= rd;
                end
            end
        end
        ot_hdc_delay #(.W(8), .D(ADD_LAT), .RESET(1)) u_i (.clk(clk), .rst_n(rr[gz]),
                                                           .d({ziv1[gz], zg1, zi1[6*gz +: 6]}), .q(zwi[8*gz +: 8]));
        wire [1:0] err;
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_add (.clk(clk), .rst_n(rr[gz]), .valid_in(ziv1[gz]),
            .a(za_r[32*gz +: 32]), .b(zb_r[32*gz +: 32]), .y(zy[32*gz +: 32]), .err(err), .valid_out(zvo[gz]));
        assign zerr_o[gz] = zvo[gz] && (err != 2'd0);
    end endgenerate
    // write (one cycle after the adder): registered one-hot {g, node} per lane
    reg [127:0]     zw_oh [0:ZW-1];
    reg [ZW*32-1:0] zy_r;
    always @(posedge clk or negedge rr[5]) begin
        if (!rr[5]) for (z_ = 0; z_ < ZW; z_ = z_ + 1) zw_oh[z_] <= 128'd0;
        else for (z_ = 0; z_ < ZW; z_ = z_ + 1) begin
            zw_oh[z_] <= 128'd0;
            if (zwi[8*z_ + 7]) zw_oh[z_][zwi[8*z_ +: 7]] <= 1'b1;
        end
    end
    always @(posedge clk) zy_r <= zy;
    always @(posedge clk) begin
        for (e_ = 0; e_ < 128; e_ = e_ + 1) begin
            for (z_ = 0; z_ < ZW; z_ = z_ + 1) if (zw_oh[z_][e_]) zm[32*e_ +: 32] <= zy_r[32*z_ +: 32];
            if (zs_we_q[e_]) zm[32*e_ +: 32] <= sid_q[32*(e_ % 4) +: 32];
        end
        root <= {zv[64] ? zm[32*64 +: 32] : 32'd0, zv[0] ? zm[0 +: 32] : 32'd0};
    end
    always @(posedge clk or negedge rr[5]) begin
        if (!rr[5]) zv <= 0;
        else if (start_q) zv <= 0;
        else for (e_ = 0; e_ < 128; e_ = e_ + 1) begin
            for (z_ = 0; z_ < ZW; z_ = z_ + 1) if (zw_oh[z_][e_]) zv[e_] <= 1'b1;
            if (zs_we_q[e_]) zv[e_] <= 1'b1;
        end
    end
    always @(posedge clk or negedge rr[5]) if (!rr[5]) zerr <= 4'd0; else zerr <= zerr_o;
endmodule

