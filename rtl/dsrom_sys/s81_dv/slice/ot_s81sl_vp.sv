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
    parameter integer HPL = 1 + ML + 4 * AL + 1      // lane_pr latency: pin flop + mul + 4 adds + BF16 output register
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
    // SAFE 10-21: 10 reset regions (was 4 with ~100 loads each): every relay leaf resets <= ~33 control / valid flops;
    // coefficient enables, relays and the fault reduce pipe carry no reset (they flush while reset is held).
    wire [23:0] rsv;
    ot_rst_relay_tree3 #(.REGIONS(24), .LEAVES(8)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_c2 = rsv[1], rs_s = rsv[2], rs_p = rsv[3], rs_r0 = rsv[4], rs_r1 = rsv[5], rs_w = rsv[6],
         rs_o = rsv[7], rs_o2 = rsv[8], rs_o3 = rsv[9];
    integer i, k;

    // ---------------------------------------------------------------- input pin flops
    reg cv_c, hqv_c, xrv_c; reg [9:0] xra_c, xwa_c; reg [7:0] xwm_c; reg [255:0] xwd_c;
    reg [159:0] cd_c; reg [9:0] swa_c; reg [7:0] swm_c; reg [255:0] swd_c; reg [23:0] cwa_c; reg [63:0] cwd_c;
    reg [255:0] hqd_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin cv_c <= 1'b0; hqv_c <= 1'b0; xrv_c <= 1'b0; end
        else begin cv_c <= c_v; hqv_c <= hq_v; xrv_c <= x_rv; end
    always @(posedge clk) begin
        xra_c <= x_ra; xwa_c <= x_wa; xwm_c <= x_wm; xwd_c <= x_wd;
        cd_c <= c_d; swa_c <= sw_a; swm_c <= sw_m; swd_c <= sw_d; cwa_c <= cw_a; cwd_c <= cw_d; hqd_c <= hq_d;
    end
    wire [3:0] op = cd_c[3:0]; wire [9:0] a0 = cd_c[13:4], a1 = cd_c[23:14]; wire [7:0] cn = cd_c[31:24];
    // S81-SLICE/VP SAFE 10-21 (c318a2024 NEEDS_RTL TT -102): the bank write-port selects (sw / cw / xw valid, bank bit,
    // word masks) and the NORM load decode each fanned out to 256+ mux / enable loads from ONE pin flop.  Every such
    // select now lands from its pin in KEPT copies, one per 32-bit word group (g 0..7 = bank g/4, word g%4) plus one per
    // bank address / enable group (g 8, 9), and one per 32-bit n_pre word (4) + the m_* group: <= ~40 loads per copy.
    // Same edge as the original pin flop: no latency change.
    localparam integer NG = 32;
    (* keep *) reg [NG-1:0]   k_swv, k_xwv, k_swa0, k_xwa0;
    (* keep *) reg [2*NG-1:0] k_cwv;
    (* keep *) reg [8*NG-1:0] k_swm, k_xwm;
    (* keep *) reg [6*NG-1:0] k_cws;                 // {cw_a[14:12], cw_a[2:0]}: port 1 / port 0 {bank, word}
    (* keep *) reg [8:0]      k_cv;                  // n_pre 16-bit groups 0..7 + the m_* group 8
    (* keep *) reg [35:0]     k_op;
    always @(posedge clk or negedge rsv[11]) if(!rsv[11]) k_swv <= 0; else k_swv <= {NG{sw_v}};
    always @(posedge clk or negedge rsv[12]) if(!rsv[12]) k_xwv <= 0; else k_xwv <= {NG{x_wv}};
    always @(posedge clk or negedge rsv[13]) if(!rsv[13]) k_cwv[NG-1:0] <= 0; else k_cwv[NG-1:0] <= {NG/2{cw_v}};
    always @(posedge clk or negedge rsv[14]) if(!rsv[14]) k_cwv[2*NG-1:NG] <= 0; else k_cwv[2*NG-1:NG] <= {NG/2{cw_v}};
    always @(posedge clk or negedge rs_c2) if(!rs_c2) k_cv <= 0; else k_cv <= {9{c_v}};
    always @(posedge clk) begin
        k_swa0 <= {NG{sw_a[0]}}; k_xwa0 <= {NG{x_wa[0]}}; k_swm <= {NG{sw_m}}; k_xwm <= {NG{x_wm}};
        k_cws <= {NG{cw_a[14:12], cw_a[2:0]}}; k_op <= {9{c_d[3:0]}};
    end

    // ---------------------------------------------------------------- sequencer (one op at a time; fixed timelines)
    reg [3:0] sop; reg [7:0] si, sn; reg [9:0] sa0, sa1; reg [1:0] sqb; reg srun;
    always @(posedge clk or negedge rs_s)
        if (!rs_s) begin srun <= 1'b0; si <= 8'd0; sop <= 4'd0; end
        else if (cv_c && op != OP_NORM && !op[3]) begin
            srun <= 1'b1; sop <= op; si <= 8'd0;
        end else if (srun) begin
            si <= si + 8'd1;
            if (si == sn - 8'd1) srun <= 1'b0;
        end
    // Same-edge command decode copies, one per payload byte. The predicate
    // lands beside cv_c; payload still captures on the original next edge.
    (* keep *) reg [3:0] payload_v;
    always @(posedge clk or negedge rsv[23])
      if(!rsv[23]) payload_v<=0;
      else payload_v <= {4{c_v && c_d[3:0] != OP_NORM && !c_d[3]}};
    wire [7:0] sn_cmd = (op == OP_GAIN) ? 8'd8 : (op == OP_POST) ? 8'd21 :
                          (op == OP_HLOAD || op == OP_HSTORE) ? 8'd16 : (op == OP_NORMR) ? 8'd1 : cn;
    always @(posedge clk) begin
      if(payload_v[0]) sa0[7:0] <= a0[7:0];
      if(payload_v[1]) begin sa0[9:8] <= a0[9:8]; sa1[5:0] <= a1[5:0]; end
      if(payload_v[2]) begin sa1[9:6] <= a1[9:6]; sn[3:0] <= sn_cmd[3:0]; end
      if(payload_v[3]) begin sn[7:4] <= sn_cmd[7:4]; sqb <= cn[1:0]; end
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
    // writers: row write (sw), capture port 0 / 1, extension write (xw), HSTORE (two rows a cycle).  Every writer
    // overwrites a whole bank's (data, mask) when it targets that bank, the later writer winning (sw, cw0, cw1, xw, hs):
    // decomposed per 32-bit word group g = 4 b + w, each group on its own kept select copies (S81-SLICE/VP SAFE 10-21).
    wire [255:0] wd_f, wm_f; wire [17:0] wa_f; wire [1:0] wv, wcb; wire wcol = |wcb;
    reg hs_v; reg [9:0] hs_a; reg [255:0] hs_d;    // HSTORE write-back (registered from hq)
    (* keep *) reg [NG-1:0] k_hsv, k_hsa0;           // kept copies of hs_v / hs_a[0] (= hs_base[0]: the step adds 2 i)
    genvar gb, gw;
    generate for (gb = 0; gb < 2; gb = gb + 1) begin : g_wb
        for (gw = 0; gw < 16; gw = gw + 1) begin : g_ww
            localparam integer G = 16 * gb + gw;
            reg [7:0] wdw; reg wmw;
            always @(*) begin
                wdw = 8'd0; wmw = 1'b0;
                if (k_swv[G]) begin
                    if (k_swa0[G] == (gb == 1)) begin
                        if (|k_swm[8 * G +: 4]) begin wdw = swd_c[8 * gw +: 8]; wmw = k_swm[8 * G + (gw/4)]; end
                    end else if (|k_swm[8 * G + 4 +: 4]) begin wdw = swd_c[128 + 8 * gw +: 8]; wmw = k_swm[8 * G + 4 + (gw/4)]; end
                end
                if (k_cwv[2 * G] && k_cws[6 * G + 2] == (gb == 1)) begin
                    wdw = cwd_c[8*(gw%4)+:8]; wmw = (k_cws[6 * G +: 2] == (gw/4)); end
                if (k_cwv[2 * G + 1] && k_cws[6 * G + 5] == (gb == 1)) begin
                    wdw = cwd_c[32+8*(gw%4)+:8]; wmw = (k_cws[6 * G + 3 +: 2] == (gw/4)); end
                if (k_xwv[G]) begin
                    if (k_xwa0[G] == (gb == 1)) begin
                        if (|k_xwm[8 * G +: 4]) begin wdw = xwd_c[8 * gw +: 8]; wmw = k_xwm[8 * G + (gw/4)]; end
                    end else if (|k_xwm[8 * G + 4 +: 4]) begin wdw = xwd_c[128 + 8 * gw +: 8]; wmw = k_xwm[8 * G + 4 + (gw/4)]; end
                end
                if (k_hsv[G]) begin wdw = ((G == 0 ? hs_a[0] : k_hsa0[G]) == (gb == 1)) ? hs_d[8 * gw +: 8] : hs_d[128 + 8 * gw +: 8]; wmw = 1'b1; end
            end
            assign wd_f[128 * gb + 8 * gw +: 8] = wdw; assign wm_f[128 * gb + 8 * gw +: 8] = {8{wmw}};
        end
        // bank enable / address / write count (group 8 + b)
        localparam integer GA = 16 * gb;
        reg [2:0] nwb; reg wvb; reg [8:0] wab;
        always @(*) begin
            wvb = 1'b0; wab = 9'd0; nwb = 3'd0;
            if (k_swv[GA]) begin
                if (k_swa0[GA] == (gb == 1)) begin
                    if (|k_swm[8 * GA +: 4]) begin wvb = 1'b1; wab = swa_c[9:1]; nwb = nwb + 3'd1; end
                end else if (|k_swm[8 * GA + 4 +: 4]) begin wvb = 1'b1; wab = swa_c[9:1] + {8'd0, k_swa0[GA]}; nwb = nwb + 3'd1; end
            end
            if (k_cwv[2 * GA] && k_cws[6 * GA + 2] == (gb == 1)) begin wvb = 1'b1; wab = cwa_c[11:3]; nwb = nwb + 3'd1; end
            if (k_cwv[2 * GA + 1] && k_cws[6 * GA + 5] == (gb == 1)) begin wvb = 1'b1; wab = cwa_c[23:15]; nwb = nwb + 3'd1; end
            if (k_xwv[GA]) begin
                if (k_xwa0[GA] == (gb == 1)) begin
                    if (|k_xwm[8 * GA +: 4]) begin wvb = 1'b1; wab = xwa_c[9:1]; nwb = nwb + 3'd1; end
                end else if (|k_xwm[8 * GA + 4 +: 4]) begin wvb = 1'b1; wab = xwa_c[9:1] + {8'd0, k_xwa0[GA]}; nwb = nwb + 3'd1; end
            end
            if (k_hsv[GA]) begin wvb = 1'b1; wab = hs_a[9:1]; nwb = nwb + 3'd1; end
        end
        assign wv[gb] = wvb; assign wa_f[9 * gb +: 9] = wab; assign wcb[gb] = nwb > 3'd1;
    end endgenerate
    wire [127:0] rq0, rq1;
    ot_sram_1r1w_512x128_m4_r2c2 u_b0 (.clk(clk), .r_ce_in(re_e), .r_addr_in(ra_e[9:1]), .rd_out(rq0),
        .w_ce_in(wv[0]), .w_addr_in(wa_f[8:0]), .wd_in(wd_f[127:0]), .w_mask_in(wm_f[127:0]),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
    ot_sram_1r1w_512x128_m4_r2c2 u_b1 (.clk(clk), .r_ce_in(re_o), .r_addr_in(ra_o[9:1]), .rd_out(rq1),
        .w_ce_in(wv[1]), .w_addr_in(wa_f[17:9]), .wd_in(wd_f[255:128]), .w_mask_in(wm_f[255:128]),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
    // macro output registers + the step that launched the read (2 edges: address edge, output register)
    reg [127:0] q0, q1; reg [3:0] dop; reg [7:0] dsi; reg dv;
    reg [3:0] dop1; reg [7:0] dsi1; reg dv1, dodd1, dswp1;
    reg [9:0] dmq1, dmq;                                      // NORMR: {n[1:0], a1[7:0]} riding with the read step
    reg xr1, xr2, xsw1;
    always @(posedge clk) begin q0 <= rq0; q1 <= rq1; xsw1 <= xra_c[0]; end
    always @(posedge clk or negedge rsv[15]) if (!rsv[15]) begin xr1 <= 1'b0; xr2 <= 1'b0; end else begin xr1 <= xrv_c; xr2 <= xr1; end
    always @(posedge clk or negedge rsv[15])
        if (!rsv[15]) begin dv1 <= 1'b0; dv <= 1'b0; end
        else begin dv1 <= srun; dv <= dv1; end
    always @(posedge clk) begin
        dop1 <= sop; dsi1 <= si; dodd1 <= re_o && !re_e; dswp1 <= swp; dmq1 <= {sqb, sa1[7:0]};
        dop <= dop1; dsi <= dsi1; dmq <= dmq1;
    end
    // S81-SLICE/VP SAFE 10-21: the bank-swap / odd-row / extension-swap selects drove 128..768 mux loads from one flop
    // (dswp -> hw_d / wl_d / lo_d, dodd -> cf / n_pre / yrow, xsw2 -> x_qd): kept copies per 32-bit word, same edge.
    (* keep *) reg [15:0] k_dswp; (* keep *) reg [15:0] k_xsw2; (* keep *) reg [7:0] k_dodd;
    always @(posedge clk) begin k_dswp <= {16{dswp1}}; k_dodd <= {8{dodd1}}; k_xsw2 <= {16{xsw1}}; end
    wire [127:0] qe, qo, q1r;                                 // rows a0 + 2i (first) / a0 + 2i + 1 (second); POST row
    wire [255:0] qoe = {qo, qe};
    genvar gq;
    generate for (gq = 0; gq < 8; gq = gq + 1) begin : g_qw
        assign qe[16 * gq +: 16] = k_dswp[gq] ? q1[16 * gq +: 16] : q0[16 * gq +: 16];
        assign qo[16 * gq +: 16] = k_dswp[8 + gq] ? q0[16 * gq +: 16] : q1[16 * gq +: 16];
        assign q1r[16 * gq +: 16] = k_dodd[gq] ? q1[16 * gq +: 16] : q0[16 * gq +: 16];
    end endgenerate

    // ---------------------------------------------------------------- hc_post: coefficients, operands, lanes
    // coefficient capture: POST steps 0..4 one-hot, decoded one edge early from the read-step pipe and kept per
    // (step, word) so each enable drives 32 flops (was dv / dop / dsi decode -> 640 enables).
    reg [31:0] cf [0:19];
    (* keep *) reg [39:0] k_cfe;                              // [4 s + i]: POST step s, word i
    always @(posedge clk)   // no reset: dv1 is reset, so k_cfe is 0 one edge into reset
        for (k = 0; k < 5; k = k + 1) k_cfe[8 * k +: 8] <= {8{dv1 && dop1 == OP_POST && dsi1 == k[7:0]}};
    always @(posedge clk)
        for (k = 0; k < 5; k = k + 1)
            for (i = 0; i < 8; i = i + 1)
                if (k_cfe[8 * k + i]) begin
`ifndef OT_S81SL_VP_MUT_POSTLAST
                    // step 0 = post row -> cf[16 + i]; steps 1..4 = comb row j = step - 1 -> cf[4 j + i]
                    if (k == 0) cf[16 + i/2][16*(i%2)+:16] <= q1r[16*i+:16]; else cf[4 * (k - 1) + i/2][16*(i%2)+:16] <= q1r[16*i+:16];
`else
                    cf[4 * k + i/2][16*(i%2)+:16] <= q1r[16*i+:16];   // bench mutant: the old order (comb rows a0..a0+3, post a0+4)
`endif
                end
    // POST step s >= 5 (cycle T): the y row read and the h half-row request (hr) leave together; the y row is at q in
    // T + 2 (macro + output register) and at yrow_d[2] in T + 5, the h half row at hqd_c in T + 5 (hr out flop, vn pin
    // flop, vn h macro edge, vn output flop, this leaf's pin flop): the lanes issue in T + 5.
    reg [127:0] yrow_d [0:2]; reg [3:0] ydv;
    always @(posedge clk or negedge rs_p) if (!rs_p) ydv <= 4'd0;
        else ydv <= {ydv[2:0], dv && dop == OP_POST && dsi >= 8'd5};
    always @(posedge clk) begin yrow_d[0] <= q1r; yrow_d[1] <= yrow_d[0]; yrow_d[2] <= yrow_d[1]; end
    // lanes: r0..r3 = h copies (BF16 -> FP32 pattern), y = y[e], c_j = comb[j][k] (word 4j + k), p = post[k]
    // SAFE 10-21: lr / ly are KEPT per lane (Yosys merged the 4 identical column copies with hs_d into one flop that
    // drove 4 lanes ~520 um apart + the bank write mux); lane_v is a kept copy per lane row (4) + one for the
    // write-back valid ring.
    // FALLBACK (define OT_S81SL_VP_RELAY, kit s81sl_vp_fb): one registered relay stage on the lane feed (lr / ly / v)
    // and one on the lane outputs (o / vo / fault), so no single-cycle wire spans the band -> lane grid (~700 um);
    // priced: POST write-back (hw_v / hw_d) +2 edges, nothing else moves.
`ifdef OT_S81SL_VP_RELAY
    localparam integer LRELAY = 1;
`else
    localparam integer LRELAY = 0;
`endif
    wire [15:0] lv, lf; wire [31:0] lo [0:15];
    wire [15:0] lv_s, lf_s; wire [31:0] lo_s [0:15];     // lane outputs as seen by the band (relayed in the fallback)
    (* keep *) reg [4:0] k_lanev;
    (* keep *) reg [31:0] lr [0:15][0:3]; (* keep *) reg [31:0] ly [0:15];
    genvar gl;
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_ln
        localparam integer KK = gl / 4, II = gl % 4;
`ifndef OT_S81SL_VP_HARD
        ot_dsrom_su_hcpost_lane_pr #(.ML(ML), .AL(AL)) u_l (.clk(clk), .rst_n(rs_p), .v(k_lanev[KK]),
`else
        // hardened cluster: the closed s81sl_hcpl view (its kit fixes ML 7 / AL 6; no #() on a hard child)
        ot_dsrom_su_hcpost_lane_pr u_l (.clk(clk), .rst_n(rs_p), .v(k_lanev[KK]),
`endif
            .r0(lr[gl][0]), .r1(lr[gl][1]), .r2(lr[gl][2]), .r3(lr[gl][3]), .y(ly[gl]),
            .c0(cf[KK]), .c1(cf[4 + KK]), .c2(cf[8 + KK]), .c3(cf[12 + KK]), .p(cf[16 + KK]),
            .vo(lv[gl]), .o(lo[gl]), .fault(lf[gl]));
    end endgenerate
    // the h half row of POST step s (requested with the y read: hq arrives aligned with ydv[2])
`ifdef OT_S81SL_VP_RELAY
    (* keep *) reg [31:0] lrA [0:15][0:3]; (* keep *) reg [31:0] lyA [0:15]; (* keep *) reg [4:0] k_lanevA;
    always @(posedge clk or negedge rs_p) if (!rs_p) begin k_lanevA <= 5'd0; k_lanev <= 5'd0; end
        else begin k_lanevA <= {5{ydv[2]}}; k_lanev <= k_lanevA; end
    always @(posedge clk)
        for (k = 0; k < 4; k = k + 1)
            for (i = 0; i < 4; i = i + 1) begin
                lrA[4 * k + i][0] <= {hqd_c[(4 * 0 + i) * 16 +: 16], 16'd0};
                lrA[4 * k + i][1] <= {hqd_c[(4 * 1 + i) * 16 +: 16], 16'd0};
                lrA[4 * k + i][2] <= {hqd_c[(4 * 2 + i) * 16 +: 16], 16'd0};
                lrA[4 * k + i][3] <= {hqd_c[(4 * 3 + i) * 16 +: 16], 16'd0};
                lyA[4 * k + i] <= yrow_d[2][32 * i +: 32];
                lr[4 * k + i][0] <= lrA[4 * k + i][0]; lr[4 * k + i][1] <= lrA[4 * k + i][1];
                lr[4 * k + i][2] <= lrA[4 * k + i][2]; lr[4 * k + i][3] <= lrA[4 * k + i][3];
                ly[4 * k + i] <= lyA[4 * k + i];
            end
`else
    always @(posedge clk or negedge rs_p) if (!rs_p) k_lanev <= 5'd0; else k_lanev <= {5{ydv[2]}};
    always @(posedge clk)
        for (k = 0; k < 4; k = k + 1)
            for (i = 0; i < 4; i = i + 1) begin
                lr[4 * k + i][0] <= {hqd_c[(4 * 0 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][1] <= {hqd_c[(4 * 1 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][2] <= {hqd_c[(4 * 2 + i) * 16 +: 16], 16'd0};
                lr[4 * k + i][3] <= {hqd_c[(4 * 3 + i) * 16 +: 16], 16'd0};
                ly[4 * k + i] <= yrow_d[2][32 * i +: 32];
            end
`endif
    genvar go;
    generate if (LRELAY != 0) begin : g_orl
        (* keep *) reg [15:0] lv_r, lf_r; (* keep *) reg [31:0] lo_r [0:15];
        always @(posedge clk) begin lv_r <= lv; lf_r <= lf; end   // no reset: the lanes hold vo / fault low in reset
        always @(posedge clk) for (k = 0; k < 16; k = k + 1) lo_r[k] <= lo[k];
        assign lv_s = lv_r; assign lf_s = lf_r;
        for (go = 0; go < 16; go = go + 1) begin : g_o assign lo_s[go] = lo_r[go]; end
    end else begin : g_onr
        assign lv_s = lv; assign lf_s = lf;
        for (go = 0; go < 16; go = go + 1) begin : g_o assign lo_s[go] = lo[go]; end
    end endgenerate
    // write-back valid: lane_v delayed by the lane latency HPL, as a RING (HPL - 1 entries, rotating pointer) + an
    // output register with kept copies (SAFE 10-21: was a 33-deep flop->flop shift line; same latency).  The write-back
    // half-row index is the position inside the contiguous 16-issue POST burst (bursts are >= 5 idle cycles apart:
    // POST steps 0..4 issue no lane op), so it is a counter over wvl instead of a 33-deep tag line (same value).
    localparam integer RD = HPL - 1 + LRELAY;          // + the output relay (fallback)
    localparam integer PW = (RD <= 2) ? 1 : $clog2(RD);
    reg [RD-1:0] wv_ring; (* keep *) reg [PW-1:0] wv_p;
    localparam integer NWG = (RD+7)/8;
    (* keep *) reg [PW-1:0] wv_wp [0:NWG-1];
    (* keep *) reg [NWG-1:0] ring_v;
    genvar gp;
    generate for(gp=0;gp<NWG;gp=gp+1) begin:g_ring_pointer
      always @(posedge clk or negedge rsv[17+gp])
        if(!rsv[17+gp]) wv_wp[gp] <= 0;
        else wv_wp[gp] <= wv_wp[gp] == RD-1 ? 0 : wv_wp[gp]+1'b1;
    end endgenerate
    always @(posedge clk or negedge rsv[22])
      if(!rsv[22]) ring_v <= 0;
`ifdef OT_S81SL_VP_RELAY
      else ring_v <= {NWG{k_lanevA[4]}};
`else
      else ring_v <= {NWG{ydv[2]}};
`endif
    localparam integer RH = RD / 2;                         // ring reset split over two relay leaves
    // Constant bit ownership keeps each async reset local. A variable vector
    // lvalue in two processes made the untouched half an async-load value.
    wire [NWG-1:0] ring_read;
    genvar rg;
    generate for(rg=0;rg<NWG;rg=rg+1) begin:g_ring_read
      reg v;
      integer rb;
      always @(*) begin
        v=1'b0;
        for(rb=0;rb<8;rb=rb+1)
          if(8*rg+rb < RD) v=v | (wv_ring[8*rg+rb] && wv_wp[rg] == 8*rg+rb);
      end
      assign ring_read[rg]=v;
    end endgenerate
    genvar gr;
    generate for (gr = 0; gr < RD; gr = gr + 1) begin : g_valid_ring
        if (gr < RH) begin : g_lo
            always @(posedge clk or negedge rs_r0)
                if (!rs_r0) wv_ring[gr] <= 1'b0;
                else if (wv_wp[gr/8] == gr) wv_ring[gr] <= ring_v[gr/8];
        end else begin : g_hi
            always @(posedge clk or negedge rs_r1)
                if (!rs_r1) wv_ring[gr] <= 1'b0;
                else if (wv_wp[gr/8] == gr) wv_ring[gr] <= ring_v[gr/8];
        end
    end endgenerate
    always @(posedge clk or negedge rs_r1)
        if (!rs_r1) wv_p <= {PW{1'b0}};
        else wv_p <= (wv_p == RD - 1) ? {PW{1'b0}} : wv_p + 1'b1;
    (* keep *) reg wvl; (* keep *) reg [16:0] k_wvl; reg [3:0] widx;
    always @(posedge clk or negedge rs_w)
        if (!rs_w) begin wvl <= 1'b0; k_wvl <= 17'd0; widx <= 4'd0; end
        else begin wvl <= |ring_read; k_wvl <= {17{|ring_read}}; widx <= wvl ? widx + 4'd1 : 4'd0; end

    // ---------------------------------------------------------------- vn seam (registered outputs)
    reg hrq_v; reg [3:0] hrq_i;                  // h read request this cycle (POST / HSTORE)
    always @(*) begin
        hrq_v = 1'b0; hrq_i = 4'd0;
        if (srun && sop == OP_POST && si >= 8'd5) begin hrq_v = 1'b1; hrq_i = si[3:0] - 4'd5; end
        if (srun && sop == OP_HSTORE) begin hrq_v = 1'b1; hrq_i = si[3:0]; end
    end
    // HSTORE: the half row returns from vn three edges after hr, plus this leaf's input flop.  The half-row index is
    // the position inside the contiguous 16-step HSTORE burst (counter over hsv_q[4]; was a 5-deep tag line).
    reg [4:0] hsv_q; reg [3:0] hs_cnt;
    always @(posedge clk or negedge rs_o) if (!rs_o) begin hsv_q <= 5'd0; hs_cnt <= 4'd0; end
        else begin hsv_q <= {hsv_q[3:0], srun && sop == OP_HSTORE}; hs_cnt <= hsv_q[4] ? hs_cnt + 4'd1 : 4'd0; end
    reg [9:0] hs_base;
    always @(posedge clk) if (cv_c && op == OP_HSTORE) hs_base <= a0;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) hs_v <= 1'b0; else hs_v <= hsv_q[4] && hqv_c;
    always @(posedge clk or negedge rsv[10])
        if(!rsv[10]) k_hsv <= 0; else k_hsv <= {NG{hsv_q[4] && hqv_c}};
    always @(posedge clk) begin hs_a <= hs_base + {hs_cnt, 1'b0}; k_hsa0 <= {NG{hs_base[0]}}; hs_d <= hqd_c; end

    // NORM / NORMR load of n_pre / m_*: decoded per 32-bit word from kept command copies (k_cv / k_op, landed at the
    // pin) and a registered NORMR-done flag with kept copies (was cv_c && op == NORM / dv && dop == NORMR -> 140 loads).
    (* keep *) reg nr_done; (* keep *) reg [8:0] k_nrd;
    always @(posedge clk or negedge rs_o2)
        if (!rs_o2) begin nr_done <= 1'b0; k_nrd <= 9'd0; end
        else begin nr_done <= dv1 && dop1 == OP_NORMR; k_nrd <= {9{dv1 && dop1 == OP_NORMR}}; end
    wire [8:0] k_norm;
    genvar gn;
    generate for (gn = 0; gn < 9; gn = gn + 1) begin : g_nm
        assign k_norm[gn] = k_cv[gn] && k_op[4 * gn +: 4] == OP_NORM;
    end endgenerate
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
        // hw_d lane field k on its own kept wvl copy (16 bits + the flow's pin-side copy): lane write-back, else the
        // HLOAD row pair
        for (k = 0; k < 16; k = k + 1)
            if (k_wvl[k]) hw_d[16 * k +: 16] <= lo_s[k][31:16];
            else hw_d[16 * k +: 16] <= qoe[16 * k +: 16];
        if (k_wvl[16]) begin hw_j <= widx[3:1]; hw_hf <= widx[0]; end
        else begin hw_j <= dsi[3:1]; hw_hf <= dsi[0]; end
        hr_j <= hrq_i[3:1]; hr_hf <= hrq_i[0];
        // 16-bit groups: the flow keeps a pin-side copy of every output flop, so a group select sees 2 x 16 loads
        for (k = 0; k < 8; k = k + 1)
            if (k_norm[k]) n_pre[16 * k +: 16] <= cd_c[32 + 16 * k +: 16];
            else if (k_nrd[k])
`ifndef OT_S81SL_VP_MUT_NORMIMM
                n_pre[16 * k +: 16] <= q1r[16 * k +: 16];
`else
                n_pre[16 * k +: 16] <= 16'd0;          // bench mutant: NORMR ignores the row (the old imm-only NORM)
`endif
        if (k_norm[8]) begin m_q <= cn[0]; m_b <= cn[1]; m_i <= a1[7:0]; end
        else if (k_nrd[8]) begin m_q <= dmq[8]; m_b <= dmq[9]; m_i <= dmq[7:0]; end
        wl_i <= dsi[2:0]; wl_d <= {qo, qe};
        lo_d <= {qo, qe};
        s_d <= cd_c;
        for (k = 0; k < 8; k = k + 1) begin
            x_qd[16 * k +: 16] <= k_xsw2[k] ? q1[16 * k +: 16] : q0[16 * k +: 16];
            x_qd[128 + 16 * k +: 16] <= k_xsw2[8 + k] ? q0[16 * k +: 16] : q1[16 * k +: 16];
        end
    end

    // ---------------------------------------------------------------- faults
    // SAFE 10-21 (c318a2024 worst path: lane fault pin -> 16-way OR + 9 sources -> fault, 989 ps): the sources are
    // registered where they arise (per-lane fault / valid flops beside the lanes, one local-source flop), reduced per
    // lane row, then folded.  The sticky fault is a diagnostic: it rises 2..3 edges later than before (no schedule use).
    (* keep *) reg [15:0] lf_q, lv_q;
    reg wvl_d, wvl_dd, lv0_d, src1, src2, lvbad, lfa;
    reg [3:0] lfr, lvor, lvand;
    always @(posedge clk or negedge rs_o2)
        if (!rs_o2) begin fault <= 1'b0; lf_q <= 16'd0; end
        else begin lf_q <= lf_s; fault <= fault | src2 | lfa | lvbad; end
    always @(posedge clk or negedge rsv[16]) if(!rsv[16]) lv_q <= 0; else lv_q <= lv_s;
    always @(posedge clk or negedge rs_o3)
        if (!rs_o3) begin
            wvl_d <= 1'b0; wvl_dd <= 1'b0; lv0_d <= 1'b0; src1 <= 1'b0; src2 <= 1'b0;
            lvbad <= 1'b0; lfa <= 1'b0; lfr <= 4'd0; lvor <= 4'd0; lvand <= 4'd0;
        end else begin
            wvl_d <= wvl;
            for (k = 0; k < 4; k = k + 1) begin lfr[k] <= |lf_q[4 * k +: 4]; lvor[k] <= |lv_q[4 * k +: 4]; lvand[k] <= &lv_q[4 * k +: 4]; end
            lv0_d <= lv_q[0]; wvl_dd <= wvl_d;
            lfa <= |lfr;
            lvbad <= (lv0_d != wvl_dd) || (|lvor != &lvand);
            src1 <= wcol | busy_hit | xrcol | (wvl && dv && dop == OP_HLOAD) | (hsv_q[4] && !hqv_c) | (ydv[2] && !hqv_c) |
                    (cv_c && op == OP_NORM && nr_done);
            src2 <= src1;
        end
endmodule
