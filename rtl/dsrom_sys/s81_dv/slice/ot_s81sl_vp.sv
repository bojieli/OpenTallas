`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): vp = the store + hc_post sub-leaf of one BEAT of a DV vector slice (x5 per slice,
// own clock root).  It owns the beat leaf's control (one command word a cycle from the slice centre, fixed latency, no
// handshake) and drives its vn (h store / norm) over registered seams.
//
//   leaf store  2 x ot_sram_1r1w_512x128_m4 (16 KiB): row r (128 b = 4 FP32 words) in bank r[0] at r >> 1; one read and
//               one write per bank per cycle.  Writers: capture (2 word ports, from the centre's return decode), row
//               writes from the centre (ring / config / collective), the h store-out.  Readers: gain load, hc_post
//               coefficients and y, h load, row reads to the centre.  Two accesses to one bank port in a cycle are a
//               schedule violation (sticky fault), never arbitrated.
//   hc_post     16 x ot_dsrom_su_hcpost_lane_pr (the closed pin-registered HC lane, ML 7 / AL 6: the golden
//               out[k][e] = BF16(y*post[k] + (r3*c[3][k] + (r2*c[2][k] + (r0*c[0][k] + r1*c[1][k]))))); lane 4k + i
//               computes copy k of element i of a half sub-beat: 16 cycles for the beat's 4 x 64 outputs, written back
//               in place into vn's h store.
// Commands (c_d): [3:0] op, [13:4] a0, [23:14] a1, [31:24] n, [159:32] imm.
//   1 GAIN  a0: 16 rows (64 FP32 gains, element order) -> vn wl rows 0..7
//   2 POST  a0: coefficient rows in the G-unit's order (dsdv_gunit_l5 CTL rows R .. R + 5 = pre, post, comb rows 0..3):
//           row a0 = post[k] at word k, rows a0 + 1 + j = comb[j][k] at word k (so POST a0 = R + 1); a1: y rows (element
//           order).  (S81-SLICE 10-18: was comb rows a0..a0+3 then post a0+4; changed on the vp side only, the G-unit
//           write order is unchanged.)
//   3 HLOAD a0: 32 rows (half row i = sub-beat i>>1, half i&1: rows a0 + 2i, a0 + 2i + 1 = vn's 256-b half-row layout)
//   4 HSTORE a0: the inverse of HLOAD (h -> leaf store)
//   5 NORM  imm[127:0] = the hc_pre coefficients -> vn n_go; n[0] / n[1] = gather the q / BF16 family, a1[7:0] = the
//           vector's global beat index (5 sid + k for h vectors) -> vq mode.  n_go one edge after the command flop.
//   7 NORMR as NORM, but hc_pre = leaf row a0 (pre[k] at word k: the G-unit's CTL row R, written at runtime by
//           dsdv_gunit_l5 via the centre's row writes) -- the compiler-visible static-row form; imm unused.  A one-step
//           sequencer op (one bank read): n_go / m_v leave 3 edges later than NORM's (command flop + 1: read address,
//           macro output register, step register, output flop), so it obeys the one-op-at-a-time rule and the bank-port
//           rules like any read op.  A NORM issued in the cycle NORMR completes is a schedule violation (sticky fault).
//   6 RDOUT a0, n: n row pairs (a0 + 2i, a0 + 2i + 1) -> lo (to the centre: ring / collective sends)
//   8..15  SU ops: forwarded unchanged to the beat's vs sub-leaf (s_v / s_d, one edge), which runs them on its own
//          fixed timeline through the extension port: row-pair reads (x_rv / x_ra -> x_qv / x_qd, 4 edges: vp pin flop,
//          macro, output register, vp output flop) and row-pair writes (x_wv / x_wa / x_wm / x_wd).  vs never
//          overlaps a vp op on a bank port (compiler slots); an overlap is a sticky fault here.
// Every input lands in a flop; every output leaves a flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vp #(
    parameter integer ML = 7,
    parameter integer AL = 6,
    parameter integer HPL = 1 + ML + 4 * AL + 1,     // lane_pr latency: pin flop + mul + 4 adds + BF16 output register
    // S81-PLAN R3 (10-25): core<->core stations of the leaf plan (die_plan internal_stations, class h = vn <-> the 16
    // hc_post lanes), every one 0 by default (= the pre-R3 netlist exactly).  All signals of one interface get the SAME
    // depth, every lane the same depth (static schedule: the compiler sees one fixed latency):
    //   CS_HI_D   stations on every lane input (v, r0..r3, y, c0..c3, p), tree form: the first CS_HI_GS stages are shared
    //             by a group of CS_H_G lanes (u_cst_hi_g<g> = g_hig[g].u_cst), the remaining CS_HI_D - CS_HI_GS are per
    //             lane (g_ln[l].u_cst_hi)
    //   CS_HO_D   stations on every lane output (vo, o, fault): CS_HO_D - CS_HO_GS per lane (g_ln[l].u_cst_ho) first,
    //             then CS_HO_GS shared per group (g_hog[g].u_cst)
    //   HQX       extra edges of the leaf's vn seam round trip hr -> hq (the leaf passes CS_VNI_D + CS_VNO_D)
    // Every fixed vp timeline that crosses these seams is derived from them: hc_post write-back = HPL + CS_HI_D +
    // CS_HO_D (+ HQX on the half-row tag), POST lane issue and HSTORE capture + HQX.
    parameter integer CS_HI_D = 0,
    parameter integer CS_HI_GS = 0,
    parameter integer CS_HO_D = 0,
    parameter integer CS_HO_GS = 0,
    parameter integer CS_H_G = 4,
    parameter integer HQX = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          c_v,
    input  wire [159:0]  c_d,
    // row-pair writes from the centre: rows sw_a (sw_d[127:0], word mask sw_m[3:0]) and sw_a + 1 ([255:128], sw_m[7:4])
    input  wire          sw_v,
    input  wire [9:0]    sw_a,
    input  wire [7:0]    sw_m,
    input  wire [255:0]  sw_d,
    // capture word writes (2 ports): word address [11:0] = {row 10, word 2}
    input  wire [1:0]    cw_v,
    input  wire [23:0]   cw_a,
    input  wire [63:0]   cw_d,
    // row-pair reads to the centre
    output reg           lo_v,
    output reg  [255:0]  lo_d,
    // vs seam (SU ops): command pass-through and the leaf-store extension port
    output reg           s_v,
    output reg  [159:0]  s_d,
    input  wire          x_rv,
    input  wire [9:0]    x_ra,
    output reg           x_qv,
    output reg  [255:0]  x_qd,
    input  wire          x_wv,
    input  wire [9:0]    x_wa,
    input  wire [7:0]    x_wm,
    input  wire [255:0]  x_wd,
    // vn seam
    output reg           hw_v, output reg [2:0] hw_j, output reg hw_hf, output reg [255:0] hw_d,
    output reg           hr_v, output reg [2:0] hr_j, output reg hr_hf,
    input  wire          hq_v, input wire [255:0] hq_d,
    output reg           n_go, output reg [127:0] n_pre,
    output reg           m_v, output reg m_q, output reg m_b, output reg [7:0] m_i,
    output reg           wl_v, output reg [2:0] wl_i, output reg [255:0] wl_d,
    output reg           fault
);
    localparam [3:0] OP_GAIN = 4'd1, OP_POST = 4'd2, OP_HLOAD = 4'd3, OP_HSTORE = 4'd4, OP_NORM = 4'd5, OP_RDOUT = 4'd6, OP_NORMR = 4'd7;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_s = rsv[1], rs_p = rsv[2], rs_o = rsv[3];
    integer i, k;

    // ---------------------------------------------------------------- input pin flops
    reg cv_c, swv_c, hqv_c, xrv_c, xwv_c; reg [1:0] cwv_c; reg [9:0] xra_c, xwa_c; reg [7:0] xwm_c; reg [255:0] xwd_c;
    reg [159:0] cd_c; reg [9:0] swa_c; reg [7:0] swm_c; reg [255:0] swd_c; reg [23:0] cwa_c; reg [63:0] cwd_c;
    reg [255:0] hqd_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin cv_c <= 1'b0; swv_c <= 1'b0; cwv_c <= 2'b00; hqv_c <= 1'b0; xrv_c <= 1'b0; xwv_c <= 1'b0; end
        else begin cv_c <= c_v; swv_c <= sw_v; cwv_c <= cw_v; hqv_c <= hq_v; xrv_c <= x_rv; xwv_c <= x_wv; end
    always @(posedge clk) begin
        xra_c <= x_ra; xwa_c <= x_wa; xwm_c <= x_wm; xwd_c <= x_wd;
        cd_c <= c_d; swa_c <= sw_a; swm_c <= sw_m; swd_c <= sw_d; cwa_c <= cw_a; cwd_c <= cw_d; hqd_c <= hq_d;
    end
    wire [3:0] op = cd_c[3:0]; wire [9:0] a0 = cd_c[13:4], a1 = cd_c[23:14]; wire [7:0] cn = cd_c[31:24];

    // ---------------------------------------------------------------- sequencer (one op at a time; fixed timelines)
    reg [3:0] sop; reg [7:0] si, sn; reg [9:0] sa0, sa1; reg [1:0] sqb; reg srun;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin srun <= 1'b0; si <= 8'd0; sop <= 4'd0; end
        else if (cv_c && op != OP_NORM && !op[3]) begin
            srun <= 1'b1; sop <= op; si <= 8'd0; sa0 <= a0; sa1 <= a1; sqb <= cn[1:0];
            sn <= (op == OP_GAIN) ? 8'd8 : (op == OP_POST) ? 8'd21 : (op == OP_HLOAD || op == OP_HSTORE) ? 8'd16 :
                  (op == OP_NORMR) ? 8'd1 : cn;
        end else if (srun) begin
            si <= si + 8'd1;
            if (si == sn - 8'd1) srun <= 1'b0;
        end
    wire busy_hit = cv_c && op != OP_NORM && !op[3] && srun;     // an op issued over a running op: schedule violation

    // per-cycle leaf-store reads (bank 0 / bank 1 row) and their purpose, by op and step
    //   GAIN   step i: rows a0 + 2i, a0 + 2i + 1 -> wl row i
    //   POST   steps 0..4: coefficient row a0 + s (one bank: s 0 = post, 1..4 = comb rows 0..3); steps 5..20: y row
    //          a1 + (s - 5) and h half row (s - 5)
    //   NORMR  step 0: row a0 (one bank) = hc_pre
    //   HLOAD  step i: rows a0 + 2i, + 1 -> hw half row i
    //   HSTORE step i: h half row i read (vn) -> written two edges + vn latency later
    //   RDOUT  step i: rows a0 + 2i, + 1 -> lo
    reg [9:0] ra_e, ra_o; reg re_e, re_o;
    reg [9:0] rr0, rr1;
    always @(*) begin
        re_e = 1'b0; re_o = 1'b0; ra_e = 10'd0; ra_o = 10'd0;
        rr0 = sa0 + {si[6:0], 1'b0}; rr1 = rr0 + 10'd1;
        if (xrv_c) begin re_e = 1'b1; re_o = 1'b1; ra_e = xra_c[0] ? xra_c + 10'd1 : xra_c; ra_o = xra_c[0] ? xra_c : xra_c + 10'd1; end
        if (srun) case (sop)
            OP_GAIN, OP_HLOAD, OP_RDOUT: begin re_e = 1'b1; re_o = 1'b1; ra_e = rr0[0] ? rr1 : rr0; ra_o = rr0[0] ? rr0 : rr1; end
            OP_POST, OP_NORMR: begin
                if (si < 8'd5) begin rr0 = sa0 + si[2:0]; if (rr0[0]) begin re_o = 1'b1; ra_o = rr0; end
                                                       else begin re_e = 1'b1; ra_e = rr0; end end
                else begin rr0 = sa1 + (si - 8'd5); if (rr0[0]) begin re_o = 1'b1; ra_o = rr0; end
                                                    else begin re_e = 1'b1; ra_e = rr0; end end
            end
            default: ;
        endcase
    end
    // GAIN / HLOAD / RDOUT need an even base: an odd a0 swaps the banks (rows a0 + 2i even/odd fixed by a0[0])
    wire swp = sa0[0] && (sop == OP_GAIN || sop == OP_HLOAD || sop == OP_RDOUT);
    wire xrcol = xrv_c && srun && sop != OP_HSTORE;   // the extension read shares the sequencer's read ports

    // ---------------------------------------------------------------- leaf store: write port selection per bank
    // writers: row write (sw), capture port 0 / 1, HSTORE (two rows a cycle)
    reg [1:0] wv; reg [8:0] wa [0:1]; reg [127:0] wd [0:1]; reg [127:0] wm [0:1]; reg wcol;
    reg hs_v; reg [9:0] hs_a; reg [255:0] hs_d;    // HSTORE write-back (registered from hq)
    reg [2:0] nw [0:1];
    always @(*) begin
        wv = 2'b00; wcol = 1'b0;
        for (k = 0; k < 2; k = k + 1) begin wa[k] = 9'd0; wd[k] = 128'd0; wm[k] = 128'd0; nw[k] = 3'd0; end
        if (swv_c) begin
            // row a -> bank a[0] at a >> 1; row a + 1 -> the other bank at (a + 1) >> 1 (a word mask of 0 skips a row)
            k = swa_c[0];
            if (|swm_c[3:0]) begin wv[k] = 1'b1; wa[k] = swa_c[9:1]; wd[k] = swd_c[127:0]; nw[k] = nw[k] + 3'd1;
                for (i = 0; i < 4; i = i + 1) wm[k][32 * i +: 32] = {32{swm_c[i]}}; end
            if (|swm_c[7:4]) begin wv[1 - k] = 1'b1; wa[1 - k] = swa_c[9:1] + {8'd0, swa_c[0]}; wd[1 - k] = swd_c[255:128];
                nw[1 - k] = nw[1 - k] + 3'd1;
                for (i = 0; i < 4; i = i + 1) wm[1 - k][32 * i +: 32] = {32{swm_c[4 + i]}}; end
        end
        for (i = 0; i < 2; i = i + 1)
            if (cwv_c[i]) begin
                k = cwa_c[12 * i + 2]; wv[k] = 1'b1; wa[k] = cwa_c[12 * i + 3 +: 9];
                wd[k] = {4{cwd_c[32 * i +: 32]}}; wm[k] = 128'd0; wm[k][32 * cwa_c[12 * i +: 2] +: 32] = {32{1'b1}};
                nw[k] = nw[k] + 3'd1;
            end
        if (xwv_c) begin
            k = xwa_c[0];
            if (|xwm_c[3:0]) begin wv[k] = 1'b1; wa[k] = xwa_c[9:1]; wd[k] = xwd_c[127:0]; nw[k] = nw[k] + 3'd1;
                for (i = 0; i < 4; i = i + 1) wm[k][32 * i +: 32] = {32{xwm_c[i]}}; end
            if (|xwm_c[7:4]) begin wv[1 - k] = 1'b1; wa[1 - k] = xwa_c[9:1] + {8'd0, xwa_c[0]}; wd[1 - k] = xwd_c[255:128];
                nw[1 - k] = nw[1 - k] + 3'd1;
                for (i = 0; i < 4; i = i + 1) wm[1 - k][32 * i +: 32] = {32{xwm_c[4 + i]}}; end
        end
        if (hs_v) begin
            wv = 2'b11; wa[0] = hs_a[9:1]; wa[1] = hs_a[9:1];
            wd[hs_a[0]] = hs_d[127:0]; wd[!hs_a[0]] = hs_d[255:128];
            wm[0] = {128{1'b1}}; wm[1] = {128{1'b1}}; nw[0] = nw[0] + 3'd1; nw[1] = nw[1] + 3'd1;
        end
        wcol = (nw[0] > 3'd1) || (nw[1] > 3'd1);
    end
    wire [127:0] rq0, rq1;
    ot_sram_1r1w_512x128_m4_r2c2 u_b0 (.clk(clk), .r_ce_in(re_e), .r_addr_in(ra_e[9:1]), .rd_out(rq0),
        .w_ce_in(wv[0]), .w_addr_in(wa[0]), .wd_in(wd[0]), .w_mask_in(wm[0]),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
    ot_sram_1r1w_512x128_m4_r2c2 u_b1 (.clk(clk), .r_ce_in(re_o), .r_addr_in(ra_o[9:1]), .rd_out(rq1),
        .w_ce_in(wv[1]), .w_addr_in(wa[1]), .wd_in(wd[1]), .w_mask_in(wm[1]),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
    // macro output registers + the step that launched the read (2 edges: address edge, output register)
    reg [127:0] q0, q1; reg [3:0] dop; reg [7:0] dsi; reg dv, dodd, dswp;
    reg [3:0] dop1; reg [7:0] dsi1; reg dv1, dodd1, dswp1;
    reg [9:0] dmq1, dmq;                                      // NORMR: {n[1:0], a1[7:0]} riding with the read step
    reg xr1, xr2, xsw1, xsw2;
    always @(posedge clk) begin q0 <= rq0; q1 <= rq1; xsw1 <= xra_c[0]; xsw2 <= xsw1; end
    always @(posedge clk or negedge rs_s) if (!rs_s) begin xr1 <= 1'b0; xr2 <= 1'b0; end else begin xr1 <= xrv_c; xr2 <= xr1; end
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin dv1 <= 1'b0; dv <= 1'b0; end
        else begin dv1 <= srun; dv <= dv1; end
    always @(posedge clk) begin
        dop1 <= sop; dsi1 <= si; dodd1 <= re_o && !re_e; dswp1 <= swp; dmq1 <= {sqb, sa1[7:0]};
        dop <= dop1; dsi <= dsi1; dodd <= dodd1; dswp <= dswp1; dmq <= dmq1;
    end
    wire [127:0] qe = dswp ? q1 : q0, qo = dswp ? q0 : q1;   // rows a0 + 2i (first) / a0 + 2i + 1 (second)
    wire [127:0] q1r = dodd ? q1 : q0;                        // POST: the one row read this step

    // ---------------------------------------------------------------- hc_post: coefficients, operands, lanes
    reg [31:0] cf [0:19];
    reg [31:0] yv [0:3];
    always @(posedge clk)
        if (dv && dop == OP_POST && dsi < 8'd5)
            for (i = 0; i < 4; i = i + 1) begin
`ifndef OT_S81SL_VP_MUT_POSTLAST
                // step 0 = post row -> cf[16 + k]; steps 1..4 = comb row j = step - 1 -> cf[4 j + k]
                if (dsi == 8'd0) cf[16 + i] <= q1r[32 * i +: 32]; else cf[4 * (dsi - 8'd1) + i] <= q1r[32 * i +: 32];
`else
                cf[4 * dsi + i] <= q1r[32 * i +: 32];   // bench mutant: the old order (comb rows a0..a0+3, post a0+4)
`endif
            end
    // POST step s >= 5 (cycle T): the y row read and the h half-row request (hr) leave together; the y row is at q in
    // T + 2 (macro + output register) and at yrow_d[2] in T + 5, the h half row at hqd_c in T + 5 (hr out flop, vn pin
    // flop, vn h macro edge, vn output flop, this leaf's pin flop): the lanes issue in T + 5.
    // S81-PLAN R3: the leaf's vn seam stations add HQX edges to the hr -> hq trip: the y row waits HQX more (YA)
    localparam integer YA = 2 + HQX;
    reg [127:0] yrow_d [0:YA]; reg [YA:0] ydv;
    integer yj;
    always @(posedge clk or negedge rs_p) if (!rs_p) ydv <= {(YA + 1){1'b0}};
        else ydv <= {ydv[YA - 1:0], dv && dop == OP_POST && dsi >= 8'd5};
    always @(posedge clk) begin
        yrow_d[0] <= q1r; for (yj = 1; yj <= YA; yj = yj + 1) yrow_d[yj] <= yrow_d[yj - 1];
    end
    // lanes: r0..r3 = h copies (BF16 -> FP32 pattern), y = y[e], c_j = comb[j][k] (word 4j + k), p = post[k]
    wire [15:0] lv, lf; wire [31:16] lo [0:15];   // lane o[15:0] is constant 0: not a lane pin (OWNER DECISION 8)
    reg  lane_v; reg [31:0] lr [0:15][0:3]; reg [31:0] ly [0:15];
    // S81-PLAN R3: lane station trees (see CS_HI_* / CS_HO_*).  Lane bundle (256 b): {p, c3, c2, c1, c0, y, r3..r0 high
    // halves} (r*[15:0] are constant 0 at the lane: not carried).
    localparam integer NG = 16 / CS_H_G, GW = 256 * CS_H_G;
    initial begin
        if (CS_H_G < 1 || 16 % CS_H_G != 0) $fatal(1, "ot_s81sl_vp: CS_H_G must divide 16");
        if (CS_HI_GS < 0 || CS_HI_GS > CS_HI_D || CS_HO_GS < 0 || CS_HO_GS > CS_HO_D || HQX < 0)
            $fatal(1, "ot_s81sl_vp: station depths must satisfy 0 <= CS_H*_GS <= CS_H*_D, HQX >= 0");
    end
    wire [4095:0] hi_s, hi_g; wire [NG-1:0] hiv_g;            // lane input bundles at the glue / after the group stages
    wire [16 * 18 - 1:0] ho_l;                               // lane output bundles {fault, vo, o[31:16]} after the per-lane stages
    wire [16 * 18 - 1:0] ho_g;                               // ... after the group stages (= what the glue reads)
    genvar gl, gg;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_hig
        ot_s81sl_cst #(.W(GW), .V(1), .D(CS_HI_GS)) u_cst (.clk(clk), .rst_n(rs_p), .d(hi_s[GW * gg +: GW]), .dv(lane_v),
            .q(hi_g[GW * gg +: GW]), .qv(hiv_g[gg]));
    end endgenerate
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_hog
        // per group: data o (16 b a lane), valid/control {fault, vo} (2 b a lane)
        wire [16 * CS_H_G - 1:0] od, oq; wire [2 * CS_H_G - 1:0] ov, oqv;
        for (gl = 0; gl < CS_H_G; gl = gl + 1) begin : g_m
            assign od[16 * gl +: 16] = ho_l[18 * (CS_H_G * gg + gl) +: 16];
            assign ov[2 * gl +: 2] = ho_l[18 * (CS_H_G * gg + gl) + 16 +: 2];
            assign ho_g[18 * (CS_H_G * gg + gl) +: 18] = {oqv[2 * gl +: 2], oq[16 * gl +: 16]};
        end
        ot_s81sl_cst #(.W(16 * CS_H_G), .V(2 * CS_H_G), .D(CS_HO_GS)) u_cst (.clk(clk), .rst_n(rs_p), .d(od), .dv(ov),
            .q(oq), .qv(oqv));
    end endgenerate
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_ln
        localparam integer KK = gl / 4, II = gl % 4;
        wire [255:0] li; wire liv, lvn, lfn; wire [31:16] lon; wire [15:0] lq; wire [1:0] lqv;
        assign hi_s[256 * gl +: 256] = {cf[16 + KK], cf[12 + KK], cf[8 + KK], cf[4 + KK], cf[KK], ly[gl],
                                        lr[gl][3][31:16], lr[gl][2][31:16], lr[gl][1][31:16], lr[gl][0][31:16]};
`ifndef OT_S81SL_CST_MUT_LANE
        localparam integer HIM = 0;
`else
        localparam integer HIM = (gl == 5) ? 1 : 0;   // bench mutant: lane 5 one input station deeper than its peers
`endif
        ot_s81sl_cst #(.W(256), .V(1), .D(CS_HI_D - CS_HI_GS + HIM)) u_cst_hi (.clk(clk), .rst_n(rs_p),
            .d(hi_g[256 * gl +: 256]), .dv(hiv_g[gl / CS_H_G]), .q(li), .qv(liv));
`ifndef OT_S81SL_VP_HARD
        ot_dsrom_su_hcpost_lane_pr #(.ML(ML), .AL(AL)) u_l (.clk(clk), .rst_n(rs_p), .v(liv),
`else
        // hardened cluster: the closed s81sl_hcpl view (its kit fixes ML 7 / AL 6; no #() on a hard child)
        ot_dsrom_su_hcpost_lane_pr u_l (.clk(clk), .rst_n(rs_p), .v(liv),
`endif
            .r0({li[15:0], 16'd0}), .r1({li[31:16], 16'd0}), .r2({li[47:32], 16'd0}), .r3({li[63:48], 16'd0}),
            .y(li[95:64]), .c0(li[127:96]), .c1(li[159:128]), .c2(li[191:160]), .c3(li[223:192]), .p(li[255:224]),
            .vo(lvn), .o(lon), .fault(lfn));
        ot_s81sl_cst #(.W(16), .V(2), .D(CS_HO_D - CS_HO_GS)) u_cst_ho (.clk(clk), .rst_n(rs_p), .d(lon), .dv({lfn, lvn}),
            .q(lq), .qv(lqv));
        assign ho_l[18 * gl +: 18] = {lqv, lq};
        assign lo[gl] = ho_g[18 * gl +: 16]; assign lv[gl] = ho_g[18 * gl + 16]; assign lf[gl] = ho_g[18 * gl + 17];
    end endgenerate
    // the h half row of POST step s (requested with the y read: hq arrives aligned with ydv[2])
    always @(posedge clk or negedge rs_p) if (!rs_p) lane_v <= 1'b0; else lane_v <= ydv[YA];
    always @(posedge clk) begin
        for (k = 0; k < 4; k = k + 1)
            for (i = 0; i < 4; i = i + 1) begin
                lr[4 * k + i][0] <= {hqd_c[(4 * 0 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][1] <= {hqd_c[(4 * 1 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][2] <= {hqd_c[(4 * 2 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][3] <= {hqd_c[(4 * 3 + i) * 16 +: 16], 16'd0};
                ly[4 * k + i] <= yrow_d[YA][32 * i +: 32];
            end
    end
    // write-back tag: the half-row index rides a delay line of the lane latency
    reg [3:0] pidx_q [0:4]; reg [3:0] pidx;
    always @(posedge clk) begin
        pidx_q[0] <= si[3:0] - 4'd5; pidx_q[1] <= pidx_q[0]; pidx_q[2] <= pidx_q[1]; pidx_q[3] <= pidx_q[2];
        pidx_q[4] <= pidx_q[3]; pidx <= pidx_q[4];
    end
    wire [3:0] widx; wire wvl;
    // S81-PLAN R3: + the lane station depths (both directions); the tag also waits the vn seam's HQX (lane_v does)
    ot_hdc_delay #(.W(4), .D(HPL + HQX + CS_HI_D + CS_HO_D)) u_wi (.clk(clk), .rst_n(rs_p), .d(pidx), .q(widx));
    ot_hdc_delay #(.W(1), .D(HPL + CS_HI_D + CS_HO_D), .RESET(1)) u_wv (.clk(clk), .rst_n(rs_p), .d(lane_v), .q(wvl));

    // ---------------------------------------------------------------- vn seam (registered outputs)
    reg hrq_v; reg [3:0] hrq_i;                  // h read request this cycle (POST / HSTORE)
    always @(*) begin
        hrq_v = 1'b0; hrq_i = 4'd0;
        if (srun && sop == OP_POST && si >= 8'd5) begin hrq_v = 1'b1; hrq_i = si[3:0] - 4'd5; end
        if (srun && sop == OP_HSTORE) begin hrq_v = 1'b1; hrq_i = si[3:0]; end
    end
    // HSTORE: the half row returns from vn three edges after hr, plus this leaf's input flop
    // S81-PLAN R3: + HQX (the leaf's vn seam stations on hr and hq)
    localparam integer HA = 4 + HQX;
    reg [3:0] hsi_q [0:HA];
    reg [HA:0] hsv_q;
    integer hj;
    always @(posedge clk or negedge rs_o) if (!rs_o) hsv_q <= {(HA + 1){1'b0}};
        else hsv_q <= {hsv_q[HA - 1:0], srun && sop == OP_HSTORE};
    always @(posedge clk) begin
        hsi_q[0] <= si[3:0]; for (hj = 1; hj <= HA; hj = hj + 1) hsi_q[hj] <= hsi_q[hj - 1];
    end
    reg [9:0] hs_base;
    always @(posedge clk) if (cv_c && op == OP_HSTORE) hs_base <= a0;
    always @(posedge clk or negedge rs_o) if (!rs_o) hs_v <= 1'b0; else hs_v <= hsv_q[HA] && hqv_c;
    always @(posedge clk) begin hs_a <= hs_base + {hsi_q[HA], 1'b0}; hs_d <= hqd_c; end

    wire nr_done = dv && dop == OP_NORMR;          // NORMR: the hc_pre row is at q this cycle
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin hw_v <= 1'b0; hr_v <= 1'b0; n_go <= 1'b0; m_v <= 1'b0; wl_v <= 1'b0; lo_v <= 1'b0; s_v <= 1'b0; x_qv <= 1'b0; end
        else begin
            hw_v <= wvl || (dv && dop == OP_HLOAD);
            hr_v <= hrq_v;
            n_go <= (cv_c && op == OP_NORM) || nr_done;
            m_v <= (cv_c && op == OP_NORM) || nr_done;
            wl_v <= dv && dop == OP_GAIN;
            lo_v <= dv && dop == OP_RDOUT;
            s_v <= cv_c && op[3];
            x_qv <= xr2;
        end
    always @(posedge clk) begin
        if (wvl) begin
            hw_j <= widx[3:1]; hw_hf <= widx[0];
            for (k = 0; k < 4; k = k + 1) for (i = 0; i < 4; i = i + 1)
                hw_d[(4 * k + i) * 16 +: 16] <= lo[4 * k + i][31:16];
        end else begin
            hw_j <= dsi[3:1]; hw_hf <= dsi[0]; hw_d <= {qo, qe};
        end
        hr_j <= hrq_i[3:1]; hr_hf <= hrq_i[0];
        if (cv_c && op == OP_NORM) begin n_pre <= cd_c[159:32]; m_q <= cn[0]; m_b <= cn[1]; m_i <= a1[7:0]; end
        else if (nr_done) begin
`ifndef OT_S81SL_VP_MUT_NORMIMM
            n_pre <= q1r;
`else
            n_pre <= 128'd0;                       // bench mutant: NORMR ignores the row (the old imm-only NORM)
`endif
            m_q <= dmq[8]; m_b <= dmq[9]; m_i <= dmq[7:0];
        end
        wl_i <= dsi[2:0]; wl_d <= {qo, qe};
        lo_d <= {qo, qe};
        s_d <= cd_c;
        x_qd <= xsw2 ? {q0, q1} : {q1, q0};
    end

    // ---------------------------------------------------------------- faults
    reg lvbad;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin fault <= 1'b0; lvbad <= 1'b0; end
        else begin
            lvbad <= (lv[0] != wvl) || (|lv != &lv);
            fault <= fault | wcol | busy_hit | xrcol | (|lf) | lvbad | (wvl && dv && dop == OP_HLOAD) |
                     (hsv_q[HA] && !hqv_c) | (ydv[YA] && !hqv_c) |
                     (cv_c && op == OP_NORM && nr_done);
        end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// S81-PLAN R3 (10-25): core<->core plan stations.  ot_s81sl_cst1 = ONE station stage (kept as its own module so the kit
// can place each stage at its plan site): W data bits with NO reset (flushed by the producer under the static schedule,
// the ot_dp_st rule) and V valid / control / fault bits asynchronously cleared by the region reset.  ot_s81sl_cst = D
// such stages in a chain (s[0] nearest the launch side), D = 0 is a wire (the pre-R3 netlist exactly).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_s81sl_cst1 #(parameter integer W = 1, parameter integer V = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, input wire [V-1:0] dv, output reg [W-1:0] q, output reg [V-1:0] qv
);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n) if (!rst_n) qv <= {V{1'b0}}; else qv <= dv;
endmodule

module ot_s81sl_cst #(parameter integer W = 1, parameter integer V = 1, parameter integer D = 0) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, input wire [V-1:0] dv, output wire [W-1:0] q, output wire [V-1:0] qv
);
    generate if (D <= 0) begin : g0
        assign q = d; assign qv = dv;
    end else begin : gd
        wire [W-1:0] cd [0:D]; wire [V-1:0] cv [0:D];
        assign cd[0] = d; assign cv[0] = dv;
        genvar j;
        for (j = 0; j < D; j = j + 1) begin : s
            ot_s81sl_cst1 #(.W(W), .V(V)) u (.clk(clk), .rst_n(rst_n), .d(cd[j]), .dv(cv[j]), .q(cd[j + 1]), .qv(cv[j + 1]));
        end
        assign q = cd[D]; assign qv = cv[D];
    end endgenerate
endmodule
