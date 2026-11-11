module gold_bf (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    sa_r, input wire [223:0] sa_d, input wire [5:0] sb_r, input wire [223:0] sb_d,
    input  wire [13:0]   we,
    input  wire          c_go, input wire c_fw, input wire c_l, input wire [2:0] c_bn, input wire [4:0] c_lvn,
    input  wire          g_go, input wire [5:0] g_hit, input wire [41:0] g_a,
    output wire [255:0]  sv_lo, output wire [255:0] sv_hi,
    output wire [13:0]   ctl_lo, output wire [13:0] ctl_hi,
    input  wire [327:0]  s0a, input wire [327:0] s0b, input wire [2:0] sf0, input wire [23:0] vf_lo,
    input  wire [327:0]  s1a, input wire [327:0] s1b, input wire [23:0] vf_hi,
    output reg           o_v, output reg o_f, output reg o_l, output reg o_g, output wire [244:0] o_d,   // packed {d[245:206], d[204:0]} as dsdv_gunit_l1f_flat (RTLC 10-24)
    output reg           o_flt
);
    reg [245:0] o_df;   // o_df[205] is never written and has no pin (dsdv_gunit_l1f_flat)
`ifdef OT_RTLC_MUT_L1F   // RTLC bench mutant, as dsdv_gunit_l1f_flat: o_d packs d[245:1]
    assign o_d = o_df[245:1];
`else
    assign o_d = {o_df[245:206], o_df[204:0]};
`endif
    localparam integer EW = 41, LW = 8 * EW, NL = 16, NS = 7 * NL;
`ifdef OT_S81_GUNIT_FWDOWN
    localparam integer NW = 24, ND = 8, NB = 32, NG = 4, NQ = 18, NR = 21;
`else
    localparam integer NW = 9, ND = 5, NB = 32, NG = 4, NQ = 18, NR = 13;
`endif
    integer i, j, k;
    genvar g, l, h, t;
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- input flops (dsdv_gunit_l1f, unchanged)
    (* keep *) reg [NW*14-1:0]  wqc;
    (* keep *) reg [NW*6-1:0]   arc, brc;
    (* keep *) reg [ND*224-1:0] adc, bdc;
    (* keep *) reg [NB*3-1:0]   cbc;
    (* keep *) reg [3:0]        cfwc;
    (* keep *) reg [NG*6-1:0]   ghc;
    (* keep *) reg [NG*42-1:0]  gac;
    reg cgo, cl, gq; reg [4:0] clv;
    generate
        for (g = 0; g < NW; g = g + 1) begin : g_wq
`ifdef OT_S81_GUNIT_FWDOWN
            localparam integer WR_REGION=(g<8)?g/2:13+(g-8)/2;
`else
            localparam integer WR_REGION=g/2;
`endif
            always @(posedge clk or negedge rq[WR_REGION])
                if (!rq[WR_REGION]) wqc[14 * g +: 14] <= 14'd0; else wqc[14 * g +: 14] <= we;
            always @(posedge clk) begin arc[6 * g +: 6] <= sa_r; brc[6 * g +: 6] <= sb_r; end
        end
        for (g = 0; g < ND; g = g + 1) begin : g_dq
            always @(posedge clk) begin adc[224 * g +: 224] <= sa_d; bdc[224 * g +: 224] <= sb_d; end
        end
        for (g = 0; g < NB; g = g + 1) begin : g_bq
            always @(posedge clk) cbc[3 * g +: 3] <= c_bn;
        end
        for (g = 0; g < NG; g = g + 1) begin : g_gq
            always @(posedge clk) begin ghc[6 * g +: 6] <= g_hit; gac[42 * g +: 42] <= g_a; end
        end
    endgenerate
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) begin cgo <= 1'b0; gq <= 1'b0; end
        else begin cgo <= c_go; gq <= g_go; end
    always @(posedge clk) begin cfwc <= {4{c_fw}}; cl <= c_l; clv <= c_lvn; end
    // ---------------------------------------------------------------- SC store (dsdv_gunit_l1f, unchanged)
    wire [NW*64-1:0] aoh, boh;
    generate
        for (g = 0; g < NW; g = g + 1) begin : g_dec
            (* keep = 1 *) dsdv_l1f_dec64 u_da (.a(arc[6 * g +: 6]), .y(aoh[64 * g +: 64]));
            (* keep = 1 *) dsdv_l1f_dec64 u_db (.a(brc[6 * g +: 6]), .y(boh[64 * g +: 64]));
        end
    endgenerate
    reg  [NS*32-1:0] sc;
    wire [4*NS-1:0]  wh;
    wire [NS*32-1:0] wdv;
    wire [4*NL-1:0]  whf;
    wire [NL*32-1:0] wdf;
    generate
        for (g = 0; g < NS; g = g + 1) begin : g_e
            for (h = 0; h < 2; h = h + 1) begin : g_h
                wire [7:0] en, hit, enf, hitf; wire [127:0] dd, ddf;
                for (t = 0; t < 4; t = t + 1) begin : g_t
                    localparam integer IX = 64 * (g / 16) + 16 * t + (g % 16), WJ = IX % 7, RJ = IX / 7;
                    localparam integer CW = g / 14, CD = g / 28;
`ifdef OT_S81_GUNIT_FWDOWN
                    localparam integer FW=8+((g<NL)?g:0), FD=4+((g<NL)?g/4:0);
`else
                    localparam integer FW=NW-1, FD=ND-1;
`endif
                    assign en[2 * t]      = wqc[14 * CW + WJ];      assign en[2 * t + 1]  = wqc[14 * CW + 7 + WJ];
                    assign hit[2 * t]     = aoh[64 * CW + RJ];      assign hit[2 * t + 1] = boh[64 * CW + RJ];
                    assign dd[32 * t +: 16]      = adc[224 * CD + 32 * WJ + 16 * h +: 16];
                    assign dd[32 * t + 16 +: 16] = bdc[224 * CD + 32 * WJ + 16 * h +: 16];
                    assign enf[2 * t]     = wqc[14 * FW + WJ];      assign enf[2 * t + 1] = wqc[14 * FW + 7 + WJ];
                    assign hitf[2 * t]    = aoh[64 * FW + RJ];      assign hitf[2 * t + 1] = boh[64 * FW + RJ];
                    assign ddf[32 * t +: 16]      = adc[224 * FD + 32 * WJ + 16 * h +: 16];
                    assign ddf[32 * t + 16 +: 16] = bdc[224 * FD + 32 * WJ + 16 * h +: 16];
                end
                (* keep = 1 *) dsdv_l1f_wdec8 u_w (.en(en), .hit(hit), .d(dd), .wh(wh[4 * g + 2 * h +: 2]), .wd(wdv[32 * g + 16 * h +: 16]));
                always @(posedge clk) begin
                    if (wh[4 * g + 2 * h])     sc[32 * g + 16 * h +: 8]     <= wdv[32 * g + 16 * h +: 8];
                    if (wh[4 * g + 2 * h + 1]) sc[32 * g + 16 * h + 8 +: 8] <= wdv[32 * g + 16 * h + 8 +: 8];
                end
                if (g < NL) begin : g_f
                    (* keep = 1 *) dsdv_l1f_wdec8 u_f (.en(enf), .hit(hitf), .d(ddf), .wh(whf[4 * g + 2 * h +: 2]),
                                                       .wd(wdf[32 * g + 16 * h +: 16]));
                end
            end
        end
    endgenerate
    wire [NB*7-1:0] cbh;
    generate
        for (g = 0; g < NB; g = g + 1) begin : g_bd
            (* keep = 1 *) dsdv_l1f_dec7 u_d (.a(cbc[3 * g +: 3]), .y(cbh[7 * g +: 7]));
        end
    endgenerate
    // S81-GUNIT-FORM-1 11-07: the beat read select as a generate (same OR of 7 AND terms per bit as dsdv_gunit_l1f_flat's
    // always loop): the loop's 512 x 7 + 512 = 4096 iterations exceed slang's default unroll budget (4000) in the core
    // kit LEC, which a legacy kit may not raise
    wire [NL*32-1:0] rdb;
    generate
        for (g = 0; g < NL * 32; g = g + 1) begin : g_rdb
            wire [6:0] hv;
            for (h = 0; h < 7; h = h + 1) begin : g_j
                assign hv[h] = cbh[7 * (g / 16) + h] & sc[32 * NL * h + g];
            end
            assign rdb[g] = |hv;
        end
    endgenerate
    wire [NL*32-1:0] svn;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_fw
            for (h = 0; h < 4; h = h + 1) begin : g_y
                (* keep = 1 *) dsdv_l1f_mux8 u_m (.s(cfwc[2 * (h / 2) + l / 8] && whf[4 * l + h]), .a(wdf[32 * l + 8 * h +: 8]),
                                                  .b(rdb[32 * l + 8 * h +: 8]), .y(svn[32 * l + 8 * h +: 8]));
            end
        end
    endgenerate
    reg s_v, s_f, s_l; reg [2:0] s_bn; reg [NL-1:0] s_lv; reg [NL*32-1:0] s_val;
    // FACE 11-07: ctl_hi has its own kept copies of {s_bn, s_l, s_f, s_v} (one output flop per pin bit; the 10-22 band
    // drove ctl_lo and ctl_hi from the same flops = face_guard feedthrough / shared); same D, same edge
    (* keep *) reg s_vh, s_fh, s_lh; (* keep *) reg [2:0] s_bnh;
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) begin s_v <= 1'b0; s_vh <= 1'b0; end else begin s_v <= cgo; s_vh <= cgo; end
    always @(posedge clk) begin
        s_f <= cfwc[0]; s_l <= cl; s_bn <= cbc[2:0];
        s_fh <= cfwc[0]; s_lh <= cl; s_bnh <= cbc[2:0];
        for (k = 0; k < NL; k = k + 1) begin
            s_lv[k] <= k < clv;
            for (j = 0; j < 4; j = j + 1) s_val[32 * k + 8 * j +: 8] <= svn[32 * k + 8 * j +: 8];
        end
    end
    assign sv_lo = s_val[255:0];  assign sv_hi = s_val[511:256];
    assign ctl_lo = {s_lv[7:0], s_bn, s_l, s_f, s_v};
    assign ctl_hi = {s_lv[15:8], s_bnh, s_lh, s_fh, s_vh};
    // ---------------------------------------------------------------- merge (fold of both sorts -> m1 -> cx8_2)
    // FACE 11-07: the sort results land in F's own kept flops (l0a .. l1b, one per pin bit); the merge register m1 is
    // retimed back across the fold onto them (fold + cx8_2 in one stage), so the merge still leaves on the same edge.
    // The 10-22 band read s0a .. s1b through the fold (face_guard unregistered / shared).  Record bit 0 (ninf) of the A
    // copies s0a / s1a is not read by the fold (dsdv_seln_fold_cx compares bits 40:1): declared dead in the kit recipe.
    wire [LW-1:0] c1, c3;
    (* keep *) reg [LW-1:0] l0b, l1b; (* keep *) reg [8*(EW-1)-1:0] l0r, l1r; reg [2:0] mf;
    wire [LW-1:0] l0a, l1a;
    generate
        for (l = 0; l < 8; l = l + 1) begin : g_land
            always @(posedge clk) begin
                l0r[(EW-1) * l +: EW-1] <= s0a[EW * l + 1 +: EW-1]; l1r[(EW-1) * l +: EW-1] <= s1a[EW * l + 1 +: EW-1];
            end
            assign l0a[EW * l +: EW] = {l0r[(EW-1) * l +: EW-1], 1'b0};
            assign l1a[EW * l +: EW] = {l1r[(EW-1) * l +: EW-1], 1'b0};
        end
    endgenerate
    always @(posedge clk) begin l0b <= s0b; l1b <= s1b; end
    dsdv_seln_fold_cx #(.EW(EW)) u_m0 (.aa(l0a), .ab(l0b), .ba(l1a), .bb(l1b), .q(c1));
    always @(posedge clk or negedge rq[12]) if (!rq[12]) mf <= 3'd0; else mf <= sf0;
    dsdv_seln_cx8_2 #(.EW(EW), .J1(2), .KB1(8), .J2(1), .KB2(8)) u_m1 (.da(c1), .db(c1), .q(c3));
    // ---------------------------------------------------------------- gather + outputs (dsdv_gunit_l1f, unchanged)
    reg [6*NS-1:0] hs;
    (* keep *) reg [NQ-1:0] gq2;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) gq2 <= {NQ{1'b0}}; else gq2 <= {NQ{gq}};
    always @(posedge clk)
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                hs[NS * j + i] <= ghc[6 * (i / 28) + j] && {gac[42 * (i / 28) + 7 * j + 4 +: 3], gac[42 * (i / 28) + 7 * j +: 4]} == 7'(i);
    reg [191:0] gd;
    always @(*) begin
        gd = 192'd0;
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                if (hs[NS * j + i]) gd[32 * j +: 32] = gd[32 * j +: 32] | sc[32 * i +: 32];
    end
    // adder faults: ot_s81sl_ve_qadd's fault = valid_out && err != 0, formed here from the A bands' raw flops
    // FACE 11-07: the adders' raw valid / error flops land in F (vfq, one flop per pin bit) before the fault OR.  The
    // ONLY edge change of the hard form: an adder fault reaches o_flt one edge later (sticky fault flag; no data / valid
    // / gather edge moves; the lockstep bench compares o_flt with the reference delayed one edge)
    reg [47:0] vfq;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) vfq <= 48'd0; else vfq <= {vf_hi, vf_lo};
    wire [NL-1:0] yf;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_yf
            wire [2:0] x;
            if (l < 8) begin : g_lo assign x = vfq[3 * l +: 3]; end
            else begin : g_hi assign x = vfq[24 + 3 * (l - 8) +: 3]; end
            assign yf[l] = x[0] && (x[2:1] != 2'd0);
        end
    endgenerate
    // FACE 11-07: the sticky fault holds in its own kept flop flt_s; o_flt is a pure output copy of it (the 10-22 band
    // fed o_flt back into its own D = face_guard shared / self-loop).  o_flt == flt_s on every edge.
    (* keep *) reg flt_s;
    always @(posedge clk or negedge rq[12])
        if (!rq[12]) begin o_v <= 1'b0; o_f <= 1'b0; o_l <= 1'b0; o_g <= 1'b0; o_flt <= 1'b0; flt_s <= 1'b0; end
        else begin
            o_v <= mf[0]; o_f <= mf[1]; o_l <= mf[2]; o_g <= gq2[NQ - 1];
            flt_s <= flt_s || (|yf) || (gq2[NQ - 1] && mf[0]);
            o_flt <= flt_s || (|yf) || (gq2[NQ - 1] && mf[0]);
        end
    wire [245:0] onext = {54'd0, gd};
    always @(posedge clk)
        for (i = 0; i < 246; i = i + 1) if (i != 205) o_df[i] <= gq2[i / 14] ? onext[i] : c3[i];
endmodule
