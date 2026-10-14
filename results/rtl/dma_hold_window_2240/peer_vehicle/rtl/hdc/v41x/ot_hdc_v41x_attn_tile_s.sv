`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 streaming-domain (1.2 GHz at SS) attention TILE, physical successor of ot_hdc_v41x_attn_tile_l
// (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv): the same function and the same cycles (output for output, every
// cycle), organised as H/HG identical HEAD GROUPS so the tile hardens hierarchically.
//
// tile_l shares one input register, one dequantiser and one set of skew delay lines between all H heads: at
// H = 16 the skewed operand bus (TD x 18 bits) and the stationary-load decode fan out across ~0.9 mm of head
// datapaths, beyond the SS wire reach of one 0.833 ns cycle (~0.5 mm).  Here every head group carries its own copy
// of that front end (R0 boundary registers, dequantiser, D1 register, skew lines -- registers only, no added
// cycle), so the tile is H/HG copies of one hardened element (ot_hdc_v41x_attn_hgrp_s) and the tile level is wiring:
// each input port fans out to the H/HG group R0 registers, each output is a group register.  The group's head
// index base is the input port gid (tied off by the tile), so all groups are one macro.
//
// The stationary-load write enables are decoded from the R0 registers as in tile_l; the chunk chains and trees
// are hdp_l's; the product is ot_hdc_v41x_attn_bmul_s (the 8 x 8 multiply split across the FML = 6 operand
// register, same value and cycle; FML must be 6).  Exactness: lockstep against tile_l (tools/hbm_fmax_attn_gate.py
// tile), and the engine ot_hdc_v41x_attn_s with TILE_S = 1 on the full-geometry golden vectors.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_hgrp_s #(
    parameter integer H = 16,          // heads of the tile
    parameter integer HG = 4,          // heads of this group
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2,
    parameter integer PWORDS = 1,
    parameter integer FPL = 3,
    parameter integer FML = 3,
    parameter integer F12 = 0,         // 1: the f12 FP32 adds (LAT 4 / 5) in the chunk chains and trees
    parameter integer PCOLP = 0        // 1: each head's p-mode columns arrive pre-selected on ld_wp (tile wiring),
                                       //    replacing the gsel AND-OR over the H/HG groups (same bits, same cycle)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        gid,       // group index (static): heads gid*HG .. gid*HG+HG-1
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire [HG*PWORDS*(TD/H)*16-1:0] ld_wp,   // PCOLP: head gh's word j of p-word w at ((gh*PWORDS + w)*R + j)*16
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    output reg               ov,
    output reg  [HG*32-1:0]  oy,
    output reg  [HG-1:0]     oflt
);
    localparam integer NC = TD / 8;
    localparam integer LV = $clog2(NC);
    localparam integer R = TD / H;
    localparam integer LAT_CORE = FML + 7 * FPL + FPL * LV;
    // FML 8 (1.2 GHz margin build): one more dequantiser stage (DQX: deq_b split across a D2 register, the
    // stationary-load write path registered once more so loads and reads keep their relative cycle) and a
    // seven-stage product (ot_hdc_v41x_attn_bmul_s7); the tile's outputs are tile_l's at FML 6, 2 cycles later
    localparam integer DQX = (FML == 8) ? 1 : 0;
    localparam integer BML = FML - DQX;

    // -- R0: boundary registers (this group's copy)
    reg              r_iv;
    reg [BW-1:0]     r_ibank;
    reg [TD*18-1:0]  r_ib;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r_iv <= 1'b0;
        else r_iv <= iv;
    end
    always @(posedge clk) begin
        r_ibank <= ibank; r_ib <= ib;
    end

    genvar gh, gk;
    wire [TD*18-1:0] dq_b;            // dequantised elements into the skew lines (d1_b, or d2_b when DQX)
    wire [BW-1:0]    dq_bank;
    // -- D1: dequantise, split across the D1 register (zero added cycles): ot_hdc_v41x_attn_deq_a (format decode,
    //    significand product, exponent sum) ahead of it, ot_hdc_v41x_attn_deq_b (normalise, range check, encode)
    //    behind it, so d1_b = {pad, flt, bf16} is the same value in the same cycle as tile_l's D1 register
    wire [TD*18-1:0] d1_b;
    reg  [TD*21-1:0] d1_a;
    reg [BW-1:0]    d1_bank;
    reg             d1_v;
    generate
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_dq
            wire [20:0] da;
            ot_hdc_v41x_attn_deq_a u_da (.e(r_ib[gk*18 +: 18]), .d(da));
            always @(posedge clk) d1_a[gk*21 +: 21] <= da;
            if (DQX == 0) begin : g_b1
                wire [15:0] y;
                wire f;
                ot_hdc_v41x_attn_deq_b u_db (.d(d1_a[gk*21 +: 21]), .y(y), .flt(f));
                assign d1_b[gk*18 +: 18] = {d1_a[gk*21 + 20], f, y};
                assign dq_b[gk*18 +: 18] = d1_b[gk*18 +: 18];
            end else begin : g_b2
                // deq_b split across the D2 register: _b1 (msb, exponent sum, mantissa shift) | _b2 (range, select)
                wire [20:0] e1;
                reg  [20:0] d2_a;
                ot_hdc_v41x_attn_deq_b1 u_db1 (.d(d1_a[gk*21 +: 21]), .e(e1));
                always @(posedge clk) d2_a <= e1;
                wire [15:0] y;
                wire f;
                ot_hdc_v41x_attn_deq_b2 u_db2 (.e(d2_a), .y(y), .flt(f));
                assign d1_b[gk*18 +: 18] = 18'd0;
                assign dq_b[gk*18 +: 18] = {d2_a[20], f, y};
            end
        end
    endgenerate
    always @(posedge clk) d1_bank <= r_ibank;
    ot_hdc_v41x_dly #(.W(BW), .D(DQX)) u_d2bank (.clk(clk), .d(d1_bank), .q(dq_bank));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) d1_v <= 1'b0;
        else d1_v <= r_iv;
    end

    // -- skew: chunk position i issues FPL*(i-1) cycles after position 0
    wire [TD*18-1:0] sk_b;
    wire [8*BW-1:0]  sk_bank;
    generate
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_skb
            localparam integer DS = (gk == 0) ? 0 : FPL * (gk - 1);
            ot_hdc_v41x_dly #(.W(BW), .D(DS)) u_d (.clk(clk), .d(dq_bank), .q(sk_bank[gk*BW +: BW]));
        end
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_ske
            localparam integer DS = ((gk % 8) == 0) ? 0 : FPL * ((gk % 8) - 1);
            ot_hdc_v41x_dly #(.W(18), .D(DS)) u_d (.clk(clk), .d(dq_b[gk*18 +: 18]), .q(sk_b[gk*18 +: 18]));
        end
    endgenerate

    // -- per head of the group (tile head index hh = gid*HG + gh)
    generate
        for (gh = 0; gh < HG; gh = gh + 1) begin : g_h
            // this head's own copy of the stationary-load R0 registers (the shared copy's ~1,000-bit word and its
            // write decode spread over the group; one copy per head keeps each load path local, same cycle)
            // (ot_hdc_v41x_kreg: kept hierarchy, so synthesis cannot merge the equal copies back into one)
            wire             r_ld_v, r_ld_mode;
            wire [BW-1:0]    r_ld_bank;
            wire [7:0]       r_ld_grp;
            wire [PWORDS*TD*16-1:0] r_ld_w;
            wire             r_ld_w2v;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_rv (.clk(clk), .rst_n(rst_n), .d(ld_v), .q(r_ld_v));
            ot_hdc_v41x_kreg #(.W(1 + BW + 8 + 1), .R(0)) u_rc (.clk(clk), .rst_n(rst_n),
                .d({ld_mode, ld_bank, ld_grp, ld_w2v}), .q({r_ld_mode, r_ld_bank, r_ld_grp, r_ld_w2v}));
            ot_hdc_v41x_kreg #(.W(PWORDS*TD*16), .R(0)) u_rw (.clk(clk), .rst_n(rst_n), .d(ld_w), .q(r_ld_w));
            // the head's tile index hh = gid*HG + gh and the group one-hot, registered from the static gid port
            // (constant after reset release: the registers only take gid out of the load paths)
            reg [7:0]      hh;
            reg [H/HG-1:0] gsel;
            integer gq;
            always @(posedge clk) begin
                hh <= gid * HG + gh;
                for (gq = 0; gq < H / HG; gq = gq + 1) gsel[gq] <= (gid == gq);
            end
            // this head's columns of a p-mode word: word j*H + hh, j = 0 .. R-1 (an AND-OR over the groups)
            reg [R*16-1:0] pcol, pcol2;
            if (PCOLP == 0) begin : g_pc
                integer gj, gg;
                always @* begin
                    pcol = {R*16{1'b0}};
                    pcol2 = {R*16{1'b0}};
                    for (gj = 0; gj < R; gj = gj + 1)
                        for (gg = 0; gg < H / HG; gg = gg + 1) begin
                            pcol[gj*16 +: 16] = pcol[gj*16 +: 16] |
                                                ({16{gsel[gg]}} & r_ld_w[(gj * H + gg * HG + gh) * 16 +: 16]);
                            if (PWORDS > 1)
                                pcol2[gj*16 +: 16] = pcol2[gj*16 +: 16] |
                                                     ({16{gsel[gg]}} & r_ld_w[(PWORDS > 1 ? TD * 16 : 0) +
                                                                              (gj * H + gg * HG + gh) * 16 +: 16]);
                        end
                end
            end else begin : g_pp
                // this head's own kept copy of its pre-selected columns (the R0 register of the p-mode words)
                wire [PWORDS*R*16-1:0] r_ld_wp;
                ot_hdc_v41x_kreg #(.W(PWORDS*R*16), .R(0)) u_rp (.clk(clk), .rst_n(rst_n),
                    .d(ld_wp[gh*PWORDS*R*16 +: PWORDS*R*16]), .q(r_ld_wp));
                always @* begin
                    pcol = r_ld_wp[0 +: R*16];
                    pcol2 = (PWORDS > 1) ? r_ld_wp[(PWORDS > 1 ? R*16 : 0) +: R*16] : {R*16{1'b0}};
                end
            end
            wire [TD-1:0]    we;
            wire [TD*16-1:0] wd;
            for (gk = 0; gk < TD; gk = gk + 1) begin : g_w
                if (PWORDS == 1) begin : g_w1
                    assign wd[gk*16 +: 16] = r_ld_mode ? pcol[(gk % R) * 16 +: 16] : r_ld_w[gk * 16 +: 16];
                    assign we[gk] = r_ld_v && (r_ld_mode ? (r_ld_grp == (gk / R)) : (r_ld_grp == hh));
                end else begin : g_w2
                    wire lo = (r_ld_grp == (gk / R));
                    wire hi = r_ld_w2v && ((r_ld_grp + 8'd1) == (gk / R));
                    assign wd[gk*16 +: 16] = !r_ld_mode ? r_ld_w[gk * 16 +: 16] :
                                             hi ? pcol2[(gk % R) * 16 +: 16] : pcol[(gk % R) * 16 +: 16];
                    assign we[gk] = r_ld_v && (r_ld_mode ? (lo || hi) : (r_ld_grp == hh));
                end
            end
            // DQX: the write (enables, data, bank) one cycle later, as the reads (the operand path's D2 stage)
            wire [TD-1:0]    we_q;
            wire [TD*16-1:0] wd_q;
            wire [BW-1:0]    wb_q;
            if (DQX == 0) begin : g_wn
                assign we_q = we; assign wd_q = wd; assign wb_q = r_ld_bank;
            end else begin : g_wr
                reg [TD-1:0]    we_r;
                reg [TD*16-1:0] wd_r;
                reg [BW-1:0]    wb_r;
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) we_r <= {TD{1'b0}};
                    else we_r <= we;
                end
                always @(posedge clk) begin
                    wd_r <= wd; wb_r <= r_ld_bank;
                end
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

// The tile: H/HG head groups; the same ports and cycles as ot_hdc_v41x_attn_tile_l.
module ot_hdc_v41x_attn_tile_s #(
    parameter integer H = 16,
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2,
    parameter integer PWORDS = 1,
    parameter integer FPL = 7,
    parameter integer FML = 6,           // 6 (split product) or 8 (+ D2 dequantiser stage, seven-stage product)
    parameter integer HG = 4,          // heads per hardened group (H % HG == 0)
    parameter integer F12 = 0,
    parameter integer PCOLP = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    output wire              ov,
    output wire [H*32-1:0]   oy,
    output wire [H-1:0]      oflt
);
    localparam integer NG = H / HG;
    localparam integer RT = TD / H;
    wire [NG-1:0] gov;
    genvar g, gh2, gw, gj2;
    generate
        if (FML != 6 && FML != 8) begin : g_bad_fml
            initial $error("ot_hdc_v41x_attn_tile_s: the split product needs FML = 6 or 8");
        end
        if (H % HG != 0) begin : g_bad
            initial $error("ot_hdc_v41x_attn_tile_s: H must be a multiple of HG");
        end
        for (g = 0; g < NG; g = g + 1) begin : g_g
            // the group's heads' p-mode columns, wired out of ld_w (word j*H + hh of each p-word)
            wire [HG*PWORDS*RT*16-1:0] wp;
            for (gh2 = 0; gh2 < HG; gh2 = gh2 + 1) begin : g_wh
                for (gw = 0; gw < PWORDS; gw = gw + 1) begin : g_ww
                    for (gj2 = 0; gj2 < RT; gj2 = gj2 + 1) begin : g_wj
                        assign wp[((gh2*PWORDS + gw)*RT + gj2)*16 +: 16] =
                            ld_w[gw*TD*16 + (gj2*H + g*HG + gh2)*16 +: 16];
                    end
                end
            end
            ot_hdc_v41x_attn_hgrp_s #(.H(H), .HG(HG), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL),
                                      .FML(FML), .F12(F12), .PCOLP(PCOLP)) u_g (
                .clk(clk), .rst_n(rst_n), .gid(g[7:0]), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank),
                .ld_grp(ld_grp), .ld_w(ld_w), .ld_wp(wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(gov[g]),
                .oy(oy[g*HG*32 +: HG*32]), .oflt(oflt[g*HG +: HG]));
        end
    endgenerate
    assign ov = gov[0];
endmodule

// ---------------------------------------------------------------------------
// Product with the 8 x 8 significand multiply split across the stage-1 register (zero added cycles): the text
// of ot_hdc_v41x_attn_bmul_l (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv) at ML = 6 with stage 1 replaced.  In the
// head-group context the bmul_l stage 1 (operand register -> 8 x 8 multiply -> product register) missed SS by
// ~200 ps; here stage 1 makes two 8 x 4 partial products and stage 2 adds them (keep-prefix 16-bit add) ahead of
// its leading-zero count, before the ML >= 5 cut.  Same value, same cycle as bmul_l at ML = 6.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_bmul_s #(
    parameter integer ML = 6           // 6 only (the split needs the operand register)
) (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] b,
    input  wire        pad,
    output reg  [31:0] y,
    output reg         flt
);
    // -- operand register (ML = 6), as bmul_l: the bank-select mux and the skewed element only
    wire [15:0] oa, ob;
    wire        opad;
    ot_hdc_v41x_dly #(.W(33), .D(1)) u_cut0 (.clk(clk), .d({a, b, pad}), .q({oa, ob, opad}));
    // -- stage 1: decode, the two 8 x 4 partial products ma * mb[3:0] and ma * mb[7:4] (exact), exponent sum
    wire [7:0] ea = oa[14:7];
    wire [7:0] eb = ob[14:7];
    wire [7:0] ma = {(ea != 8'd0), oa[6:0]};
    wire [7:0] mb = {(eb != 8'd0), ob[6:0]};
    wire [8:0] esum_c = {1'b0, (ea == 8'd0) ? 8'd1 : ea} + {1'b0, (eb == 8'd0) ? 8'd1 : eb};
    wire nonfin_c = !opad && ((ea == 8'hff) || (eb == 8'hff));
    wire zero_c = opad || (ma == 8'd0) || (mb == 8'd0);
    reg [11:0] s1_pl, s1_ph;
    reg [8:0]  s1_esum;
    reg        s1_sign, s1_zero, s1_nonfin;
    always @(posedge clk) begin
        s1_pl <= ma * mb[3:0];
        s1_ph <= ma * mb[7:4];
        s1_esum <= esum_c;
        s1_sign <= oa[15] ^ ob[15];
        s1_zero <= zero_c;
        s1_nonfin <= nonfin_c;
    end
    // the 16-bit product, summed at the head of stage 2 (keep-prefix adder) ahead of its leading-zero count
    wire [15:0] s1_p;
    wire        pco;
    ot_hdc_ksadd_k #(.W(16)) u_ps (.a({4'd0, s1_pl}), .b({s1_ph, 4'd0}), .cin(1'b0), .s(s1_p), .cout(pco));

    // -- stage 2: normalise; normal encoding; subnormal shift amounts
    //: value = P * 2^(esum - 268); msb at 15 - lz; biased exponent
    //: esum - 126 - lz; a subnormal result is P * 2^(esum - 119) in units of
    //: 2^-149, i.e. P << (esum - 119) or P >> (119 - esum) rounded.
    reg [3:0] lz0;
    integer i;
    always @* begin
        lz0 = 4'd15;
        for (i = 0; i < 16; i = i + 1)
            if (s1_p[i]) lz0 = 4'd15 - i[3:0];
    end
    wire [3:0]  lz;
    wire [15:0] c1_p;
    wire [8:0]  c1_esum;
    wire        c1_sign, c1_zero, c1_nonfin;
    ot_hdc_v41x_dly #(.W(4 + 16 + 9 + 3), .D((ML >= 5) ? 1 : 0)) u_cut2 (.clk(clk),
        .d({lz0, s1_p, s1_esum, s1_sign, s1_zero, s1_nonfin}), .q({lz, c1_p, c1_esum, c1_sign, c1_zero, c1_nonfin}));
    wire [15:0] pn = c1_p << lz;
    wire signed [10:0] biased = $signed({2'b00, c1_esum}) - 11'sd126 - $signed({7'd0, lz});
    wire normal_c = biased >= 11'sd1;
    wire over_c = biased >= 11'sd255;
    wire signed [10:0] lsh = $signed({2'b00, c1_esum}) - 11'sd119;   // left shift if >= 0
    reg [31:0] s2_code_n;
    reg [15:0] s2_p;
    reg [4:0]  s2_lsh;            // 0 .. 22 when used
    reg [4:0]  s2_rsh;            // 1 .. 17 (clamped) when used
    reg        s2_left, s2_normal, s2_over, s2_sign, s2_zero, s2_nonfin;
    always @(posedge clk) begin
        s2_code_n <= {c1_sign, biased[7:0], pn[14:0], 8'd0};
        s2_p <= c1_p;
        s2_left <= !lsh[10];
        s2_lsh <= (lsh > 11'sd22) ? 5'd22 : lsh[4:0];
        s2_rsh <= (lsh < -11'sd17) ? 5'd17 : (-lsh[4:0]);
        s2_normal <= normal_c;
        s2_over <= over_c;
        s2_sign <= c1_sign;
        s2_zero <= c1_zero;
        s2_nonfin <= c1_nonfin;
    end

    // -- stage 3: subnormal alignment [cut, ML >= 4] and rounding, select, encode
    wire [22:0] lft0 = {7'd0, s2_p} << s2_lsh;
    wire [15:0] rgt0 = s2_p >> s2_rsh;
    wire [31:0] below = {s2_p, 16'd0} >> s2_rsh;       // bits shifted out, MSB first at [15]
    wire [22:0] lft;
    wire [15:0] rgt;
    wire [31:0] c3_code_n;
    wire rb, st, c3_left, c3_normal, c3_over, c3_sign, c3_zero, c3_nonfin;
    ot_hdc_v41x_dly #(.W(23 + 16 + 32 + 8), .D((ML >= 4) ? 1 : 0)) u_cut3 (.clk(clk),
        .d({lft0, rgt0, s2_code_n, below[15], |below[14:0], s2_left, s2_normal, s2_over, s2_sign, s2_zero, s2_nonfin}),
        .q({lft, rgt, c3_code_n, rb, st, c3_left, c3_normal, c3_over, c3_sign, c3_zero, c3_nonfin}));
    wire [23:0] sub_f = c3_left ? {1'b0, lft} : ({8'd0, rgt} + {23'd0, rb && (st || rgt[0])});
    wire [31:0] code_s = {c3_sign, 7'd0, sub_f};
    always @(posedge clk) begin
        if (c3_nonfin) begin
            y <= 32'd0; flt <= 1'b1;
        end else if (c3_zero) begin
            y <= 32'd0; flt <= 1'b0;
        end else if (c3_normal) begin
            y <= c3_over ? 32'd0 : c3_code_n; flt <= c3_over;
        end else begin
            y <= (sub_f == 24'd0) ? 32'd0 : code_s; flt <= 1'b0;
        end
    end
endmodule

// Head datapath: ot_hdc_v41x_attn_hdp_l with the split product ot_hdc_v41x_attn_bmul_s (FML must be 6).
module ot_hdc_v41x_attn_hdp_s #(
    parameter integer TD = 64,
    parameter integer NBANK = 3,
    parameter integer BW = 2,
    parameter integer FPL = 3,
    parameter integer FML = 3,
    parameter integer F12 = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [TD-1:0]     we,
    input  wire [BW-1:0]     wbank,
    input  wire [TD*16-1:0]  wd,
    input  wire [8*BW-1:0]   sk_bank,
    input  wire [TD*18-1:0]  sk_b,
    output wire [31:0]       y,
    output wire              f
);
    localparam integer NC = TD / 8;
    wire [TD*32-1:0] p;
    wire [TD-1:0]    pf;
    genvar gk, gn;
    generate
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_m
            reg [NBANK*16-1:0] ab;
            integer bb;
            always @(posedge clk)
                for (bb = 0; bb < NBANK; bb = bb + 1)
                    if (we[gk] && (wbank == bb)) ab[bb*16 +: 16] <= wd[gk*16 +: 16];
            wire [BW-1:0] bk = sk_bank[(gk % 8)*BW +: BW];
            wire [15:0] av = ab[bk*16 +: 16];
            wire [17:0] be = sk_b[gk*18 +: 18];
            wire mf;
            if (FML == 7) begin : g_m7
                ot_hdc_v41x_attn_bmul_s7 u_m (.clk(clk), .a(av), .b(be[15:0]), .pad(be[17]), .y(p[gk*32 +: 32]), .flt(mf));
            end else begin : g_m6
                ot_hdc_v41x_attn_bmul_s #(.ML(FML)) u_m (.clk(clk), .a(av), .b(be[15:0]), .pad(be[17]), .y(p[gk*32 +: 32]), .flt(mf));
            end
            // dequant fault rides with the product
            wire dfq;
            ot_hdc_v41x_dly #(.W(1), .D(FML)) u_df (.clk(clk), .d(be[16] & ~be[17]), .q(dfq));
            assign pf[gk] = mf | dfq;
        end
        wire [(2*NC-1)*32-1:0] tn;      // heap order: leaves (chunk sums) at NC-1 .. 2NC-2
        wire [2*NC-2:0]        tf;
        for (gn = 0; gn < NC; gn = gn + 1) begin : g_c
            ot_hdc_v41x_attn_chunk_s #(.FPL(FPL), .F12(F12)) u_c (.clk(clk), .rst_n(rst_n), .p(p[gn*256 +: 256]), .pf(pf[gn*8 +: 8]),
                                        .y(tn[(NC-1+gn)*32 +: 32]), .f(tf[NC-1+gn]));
        end
        for (gn = 0; gn < NC - 1; gn = gn + 1) begin : g_node
            wire [31:0] s;
            wire sf;
            ot_hdc_v41x_qaddf #(.LAT(FPL), .F12(F12)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(tn[(2*gn+1)*32 +: 32]),
                             .b(tn[(2*gn+2)*32 +: 32]), .y(s), .fault(sf));
            wire fdq;
            ot_hdc_v41x_dly #(.W(1), .D(FPL)) u_fd (.clk(clk), .d(tf[2*gn+1] | tf[2*gn+2]), .q(fdq));
            assign tn[gn*32 +: 32] = s;
            assign tf[gn] = fdq | sf;
        end
    endgenerate
    assign y = tn[31:0];
    assign f = tf[0];
endmodule

// One chunk (8 products, sequential sum): ot_hdc_v41x_attn_chunk_l with the add unit ot_hdc_v41x_qaddf.
module ot_hdc_v41x_attn_chunk_s #(
    parameter integer FPL = 3,
    parameter integer F12 = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [8*32-1:0] p,
    input  wire [7:0]    pf,
    output wire [31:0]   y,
    output wire          f
);
    wire [8*32-1:0] acc;
    wire [7:0]      af;
    assign acc[31:0] = p[31:0];
    assign af[0] = pf[0];
    genvar gi;
    generate
        for (gi = 1; gi < 8; gi = gi + 1) begin : g_a
            wire [31:0] s;
            wire sf;
            ot_hdc_v41x_qaddf #(.LAT(FPL), .F12(F12)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(acc[(gi-1)*32 +: 32]),
                             .b(p[gi*32 +: 32]), .y(s), .fault(sf));
            wire fdq;
            ot_hdc_v41x_dly #(.W(1), .D(FPL)) u_fd (.clk(clk), .d(af[gi-1] | pf[gi]), .q(fdq));
            assign acc[gi*32 +: 32] = s;
            assign af[gi] = fdq | sf;
        end
    endgenerate
    assign y = acc[7*32 +: 32];
    assign f = af[7];
endmodule

// Fault-reporting binary32 add: F12 = 0 is ot_hdc_v41x_qaddl #(LAT) (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv);
// F12 = 1 is the 1.2 GHz f12 unit of the same function (rtl/hdc/ot_hdc_fp32_f12.sv, which a F12 build lists):
// LAT 4 ot_hdc_fp32_add_f12_l4 (registered operands), LAT 5 ot_hdc_fp32_add_f12_l5x (an operand mux in front),
// LAT 6 ot_hdc_fp32_add_f12_l6x (rtl/hdc/v41x/ot_dsrom_su_add6.sv, which a LAT-6 F12 build lists).
module ot_hdc_v41x_qaddf #(
    parameter integer LAT = 3,
    parameter integer F12 = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    generate
        if (F12 != 0 && LAT == 4) begin : g_f4
            wire [1:0] err;
            wire vo;
            ot_hdc_fp32_add_f12_l4 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                      .valid_out(vo));
            assign fault = vo && (err != 2'd0);
        end else if (F12 != 0 && LAT == 5) begin : g_f5
            wire [1:0] err;
            wire vo;
            ot_hdc_fp32_add_f12_l5x u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                       .valid_out(vo));
            assign fault = vo && (err != 2'd0);
        end else if (F12 != 0 && LAT == 6) begin : g_f6
            // LAT 6: ot_hdc_fp32_add_f12_l6x (rtl/hdc/v41x/ot_dsrom_su_add6.sv, the DS ROM kit's six-cut adder: the
            // l5x cuts plus one between the magnitude compare and the alignment); the routed hgrp_m4 leaf missed SS
            // by 172 ps on the LAT-4 decode/compare/align stage fed straight by the previous chain adder's output
            wire [1:0] err;
            wire vo;
            ot_hdc_fp32_add_f12_l6x u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                       .valid_out(vo));
            assign fault = vo && (err != 2'd0);
        end else if (F12 != 0 && LAT == 7) begin : g_f7
            // LAT 7: the six cuts of l6x plus one between the 28-bit sum/difference and the sentinel LZC (CUTS bit 2)
            wire [1:0] err;
            wire vo;
            ot_hdc_fp32_add_f12 #(.CUTS(7'b1101111)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y),
                                                     .err(err), .valid_out(vo));
            assign fault = vo && (err != 2'd0);
        end else begin : g_l
            ot_hdc_v41x_qaddl #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(y), .fault(fault));
        end
    endgenerate
endmodule

// The attention dequantiser ot_hdc_v41x_attn_deq (rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv) split in two: _a computes
// {pad, nan, sgn, prod[5:0], bx[10:0]} (bx before the msb correction), _b the rest of the same expressions.
module ot_hdc_v41x_attn_deq_a (
    input  wire [17:0] e,          // {pad, fmt, code[7:0], scale[7:0]}
    output wire [20:0] d           // {pad, nan, sgn, prod[5:0], bx[10:0]} -- 1 + 1 + 1 + 6 + 11 = 20 bits + spare
);
    wire pad = e[17];
    wire fmt = e[16];
    wire [7:0] c = e[15:8];
    wire [7:0] s = e[7:0];
    reg signed [10:0] bx;
    reg [5:0] prod;
    reg sgn, nan;
    always @* begin
        if (!fmt) begin
            sgn = c[7];
            nan = ((c[6:3] == 4'hf) && (c[2:0] == 3'd7)) || (s == 8'hff);
            prod = {2'b00, (c[6:3] != 4'd0), c[2:0]};
            bx = $signed({7'd0, (c[6:3] == 4'd0) ? 4'd1 : c[6:3]}) + $signed({3'd0, s}) - 11'sd137;
        end else begin
            sgn = c[3] ^ s[7];
            nan = (s[6:3] == 4'hf) && (s[2:0] == 3'd7);
            prod = {(c[2:1] != 2'd0), c[0]} * {(s[6:3] != 4'd0), s[2:0]};
            bx = $signed({9'd0, (c[2:1] == 2'd0) ? 2'd1 : c[2:1]}) - 11'sd2
               + $signed({7'd0, (s[6:3] == 4'd0) ? 4'd1 : s[6:3]}) - 11'sd10;
        end
    end
    assign d = {pad, 1'b0, nan, sgn, prod, bx};
endmodule

module ot_hdc_v41x_attn_deq_b (
    input  wire [20:0] d,
    output reg  [15:0] y,
    output reg         flt
);
    wire pad = d[20];
    wire nan = d[18];
    wire sgn = d[17];
    wire [5:0] prod = d[16:11];
    wire signed [10:0] bx0 = d[10:0];
    reg signed [10:0] bx;
    reg [6:0] man;
    reg [2:0] msb;
    reg zero;
    integer i;
    always @* begin
        msb = 3'd0;
        zero = (prod == 6'd0);
        for (i = 0; i < 6; i = i + 1)
            if (prod[i]) msb = i[2:0];
        bx = bx0 + $signed({8'd0, msb}) + 11'sd127;
        man = ({1'b0, prod} << (3'd6 - msb));
        if (pad) begin
            y = 16'd0; flt = 1'b0;
        end else if (nan) begin
            y = 16'd0; flt = 1'b1;
        end else if (zero) begin
            y = {sgn, 15'd0}; flt = 1'b0;
        end else if ((bx < 11'sd1) || (bx > 11'sd254)) begin
            y = 16'd0; flt = 1'b1;
        end else begin
            y = {sgn, bx[7:0], man[5:0], 1'b0}; flt = 1'b0;
        end
    end
endmodule

// ---------------------------------------------------------------------------
// FML 8 pieces (1.2 GHz margin build; the routed hgrp_m4 leaf at FML 6 missed SS by 72-119 ps on the dequantiser
// (d1_a -> deq_b -> skew / operand register), the product's stage 1 (decode + exponent sum + 8 x 4 products from
// the operand register) and stage 3 (the subnormal rounding increment, mapped as an OR ripple)).
// ---------------------------------------------------------------------------
// ot_hdc_v41x_attn_deq_b's expressions split in two: _b1 the msb, the biased exponent (keep-prefix adder) and the
// mantissa shift; _b2 the range check and the select.  e = {pad, nan, sgn, nz, man[5:0], bx[10:0]} (nz = product
// nonzero, so an all-zero D2 word decodes as deq_b's all-zero D1 word: a zero, no fault).
module ot_hdc_v41x_attn_deq_b1 (
    input  wire [20:0] d,
    output wire [20:0] e
);
    wire pad = d[20];
    wire nan = d[18];
    wire sgn = d[17];
    wire [5:0] prod = d[16:11];
    wire [10:0] bx0 = d[10:0];
    reg [2:0] msb;
    integer i;
    always @* begin
        msb = 3'd0;
        for (i = 0; i < 6; i = i + 1)
            if (prod[i]) msb = i[2:0];
    end
    wire nz = (prod != 6'd0);
    wire [6:0] man = ({1'b0, prod} << (3'd6 - msb));
    // bx = bx0 + msb + 127 (11-bit two's complement, as deq_b's signed sum)
    wire [10:0] k = 11'd127 + {8'd0, msb};
    wire [10:0] bx;
    wire bco;
    ot_hdc_ksadd_k #(.W(11)) u_bx (.a(bx0), .b(k), .cin(1'b0), .s(bx), .cout(bco));
    assign e = {pad, nan, sgn, nz, man[5:0], bx};
endmodule

module ot_hdc_v41x_attn_deq_b2 (
    input  wire [20:0] e,
    output reg  [15:0] y,
    output reg         flt
);
    wire pad = e[20];
    wire nan = e[19];
    wire sgn = e[18];
    wire zero = !e[17];
    wire [5:0] man = e[16:11];
    wire signed [10:0] bx = e[10:0];
    always @* begin
        if (pad) begin
            y = 16'd0; flt = 1'b0;
        end else if (nan) begin
            y = 16'd0; flt = 1'b1;
        end else if (zero) begin
            y = {sgn, 15'd0}; flt = 1'b0;
        end else if ((bx < 11'sd1) || (bx > 11'sd254)) begin
            y = 16'd0; flt = 1'b1;
        end else begin
            y = {sgn, bx[7:0], man, 1'b0}; flt = 1'b0;
        end
    end
endmodule

// y = a * b (8 x 4 bits, exact): four AND rows, two 3:2 carry-save levels, one kept-prefix add
module ot_hdc_v41x_attn_m84 (
    input  wire [7:0]  a,
    input  wire [3:0]  b,
    output wire [11:0] y
);
    wire [11:0] r0 = b[0] ? {4'd0, a}       : 12'd0;
    wire [11:0] r1 = b[1] ? {3'd0, a, 1'b0} : 12'd0;
    wire [11:0] r2 = b[2] ? {2'd0, a, 2'b0} : 12'd0;
    wire [11:0] r3 = b[3] ? {1'd0, a, 3'b0} : 12'd0;
    wire [11:0] s1 = r0 ^ r1 ^ r2;
    wire [11:0] c1 = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
    wire [11:0] s2 = s1 ^ c1 ^ r3;
`ifdef OT_NEG_ATTN_M84
    // NEGATIVE CONTROL (compile-time only): the second level drops the (s1 & r3) carry; lockstep must FAIL
    wire [11:0] c2 = ((s1 & c1) | (c1 & r3)) << 1;
`else
    wire [11:0] c2 = ((s1 & c1) | (s1 & r3) | (c1 & r3)) << 1;
`endif
    wire co;
    ot_hdc_ksadd_k #(.W(12)) u_a (.a(s2), .b(c2), .cin(1'b0), .s(y), .cout(co));
endmodule

// ot_hdc_v41x_attn_bmul_s with one more stage (ML 7): the operand decode and the exponent sum (keep-prefix adder)
// get their own stage ahead of the two 8 x 4 partial products, and the subnormal rounding increment is a
// keep-prefix incrementer.  Same value as bmul_s / bmul_l at ML 6, one cycle later.
module ot_hdc_v41x_attn_bmul_s7 (
    input  wire        clk,
    input  wire [15:0] a,
    input  wire [15:0] b,
    input  wire        pad,
    output reg  [31:0] y,
    output reg         flt
);
    wire [15:0] oa, ob;
    wire        opad;
    ot_hdc_v41x_dly #(.W(33), .D(1)) u_cut0 (.clk(clk), .d({a, b, pad}), .q({oa, ob, opad}));
    // -- stage 1a: decode, exponent sum
    wire [7:0] ea = oa[14:7];
    wire [7:0] eb = ob[14:7];
    wire [7:0] ma_c = {(ea != 8'd0), oa[6:0]};
    wire [7:0] mb_c = {(eb != 8'd0), ob[6:0]};
    wire [8:0] esum_w;
    wire       esum_co;
    ot_hdc_ksadd_k #(.W(9)) u_es (.a({1'b0, (ea == 8'd0) ? 8'd1 : ea}), .b({1'b0, (eb == 8'd0) ? 8'd1 : eb}),
                                  .cin(1'b0), .s(esum_w), .cout(esum_co));
    reg [7:0] d_ma, d_mb;
    reg [8:0] d_esum;
    reg       d_sign, d_zero, d_nonfin;
    always @(posedge clk) begin
        d_ma <= ma_c;
        d_mb <= mb_c;
        d_esum <= esum_w;
        d_sign <= oa[15] ^ ob[15];
        d_zero <= opad || (ma_c == 8'd0) || (mb_c == 8'd0);
        d_nonfin <= !opad && ((ea == 8'hff) || (eb == 8'hff));
    end
    // -- stage 1b: the two 8 x 4 partial products.  Margin (option-B leaf lb_u45_m6 @770: d_mb -> s1_ph -28.3 ps,
    // +35.0 at 833.333, the leaf's only class under +40): each 8 x 4 product is four AND rows, two explicit 3:2
    // carry-save levels and one kept-prefix add (ABC had mapped the inferred multiply to a 13-gate ripple)
    reg [11:0] s1_pl, s1_ph;
    reg [8:0]  s1_esum;
    reg        s1_sign, s1_zero, s1_nonfin;
    wire [11:0] m84_l, m84_h;
    ot_hdc_v41x_attn_m84 u_m84l (.a(d_ma), .b(d_mb[3:0]), .y(m84_l));
    ot_hdc_v41x_attn_m84 u_m84h (.a(d_ma), .b(d_mb[7:4]), .y(m84_h));
    always @(posedge clk) begin
        s1_pl <= m84_l;
        s1_ph <= m84_h;
        s1_esum <= d_esum;
        s1_sign <= d_sign;
        s1_zero <= d_zero;
        s1_nonfin <= d_nonfin;
    end
    wire [15:0] s1_p;
    wire        pco;
    ot_hdc_ksadd_k #(.W(16)) u_ps (.a({4'd0, s1_pl}), .b({s1_ph, 4'd0}), .cin(1'b0), .s(s1_p), .cout(pco));
    // -- stage 2 (as bmul_s)
    reg [3:0] lz0;
    integer i;
    always @* begin
        lz0 = 4'd15;
        for (i = 0; i < 16; i = i + 1)
            if (s1_p[i]) lz0 = 4'd15 - i[3:0];
    end
    wire [3:0]  lz;
    wire [15:0] c1_p;
    wire [8:0]  c1_esum;
    wire        c1_sign, c1_zero, c1_nonfin;
    ot_hdc_v41x_dly #(.W(4 + 16 + 9 + 3), .D(1)) u_cut2 (.clk(clk),
        .d({lz0, s1_p, s1_esum, s1_sign, s1_zero, s1_nonfin}), .q({lz, c1_p, c1_esum, c1_sign, c1_zero, c1_nonfin}));
    wire [15:0] pn = c1_p << lz;
    wire signed [10:0] biased = $signed({2'b00, c1_esum}) - 11'sd126 - $signed({7'd0, lz});
    wire normal_c = biased >= 11'sd1;
    wire over_c = biased >= 11'sd255;
    wire signed [10:0] lsh = $signed({2'b00, c1_esum}) - 11'sd119;
    reg [31:0] s2_code_n;
    reg [15:0] s2_p;
    reg [4:0]  s2_lsh;
    reg [4:0]  s2_rsh;
    reg        s2_left, s2_normal, s2_over, s2_sign, s2_zero, s2_nonfin;
    always @(posedge clk) begin
        s2_code_n <= {c1_sign, biased[7:0], pn[14:0], 8'd0};
        s2_p <= c1_p;
        s2_left <= !lsh[10];
        s2_lsh <= (lsh > 11'sd22) ? 5'd22 : lsh[4:0];
        s2_rsh <= (lsh < -11'sd17) ? 5'd17 : (-lsh[4:0]);
        s2_normal <= normal_c;
        s2_over <= over_c;
        s2_sign <= c1_sign;
        s2_zero <= c1_zero;
        s2_nonfin <= c1_nonfin;
    end
    // -- stage 3: subnormal alignment [cut], rounding (keep-prefix increment), select, encode
    wire [22:0] lft0 = {7'd0, s2_p} << s2_lsh;
    wire [15:0] rgt0 = s2_p >> s2_rsh;
    wire [31:0] below = {s2_p, 16'd0} >> s2_rsh;
    wire [22:0] lft;
    wire [15:0] rgt;
    wire [31:0] c3_code_n;
    wire rb, st, c3_left, c3_normal, c3_over, c3_sign, c3_zero, c3_nonfin;
    ot_hdc_v41x_dly #(.W(23 + 16 + 32 + 8), .D(1)) u_cut3 (.clk(clk),
        .d({lft0, rgt0, s2_code_n, below[15], |below[14:0], s2_left, s2_normal, s2_over, s2_sign, s2_zero, s2_nonfin}),
        .q({lft, rgt, c3_code_n, rb, st, c3_left, c3_normal, c3_over, c3_sign, c3_zero, c3_nonfin}));
    wire [15:0] rgt_i;
    wire        rgt_co;
    ot_hdc_inc_k #(.W(16)) u_rnd (.a(rgt), .inc(rb && (st || rgt[0])), .y(rgt_i), .co(rgt_co));
    wire [23:0] sub_f = c3_left ? {1'b0, lft} : {7'd0, rgt_co, rgt_i};
    wire [31:0] code_s = {c3_sign, 7'd0, sub_f};
    always @(posedge clk) begin
        if (c3_nonfin) begin
            y <= 32'd0; flt <= 1'b1;
        end else if (c3_zero) begin
            y <= 32'd0; flt <= 1'b0;
        end else if (c3_normal) begin
            y <= c3_over ? 32'd0 : c3_code_n; flt <= c3_over;
        end else begin
            y <= (sub_f == 24'd0) ? 32'd0 : code_s; flt <= 1'b0;
        end
    end
endmodule
