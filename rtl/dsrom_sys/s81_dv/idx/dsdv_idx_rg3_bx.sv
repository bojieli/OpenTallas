`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// STW-S81c-TOK4-BAND (10-22): the X band of the banded idx rg3 (see dsdv_idx_rg3_band.sv for the band map), in its own
// file so X iterations never touch the R / S bands' source bindings.
// ---------------------------------------------------------------------------------------------------------------------

// X is itself two (MAIN) or three (FB) hard tiles under a wires-only X cluster (gate 10-22 18:2x: the flat X tile hung the
// N rri pin flops and the S kq pin flops 432 um apart around 8 SRAM on ONE root, TT / FF pin-flop spread 230 / 201 ps):
//   dsdv_idx_rg3_bxn      landing strip: rri pin flops (RH relays), rrr lane register, rkc, the registered landing writes
//                         lw_* (S face = the SRAM write ports below; source-registered) and xr_o
//   dsdv_idx_rg3_bxmh #H  one landing-SRAM column (h0 or h1 of every unit) + its read stages + its half of the key mux and
//                         of kq (H 0 also the scale select k_sc); the key mux is column-local (key half H reads only hH)
//   dsdv_idx_rg3_bxm      both columns (MAIN hard tile); FB hardens the two bxmh columns separately
// Cut at existing registers only (lw_* / rrr / kq / the S stage in R): cycle-exact to the flat X of 2e189d817
// (tb_dsdv_idx_rg3_bx_lsw); each tile carries its own copy of X's reset forest (same depth -> same release edge).
module dsdv_idx_rg3_bx #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter bit READ_STAGE = 0,
    parameter integer RH = 1
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [1087:0] rri,           // 4 x 272-b response lanes {data 256, tag10, beat 4, pop, v}
    input  wire [17:0]   sx_i,          // R's S stage {gatk[1], s_v x4 (one copy a landing unit), s_it[34:25], s_it[2:0]}
    output wire [67:0]   xr_o,          // {rkc[3:0], rrr[3][15:0], .., rrr[0][15:0]}
    output wire [543:0]  kq_o           // key word, one edge after the K stage (= the old kr[0])
);
    wire [3:0] lw_v, lw_h1; wire [39:0] lw_a; wire [1023:0] lw_d;
    dsdv_idx_rg3_bxn #(.MUT(MUT), .RH(RH)) u_n (.ck(ck), .rst(rst), .rri(rri), .xr_o(xr_o),
        .lw_v(lw_v), .lw_h1(lw_h1), .lw_a(lw_a), .lw_d(lw_d));
    dsdv_idx_rg3_bxm #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .READ_STAGE(READ_STAGE)) u_m (.ck(ck), .rst(rst), .sx_i(sx_i),
        .lw_v(lw_v), .lw_h1(lw_h1), .lw_a(lw_a), .lw_d(lw_d), .kq_o(kq_o));
endmodule

module dsdv_idx_rg3_bxn #(
    parameter integer MUT = 0,
    parameter integer RH = 1
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [1087:0] rri,
    output wire [67:0]   xr_o,
    output wire [3:0]    lw_v,          // landing write valid (reset rl[1])
    output wire [3:0]    lw_h1,         // write the h1 column (else h0)
    output wire [39:0]   lw_a,          // {lw_a[3], .., lw_a[0]} 10 b each
    output wire [1023:0] lw_d           // {lw_d[3], .., lw_d[0]} 256 b each
);
    // reset: same forest depth as dsdv_idx_rg3 (rs 2 + u_r0 3 + u_r1 3 edges) -> same release edge
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire       r0;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r0 (.clk(ck), .rst_n_in(rs[1]), .rst_n(r0));
    wire [1:0] rl;                                  // [0] rrr valid / pop (rg3 rl[1]), [1] lw_v (rl[22])
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r1 (.clk(ck), .rst_n_in(r0), .rst_n(rl));
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
    reg  [3:0]  lw_vr, lw_h1r;
    reg  [3:0][9:0] lw_ar;
    reg  [3:0][255:0] lw_dr;
    integer u;
    always @(posedge ck) for (u = 0; u < 4; u = u + 1) begin : g_rsp
        reg g; reg [3:0] s_; reg [3:0] cl; reg sc; reg [3:0] bt;
        g = rt[u][14]; s_ = {rt[u][5], rt[u][13:11]}; cl = rt[u][10:7]; sc = rt[u][6]; bt = rb[u];
        lw_dr[u] <= rrr[u][271:16];
        lw_h1r[u] <= !sc && bt[0];
        if (!sc) lw_ar[u] <= {2'b00, s_, g ? cl : cl + {3'd0, bt[1]}};
        else if (!g) lw_ar[u] <= {5'b01000, s_, bt[0]};
        else lw_ar[u] <= {2'b10, s_, cl};
    end
    always @(posedge ck or negedge rl[1]) if (!rl[1]) lw_vr <= 4'd0; else lw_vr <= mine;
    assign lw_v = lw_vr; assign lw_h1 = lw_h1r; assign lw_a = lw_ar; assign lw_d = lw_dr;
endmodule

module dsdv_idx_rg3_bxm #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter bit READ_STAGE = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [17:0]   sx_i,
    input  wire [3:0]    lw_v,
    input  wire [3:0]    lw_h1,
    input  wire [39:0]   lw_a,
    input  wire [1023:0] lw_d,
    output wire [543:0]  kq_o
);
    wire [287:0] k0;                                // {k_sc, key[255:0]}
    wire [255:0] k1;                                // key[511:256]
    dsdv_idx_rg3_bxmh #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .READ_STAGE(READ_STAGE), .H(0)) u_c0 (.ck(ck), .rst(rst), .sx_i(sx_i),
        .lw_v(lw_v), .lw_h1(lw_h1), .lw_a(lw_a), .lw_d(lw_d), .kq_o(k0));
    dsdv_idx_rg3_bxmh #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .READ_STAGE(READ_STAGE), .H(1)) u_c1 (.ck(ck), .rst(rst), .sx_i(sx_i),
        .lw_v(lw_v), .lw_h1(lw_h1), .lw_a(lw_a), .lw_d(lw_d), .kq_o(k1));
    assign kq_o = {k0[287:256], k1, k0[255:0]};
endmodule

// one landing-SRAM column: H 0 = the h0 SRAM of every unit (S and C reads; key[255:0] + the scale select), H 1 = h1 (C reads;
// key[511:256]).  kq_o = H 0: {k_sc, key[255:0]} (288 b), H 1: key[511:256] (256 b).
module dsdv_idx_rg3_bxmh #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter bit READ_STAGE = 0,
    parameter integer H = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [17:0]   sx_i,
    input  wire [3:0]    lw_v,
    input  wire [3:0]    lw_h1,
    input  wire [39:0]   lw_a,
    input  wire [1023:0] lw_d,
    output wire [(H ? 256 : 288)-1:0] kq_o
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire       r0, rl2;                             // rl2 = c_v (rg3 rl[25])
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r0 (.clk(ck), .rst_n_in(rs[1]), .rst_n(r0));
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r1 (.clk(ck), .rst_n_in(r0), .rst_n(rl2));
    // read side: R's S stage, the C stage copy, this column's landing SRAMs
    wire        gatk1 = sx_i[17];
    wire [3:0]  s_vx  = sx_i[16:13];
    wire [34:25] s_hi = sx_i[12:3];
    wire [2:0]  s_lo  = sx_i[2:0];
    reg         c_v;
    reg  [34:25] c_hi;
    always @(posedge ck or negedge rl2) if (!rl2) c_v <= 1'b0; else c_v <= s_vx[0];
    always @(posedge ck) c_hi <= s_hi;
    wire [1:0]  su_b = s_hi[34:33];
    wire [1:0]  c_u  = c_hi[34:33];
    wire [9:0]  s_row = gatk1 ? {2'b10, s_hi[32:29], s_hi[28:25]} : {5'b01000, s_hi[32:29], s_hi[28]};
    wire [9:0]  c_row = {2'b00, c_hi[32:29], c_hi[28:25]};
    wire [3:0][255:0] hq_raw, hq;
    genvar gu;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_land
        wire rs0 = H == 0 && s_vx[gu] && su_b == 2'(gu);
        wire rc  = c_v && c_u == 2'(gu);
        wire we  = lw_v[gu] && (H ? lw_h1[gu] : !lw_h1[gu]);
        dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_h (
            .ck(ck), .re(rs0 || rc), .ra(rs0 ? s_row : c_row), .rd(hq_raw[gu]),
            .we(we), .wa(lw_a[10 * gu +: 10]), .wd(lw_d[256 * gu +: 256]));
        if (READ_STAGE) begin : g_readcap
            // One unreset capture bank beside each SRAM read face. This removes
            // the SRAM access + wide mux from the path to the S-face output.
            (* keep = "true" *) reg [255:0] q;
            always @(posedge ck) q <= hq_raw[gu];
            assign hq[gu] = q;
        end else begin : g_noreadcap
            assign hq[gu] = hq_raw[gu];
        end
    end endgenerate
    // key half H: lane gk = 16 H + j reads hH of the unit its select names (select from cu = the old cu_a (H 0) / cu_b (H 1))
    (* keep = "true" *) reg [1:0] cu;
    (* keep = "true" *) reg [15:0] ks0, ks1, ks2, ks3;
    always @(posedge ck) begin
        cu <= s_hi[34:33];
        ks0 <= {16{cu == 2'd0}}; ks1 <= {16{cu == 2'd1}}; ks2 <= {16{cu == 2'd2}}; ks3 <= {16{cu == 2'd3}};
    end
    wire [15:0] km0, km1, km2, km3;
    generate if (READ_STAGE) begin : g_keysel_delay
        (* keep = "true" *) reg [15:0] d0,d1,d2,d3;
        always @(posedge ck) begin d0<=ks0; d1<=ks1; d2<=ks2; d3<=ks3; end
        assign km0=d0; assign km1=d1; assign km2=d2; assign km3=d3;
    end else begin : g_keysel_direct
        assign km0=ks0; assign km1=ks1; assign km2=ks2; assign km3=ks3;
    end endgenerate
    wire [255:0] k_key;
    genvar gk;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_km
        localparam integer O = 16 * gk;
        assign k_key[O +: 16] = ({16{km0[gk]}} & hq[0][O +: 16]) | ({16{km1[gk]}} & hq[1][O +: 16]) |
                                ({16{km2[gk]}} & hq[2][O +: 16]) | ({16{km3[gk]}} & hq[3][O +: 16]);
    end endgenerate
    generate if (H == 0) begin : g_sc
        // the scale-select capture: the RAW {su_b, s_lo} land in pin flops beside the S-face sx_i pins and the 32-way
        // decode follows them (cycle-identical to registering the decoded ssel; gate 10-22 20:4x: the 32 decoded ssel
        // flops sat at the SRAM read channel as boundary flops, TT 369..419 ps vs 325..347 for the S pin band)
        // native census (gates 10-22 20:3x..21:0x): a raw {su_b, s_lo} capture maps (abc) to a flat 32-minterm AND-OR,
        // so every raw select bit drives 32 loads PER k_sc bit (1 copy: 59; 8 copies x 4 b: 34..62; 16 x 2 b: 64; 32 x
        // 1 b: the sx_i[12:11] ports drive 42).  Only a ONE-HOT select is census-safe: the decoded selects land in pin
        // flops (two copies, each serving 16 k_sc bits -> 16 loads per flop; the ports feed a 4 + 8 predecode).
        // Cycle-identical to the raw capture.
        (* keep = "true" *) reg [31:0] ss0, ss1;          // one-hot {su_b, s_lo}; ss0 -> k_sc[15:0], ss1 -> k_sc[31:16]
        // Preserve the 4+8 predecode boundary through ABC. Without keep,
        // mapping may flatten 32 minterms onto sx_i[12:11] (36 loads).
        (* keep = "true" *) wire [3:0] spre_u;
        (* keep = "true" *) wire [7:0] spre_l;
        for (genvar u = 0; u < 4; u = u + 1) begin : g_su_pre
            assign spre_u[u] = su_b == 2'(u);
        end
        for (genvar l = 0; l < 8; l = l + 1) begin : g_sl_pre
            assign spre_l[l] = s_lo == 3'(l);
        end
        wire [31:0] sdec;
        genvar ga;
        for (ga = 0; ga < 32; ga = ga + 1) begin : g_ss
            assign sdec[ga] = spre_u[ga / 8] && spre_l[ga % 8];
        end
        always @(posedge ck) begin ss0 <= sdec; ss1 <= sdec; end
        wire [31:0] sm0,sm1;
        if (READ_STAGE) begin : g_scsel_delay
            (* keep = "true" *) reg [31:0] d0,d1;
            always @(posedge ck) begin d0<=ss0; d1<=ss1; end
            assign sm0=d0; assign sm1=d1;
        end else begin : g_scsel_direct
            assign sm0=ss0; assign sm1=ss1;
        end
        reg [31:0] k_sc;
        always @(posedge ck) begin : g_scr
            reg [31:0] x; integer a_;
            x = 32'd0;
            for (a_ = 0; a_ < 32; a_ = a_ + 1)
                x = x | {{16{sm1[a_]}} & hq[a_ / 8][32 * (a_ % 8) + 16 +: 16], {16{sm0[a_]}} & hq[a_ / 8][32 * (a_ % 8) +: 16]};
            k_sc <= x;
        end
        (* keep = "true" *) reg [287:0] kq;         // S face pin flops
        always @(posedge ck) kq <= {k_sc, k_key};
        assign kq_o = kq;
    end else begin : g_nsc
        (* keep = "true" *) reg [255:0] kq;
        always @(posedge ck) kq <= k_key;
        assign kq_o = kq;
    end endgenerate
endmodule
