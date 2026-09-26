`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Stream unit of the hardwired decode core.
//
// A 2-D loop (outer o, inner i) issues one element per cycle, never stalling.
// Each element reads up to three operands -- A (vector memory, or the weight ROM
// as BF16), B (vector memory, or a constant-ROM pair lo/hi), C (vector memory,
// or constant-ROM lo) -- and passes a fixed pipeline:
//
//     P = A | A*B | A*A | A*imm1          Q = C * (+-B.hi)
//     R = P | P+Q | P+C | P-B | P+imm2
//     S = R | exp(R) | 1/R | 1/sqrt(R) | 1/(exp(R)+1)   (the instruction's SFU class)
//     out = (S | S*C) (| *B)
//
// then is written (vector memory or KV SRAM) and/or reduced per segment.
// Every operator is a qualified pipelined binary32 unit; the SFU class sets the
// pipeline depth, so a new instruction of another class waits for the unit to
// drain (in-order writes, no reorder logic).  Depth from the address cycle to
// the write: 27 (no SFU), 73 (reciprocal), 88 (rsqrt), 119 (exp), 170 (sigmoid).
// `progress` counts the elements the latest instruction has written, for
// element chaining by the sequencer.
// ---------------------------------------------------------------------------
module ot_hdc_stream #(
    parameter integer W  = 16,
    parameter integer WR = 64,        // bf16 lanes per weight-ROM word
    parameter integer AW = 24,
    parameter integer NW = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_nin,
    input  wire              i_asrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi,
    input  wire              i_bsrc,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_csrc,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire [1:0]        i_ma,
    input  wire [1:0]        i_mb,
    input  wire [2:0]        i_ad,
    input  wire [2:0]        i_sfu,
    input  wire              i_mc,
    input  wire              i_md,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire [1:0]        i_red,
    input  wire              i_redsq,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2,
    // reads
    output reg               va_re,
    output reg  [AW-1:0]     va_addr,
    input  wire [31:0]       va_q,
    output reg               vb_re,
    output reg  [AW-1:0]     vb_addr,
    input  wire [31:0]       vb_q,
    output reg               vc_re,
    output reg  [AW-1:0]     vc_addr,
    input  wire [31:0]       vc_q,
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    input  wire [WR*16-1:0]  wrom_q,
    output reg               crom_re,
    output reg  [AW-1:0]     crom_addr,
    input  wire [63:0]       crom_q,
    // writes
    output reg               vm_we,
    output reg  [AW-1:0]     vm_waddr,
    output reg  [31:0]       vm_wdata,
    output reg               kv_we,
    output reg  [AW-1:0]     kv_waddr,
    output reg  [31:0]       kv_wdata,
    output wire              red_we,
    output wire [AW-1:0]     red_addr,
    output wire [31:0]       red_data,
    // elements the latest accepted instruction has written
    output reg  [15:0]       progress,
    output reg               fault
);
    localparam integer LW = $clog2(WR);   // weight-ROM element -> word, lane
    localparam [1:0] MA_BYP = 0, MA_AB = 1, MA_AA = 2, MA_AIMM = 3;
    localparam [1:0] MB_OFF = 0, MB_POS = 1, MB_NEG = 2;
    localparam [2:0] AD_BYP = 0, AD_Q = 1, AD_C = 2, AD_NEGB = 3, AD_IMM = 4;
    localparam [2:0] SFU_NONE = 0, SFU_EXP = 1, SFU_RECIP = 2, SFU_RSQRT = 3, SFU_SIGM = 4;
    localparam integer D_EXP = 92, D_RECIP = 46, D_RSQRT = 61;
    localparam integer D_SIGM = D_EXP + 5 + D_RECIP;   // exp, +1, reciprocal
    localparam integer TAP0 = 11;                 // S3 -> S14
    localparam integer TAPMAX = TAP0 + D_SIGM;

    // -- issue loop -----------------------------------------------------------
    reg              active;
    reg [2:0]        cls;
    reg [7:0]        inflight;
    reg [NW-1:0]     o, i, nout_r, nin_r;
    reg              i_last_r, o_last_r;
    reg [NW:0]       fin_th;                      // nin - 8 (signed)
    reg [AW-1:0]     rowa, rowb, rowc, rowd, cura, curb, curc, curd, rrow;
    reg [AW-1:0]     aso, asi, bso, bsi, cso, csi, dso, dsi, rso;
    reg              asrc, bsrc, csrc, mc, md, redsq;
    reg [1:0]        ma, mb, dst, red;
    reg [2:0]        ad;
    reg [31:0]       imm1, imm2;
    wire             reducer_busy;

    assign ready = !active && ((i_sfu == cls) || (inflight == 0));
    wire   accept = go && ready;
    wire   emit = active;
    wire   retire;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; cls <= SFU_NONE; inflight <= 0;
        end else begin
            inflight <= inflight + (emit ? 8'd1 : 8'd0) - (retire ? 8'd1 : 8'd0);
            if (accept) begin
                active <= 1'b1; cls <= i_sfu;
            end else if (active && i_last_r && o_last_r) begin
                active <= 1'b0;
            end
        end
    end
    always @(posedge clk) begin
        if (accept) begin
            o <= 0; i <= 0; nout_r <= i_nout; nin_r <= i_nin;
            i_last_r <= (i_nin == 1); o_last_r <= (i_nout == 1);
            fin_th <= {1'b0, i_nin} - 17'd8;
            rowa <= i_abase; cura <= i_abase; rowb <= i_bbase; curb <= i_bbase;
            rowc <= i_cbase; curc <= i_cbase; rowd <= i_dbase; curd <= i_dbase; rrow <= i_rbase;
            aso <= i_aso; asi <= i_asi; bso <= i_bso; bsi <= i_bsi; cso <= i_cso; csi <= i_csi;
            dso <= i_dso; dsi <= i_dsi; rso <= i_rso;
            asrc <= i_asrc; bsrc <= i_bsrc; csrc <= i_csrc; mc <= i_mc; md <= i_md;
            ma <= i_ma; mb <= i_mb; ad <= i_ad; dst <= i_dst; red <= i_red; redsq <= i_redsq;
            imm1 <= i_imm1; imm2 <= i_imm2;
        end else if (active) begin
            if (!i_last_r) begin
                i <= i + 1'b1; i_last_r <= (i + 2 == nin_r);
                cura <= cura + asi; curb <= curb + bsi; curc <= curc + csi; curd <= curd + dsi;
            end else begin
                i <= 0; i_last_r <= (nin_r == 1);
                o <= o + 1'b1; o_last_r <= (o + 2 == nout_r);
                rowa <= rowa + aso; cura <= rowa + aso; rowb <= rowb + bso; curb <= rowb + bso;
                rowc <= rowc + cso; curc <= rowc + cso; rowd <= rowd + dso; curd <= rowd + dso;
                rrow <= rrow + rso;
            end
        end
    end

    // -- address cycle (c') -----------------------------------------------------
    // Tag fields of one element.
    reg          e_v;
    reg          e_asrc, e_bsrc, e_csrc, e_mc, e_md, e_redsq;
    reg [1:0]    e_ma, e_mb, e_dst, e_red;
    reg [2:0]    e_ad;
    reg [31:0]   e_imm1, e_imm2;
    reg [LW-1:0] e_lane;
    reg          e_ifirst, e_first8, e_final, e_last;
    reg [2:0]    e_p;
    reg [AW-1:0] e_daddr, e_raddr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            e_v <= 1'b0; va_re <= 1'b0; vb_re <= 1'b0; vc_re <= 1'b0; wrom_re <= 1'b0; crom_re <= 1'b0;
        end else begin
            e_v <= emit;
            va_re <= emit && !asrc; wrom_re <= emit && asrc;
            vb_re <= emit && !bsrc; vc_re <= emit && !csrc;
            crom_re <= emit && (bsrc || csrc);
        end
    end
    always @(posedge clk) begin
        va_addr <= cura; wrom_addr <= cura >> LW; e_lane <= cura[LW-1:0];
        vb_addr <= curb; vc_addr <= curc; crom_addr <= bsrc ? curb : curc;
        e_asrc <= asrc; e_bsrc <= bsrc; e_csrc <= csrc; e_mc <= mc; e_md <= md; e_redsq <= redsq;
        e_ma <= ma; e_mb <= mb; e_ad <= ad; e_dst <= dst; e_red <= red;
        e_imm1 <= imm1; e_imm2 <= imm2;
        e_ifirst <= (i == 0); e_first8 <= (i < 8);
        e_final <= ($signed({1'b0, i}) >= $signed(fin_th)); e_last <= i_last_r;
        e_p <= i[2:0]; e_daddr <= curd; e_raddr <= rrow;
    end

    // -- S1 (memories answer) -> S2 (capture) -> S3 (operand select) -----------
    localparam integer FT = 1+1+1+1+1+1 + 2+2+2+2 + 3 + 32+32 + LW + 1+1+1+1 + 3 + AW + AW;
    wire [FT-1:0] e_tag = {e_asrc, e_bsrc, e_csrc, e_mc, e_md, e_redsq, e_ma, e_mb, e_dst, e_red, e_ad, e_imm1, e_imm2,
                           e_lane, e_ifirst, e_first8, e_final, e_last, e_p, e_daddr, e_raddr};
    reg [FT-1:0] s1_tag;
    reg          s1_v, s2_v, s3_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= e_v; s2_v <= s1_v; s3_v <= s2_v; end
    end
    wire          t_asrc, t_bsrc, t_csrc, t_mc, t_md, t_redsq;
    wire [1:0]    t_ma, t_mb, t_dst, t_red;
    wire [2:0]    t_ad;
    wire [31:0]   t_imm1, t_imm2;
    wire [LW-1:0] t_lane;
    wire          t_ifirst, t_first8, t_final, t_last;
    wire [2:0]    t_p;
    wire [AW-1:0] t_daddr, t_raddr;
    always @(posedge clk) s1_tag <= e_tag;
    assign {t_asrc, t_bsrc, t_csrc, t_mc, t_md, t_redsq, t_ma, t_mb, t_dst, t_red, t_ad, t_imm1, t_imm2,
            t_lane, t_ifirst, t_first8, t_final, t_last, t_p, t_daddr, t_raddr} = s1_tag;
    reg [31:0] s2_a, s2_blo, s2_bhi, s2_c, s2_imm1, s2_imm2;
    reg [1:0]  s2_ma, s2_mb;
    reg [2:0]  s2_ad;
    // tail tag: travels S2 -> write
    localparam integer TT = 1 + 1 + 2 + AW + 2 + 1 + AW + 1+1+1+1 + 3;
    reg [TT-1:0] s2_tail;
    always @(posedge clk) begin
        s2_a <= t_asrc ? {wrom_q[16*t_lane +: 16], 16'h0000} : va_q;
        s2_blo <= t_bsrc ? crom_q[31:0] : vb_q;
        s2_bhi <= t_bsrc ? crom_q[63:32] : 32'd0;
        s2_c <= (t_csrc && !t_bsrc) ? crom_q[31:0] : vc_q;
        s2_imm1 <= t_imm1; s2_imm2 <= t_imm2;
        s2_ma <= t_ma; s2_mb <= t_mb; s2_ad <= t_ad;
        s2_tail <= {t_mc, t_md, t_dst, t_daddr, t_red, t_redsq, t_raddr, t_ifirst, t_first8, t_final, t_last, t_p};
    end
    reg [31:0] ma_x, ma_y, mb_x, mb_y, s3_a, s3_blo, s3_c, s3_imm2;
    reg [1:0]  s3_ma, s3_mb;
    reg [2:0]  s3_ad;
    reg [TT-1:0] s3_tail;
    always @(posedge clk) begin
        ma_x <= s2_a;
        ma_y <= (s2_ma == MA_AB) ? s2_blo : (s2_ma == MA_AA) ? s2_a : s2_imm1;
        mb_x <= s2_c;
        mb_y <= (s2_mb == MB_NEG) ? {~s2_bhi[31], s2_bhi[30:0]} : s2_bhi;
        s3_a <= s2_a; s3_blo <= s2_blo; s3_c <= s2_c; s3_imm2 <= s2_imm2;
        s3_ma <= s2_ma; s3_mb <= s2_mb; s3_ad <= s2_ad; s3_tail <= s2_tail;
    end

    // -- S3 -> S8: the two multipliers ------------------------------------------
    wire [31:0] p_mul, q_mul;
    wire fa, fb_;
    ot_hdc_fmul u_ma (clk, rst_n, s3_v && s3_ma != MA_BYP, ma_x, ma_y, p_mul, fa);
    ot_hdc_fmul u_mb (clk, rst_n, s3_v && s3_mb != MB_OFF, mb_x, mb_y, q_mul, fb_);
    wire [31:0] a8, blo8, c8, imm2_8;
    wire [1:0]  ma8;
    wire [2:0]  ad8;
    ot_hdc_delay #(.W(32*4 + 2 + 3), .D(5)) u_d38 (.clk(clk), .rst_n(rst_n),
        .d({s3_a, s3_blo, s3_c, s3_imm2, s3_ma, s3_ad}), .q({a8, blo8, c8, imm2_8, ma8, ad8}));
    wire [8:0] v3;
    ot_hdc_vline #(.D(8)) u_v3 (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(v3));   // v3[k] = S3+k

    // -- S8 -> S9 operand select -> S14 adder ----------------------------------
    reg [31:0] ad_x, ad_y;
    reg [2:0]  ad9;
    always @(posedge clk) begin
        ad_x <= (ma8 == MA_BYP) ? a8 : p_mul;
        case (ad8)
            AD_Q:    ad_y <= q_mul;
            AD_C:    ad_y <= c8;
            AD_NEGB: ad_y <= {~blo8[31], blo8[30:0]};
            default: ad_y <= imm2_8;
        endcase
        ad9 <= ad8;
    end
    wire [31:0] r_add, px14;
    wire fad;
    ot_hdc_fadd u_ad (clk, rst_n, v3[6] && ad9 != AD_BYP, ad_x, ad_y, r_add, fad);
    wire [2:0] ad14;
    ot_hdc_delay #(.W(35), .D(5)) u_d914 (.clk(clk), .rst_n(rst_n), .d({ad_x, ad9}), .q({px14, ad14}));
    wire [5:0] v9;
    ot_hdc_vline #(.D(5)) u_v9 (.clk(clk), .rst_n(rst_n), .v(v3[6]), .vd(v9));    // v9[5] = S14
    wire [31:0] r14 = (ad14 == AD_BYP) ? px14 : r_add;
    wire        v14 = v9[5];

    // -- S14: special functions ----------------------------------------------------
    wire [31:0] y_exp, y_rcp, y_rsq;
    wire vo_exp, vo_rcp, vo_rsq, f_exp, f_rcp, f_rsq;
    ot_hdc_exp   u_exp (.clk(clk), .rst_n(rst_n), .v(v14 && (cls == SFU_EXP || cls == SFU_SIGM)), .x(r14),
                        .y(y_exp), .vo(vo_exp), .fault(f_exp));
    // sigmoid denominator: exp(R) + 1, then the reciprocal
    wire [31:0] e1;
    wire f_e1;
    wire [5:0] ve1;
    ot_hdc_fadd u_e1 (clk, rst_n, vo_exp && cls == SFU_SIGM, y_exp, 32'h3F800000, e1, f_e1);
    ot_hdc_vline #(.D(5)) u_ve1 (.clk(clk), .rst_n(rst_n), .v(vo_exp && cls == SFU_SIGM), .vd(ve1));
    wire        rcp_v = (cls == SFU_SIGM) ? ve1[5] : (v14 && cls == SFU_RECIP);
    wire [31:0] rcp_x = (cls == SFU_SIGM) ? e1 : r14;
    ot_hdc_recip u_rcp (.clk(clk), .rst_n(rst_n), .v(rcp_v), .x(rcp_x), .y(y_rcp), .vo(vo_rcp), .fault(f_rcp));
    ot_hdc_rsqrt u_rsq (.clk(clk), .rst_n(rst_n), .v(v14 && cls == SFU_RSQRT), .x(r14), .y(y_rsq), .vo(vo_rsq), .fault(f_rsq));

    // B, C and the tail tag ride a tapped line from S3; the tap is the class depth.
    localparam integer LT = 32 + 32 + TT;
    reg [LT*TAPMAX-1:0] tl;              // tap n (1-based) = tl[LT*n-1 -: LT]
    reg [TAPMAX:1] tlv;
    always @(posedge clk) tl <= {tl[LT*(TAPMAX-1)-1:0], s3_blo, s3_c, s3_tail};
    always @(posedge clk or negedge rst_n) begin
        //: A class switch happens only with nothing in flight, but the line
        //: still holds the valid bits of retired elements beyond the old tap;
        //: they would retire a second time at the new, deeper tap.
        if (!rst_n) tlv <= 0;
        else if (accept && i_sfu != cls) tlv <= 0;
        else tlv <= {tlv[TAPMAX-1:1], s3_v};
    end
    reg [LT-1:0] tap;
    reg          tapv;
    reg [31:0]   s_val;
    always @(*) begin
        case (cls)
            SFU_EXP:   begin tap = tl[LT*(TAP0 + D_EXP)-1 -: LT];   tapv = tlv[TAP0 + D_EXP];   s_val = y_exp; end
            SFU_RECIP: begin tap = tl[LT*(TAP0 + D_RECIP)-1 -: LT]; tapv = tlv[TAP0 + D_RECIP]; s_val = y_rcp; end
            SFU_RSQRT: begin tap = tl[LT*(TAP0 + D_RSQRT)-1 -: LT]; tapv = tlv[TAP0 + D_RSQRT]; s_val = y_rsq; end
            SFU_SIGM:  begin tap = tl[LT*(TAP0 + D_SIGM)-1 -: LT];  tapv = tlv[TAP0 + D_SIGM];  s_val = y_rcp; end
            default:   begin tap = tl[LT*(TAP0)-1 -: LT];           tapv = tlv[TAP0];           s_val = r14;   end
        endcase
    end

    // -- MC select (+1) -> multiplier (+5) -> MD select (+1) -> multiplier (+5) -> write
    reg [31:0] mc_x, mc_y, mc_b;
    reg        mc_v;
    reg [TT-1:0] mc_tail;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) mc_v <= 1'b0;
        else mc_v <= tapv;
    end
    always @(posedge clk) begin
        mc_x <= s_val; mc_b <= tap[LT-1 -: 32]; mc_y <= tap[LT-33 -: 32]; mc_tail <= tap[TT-1:0];
    end
    wire [31:0] mc_out, byp5, b5;
    wire fmc;
    ot_hdc_fmul u_mc (clk, rst_n, mc_v && mc_tail[TT-1], mc_x, mc_y, mc_out, fmc);
    wire [TT-1:0] c_tail;
    wire [5:0] vmc;
    ot_hdc_vline #(.D(5)) u_vmc (.clk(clk), .rst_n(rst_n), .v(mc_v), .vd(vmc));
    ot_hdc_delay #(.W(64 + TT), .D(5)) u_dmc (.clk(clk), .rst_n(rst_n), .d({mc_x, mc_b, mc_tail}),
                                             .q({byp5, b5, c_tail}));
    reg [31:0] md_x, md_y;
    reg        md_v;
    reg [TT-1:0] md_tail;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) md_v <= 1'b0;
        else md_v <= vmc[5];
    end
    always @(posedge clk) begin
        md_x <= c_tail[TT-1] ? mc_out : byp5; md_y <= b5; md_tail <= c_tail;
    end
    wire [31:0] md_out, dbyp5;
    wire fmd;
    ot_hdc_fmul u_md (clk, rst_n, md_v && md_tail[TT-2], md_x, md_y, md_out, fmd);
    wire [TT-1:0] o_tail;
    wire [5:0] vmd;
    ot_hdc_vline #(.D(5)) u_vmd (.clk(clk), .rst_n(rst_n), .v(md_v), .vd(vmd));
    ot_hdc_delay #(.W(32 + TT), .D(5)) u_dmd (.clk(clk), .rst_n(rst_n), .d({md_x, md_tail}), .q({dbyp5, o_tail}));
    wire          o_mc, o_md;
    wire [1:0]    o_dst, o_red;
    wire          o_redsq;
    wire [AW-1:0] o_daddr, o_raddr;
    wire          o_ifirst, o_first8, o_final, o_last;
    wire [2:0]    o_p;
    assign {o_mc, o_md, o_dst, o_daddr, o_red, o_redsq, o_raddr, o_ifirst, o_first8, o_final, o_last, o_p} = o_tail;
    wire [31:0] out = o_md ? md_out : dbyp5;
    wire        ov = vmd[5];
    assign retire = ov;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vm_we <= 1'b0; kv_we <= 1'b0; end
        else begin
            vm_we <= ov && o_dst == 2'd1;
            kv_we <= ov && o_dst == 2'd2;
        end
    end
    always @(posedge clk) begin
        vm_waddr <= o_daddr; vm_wdata <= out;
        //: the KV cache holds BF16 (RNE), so attention products are exact BF16 x BF16
        kv_waddr <= o_daddr; kv_wdata <= (out + 32'h7FFF + {31'd0, out[16]}) & 32'hFFFF0000;
    end

    // -- reducer ------------------------------------------------------------------
    reg          rd_v, rd_sq;
    reg [1:0]    rd_mode;
    reg [31:0]   rd_x;
    reg          rd_ifirst, rd_first8, rd_final, rd_last;
    reg [2:0]    rd_p;
    reg [AW-1:0] rd_addr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rd_v <= 1'b0;
        else rd_v <= ov && o_red != 2'd0;
    end
    always @(posedge clk) begin
        rd_mode <= o_red; rd_sq <= o_redsq; rd_x <= out; rd_ifirst <= o_ifirst; rd_first8 <= o_first8;
        rd_final <= o_final; rd_last <= o_last; rd_p <= o_p; rd_addr <= o_raddr;
    end
    wire f_red;
    ot_hdc_reduce #(.AW(AW)) u_red (.clk(clk), .rst_n(rst_n), .v_in(rd_v), .mode_in(rd_mode),
        .sq(rd_sq), .x_in(rd_x), .ifirst_in(rd_ifirst), .first8_in(rd_first8), .final_in(rd_final),
        .last_in(rd_last), .p_in(rd_p), .raddr_in(rd_addr), .o_we(red_we), .o_addr(red_addr), .o_data(red_data), .busy(reducer_busy),
        .fault(f_red));

    // Element chaining: count emitted and retired elements.  Retirement is in
    // order, so the latest instruction has written (retired count - emitted
    // count at its acceptance) elements; registered, it trails the write
    // register by nothing.
    reg [15:0] n_emit, n_retire, first_mark;
    wire [15:0] done_n = n_retire - first_mark;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_emit <= 0; n_retire <= 0; first_mark <= 0; progress <= 0;
        end else begin
            n_emit <= n_emit + (emit ? 16'd1 : 16'd0);
            n_retire <= n_retire + (retire ? 16'd1 : 16'd0);
            if (accept) begin
                first_mark <= n_emit; progress <= 0;
            end else begin
                progress <= done_n[15] ? 16'd0 : done_n;
            end
        end
    end

    //: Registered: the OR of every valid bit is wide.  Cleared on the
    //: accepting edge so a just-issued op never reads as drained.
    wire idle_c = !active && inflight == 0 && !vm_we && !kv_we && !rd_v && !reducer_busy;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(accept);
    end
    //: A status bit: registered in two levels so the wide OR never meets a port
    //: or a consumer in the same cycle it forms.
    reg [2:0] fault_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault_q <= 0; fault <= 1'b0; end
        else begin
            fault_q <= {fa | fb_ | fad, f_exp | f_e1 | f_rcp | f_rsq, fmc | fmd | f_red};
            fault <= |fault_q;
        end
    end
endmodule
