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
//   2 POST  a0: coefficient rows (comb[j][k] at word 4j + k, post[k] at word 16 + k), a1: y rows (element order)
//   3 HLOAD a0: 32 rows (half row i = sub-beat i>>1, half i&1: rows a0 + 2i, a0 + 2i + 1 = vn's 256-b half-row layout)
//   4 HSTORE a0: the inverse of HLOAD (h -> leaf store)
//   5 NORM  imm[127:0] = the hc_pre coefficients -> vn n_go
//   6 RDOUT a0, n: n row pairs (a0 + 2i, a0 + 2i + 1) -> lo (to the centre: ring / collective sends)
// Every input lands in a flop; every output leaves a flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vp #(
    parameter integer ML = 7,
    parameter integer AL = 6,
    parameter integer HPL = 1 + ML + 4 * AL + 1      // lane_pr latency: pin flop + mul + 4 adds + BF16 output register
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          c_v,
    input  wire [159:0]  c_d,
    // row writes from the centre
    input  wire          sw_v,
    input  wire [9:0]    sw_a,
    input  wire [3:0]    sw_m,
    input  wire [127:0]  sw_d,
    // capture word writes (2 ports): word address [11:0] = {row 10, word 2}
    input  wire [1:0]    cw_v,
    input  wire [23:0]   cw_a,
    input  wire [63:0]   cw_d,
    // row-pair reads to the centre
    output reg           lo_v,
    output reg  [255:0]  lo_d,
    // vn seam
    output reg           hw_v, output reg [2:0] hw_j, output reg hw_hf, output reg [255:0] hw_d,
    output reg           hr_v, output reg [2:0] hr_j, output reg hr_hf,
    input  wire          hq_v, input wire [255:0] hq_d,
    output reg           n_go, output reg [127:0] n_pre,
    output reg           wl_v, output reg [2:0] wl_i, output reg [255:0] wl_d,
    output reg           fault
);
    localparam [3:0] OP_GAIN = 4'd1, OP_POST = 4'd2, OP_HLOAD = 4'd3, OP_HSTORE = 4'd4, OP_NORM = 4'd5, OP_RDOUT = 4'd6;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_s = rsv[1], rs_p = rsv[2], rs_o = rsv[3];
    integer i, k;

    // ---------------------------------------------------------------- input pin flops
    reg cv_c, swv_c, hqv_c; reg [1:0] cwv_c;
    reg [159:0] cd_c; reg [9:0] swa_c; reg [3:0] swm_c; reg [127:0] swd_c; reg [23:0] cwa_c; reg [63:0] cwd_c;
    reg [255:0] hqd_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin cv_c <= 1'b0; swv_c <= 1'b0; cwv_c <= 2'b00; hqv_c <= 1'b0; end
        else begin cv_c <= c_v; swv_c <= sw_v; cwv_c <= cw_v; hqv_c <= hq_v; end
    always @(posedge clk) begin
        cd_c <= c_d; swa_c <= sw_a; swm_c <= sw_m; swd_c <= sw_d; cwa_c <= cw_a; cwd_c <= cw_d; hqd_c <= hq_d;
    end
    wire [3:0] op = cd_c[3:0]; wire [9:0] a0 = cd_c[13:4], a1 = cd_c[23:14]; wire [7:0] cn = cd_c[31:24];

    // ---------------------------------------------------------------- sequencer (one op at a time; fixed timelines)
    reg [3:0] sop; reg [7:0] si, sn; reg [9:0] sa0, sa1; reg srun;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin srun <= 1'b0; si <= 8'd0; sop <= 4'd0; end
        else if (cv_c && op != OP_NORM) begin
            srun <= 1'b1; sop <= op; si <= 8'd0; sa0 <= a0; sa1 <= a1;
            sn <= (op == OP_GAIN) ? 8'd8 : (op == OP_POST) ? 8'd21 : (op == OP_HLOAD || op == OP_HSTORE) ? 8'd16 : cn;
        end else if (srun) begin
            si <= si + 8'd1;
            if (si == sn - 8'd1) srun <= 1'b0;
        end
    wire busy_hit = cv_c && op != OP_NORM && srun;     // an op issued over a running op: schedule violation

    // per-cycle leaf-store reads (bank 0 / bank 1 row) and their purpose, by op and step
    //   GAIN   step i: rows a0 + 2i, a0 + 2i + 1 -> wl row i
    //   POST   steps 0..4: coefficient row a0 + s (one bank); steps 5..20: y row a1 + (s - 5) and h half row (s - 5)
    //   HLOAD  step i: rows a0 + 2i, + 1 -> hw half row i
    //   HSTORE step i: h half row i read (vn) -> written two edges + vn latency later
    //   RDOUT  step i: rows a0 + 2i, + 1 -> lo
    reg [9:0] ra_e, ra_o; reg re_e, re_o;
    reg [9:0] rr0, rr1;
    always @(*) begin
        re_e = 1'b0; re_o = 1'b0; ra_e = 10'd0; ra_o = 10'd0;
        rr0 = sa0 + {si[6:0], 1'b0}; rr1 = rr0 + 10'd1;
        if (srun) case (sop)
            OP_GAIN, OP_HLOAD, OP_RDOUT: begin re_e = 1'b1; re_o = 1'b1; ra_e = rr0[0] ? rr1 : rr0; ra_o = rr0[0] ? rr0 : rr1; end
            OP_POST: begin
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

    // ---------------------------------------------------------------- leaf store: write port selection per bank
    // writers: row write (sw), capture port 0 / 1, HSTORE (two rows a cycle)
    reg [1:0] wv; reg [8:0] wa [0:1]; reg [127:0] wd [0:1]; reg [127:0] wm [0:1]; reg wcol;
    reg hs_v; reg [9:0] hs_a; reg [255:0] hs_d;    // HSTORE write-back (registered from hq)
    reg [2:0] nw [0:1];
    always @(*) begin
        wv = 2'b00; wcol = 1'b0;
        for (k = 0; k < 2; k = k + 1) begin wa[k] = 9'd0; wd[k] = 128'd0; wm[k] = 128'd0; nw[k] = 3'd0; end
        if (swv_c) begin
            k = swa_c[0]; wv[k] = 1'b1; wa[k] = swa_c[9:1]; wd[k] = swd_c; nw[k] = nw[k] + 3'd1;
            for (i = 0; i < 4; i = i + 1) wm[k][32 * i +: 32] = {32{swm_c[i]}};
        end
        for (i = 0; i < 2; i = i + 1)
            if (cwv_c[i]) begin
                k = cwa_c[12 * i + 2]; wv[k] = 1'b1; wa[k] = cwa_c[12 * i + 3 +: 9];
                wd[k] = {4{cwd_c[32 * i +: 32]}}; wm[k] = 128'd0; wm[k][32 * cwa_c[12 * i +: 2] +: 32] = {32{1'b1}};
                nw[k] = nw[k] + 3'd1;
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
    always @(posedge clk) begin q0 <= rq0; q1 <= rq1; end
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin dv1 <= 1'b0; dv <= 1'b0; end
        else begin dv1 <= srun; dv <= dv1; end
    always @(posedge clk) begin
        dop1 <= sop; dsi1 <= si; dodd1 <= re_o && !re_e; dswp1 <= swp;
        dop <= dop1; dsi <= dsi1; dodd <= dodd1; dswp <= dswp1;
    end
    wire [127:0] qe = dswp ? q1 : q0, qo = dswp ? q0 : q1;   // rows a0 + 2i (first) / a0 + 2i + 1 (second)
    wire [127:0] q1r = dodd ? q1 : q0;                        // POST: the one row read this step

    // ---------------------------------------------------------------- hc_post: coefficients, operands, lanes
    reg [31:0] cf [0:19];
    reg [31:0] yv [0:3];
    always @(posedge clk)
        if (dv && dop == OP_POST && dsi < 8'd5)
            for (i = 0; i < 4; i = i + 1) cf[4 * dsi + i] <= q1r[32 * i +: 32];
    // POST step s >= 5 (cycle T): the y row read and the h half-row request (hr) leave together; the y row is at q in
    // T + 2 (macro + output register) and at yrow_d[1] in T + 4, the h half row at hqd_c in T + 4 (hr out flop, vn pin
    // flop, vn read flop, this leaf's pin flop): the lanes issue in T + 4 (lane_v, lr, ly registered at its end).
    reg [255:0] yrow_d [0:3]; reg [3:0] ydv;
    always @(posedge clk or negedge rs_p) if (!rs_p) ydv <= 4'd0;
        else ydv <= {ydv[2:0], dv && dop == OP_POST && dsi >= 8'd5};
    always @(posedge clk) begin
        yrow_d[0] <= {128'd0, q1r}; yrow_d[1] <= yrow_d[0]; yrow_d[2] <= yrow_d[1]; yrow_d[3] <= yrow_d[2];
    end
    // lanes: r0..r3 = h copies (BF16 -> FP32 pattern), y = y[e], c_j = comb[j][k] (word 4j + k), p = post[k]
    wire [15:0] lv, lf; wire [31:0] lo [0:15];
    reg  lane_v; reg [31:0] lr [0:15][0:3]; reg [31:0] ly [0:15];
    genvar gl;
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_ln
        localparam integer KK = gl / 4, II = gl % 4;
        ot_dsrom_su_hcpost_lane_pr #(.ML(ML), .AL(AL)) u_l (.clk(clk), .rst_n(rs_p), .v(lane_v),
            .r0(lr[gl][0]), .r1(lr[gl][1]), .r2(lr[gl][2]), .r3(lr[gl][3]), .y(ly[gl]),
            .c0(cf[KK]), .c1(cf[4 + KK]), .c2(cf[8 + KK]), .c3(cf[12 + KK]), .p(cf[16 + KK]),
            .vo(lv[gl]), .o(lo[gl]), .fault(lf[gl]));
    end endgenerate
    // the h half row of POST step s (vn read requested at the y-read step +2: hq_v arrives aligned with ydv[3])
    always @(posedge clk or negedge rs_p) if (!rs_p) lane_v <= 1'b0; else lane_v <= ydv[1];
    always @(posedge clk) begin
        for (k = 0; k < 4; k = k + 1)
            for (i = 0; i < 4; i = i + 1) begin
                lr[4 * k + i][0] <= {hqd_c[(4 * 0 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][1] <= {hqd_c[(4 * 1 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][2] <= {hqd_c[(4 * 2 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][3] <= {hqd_c[(4 * 3 + i) * 16 +: 16], 16'd0};
                ly[4 * k + i] <= yrow_d[1][32 * i +: 32];
            end
    end
    // write-back tag: the half-row index rides a delay line of the lane latency
    reg [3:0] pidx_q [0:3]; reg [3:0] pidx;
    always @(posedge clk) begin
        pidx_q[0] <= si[3:0] - 4'd5; pidx_q[1] <= pidx_q[0]; pidx_q[2] <= pidx_q[1]; pidx_q[3] <= pidx_q[2];
        pidx <= pidx_q[3];
    end
    wire [3:0] widx; wire wvl;
    ot_hdc_delay #(.W(4), .D(HPL)) u_wi (.clk(clk), .rst_n(rs_p), .d(pidx), .q(widx));
    ot_hdc_delay #(.W(1), .D(HPL), .RESET(1)) u_wv (.clk(clk), .rst_n(rs_p), .d(lane_v), .q(wvl));

    // ---------------------------------------------------------------- vn seam (registered outputs)
    reg hrq_v; reg [3:0] hrq_i;                  // h read request this cycle (POST / HSTORE)
    always @(*) begin
        hrq_v = 1'b0; hrq_i = 4'd0;
        if (srun && sop == OP_POST && si >= 8'd5) begin hrq_v = 1'b1; hrq_i = si[3:0] - 4'd5; end
        if (srun && sop == OP_HSTORE) begin hrq_v = 1'b1; hrq_i = si[3:0]; end
    end
    // HSTORE: the half row returns from vn two edges after hr, plus this leaf's input flop
    reg [3:0] hsi_q [0:3];
    reg [3:0] hsv_q;
    always @(posedge clk or negedge rs_o) if (!rs_o) hsv_q <= 4'd0;
        else hsv_q <= {hsv_q[2:0], srun && sop == OP_HSTORE};
    always @(posedge clk) begin
        hsi_q[0] <= si[3:0]; hsi_q[1] <= hsi_q[0]; hsi_q[2] <= hsi_q[1]; hsi_q[3] <= hsi_q[2];
    end
    reg [9:0] hs_base;
    always @(posedge clk) if (cv_c && op == OP_HSTORE) hs_base <= a0;
    always @(posedge clk or negedge rs_o) if (!rs_o) hs_v <= 1'b0; else hs_v <= hsv_q[3] && hqv_c;
    always @(posedge clk) begin hs_a <= hs_base + {hsi_q[3], 1'b0}; hs_d <= hqd_c; end

    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin hw_v <= 1'b0; hr_v <= 1'b0; n_go <= 1'b0; wl_v <= 1'b0; lo_v <= 1'b0; end
        else begin
            hw_v <= wvl || (dv && dop == OP_HLOAD);
            hr_v <= hrq_v;
            n_go <= cv_c && op == OP_NORM;
            wl_v <= dv && dop == OP_GAIN;
            lo_v <= dv && dop == OP_RDOUT;
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
        if (cv_c && op == OP_NORM) n_pre <= cd_c[159:32];
        wl_i <= dsi[2:0]; wl_d <= {qo, qe};
        lo_d <= {qo, qe};
    end

    // ---------------------------------------------------------------- faults
    reg lvbad;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin fault <= 1'b0; lvbad <= 1'b0; end
        else begin
            lvbad <= (lv[0] != wvl) || (|lv != &lv);
            fault <= fault | wcol | busy_hit | (|lf) | lvbad | (wvl && dv && dop == OP_HLOAD) |
                     (hsv_q[3] && !hqv_c) | (ydv[1] && !hqv_c);
        end
endmodule
