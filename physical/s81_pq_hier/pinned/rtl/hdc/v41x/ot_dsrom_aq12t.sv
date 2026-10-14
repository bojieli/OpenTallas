`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_aq12t: T_AQ hardened sub-tile of the DS-ROM PQ spine screen (el1011-ds-misc/pqc 2026-10-11, textbook audit
// class 1: one clock tree over 133k / 225k sinks).  Bit for bit and cycle for cycle ot_dsrom_aq12m (same ports, LATENCY
// 29): the only change is the x wait line (1024 b x 20 registers) moved into a 128-deep SRAM ring (4 x 1R1W 128 x 256)
// with a capture flop on every macro output.  Sinks ~11.5k flops + 4 macros (was 32k).  Lockstep bench:
// physical/s81_pq_tiles/tb/tb_aq12t_eq.sv (aq12t vs aq12m, every output on every valid).
// Below: ot_dsrom_aq12m's body (pinned physical/s81_pq_xrv/pinned/rtl/hdc/v41x/ot_dsrom_aq12m.sv, sha c3723230) with u_x
// replaced; ot_dsrom_aq12m_mul is taken from that file.
// ---------------------------------------------------------------------------
module ot_dsrom_aq12t (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output reg           fault
);
    // the tile's reset relay (el1011-ds-misc/pqc): rst_n is synchronised and re-driven from a flop next to the tile's
    // control flops (vline, multiplier valids, ring pointers, vo / fault); no datapath register is reset.
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    localparam integer LATENCY = 29;
    localparam [30:0] FLOOR_FP8 = 31'h38d1b717;   // float32(1e-4)
    localparam [31:0] INV_448   = 32'h3b124925;   // float32(1/448)
    integer i;

    wire [LATENCY:0] vl;
`ifdef OT_PQ_AQ_PIN_LAUNCH
`ifdef OT_PQ_AQ_PIN_MUT_DELAY
    // Wrong relocation: retaining AQ's old stage delays valid by one cycle.
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_l), .v(v), .vd(vl));
`else
    // v is already registered by the controller at the same global edge at
    // which s0_x captures. Remove only that first validity stage; all used
    // vl[11] / vl[LATENCY-1] still match the original AQ on every cycle.
    wire [LATENCY-1:0] v_pin;
    ot_hdc_vline #(.D(LATENCY-1)) u_v (.clk(clk), .rst_n(rst_l), .v(v), .vd(v_pin));
    assign vl = {v_pin, 1'b0};
`endif
`else
    ot_hdc_vline #(.D(LATENCY)) u_v (.clk(clk), .rst_n(rst_l), .v(v), .vd(vl));
`endif
    // register cycle k reads cycle k-1: s0_x at 1; elements wait to the max(fld, 1) stage at 22 (xg at 21: 20 registers)
    reg  [1023:0] s0_x;
    always @(posedge clk) s0_x <= x;
    // ---- T_AQ (el1011-ds-misc/pqc 2026-10-11): the 1024 b x 20-register delay line (20,480 flops, 30% of the screen's
    //      clock sinks) is a 128-deep ring in four 1R1W 128 x 256 SRAM macros (macro k = lanes 8k..8k+7).  Written every
    //      cycle at wp; read at wp - 18; every SRAM output captured in a flop (xg_r, no logic before it).  Timing:
    //      s0_x(t) written at edge t -> t+1; read issued with ra(t+18) = wp(t); rd valid in cycle t+19; xg_r(t+20) =
    //      s0_x(t), exactly the 20-register line.  The pointers are the only reset flops (14 b, control).
    reg  [6:0] r_wp, r_rp;
    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) begin r_wp <= 7'd0; r_rp <= 7'd110; end           // rp = wp - 18 (mod 128)
`ifdef OT_AQ12T_MUT_RA
        else begin r_wp <= r_wp + 7'd1; r_rp <= r_rp + 7'd2; end       // mutant: the read pointer runs away
`else
        else begin r_wp <= r_wp + 7'd1; r_rp <= r_rp + 7'd1; end
`endif
    end
    wire [1023:0] xr;
    reg  [1023:0] xg_r;
    genvar gm;
    generate for (gm = 0; gm < 4; gm = gm + 1) begin : g_m
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(1'b1), .r_addr_in(r_rp), .rd_out(xr[256*gm +: 256]),
            .w_ce_in(1'b1), .w_addr_in(r_wp), .wd_in(s0_x[256*gm +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    always @(posedge clk) xg_r <= xr;
    wire [1023:0] xg = xg_r;

    // -- max tree: level L compares at cycle 2L, selects at 2L + 1 (m1 3, m2 5, m3 7, m4 9) -----------------------
    reg [30:0] c1a [0:15], c1b [0:15];
    reg [30:0] m1 [0:15];
    reg [30:0] c2a [0:7],  c2b [0:7];
    reg [30:0] m2 [0:7];
    reg [30:0] c3a [0:3],  c3b [0:3];
    reg [30:0] m3 [0:3];
    reg [30:0] c4a [0:1],  c4b [0:1];
    reg [30:0] m4 [0:1];
    reg [15:0] g1r;
    reg [7:0]  g2r;
    reg [3:0]  g3r;
    reg [1:0]  g4r;
    reg  [3:0] nf1;                  // four 8-lane partial ORs (cycle 2), reduced at 3
    reg        nf2;
    reg  [3:0] nfx;
    always @(*) begin
        nfx = 4'd0;
        for (i = 0; i < 32; i = i + 1) nfx[i/8] = nfx[i/8] | (s0_x[32*i + 23 +: 8] == 8'hFF);
    end
    wire [15:0] ge1;
    wire [7:0]  ge2;
    wire [3:0]  ge3;
    wire [1:0]  ge4;
    genvar gk;
    generate
        for (gk = 0; gk < 16; gk = gk + 1) begin : g_c1
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(s0_x[64*gk +: 31]), .b(~s0_x[64*gk + 32 +: 31]), .cin(1'b1), .s(sd), .cout(ge1[gk]));
        end
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_c2
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(m1[2*gk]), .b(~m1[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge2[gk]));
        end
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_c3
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(m2[2*gk]), .b(~m2[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge3[gk]));
        end
        for (gk = 0; gk < 2; gk = gk + 1) begin : g_c4
            wire [30:0] sd;
            ot_v41_ksadd #(.W(31)) u_ge (.a(m3[2*gk]), .b(~m3[2*gk+1]), .cin(1'b1), .s(sd), .cout(ge4[gk]));
        end
    endgenerate
    always @(posedge clk) begin
        g1r <= ge1;
        for (i = 0; i < 16; i = i + 1) begin c1a[i] <= s0_x[64*i +: 31]; c1b[i] <= s0_x[64*i + 32 +: 31]; end
        for (i = 0; i < 16; i = i + 1) m1[i] <= g1r[i] ? c1a[i] : c1b[i];
        g2r <= ge2;
        for (i = 0; i < 8; i = i + 1) begin c2a[i] <= m1[2*i]; c2b[i] <= m1[2*i+1]; end
        for (i = 0; i < 8; i = i + 1) m2[i] <= g2r[i] ? c2a[i] : c2b[i];
        g3r <= ge3;
        for (i = 0; i < 4; i = i + 1) begin c3a[i] <= m2[2*i]; c3b[i] <= m2[2*i+1]; end
        for (i = 0; i < 4; i = i + 1) m3[i] <= g3r[i] ? c3a[i] : c3b[i];
        g4r <= ge4;
        for (i = 0; i < 2; i = i + 1) begin c4a[i] <= m3[2*i]; c4b[i] <= m3[2*i+1]; end
`ifdef OT_AQ12M_MUT_SEL
        for (i = 0; i < 2; i = i + 1) m4[i] <= g4r[i] ? c4b[i] : c4a[i];
`else
        for (i = 0; i < 2; i = i + 1) m4[i] <= g4r[i] ? c4a[i] : c4b[i];
`endif
        nf1 <= nfx; nf2 <= |nf1;
    end
    // -- S5: max(m4[0], m4[1], floor): the three compares registered (cycle 10), the select (amax, cycle 11) -----
    reg [30:0] amax, m4a, m4b;
    reg        abr, afr, bfr;
    wire ab, af, bf;
    wire [30:0] sd_ab, sd_af, sd_bf;
    ot_v41_ksadd #(.W(31)) u_ab (.a(m4[0]), .b(~m4[1]), .cin(1'b1), .s(sd_ab), .cout(ab));
    ot_v41_ksadd #(.W(31)) u_af (.a(m4[0]), .b(~FLOOR_FP8), .cin(1'b1), .s(sd_af), .cout(af));
    ot_v41_ksadd #(.W(31)) u_bf (.a(m4[1]), .b(~FLOOR_FP8), .cin(1'b1), .s(sd_bf), .cout(bf));
    always @(posedge clk) begin
        abr <= ab; afr <= af; bfr <= bf; m4a <= m4[0]; m4b <= m4[1];
        amax <= (abr && afr) ? m4a : (!abr && bfr) ? m4b : FLOOR_FP8;
    end

    // -- cycles 12..20: amax * (1/448), every multiplier cut (LAT 9) ------------------------------------------
    wire [31:0] prod;
    wire [1:0]  perr;
    wire        pvo;
    ot_dsrom_aq12m_mul u_scale (.clk(clk), .rst_n(rst_l), .valid_in(vl[11]), .a({1'b0, amax}), .b(INV_448), .y(prod),
                                .err(perr), .valid_out(pvo));
    wire pfault = pvo && (perr != 2'd0);
    wire nf20;                                   // nf2 (cycle 3) aligned with prod (cycle 20)
    ot_hdc_delay #(.W(1), .D(17)) u_nf (.clk(clk), .rst_n(rst_l), .d(nf2), .q(nf20));

    // -- cycle 21: ce = ceil_log2(prod) + 127 registered once -------------------------------------------------------
    reg [8:0] ce_r;
    reg       ce_nf;
    always @(posedge clk) begin
        ce_r <= {1'b0, prod[30:23]} + {8'd0, (prod[22:0] != 23'd0)};
        ce_nf <= nf20 | pfault;
    end
    // -- cycle 22 (S11): e, and {e + 121 (dm), e + 127 (ep)} in eight kept copies, copy k feeding lanes 4k..4k+3 ----
    //    each lane's max(fld, 1) and the S12 pass-through fields registered from xg in the same cycle
    reg signed [9:0]  s11_e;
    reg               s11_nf;
    wire signed [10:0] ep_d = $signed({2'b00, ce_r});
    wire signed [10:0] dm_d = $signed({2'b00, ce_r}) - 11'sd6;
    wire [175:0] s11_epdm;                    // copy k: {dm, ep} at [22k +: 22]
    generate
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_s11c
            ot_v41_kreg #(.W(22)) u_c (.clk(clk), .arst_n(1'b1), .d({dm_d, ep_d}), .q(s11_epdm[22*gk +: 22]));
        end
    endgenerate
    reg [7:0]  s11_ev [0:31];                 // max(fld, 1)
    reg [23:0] s11_sig [0:31];
    reg [31:0] s11_sgn;
    reg [7:0]  fld;
    always @(posedge clk) begin
        s11_e <= $signed({1'b0, ce_r}) - 10'sd127;
        s11_nf <= ce_nf;
        for (i = 0; i < 32; i = i + 1) begin
            fld = xg[32*i + 23 +: 8];
            s11_ev[i] <= (fld == 8'd0) ? 8'd1 : fld;
            s11_sig[i] <= {(fld != 8'd0), xg[32*i +: 23]};
            s11_sgn[i] <= xg[32*i + 31] && (xg[32*i +: 31] != 31'd0);
        end
    end

    // -- cycle 23 (S12): per-element exponent difference dd = -6 - (exp(x) - e) ------------------------------------
    reg signed [10:0] s12_ev [0:31];
    reg signed [10:0] s12_dd [0:31];
    reg [23:0]        s12_sig [0:31];
    reg [31:0]        s12_sgn;
    reg signed [9:0]  s12_e;
    reg               s12_nf;
    reg signed [10:0] ev;
    always @(posedge clk) begin
        s12_e <= s11_e; s12_nf <= s11_nf; s12_sgn <= s11_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            ev = $signed({3'b000, s11_ev[i]});
            s12_ev[i] <= ev - $signed(s11_epdm[22*(i/4) +: 11]);
`ifdef OT_AQ12M_MUT_DD
            s12_dd[i] <= $signed(s11_epdm[22*(i/4) +: 11]) - ev;
`else
            s12_dd[i] <= $signed(s11_epdm[22*(i/4) + 11 +: 11]) - ev;
`endif
            s12_sig[i] <= s11_sig[i];
        end
    end
    // -- cycle 24 (S13): grid exponent and shift ------------------------------------------------------------------
    reg [23:0]       s13_sig [0:31];
    reg [4:0]        s13_rs [0:31];
    reg signed [4:0] s13_g [0:31];
    reg [31:0]       s13_sgn;
    reg signed [9:0] s13_e;
    reg              s13_nf;
    always @(posedge clk) begin
        s13_e <= s12_e; s13_nf <= s12_nf; s13_sgn <= s12_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s13_sig[i] <= s12_sig[i];
            if (s12_dd[i] > 11'sd0) begin
                s13_g[i] <= -5'sd6;
                s13_rs[i] <= (s12_dd[i] > 11'sd6) ? 5'd26 : (5'd20 + s12_dd[i][4:0]);
            end else begin
                s13_g[i] <= s12_ev[i][4:0];
                s13_rs[i] <= 5'd20;
            end
        end
    end
    // -- cycle 25 (S14a): the rounding shift, registered (51 bits a lane) ---------------------------------------
    reg [50:0]       s14_w [0:31];
    reg [31:0]       s14a_sgn;
    reg signed [4:0] s14a_g [0:31];
    reg signed [9:0] s14a_e;
    reg              s14a_nf;
    always @(posedge clk) begin
        s14a_e <= s13_e; s14a_nf <= s13_nf; s14a_sgn <= s13_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s14_w[i] <= {s13_sig[i], 27'd0} >> s13_rs[i];
            s14a_g[i] <= s13_g[i];
        end
    end
    // -- cycle 26 (S14b): quotient, guard and the sticky OR --------------------------------------------------------
    reg [23:0]       s14_tq [0:31];
    reg [31:0]       s14_gd, s14_st, s14_sgn;
    reg signed [4:0] s14_g [0:31];
    reg signed [9:0] s14_e;
    reg              s14_nf;
    always @(posedge clk) begin
        s14_e <= s14a_e; s14_nf <= s14a_nf; s14_sgn <= s14a_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s14_tq[i] <= s14_w[i][50:27];
            s14_gd[i] <= s14_w[i][26];
`ifdef OT_AQ12M_MUT_ST
            s14_st[i] <= 1'b0;                                           // mutant: sticky dropped
`else
            s14_st[i] <= (s14_w[i][25:0] != 26'd0);
`endif
            s14_g[i] <= s14a_g[i];
        end
    end
    // -- cycle 27 (S15): round to the grid -------------------------------------------------------------------------
    reg [4:0]        s15_c [0:31];
    reg signed [4:0] s15_g [0:31];
    reg [31:0]       s15_sgn;
    reg signed [9:0] s15_e;
    reg              s15_nf;
    always @(posedge clk) begin
        s15_e <= s14_e; s15_nf <= s14_nf; s15_sgn <= s14_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            s15_c[i] <= s14_tq[i][4:0] + {4'd0, s14_gd[i] & (s14_st[i] | s14_tq[i][0])};
            s15_g[i] <= s14_g[i];
        end
    end
    // -- cycle 28 (S16): encode terms ------------------------------------------------------------------------------
    reg [4:0]         s16_c [0:31];
    reg [3:0]         s16_g4 [0:31];
    reg signed [11:0] s16_be [0:31];
    reg [7:0]         s16_cn [0:31];
    reg [6:0]         s16_sub [0:31];
    reg [31:0]        s16_sgn;
    reg signed [9:0]  s16_e;
    reg               s16_nf;
    reg [2:0]         p;
    reg [4:0]         c;
    reg signed [11:0] shs;
    always @(posedge clk) begin
        s16_e <= s15_e; s16_nf <= s15_nf; s16_sgn <= s15_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            c = s15_c[i];
            p = c[4] ? 3'd4 : c[3] ? 3'd3 : c[2] ? 3'd2 : c[1] ? 3'd1 : 3'd0;
            s16_c[i] <= c;
            s16_g4[i] <= s15_g[i][3:0];
            s16_be[i] <= $signed({9'd0, p}) + s15_g[i] - 12'sd3 + s15_e + 12'sd127;
            s16_cn[i] <= {3'd0, c} << (3'd7 - p);
            shs = s15_g[i] - 12'sd3 + s15_e + 12'sd133;
            s16_sub[i] <= (shs < 12'sd0) ? 7'd0 : ({2'd0, c} << shs[3:0]);
        end
    end
    // -- cycle 29 (S17): codes and dequantised BF16 (output registers) ----------------------------------------------
    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= vl[LATENCY - 1]; fault <= vl[LATENCY - 1] && s16_nf; end
    end
    always @(posedge clk) begin
        e <= s16_e;
        for (i = 0; i < 32; i = i + 1) begin
            if (s16_c[i][4])      q[8*i +: 8] <= {s16_sgn[i], s16_g4[i] + 4'd8, 3'd0};
            else if (s16_c[i][3]) q[8*i +: 8] <= {s16_sgn[i], s16_g4[i] + 4'd7, s16_c[i][2:0]};
            else                  q[8*i +: 8] <= {s16_sgn[i], 4'd0, s16_c[i][2:0]};
            if (s16_c[i] == 5'd0)          y[16*i +: 16] <= {s16_sgn[i], 15'd0};
            else if (s16_be[i] >= 12'sd255) y[16*i +: 16] <= {s16_sgn[i], 8'hFF, 7'd0};
            else if (s16_be[i] >= 12'sd1)   y[16*i +: 16] <= {s16_sgn[i], s16_be[i][7:0], s16_cn[i][6:0]};
            else                            y[16*i +: 16] <= {s16_sgn[i], 8'd0, s16_sub[i]};
        end
    end
endmodule
