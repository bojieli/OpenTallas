`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the S81 SU slab master rebuilt as a hierarchical slab.  Same pins
// and adapter as dsfd_sp_su (contract su_hc v2: c_cmd / c_done / inp / VM rd S_RD rows / VM wr S_WR rows / flt /
// online / fcode); inside, one control tile and NT hardened engine tiles on two registered chains:
//
//   pins -> NPO pin owners ot_s81_su_pin (stacked along the VM pin edge, each its slots' pin flops / registers) and the
//           control tile ot_s81_su_ctl (adapter, ot_s81_su_hctl job control / VM read issue / completion)
//       down spine (VM response rows + job announce, S_RD x 512 b): relay stations at the stops QN, KV, QB 0..NQB-1,
//         SW 0..NSW-1, SM 0..NSM-1 (one register a stop); each tile taps its stop
//       up spine (S_WR write row slots): a relay station a stop merges that tile's registered slots into its window
//   regional reset: pin -> relay -> ctl; a reset spine station a stop -> the tile's own two-flop relay
// Tiles carry one copy of each bus (no pass-through): pins = the down tap + its own write slots + status.
//
// Tile decomposition (production params): QN norm x 2 (128 lanes, D 1,280, its q gain set slice), KV norm x 2 (256
// lanes, the RoPE tail in the second, its kv gain set slice), QB x 4 (8 blocks each), SW x 8 (128 lanes each), SM x 8
// (2 heads x 16 lanes each); a norm's group sums of squares meet in its head tile over a registered rung (the golden's
// top tree level, left + right), the rstd returns the same way.
// The values are those of dsfd_sp_su (bit-exact gate tools/s81_suhc/su_gate.py --hier); added latency: the chain
// hops (a cycle a tile each way) and the norm tiles' ready round trip.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_su_h #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, OQ = 1024, MUT = 0, AMUT = 0,
    // lane-group tiles (production: QN 2 x 128 lanes, KV 2 x 256 lanes, QB 4 x 8 blocks, SW 8 x 128 lanes, SM 8 x 2
    // heads; pin owners 4 x (4 read + 4 write slots); every tile <= ~600 x 600 um)
    // QN (el1011-s81su-qn, spec v3): a tap (2 data halves) + NQE = QN_N / 8 norm engines + a reduce + NQQ = QN_N / 32
    // act-quant engines; spine stops: the tap, then the quant engines (the norm engines and the reduce hang off the tap)
    parameter integer NQE = QN_N / 8,
    parameter integer NQQ = QN_N / 32,
    // KV (el1011-s81su-kv, spec v3): a tap (4 data quarters) + NKE = KV_N / 8 norm engines (the last 8: RoPE) + 4 half
    // trees + a reduce + NKQ = KV_N / 32 act-quant engines; ONE spine stop (the tap's; the engines' slots merge there).
    // NKV = the exps-row writes of a KV vector (one a group of 8 blocks; the control tile's rows_out)
    parameter integer NKV = KV_N / 256,
    parameter integer NKE = KV_N / 8,
    parameter integer NKQ = KV_N / 32,
    // QB (el1011-s81su, spec v3): one tap + NPB engines (rate-matched to the down spine: NPB = S_RD / 2 blocks a pass)
    parameter integer NPB = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer ERL = (S_RD >= 16) ? 3 : 1,      // tap -> engine relays, equal depth on every engine (lockstep)
    parameter integer NSW = (SW_W >= 128) ? SW_W / 128 : 1,
    // SW (el1011-s81su-sw, spec v3): one tap + NSWQ act-quant engines (the QB master) on the spine, NSWQ * 2 * 16 / SLPE
    // ... lane engines off the tap (SLPE lanes each, rate-matched: a beat takes >= SLPE spine cycles); ERS equal-depth
    // relay stations tap -> lane engine (and lane faults back), <= 500 um a station over the ~3.2 x 2 mm SW region
    parameter integer NSWQ = (S_RD / 2 > 2) ? S_RD / 2 : 2,
    parameter integer ERS = (S_RD >= 16) ? 5 : 1,
    parameter integer NSM = (SM_H >= 2) ? SM_H / 2 : 1,
    parameter integer NPO = (S_RD >= 16 && S_WR >= 16) ? 4 : 1,
    // relay stations on every pin owner link (spine slices and control seams), the same depth on every link so the
    // slots of a cycle stay aligned: the pin owners stack ~1.9 mm along the VM pin edge (<= 500 um a station)
    parameter integer NRL = (S_RD >= 16) ? 4 : 1,
    // relay stations a spine stop / norm rung hop (adjacent tiles' centres ~620 um apart: 2 for <= 500 um a station)
    // and on the controller pulse nets c_cmd / c_done between the slab's N-face pins and the control tile (cck domain;
    // ~2.25 mm in the su_s composition: 5 stations for <= 500 um)
    parameter integer SRD = (S_RD >= 16) ? 2 : 1,
    // SM stop (spec v3): relay stations on every link between its masters (a stop ~1.3 x 1.0 mm: 2 for <= 500 um)
    parameter integer SRL = (S_RD >= 16) ? 2 : 1,
    parameter integer NRC = (S_RD >= 16) ? 5 : 1
) (
    input  wire                cck, crs,
    input  wire                sk, srs,
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode
);
    // SU_TILE_TOPS: per-tile-class output mutant, +tmut=K (0 = none)
    logic [7:0] tmut;
    initial begin tmut = 8'd0; void'($value$plusargs("tmut=%d", tmut)); $display("SU_TILE_TOPS tmut=%0d", tmut); end

    localparam integer NQB = 1 + NPB;                  // QB stops: the tap, then the engines
    localparam integer NQN = 1 + NQQ;                  // QN stops: the tap, then the quant engines
    localparam integer NSWS = 1 + NSWQ;                // SW stops: the tap, then the quant engines
    localparam integer NTL = NQN + 1 + NQB + NSWS + NSM;
    localparam integer SLPE = (SW_W / (8 * S_RD) > 16) ? 16 : (SW_W / (8 * S_RD) < 1) ? 1 : SW_W / (8 * S_RD);
    localparam integer SL = 2 * NSWQ, SNPS = (SW_W / 16) / SL, SEPR = 16 / SLPE, SNCH = SL * SEPR, SNE = SNCH * SNPS;
    // SW tap -> lane engines, lane chains -> quant engines
    wire [SL*512-1:0]    sw_d;
    wire [SNPS-1:0]      sw_gv, sw_uv;
    wire [11:0]          sw_t;
    wire [31:0]          sw_w, sw_lim;
    wire [13:0]          sw_ob;
    wire [SNCH-1:0]      sw_f;                         // chain-head lane faults, relayed into the tap
    wire [SNE-1:0]       sc_v, sc_f;                   // engine e = ch * SNPS + P: its chain output
    wire [SNE*16*SLPE-1:0] sc_d;
    wire [SNE*12-1:0]    sc_t;
    wire                 snxv [0:NSWQ-1];
    wire [255:0]         snxq [0:NSWQ-1];
    wire [9:0]           snxe [0:NSWQ-1];
    localparam integer QL = QN_N / 16;                 // QN tap positions (rows a vector)
    localparam integer DQ_ = 1280;                     // q width (the golden's DQ)
    // QB tap -> engines (positions 2b / 2b + 1 to engine b) and the engines' pair exchange
    wire [2*NPB-1:0]     qe_v;
    wire [2*NPB*512-1:0] qe_d;
    wire [2*NPB*12-1:0]  qe_t;
    wire [13:0]          qe_ob;
    wire                 qe_f4;
    wire                 nxv [0:NPB-1];
    wire [255:0]         nxq [0:NPB-1];
    wire [9:0]           nxe [0:NPB-1];
    localparam integer KR = S_RD / NPO, KW = S_WR / NPO;
    // spines: stop t = tile t.  Down: dn[t] is the relay register at stop t (dn[0]: the pin owners' row registers +
    // the control tile's job announce); the tile taps it and the next stop re-registers it.  Up: up[t] is the relay
    // register at stop t, = up[t + 1] with tile t's registered write slots merged into its window; up[0]: the wide
    // part to the pin owners (each its slice), the status to the control tile.
    wire                  dst [0:NTL];
    wire [3:0]            dkd [0:NTL];
    wire [1:0]            dgs [0:NTL];
    wire                  df4 [0:NTL];
    wire [7:0]            dji [0:NTL];
    wire [S_RD-1:0]       dv  [0:NTL];
    wire [S_RD*512-1:0]   dd  [0:NTL];
    wire [S_WR-1:0]       uv  [0:NTL];
    wire [S_WR*14-1:0]    ua  [0:NTL];
    wire [S_WR*16-1:0]    um  [0:NTL];
    wire [S_WR*512-1:0]   ud  [0:NTL];
    wire                  ufu [0:NTL], ufo [0:NTL], ual [0:NTL], ude [0:NTL], urd [0:NTL];
    wire [7:0]            urj [0:NTL];
    wire                  rst [0:NTL];
    assign uv[NTL] = 0; assign ua[NTL] = 0; assign um[NTL] = 0; assign ud[NTL] = 0;
    assign ufu[NTL] = 1'b0; assign ufo[NTL] = 1'b0; assign ual[NTL] = 1'b1; assign ude[NTL] = 1'b1;
    assign urd[NTL] = 1'b0; assign urj[NTL] = 8'd0;

    // ------------------------------------------------------------------ controller pulse nets: NRC relay stations (cck)
    wire        cc_v, cd_v;
    wire [83:0] cc_d;
    wire [7:0]  cd_t;
    ot_hdc_delay #(.W(2), .D(NRC), .RESET(1)) u_rcv (.clk(cck), .rst_n(crs), .d({c_cmd_v, cd_v}), .q({cc_v, c_done_v}));
    ot_hdc_delay #(.W(92), .D(NRC)) u_rcd (.clk(cck), .rst_n(crs), .d({c_cmd_d, cd_t}), .q({cc_d, c_done_tag}));

    // ------------------------------------------------------------------ control tile
    wire [S_RD-1:0]    c_rq_v;
    wire [S_RD*14-1:0] c_rq_row;
    wire [S_RD-1:0]    p_rv;
    wire [S_RD*30-1:0] p_rf;
    wire [S_WR-1:0]    p_uv;
    wire               rst_c;
    /* SU_TILE_TOPS: ot_s81_su_ctl u_ctl (slab line 145) */
if (((QN_N) == (256)) && ((KV_N) == (512)) && ((QB_NB) == (32)) && ((SW_W) == (1024)) && ((SM_H) == (16)) && ((SM_LPH) == (16)) && ((S_RD) == (16)) && ((S_WR) == (16)) && (((SW_W >= 64) ? SW_W / 64 : 1) == (16)) && ((QB_NB / 2) == (16)) && ((QN_N / 64) == (4)) && ((NKV) == (2)) && ((MUT) == (0)) && ((AMUT) == (0))) begin : g_tt0_u_ctl
wire [223:0] tt_mut;
dsfd_su_t_ctl u_ctl (.cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(cc_v), .c_cmd_d(cc_d), .c_done_v(cd_v), .c_done_tag(cd_t), .inp(inp), .flt(flt), .online(online), .fcode(fcode), .rst_o(rst_c), .p_rq_v(c_rq_v), .p_rq_row(tt_mut), .p_rv(p_rv), .p_rf(p_rf), .p_uv(p_uv), .dn_st(dst[0]), .dn_kind(dkd[0]), .dn_gsel(dgs[0]), .dn_fp4(df4[0]), .dn_jid(dji[0]), .up_fu(ufu[0]), .up_fo(ufo[0]), .up_alive(ual[0]), .up_den(ude[0]), .up_rdy(urd[0]), .up_rjid(urj[0]));
assign c_rq_row = tt_mut ^ ((tmut == 8'd1) ? ((223) >= 30 ? ((223) + 1)'(64'h4000_4000) : (223) >= 14 ? ((223) + 1)'(64'h4000) : ((223) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(cck) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.cck %m slab %0d pin %0d", $bits(cck), (0) + 1); tt_bad = 1; end if ($bits(crs) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.crs %m slab %0d pin %0d", $bits(crs), (0) + 1); tt_bad = 1; end if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.sk %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(srs) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.srs %m slab %0d pin %0d", $bits(srs), (0) + 1); tt_bad = 1; end if ($bits(cc_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.c_cmd_v %m slab %0d pin %0d", $bits(cc_v), (0) + 1); tt_bad = 1; end if ($bits(cc_d) != (83) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.c_cmd_d %m slab %0d pin %0d", $bits(cc_d), (83) + 1); tt_bad = 1; end if ($bits(cd_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.c_done_v %m slab %0d pin %0d", $bits(cd_v), (0) + 1); tt_bad = 1; end if ($bits(cd_t) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.c_done_tag %m slab %0d pin %0d", $bits(cd_t), (7) + 1); tt_bad = 1; end if ($bits(inp) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.inp %m slab %0d pin %0d", $bits(inp), (0) + 1); tt_bad = 1; end if ($bits(flt) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.flt %m slab %0d pin %0d", $bits(flt), (0) + 1); tt_bad = 1; end if ($bits(online) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.online %m slab %0d pin %0d", $bits(online), (0) + 1); tt_bad = 1; end if ($bits(fcode) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.fcode %m slab %0d pin %0d", $bits(fcode), (3) + 1); tt_bad = 1; end if ($bits(rst_c) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.rst_o %m slab %0d pin %0d", $bits(rst_c), (0) + 1); tt_bad = 1; end if ($bits(c_rq_v) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.p_rq_v %m slab %0d pin %0d", $bits(c_rq_v), (15) + 1); tt_bad = 1; end if ($bits(c_rq_row) != (223) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.p_rq_row %m slab %0d pin %0d", $bits(c_rq_row), (223) + 1); tt_bad = 1; end if ($bits(p_rv) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.p_rv %m slab %0d pin %0d", $bits(p_rv), (15) + 1); tt_bad = 1; end if ($bits(p_rf) != (479) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.p_rf %m slab %0d pin %0d", $bits(p_rf), (479) + 1); tt_bad = 1; end if ($bits(p_uv) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.p_uv %m slab %0d pin %0d", $bits(p_uv), (15) + 1); tt_bad = 1; end if ($bits(dst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.dn_st %m slab %0d pin %0d", $bits(dst[0]), (0) + 1); tt_bad = 1; end if ($bits(dkd[0]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.dn_kind %m slab %0d pin %0d", $bits(dkd[0]), (3) + 1); tt_bad = 1; end if ($bits(dgs[0]) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.dn_gsel %m slab %0d pin %0d", $bits(dgs[0]), (1) + 1); tt_bad = 1; end if ($bits(df4[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.dn_fp4 %m slab %0d pin %0d", $bits(df4[0]), (0) + 1); tt_bad = 1; end if ($bits(dji[0]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.dn_jid %m slab %0d pin %0d", $bits(dji[0]), (7) + 1); tt_bad = 1; end if ($bits(ufu[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.up_fu %m slab %0d pin %0d", $bits(ufu[0]), (0) + 1); tt_bad = 1; end if ($bits(ufo[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.up_fo %m slab %0d pin %0d", $bits(ufo[0]), (0) + 1); tt_bad = 1; end if ($bits(ual[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.up_alive %m slab %0d pin %0d", $bits(ual[0]), (0) + 1); tt_bad = 1; end if ($bits(ude[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.up_den %m slab %0d pin %0d", $bits(ude[0]), (0) + 1); tt_bad = 1; end if ($bits(urd[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.up_rdy %m slab %0d pin %0d", $bits(urd[0]), (0) + 1); tt_bad = 1; end if ($bits(urj[0]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_ctl.up_rjid %m slab %0d pin %0d", $bits(urj[0]), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_ctl initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_ctl u_ctl line 145 %m"); $display("  QN_N = %0d", (QN_N)); $display("  KV_N = %0d", (KV_N)); $display("  QB_NB = %0d", (QB_NB)); $display("  SW_W = %0d", (SW_W)); $display("  SM_H = %0d", (SM_H)); $display("  SM_LPH = %0d", (SM_LPH)); $display("  S_RD = %0d", (S_RD)); $display("  S_WR = %0d", (S_WR)); $display("  NSW = %0d", ((SW_W >= 64) ? SW_W / 64 : 1)); $display("  NQB = %0d", (QB_NB / 2)); $display("  NQN = %0d", (QN_N / 64)); $display("  NKV = %0d", (NKV)); $display("  MUT = %0d", (MUT)); $display("  AMUT = %0d", (AMUT)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
    // reset spine head
    reg rs0;
    always @(posedge sk or negedge rst_c) if (!rst_c) rs0 <= 1'b0; else rs0 <= 1'b1;
    assign rst[0] = rs0;

    // ------------------------------------------------------------------ pin owners (+ NRL relay stations every link)
    genvar o;
    generate for (o = 0; o < NPO; o = o + 1) begin : g_po
        wire [KR-1:0]    rv, dnv;  wire [KR*30-1:0] rf;   wire [KW-1:0] uvo;
        wire [KR*512-1:0] dnd;
        wire [KR-1:0]    rq_v_r;  wire [KR*14-1:0] rq_row_r;
        wire [KW-1:0]    upv;     wire [KW*14-1:0] upa;   wire [KW*16-1:0] upm;  wire [KW*512-1:0] upd;
        // control-signal relays (reset), data relays (no reset)
        ot_hdc_delay #(.W(KR + KR + KW + KR + KW), .D(NRL), .RESET(1)) u_rlc (.clk(sk), .rst_n(rs0),
            .d({c_rq_v[KR * o +: KR], rv, uvo, dnv, uv[0][KW * o +: KW]}),
            .q({rq_v_r, p_rv[KR * o +: KR], p_uv[KW * o +: KW], dv[0][KR * o +: KR], upv}));
        ot_hdc_delay #(.W(KR * 14 + KR * 30 + KR * 512 + KW * (14 + 16 + 512)), .D(NRL)) u_rld (.clk(sk), .rst_n(rs0),
            .d({c_rq_row[KR * 14 * o +: KR * 14], rf, dnd, ua[0][KW * 14 * o +: KW * 14], um[0][KW * 16 * o +: KW * 16],
                ud[0][KW * 512 * o +: KW * 512]}),
            .q({rq_row_r, p_rf[KR * 30 * o +: KR * 30], dd[0][KR * 512 * o +: KR * 512], upa, upm, upd}));
        /* SU_TILE_TOPS: ot_s81_su_pin u_po (slab line 172) */
if (((KR) == (4)) && ((KW) == (4))) begin : g_tt0_u_po
wire [2047:0] tt_mut;
dsfd_su_t_pin u_po (.ck(sk), .rst(rs0), .rq_v(rq_v[KR * o +: KR]), .rq_row(rq_row[KR * 14 * o +: KR * 14]), .rs_v(rs_v[KR * o +: KR]), .rs_d(rs_d[KR * 512 * o +: KR * 512]), .wq_v(wq_v[KW * o +: KW]), .wq_row(wq_row[KW * 14 * o +: KW * 14]), .wq_mask(wq_mask[KW * 16 * o +: KW * 16]), .wq_d(tt_mut), .dn_v(dnv), .dn_d(dnd), .up_v(upv), .up_a(upa), .up_m(upm), .up_d(upd), .c_rq_v(rq_v_r), .c_rq_row(rq_row_r), .c_rv(rv), .c_rf(rf), .c_uv(uvo));
assign wq_d[KW * 512 * o +: KW * 512] = tt_mut ^ ((tmut == 8'd7) ? ((2047) >= 30 ? ((2047) + 1)'(64'h4000_4000) : (2047) >= 14 ? ((2047) + 1)'(64'h4000) : ((2047) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rs0) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.rst %m slab %0d pin %0d", $bits(rs0), (0) + 1); tt_bad = 1; end if ($bits(rq_v[KR * o +: KR]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.rq_v %m slab %0d pin %0d", $bits(rq_v[KR * o +: KR]), (3) + 1); tt_bad = 1; end if ($bits(rq_row[KR * 14 * o +: KR * 14]) != (55) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.rq_row %m slab %0d pin %0d", $bits(rq_row[KR * 14 * o +: KR * 14]), (55) + 1); tt_bad = 1; end if ($bits(rs_v[KR * o +: KR]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.rs_v %m slab %0d pin %0d", $bits(rs_v[KR * o +: KR]), (3) + 1); tt_bad = 1; end if ($bits(rs_d[KR * 512 * o +: KR * 512]) != (2047) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.rs_d %m slab %0d pin %0d", $bits(rs_d[KR * 512 * o +: KR * 512]), (2047) + 1); tt_bad = 1; end if ($bits(wq_v[KW * o +: KW]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.wq_v %m slab %0d pin %0d", $bits(wq_v[KW * o +: KW]), (3) + 1); tt_bad = 1; end if ($bits(wq_row[KW * 14 * o +: KW * 14]) != (55) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.wq_row %m slab %0d pin %0d", $bits(wq_row[KW * 14 * o +: KW * 14]), (55) + 1); tt_bad = 1; end if ($bits(wq_mask[KW * 16 * o +: KW * 16]) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.wq_mask %m slab %0d pin %0d", $bits(wq_mask[KW * 16 * o +: KW * 16]), (63) + 1); tt_bad = 1; end if ($bits(wq_d[KW * 512 * o +: KW * 512]) != (2047) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.wq_d %m slab %0d pin %0d", $bits(wq_d[KW * 512 * o +: KW * 512]), (2047) + 1); tt_bad = 1; end if ($bits(dnv) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.dn_v %m slab %0d pin %0d", $bits(dnv), (3) + 1); tt_bad = 1; end if ($bits(dnd) != (2047) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.dn_d %m slab %0d pin %0d", $bits(dnd), (2047) + 1); tt_bad = 1; end if ($bits(upv) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.up_v %m slab %0d pin %0d", $bits(upv), (3) + 1); tt_bad = 1; end if ($bits(upa) != (55) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.up_a %m slab %0d pin %0d", $bits(upa), (55) + 1); tt_bad = 1; end if ($bits(upm) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.up_m %m slab %0d pin %0d", $bits(upm), (63) + 1); tt_bad = 1; end if ($bits(upd) != (2047) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.up_d %m slab %0d pin %0d", $bits(upd), (2047) + 1); tt_bad = 1; end if ($bits(rq_v_r) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.c_rq_v %m slab %0d pin %0d", $bits(rq_v_r), (3) + 1); tt_bad = 1; end if ($bits(rq_row_r) != (55) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.c_rq_row %m slab %0d pin %0d", $bits(rq_row_r), (55) + 1); tt_bad = 1; end if ($bits(rv) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.c_rv %m slab %0d pin %0d", $bits(rv), (3) + 1); tt_bad = 1; end if ($bits(rf) != (119) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.c_rf %m slab %0d pin %0d", $bits(rf), (119) + 1); tt_bad = 1; end if ($bits(uvo) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_pin.c_uv %m slab %0d pin %0d", $bits(uvo), (3) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_po initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_pin u_po line 172 %m"); $display("  KR = %0d", (KR)); $display("  KW = %0d", (KW)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
    end endgenerate

    // ------------------------------------------------------------------ QN: norm engines + reduce (off the spine)
    wire [QL-1:0]       qt_v [0:1];
    wire [QL*256-1:0]   qt_d [0:1];
    wire [QL*8-1:0]     qt_t [0:1];
    wire                qt_gq, qt_go;
    wire [1:0]          qt_gr, qt_gw;
    wire [13:0]         qt_ob;
    wire [31:0]         qt_eps;
    wire [NQE:0]        qn_f;                          // engine faults + the reduce's (relayed into the tap)
    wire [NQE-1:0]      qy_v;
    wire [NQE*8-1:0]    qy_i;
    wire [NQE*256-1:0]  qy_d;
    wire [NQE-1:0]      qp_v, qp_p;
    wire [NQE*32-1:0]   qp_d;
    wire                qr_v;
    wire [31:0]         qr_d;
    wire                qnxv [0:NQQ-1];
    wire [255:0]        qnxq [0:NQQ-1];
    wire [9:0]          qnxe [0:NQQ-1];
    genvar qe;
    generate for (qe = 0; qe < NQE; qe = qe + 1) begin : g_qne
        // engine qe = position qe / 2, data half qe % 2; equal-depth relays tap -> engine, engine -> reduce, rstd back
        wire iv, igq, ef, pv, pvr; wire [255:0] ix; wire [7:0] it, pi; wire [1:0] igr, igw; wire [31:0] pd, pdr;
        wire rv; wire [31:0] rd;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_iv (.clk(sk), .rst_n(rst[0]), .d(qt_v[qe % 2][qe / 2]), .q(iv));
        ot_hdc_delay #(.W(256 + 8 + 5), .D(ERL)) u_id (.clk(sk), .rst_n(rst[0]),
            .d({qt_d[qe % 2][256 * (qe / 2) +: 256], qt_t[qe % 2][8 * (qe / 2) +: 8], qt_gq, qt_gr, qt_gw}),
            .q({ix, it, igq, igr, igw}));
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(qr_v), .q(rv));
        ot_hdc_delay #(.W(32), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d(qr_d), .q(rd));
        /* SU_TILE_TOPS: ot_s81_su_qne u_qne (slab line 211) */
if (((DQ_ / QN_N) == (5)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt0_u_qne
wire [255:0] tt_mut;
dsfd_su_t_qne u_qne (.ck(sk), .rst(rst[0]), .i_v(iv), .i_x(ix), .i_t(it), .i_gq(igq), .i_gr(igr), .i_gw(igw), .r_v(rv), .r_d(rd), .p_v(pv), .p_i(pi), .p_d(pd), .y_v(qy_v[qe]), .y_i(qy_i[8 * qe +: 8]), .y(tt_mut), .o_f(ef));
assign qy_d[256 * qe +: 256] = tt_mut ^ ((tmut == 8'd10) ? ((255) >= 30 ? ((255) + 1)'(64'h4000_4000) : (255) >= 14 ? ((255) + 1)'(64'h4000) : ((255) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(iv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.i_v %m slab %0d pin %0d", $bits(iv), (0) + 1); tt_bad = 1; end if ($bits(ix) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.i_x %m slab %0d pin %0d", $bits(ix), (255) + 1); tt_bad = 1; end if ($bits(it) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.i_t %m slab %0d pin %0d", $bits(it), (7) + 1); tt_bad = 1; end if ($bits(igq) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.i_gq %m slab %0d pin %0d", $bits(igq), (0) + 1); tt_bad = 1; end if ($bits(igr) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.i_gr %m slab %0d pin %0d", $bits(igr), (1) + 1); tt_bad = 1; end if ($bits(igw) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.i_gw %m slab %0d pin %0d", $bits(igw), (1) + 1); tt_bad = 1; end if ($bits(rv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.r_v %m slab %0d pin %0d", $bits(rv), (0) + 1); tt_bad = 1; end if ($bits(rd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.r_d %m slab %0d pin %0d", $bits(rd), (31) + 1); tt_bad = 1; end if ($bits(pv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.p_v %m slab %0d pin %0d", $bits(pv), (0) + 1); tt_bad = 1; end if ($bits(pi) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.p_i %m slab %0d pin %0d", $bits(pi), (7) + 1); tt_bad = 1; end if ($bits(pd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.p_d %m slab %0d pin %0d", $bits(pd), (31) + 1); tt_bad = 1; end if ($bits(qy_v[qe]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.y_v %m slab %0d pin %0d", $bits(qy_v[qe]), (0) + 1); tt_bad = 1; end if ($bits(qy_i[8 * qe +: 8]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.y_i %m slab %0d pin %0d", $bits(qy_i[8 * qe +: 8]), (7) + 1); tt_bad = 1; end if ($bits(qy_d[256 * qe +: 256]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.y %m slab %0d pin %0d", $bits(qy_d[256 * qe +: 256]), (255) + 1); tt_bad = 1; end if ($bits(ef) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qne.o_f %m slab %0d pin %0d", $bits(ef), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qne initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qne u_qne line 211 %m"); $display("  NV = %0d", (DQ_ / QN_N)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        ot_hdc_delay #(.W(2), .D(ERL), .RESET(1)) u_pv (.clk(sk), .rst_n(rst[0]), .d({pv, ef}), .q({qp_v[qe], qn_f[qe]}));
        ot_hdc_delay #(.W(33), .D(ERL)) u_pd (.clk(sk), .rst_n(rst[0]), .d({pi[0], pd}), .q({qp_p[qe], qp_d[32 * qe +: 32]}));
    end endgenerate
    generate if (1) begin : g_qnr
        wire go, rf; wire [31:0] eps;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_gv (.clk(sk), .rst_n(rst[0]), .d(qt_go), .q(go));
        ot_hdc_delay #(.W(32), .D(ERL)) u_gd (.clk(sk), .rst_n(rst[0]), .d(qt_eps), .q(eps));
        // two half trees (engines 0..NQE/2-1, NQE/2..NQE-1) -> the reduce (NE 2: the golden tree's top add, vector
        // levels, / D, + eps, rsqrt); each half is its own hardened tile (<= 15k sinks)
        wire [1:0] hv, hp, hf; wire [63:0] hd;
        genvar hh;
        for (hh = 0; hh < 2; hh = hh + 1) begin : g_qnh
            /* SU_TILE_TOPS: ot_s81_su_qnh u_qnh (slab line 226) */
if (((NQE / 2) == (16)) && ((LA) == (4))) begin : g_tt0_u_qnh
wire [31:0] tt_mut;
dsfd_su_t_qnh u_qnh (.ck(sk), .rst(rst[0]), .i_go(go), .p_v(qp_v[hh * (NQE / 2) +: NQE / 2]), .p_p(qp_p[hh * (NQE / 2) +: NQE / 2]), .p_d(qp_d[hh * 16 * NQE +: 16 * NQE]), .s_v(hv[hh]), .s_p(hp[hh]), .s_d(tt_mut), .o_f(hf[hh]));
assign hd[32 * hh +: 32] = tt_mut ^ ((tmut == 8'd11) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(go) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.i_go %m slab %0d pin %0d", $bits(go), (0) + 1); tt_bad = 1; end if ($bits(qp_v[hh * (NQE / 2) +: NQE / 2]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.p_v %m slab %0d pin %0d", $bits(qp_v[hh * (NQE / 2) +: NQE / 2]), (15) + 1); tt_bad = 1; end if ($bits(qp_p[hh * (NQE / 2) +: NQE / 2]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.p_p %m slab %0d pin %0d", $bits(qp_p[hh * (NQE / 2) +: NQE / 2]), (15) + 1); tt_bad = 1; end if ($bits(qp_d[hh * 16 * NQE +: 16 * NQE]) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.p_d %m slab %0d pin %0d", $bits(qp_d[hh * 16 * NQE +: 16 * NQE]), (511) + 1); tt_bad = 1; end if ($bits(hv[hh]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.s_v %m slab %0d pin %0d", $bits(hv[hh]), (0) + 1); tt_bad = 1; end if ($bits(hp[hh]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.s_p %m slab %0d pin %0d", $bits(hp[hh]), (0) + 1); tt_bad = 1; end if ($bits(hd[32 * hh +: 32]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.s_d %m slab %0d pin %0d", $bits(hd[32 * hh +: 32]), (31) + 1); tt_bad = 1; end if ($bits(hf[hh]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.o_f %m slab %0d pin %0d", $bits(hf[hh]), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qnh initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qnh u_qnh line 226 %m"); $display("  NE = %0d", (NQE / 2)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        end
        /* SU_TILE_TOPS: ot_s81_su_qnr u_qnr (slab line 231) */
if (((2) == (2)) && ((DQ_ / QN_N) == (5)) && ((DQ_) == (1280)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt0_u_qnr
wire [31:0] tt_mut;
dsfd_su_t_qnr u_qnr (.ck(sk), .rst(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(qr_v), .r_d(tt_mut), .o_f(rf));
assign qr_d = tt_mut ^ ((tmut == 8'd13) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(go) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.i_go %m slab %0d pin %0d", $bits(go), (0) + 1); tt_bad = 1; end if ($bits(eps) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.i_eps %m slab %0d pin %0d", $bits(eps), (31) + 1); tt_bad = 1; end if ($bits(hv) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_v %m slab %0d pin %0d", $bits(hv), (1) + 1); tt_bad = 1; end if ($bits(hp) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_p %m slab %0d pin %0d", $bits(hp), (1) + 1); tt_bad = 1; end if ($bits(hd) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_d %m slab %0d pin %0d", $bits(hd), (63) + 1); tt_bad = 1; end if ($bits(hf) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_f %m slab %0d pin %0d", $bits(hf), (1) + 1); tt_bad = 1; end if ($bits(qr_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.r_v %m slab %0d pin %0d", $bits(qr_v), (0) + 1); tt_bad = 1; end if ($bits(qr_d) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.r_d %m slab %0d pin %0d", $bits(qr_d), (31) + 1); tt_bad = 1; end if ($bits(rf) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.o_f %m slab %0d pin %0d", $bits(rf), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else if (((2) == (4)) && ((DQ_ / QN_N) == (1)) && ((DQ_) == (512)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt1_u_qnr
wire [31:0] tt_mut;
dsfd_su_t_kvr u_qnr (.ck(sk), .rst(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(qr_v), .r_d(tt_mut), .o_f(rf));
assign qr_d = tt_mut ^ ((tmut == 8'd5) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(go) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.i_go %m slab %0d pin %0d", $bits(go), (0) + 1); tt_bad = 1; end if ($bits(eps) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.i_eps %m slab %0d pin %0d", $bits(eps), (31) + 1); tt_bad = 1; end if ($bits(hv) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_v %m slab %0d pin %0d", $bits(hv), (3) + 1); tt_bad = 1; end if ($bits(hp) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_p %m slab %0d pin %0d", $bits(hp), (3) + 1); tt_bad = 1; end if ($bits(hd) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_d %m slab %0d pin %0d", $bits(hd), (127) + 1); tt_bad = 1; end if ($bits(hf) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_f %m slab %0d pin %0d", $bits(hf), (3) + 1); tt_bad = 1; end if ($bits(qr_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.r_v %m slab %0d pin %0d", $bits(qr_v), (0) + 1); tt_bad = 1; end if ($bits(qr_d) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.r_d %m slab %0d pin %0d", $bits(qr_d), (31) + 1); tt_bad = 1; end if ($bits(rf) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.o_f %m slab %0d pin %0d", $bits(rf), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qnr initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qnr u_qnr line 231 %m"); $display("  NE = %0d", (2)); $display("  NV = %0d", (DQ_ / QN_N)); $display("  D = %0d", (DQ_)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rf (.clk(sk), .rst_n(rst[0]), .d(rf), .q(qn_f[NQE]));
    end endgenerate


    // ------------------------------------------------------------------ KV: norm engines + reduce + quant (off the spine)
    localparam integer KL = KV_N / 16;                 // KV tap positions (rows a vector)
    localparam integer NRP = 64 / 8;                   // RoPE engines (RD 64)
    wire [KL-1:0]       kt_v  [0:3];
    wire [KL*128-1:0]   kt_d  [0:3];
    wire [511:0]        kt_cs [0:3];
    wire                kt_gk, kt_go;
    wire [1:0]          kt_gr, kt_gw;
    wire [13:0]         kt_ob;
    wire [31:0]         kt_eps;
    wire [NKE:0]        kv_f;
    wire [NKE-1:0]      ky_v, kp_v;
    wire [NKE*256-1:0]  ky_d;
    wire [NKE*32-1:0]   kp_d;
    wire                kr_v;
    wire [31:0]         kr_d;
    wire [NKQ-1:0]      kq_v, kq_fu, kq_fo, kq_al, kq_de, kq_ev;
    wire [NKQ*14-1:0]   kq_a;
    wire [NKQ*16-1:0]   kq_m;
    wire [NKQ*512-1:0]  kq_d;
    wire [NKQ*10-1:0]   kq_ee;
    wire                kqxv [0:NKQ-1];
    wire [255:0]        kqxq [0:NKQ-1];
    genvar ke;
    generate for (ke = 0; ke < NKE; ke = ke + 1) begin : g_kve
        // engine ke = position ke / 2, data half ke % 2 = quarters 2 (ke % 2), 2 (ke % 2) + 1; equal-depth relays
        localparam integer KP = ke / 2, KH = ke % 2;
        wire iv, igk, ef, pv, yv; wire [255:0] ix, yd; wire [1:0] igr, igw; wire [31:0] pd; wire rv; wire [31:0] rd;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_iv (.clk(sk), .rst_n(rst[0]), .d(kt_v[2 * KH][KP]), .q(iv));
        ot_hdc_delay #(.W(256 + 5), .D(ERL)) u_id (.clk(sk), .rst_n(rst[0]),
            .d({kt_d[2 * KH + 1][128 * KP +: 128], kt_d[2 * KH][128 * KP +: 128], kt_gk, kt_gr, kt_gw}),
            .q({ix, igk, igr, igw}));
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(kr_v), .q(rv));
        ot_hdc_delay #(.W(32), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d(kr_d), .q(rd));
        if (ke >= NKE - NRP) begin : g_rp
            // RoPE engine k: cos / sin of lane pairs 4 k .. 4 k + 3 = quarter k % 4 of param rows 1 / 2 (cos), 3 / 4 (sin)
            localparam integer K = ke - (NKE - NRP);
            wire [127:0] cc, sn;
            ot_hdc_delay #(.W(256), .D(ERL)) u_cs (.clk(sk), .rst_n(rst[0]),
                .d({kt_cs[K % 4][(K < 4 ? 256 : 384) +: 128], kt_cs[K % 4][(K < 4 ? 0 : 128) +: 128]}), .q({sn, cc}));
            /* SU_TILE_TOPS: ot_s81_su_kve u_kve (slab line 278) */
if (((1) == (0)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt0_u_kve
wire [255:0] tt_mut;
dsfd_su_t_kve u_kve (.ck(sk), .rst(rst[0]), .i_v(iv), .i_x(ix), .i_gk(igk), .i_gr(igr), .i_gw(igw), .r_v(rv), .r_d(rd), .p_v(pv), .p_d(pd), .y_v(yv), .y(tt_mut), .o_f(ef));
always @(cc) if ($time > 0 && (cc) != (128'd0)) begin $display("SU_TILE_TOPS_TIE dsfd_su_t_kve core port i_cos %m: the slab drives a value the routed top ties to 128'd0"); $fatal(1, "SU_TILE_TOPS tie"); end
always @(sn) if ($time > 0 && (sn) != (128'd0)) begin $display("SU_TILE_TOPS_TIE dsfd_su_t_kve core port i_sin %m: the slab drives a value the routed top ties to 128'd0"); $fatal(1, "SU_TILE_TOPS tie"); end
assign yd = tt_mut ^ ((tmut == 8'd2) ? ((255) >= 30 ? ((255) + 1)'(64'h4000_4000) : (255) >= 14 ? ((255) + 1)'(64'h4000) : ((255) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(iv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_v %m slab %0d pin %0d", $bits(iv), (0) + 1); tt_bad = 1; end if ($bits(ix) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_x %m slab %0d pin %0d", $bits(ix), (255) + 1); tt_bad = 1; end if ($bits(igk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_gk %m slab %0d pin %0d", $bits(igk), (0) + 1); tt_bad = 1; end if ($bits(igr) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_gr %m slab %0d pin %0d", $bits(igr), (1) + 1); tt_bad = 1; end if ($bits(igw) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_gw %m slab %0d pin %0d", $bits(igw), (1) + 1); tt_bad = 1; end if ($bits(rv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.r_v %m slab %0d pin %0d", $bits(rv), (0) + 1); tt_bad = 1; end if ($bits(rd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.r_d %m slab %0d pin %0d", $bits(rd), (31) + 1); tt_bad = 1; end if ($bits(pv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.p_v %m slab %0d pin %0d", $bits(pv), (0) + 1); tt_bad = 1; end if ($bits(pd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.p_d %m slab %0d pin %0d", $bits(pd), (31) + 1); tt_bad = 1; end if ($bits(yv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.y_v %m slab %0d pin %0d", $bits(yv), (0) + 1); tt_bad = 1; end if ($bits(yd) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.y %m slab %0d pin %0d", $bits(yd), (255) + 1); tt_bad = 1; end if ($bits(ef) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.o_f %m slab %0d pin %0d", $bits(ef), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else if (((1) == (1)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt1_u_kve
wire [255:0] tt_mut;
dsfd_su_t_kvp u_kve (.ck(sk), .rst(rst[0]), .i_v(iv), .i_x(ix), .i_gk(igk), .i_gr(igr), .i_gw(igw), .i_cos(cc), .i_sin(sn), .r_v(rv), .r_d(rd), .p_v(pv), .p_d(pd), .y_v(yv), .y(tt_mut), .o_f(ef));
assign yd = tt_mut ^ ((tmut == 8'd3) ? ((255) >= 30 ? ((255) + 1)'(64'h4000_4000) : (255) >= 14 ? ((255) + 1)'(64'h4000) : ((255) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(iv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_v %m slab %0d pin %0d", $bits(iv), (0) + 1); tt_bad = 1; end if ($bits(ix) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_x %m slab %0d pin %0d", $bits(ix), (255) + 1); tt_bad = 1; end if ($bits(igk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_gk %m slab %0d pin %0d", $bits(igk), (0) + 1); tt_bad = 1; end if ($bits(igr) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_gr %m slab %0d pin %0d", $bits(igr), (1) + 1); tt_bad = 1; end if ($bits(igw) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_gw %m slab %0d pin %0d", $bits(igw), (1) + 1); tt_bad = 1; end if ($bits(cc) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_cos %m slab %0d pin %0d", $bits(cc), (127) + 1); tt_bad = 1; end if ($bits(sn) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_sin %m slab %0d pin %0d", $bits(sn), (127) + 1); tt_bad = 1; end if ($bits(rv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.r_v %m slab %0d pin %0d", $bits(rv), (0) + 1); tt_bad = 1; end if ($bits(rd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.r_d %m slab %0d pin %0d", $bits(rd), (31) + 1); tt_bad = 1; end if ($bits(pv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.p_v %m slab %0d pin %0d", $bits(pv), (0) + 1); tt_bad = 1; end if ($bits(pd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.p_d %m slab %0d pin %0d", $bits(pd), (31) + 1); tt_bad = 1; end if ($bits(yv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.y_v %m slab %0d pin %0d", $bits(yv), (0) + 1); tt_bad = 1; end if ($bits(yd) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.y %m slab %0d pin %0d", $bits(yd), (255) + 1); tt_bad = 1; end if ($bits(ef) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.o_f %m slab %0d pin %0d", $bits(ef), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_kve initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_kve u_kve line 278 %m"); $display("  RP = %0d", (1)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        end else begin : g_np
            /* SU_TILE_TOPS: ot_s81_su_kve u_kve (slab line 282) */
if (((0) == (0)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt0_u_kve
wire [255:0] tt_mut;
dsfd_su_t_kve u_kve (.ck(sk), .rst(rst[0]), .i_v(iv), .i_x(ix), .i_gk(igk), .i_gr(igr), .i_gw(igw), .r_v(rv), .r_d(rd), .p_v(pv), .p_d(pd), .y_v(yv), .y(tt_mut), .o_f(ef));
always @(128'd0) if ($time > 0 && (128'd0) != (128'd0)) begin $display("SU_TILE_TOPS_TIE dsfd_su_t_kve core port i_cos %m: the slab drives a value the routed top ties to 128'd0"); $fatal(1, "SU_TILE_TOPS tie"); end
always @(128'd0) if ($time > 0 && (128'd0) != (128'd0)) begin $display("SU_TILE_TOPS_TIE dsfd_su_t_kve core port i_sin %m: the slab drives a value the routed top ties to 128'd0"); $fatal(1, "SU_TILE_TOPS tie"); end
assign yd = tt_mut ^ ((tmut == 8'd2) ? ((255) >= 30 ? ((255) + 1)'(64'h4000_4000) : (255) >= 14 ? ((255) + 1)'(64'h4000) : ((255) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(iv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_v %m slab %0d pin %0d", $bits(iv), (0) + 1); tt_bad = 1; end if ($bits(ix) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_x %m slab %0d pin %0d", $bits(ix), (255) + 1); tt_bad = 1; end if ($bits(igk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_gk %m slab %0d pin %0d", $bits(igk), (0) + 1); tt_bad = 1; end if ($bits(igr) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_gr %m slab %0d pin %0d", $bits(igr), (1) + 1); tt_bad = 1; end if ($bits(igw) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.i_gw %m slab %0d pin %0d", $bits(igw), (1) + 1); tt_bad = 1; end if ($bits(rv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.r_v %m slab %0d pin %0d", $bits(rv), (0) + 1); tt_bad = 1; end if ($bits(rd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.r_d %m slab %0d pin %0d", $bits(rd), (31) + 1); tt_bad = 1; end if ($bits(pv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.p_v %m slab %0d pin %0d", $bits(pv), (0) + 1); tt_bad = 1; end if ($bits(pd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.p_d %m slab %0d pin %0d", $bits(pd), (31) + 1); tt_bad = 1; end if ($bits(yv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.y_v %m slab %0d pin %0d", $bits(yv), (0) + 1); tt_bad = 1; end if ($bits(yd) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.y %m slab %0d pin %0d", $bits(yd), (255) + 1); tt_bad = 1; end if ($bits(ef) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kve.o_f %m slab %0d pin %0d", $bits(ef), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else if (((0) == (1)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt1_u_kve
wire [255:0] tt_mut;
dsfd_su_t_kvp u_kve (.ck(sk), .rst(rst[0]), .i_v(iv), .i_x(ix), .i_gk(igk), .i_gr(igr), .i_gw(igw), .i_cos(128'd0), .i_sin(128'd0), .r_v(rv), .r_d(rd), .p_v(pv), .p_d(pd), .y_v(yv), .y(tt_mut), .o_f(ef));
assign yd = tt_mut ^ ((tmut == 8'd3) ? ((255) >= 30 ? ((255) + 1)'(64'h4000_4000) : (255) >= 14 ? ((255) + 1)'(64'h4000) : ((255) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(iv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_v %m slab %0d pin %0d", $bits(iv), (0) + 1); tt_bad = 1; end if ($bits(ix) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_x %m slab %0d pin %0d", $bits(ix), (255) + 1); tt_bad = 1; end if ($bits(igk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_gk %m slab %0d pin %0d", $bits(igk), (0) + 1); tt_bad = 1; end if ($bits(igr) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_gr %m slab %0d pin %0d", $bits(igr), (1) + 1); tt_bad = 1; end if ($bits(igw) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_gw %m slab %0d pin %0d", $bits(igw), (1) + 1); tt_bad = 1; end if ($bits(128'd0) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_cos %m slab %0d pin %0d", $bits(128'd0), (127) + 1); tt_bad = 1; end if ($bits(128'd0) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.i_sin %m slab %0d pin %0d", $bits(128'd0), (127) + 1); tt_bad = 1; end if ($bits(rv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.r_v %m slab %0d pin %0d", $bits(rv), (0) + 1); tt_bad = 1; end if ($bits(rd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.r_d %m slab %0d pin %0d", $bits(rd), (31) + 1); tt_bad = 1; end if ($bits(pv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.p_v %m slab %0d pin %0d", $bits(pv), (0) + 1); tt_bad = 1; end if ($bits(pd) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.p_d %m slab %0d pin %0d", $bits(pd), (31) + 1); tt_bad = 1; end if ($bits(yv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.y_v %m slab %0d pin %0d", $bits(yv), (0) + 1); tt_bad = 1; end if ($bits(yd) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.y %m slab %0d pin %0d", $bits(yd), (255) + 1); tt_bad = 1; end if ($bits(ef) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvp.o_f %m slab %0d pin %0d", $bits(ef), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_kve initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_kve u_kve line 282 %m"); $display("  RP = %0d", (0)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        end
        assign ky_v[ke] = yv; assign ky_d[256 * ke +: 256] = yd;
        ot_hdc_delay #(.W(2), .D(ERL), .RESET(1)) u_pv (.clk(sk), .rst_n(rst[0]), .d({pv, ef}), .q({kp_v[ke], kv_f[ke]}));
        ot_hdc_delay #(.W(32), .D(ERL)) u_pd (.clk(sk), .rst_n(rst[0]), .d(pd), .q(kp_d[32 * ke +: 32]));
    end endgenerate
    generate if (1) begin : g_kvr
        localparam integer NKH = NKE / 16;
        wire go, rf; wire [31:0] eps;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_gv (.clk(sk), .rst_n(rst[0]), .d(kt_go), .q(go));
        ot_hdc_delay #(.W(32), .D(ERL)) u_gd (.clk(sk), .rst_n(rst[0]), .d(kt_eps), .q(eps));
        // NKH half trees of 16 engines (the QN master qnh) -> the reduce (NE NKH: the golden tree's top levels)
        wire [NKH-1:0] hv, hp, hf; wire [NKH*32-1:0] hd;
        genvar hh;
        for (hh = 0; hh < NKH; hh = hh + 1) begin : g_kvh
            /* SU_TILE_TOPS: ot_s81_su_qnh u_qnh (slab line 299) */
if (((16) == (16)) && ((LA) == (4))) begin : g_tt0_u_qnh
wire [31:0] tt_mut;
dsfd_su_t_qnh u_qnh (.ck(sk), .rst(rst[0]), .i_go(go), .p_v(kp_v[16 * hh +: 16]), .p_p(16'd0), .p_d(kp_d[512 * hh +: 512]), .s_v(hv[hh]), .s_p(hp[hh]), .s_d(tt_mut), .o_f(hf[hh]));
assign hd[32 * hh +: 32] = tt_mut ^ ((tmut == 8'd11) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(go) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.i_go %m slab %0d pin %0d", $bits(go), (0) + 1); tt_bad = 1; end if ($bits(kp_v[16 * hh +: 16]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.p_v %m slab %0d pin %0d", $bits(kp_v[16 * hh +: 16]), (15) + 1); tt_bad = 1; end if ($bits(16'd0) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.p_p %m slab %0d pin %0d", $bits(16'd0), (15) + 1); tt_bad = 1; end if ($bits(kp_d[512 * hh +: 512]) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.p_d %m slab %0d pin %0d", $bits(kp_d[512 * hh +: 512]), (511) + 1); tt_bad = 1; end if ($bits(hv[hh]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.s_v %m slab %0d pin %0d", $bits(hv[hh]), (0) + 1); tt_bad = 1; end if ($bits(hp[hh]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.s_p %m slab %0d pin %0d", $bits(hp[hh]), (0) + 1); tt_bad = 1; end if ($bits(hd[32 * hh +: 32]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.s_d %m slab %0d pin %0d", $bits(hd[32 * hh +: 32]), (31) + 1); tt_bad = 1; end if ($bits(hf[hh]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnh.o_f %m slab %0d pin %0d", $bits(hf[hh]), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qnh initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qnh u_qnh line 299 %m"); $display("  NE = %0d", (16)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        end
        /* SU_TILE_TOPS: ot_s81_su_qnr u_kvr (slab line 303) */
if (((NKH) == (2)) && ((1) == (5)) && ((KV_N) == (1280)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt0_u_kvr
wire [31:0] tt_mut;
dsfd_su_t_qnr u_kvr (.ck(sk), .rst(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(kr_v), .r_d(tt_mut), .o_f(rf));
assign kr_d = tt_mut ^ ((tmut == 8'd13) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(go) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.i_go %m slab %0d pin %0d", $bits(go), (0) + 1); tt_bad = 1; end if ($bits(eps) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.i_eps %m slab %0d pin %0d", $bits(eps), (31) + 1); tt_bad = 1; end if ($bits(hv) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_v %m slab %0d pin %0d", $bits(hv), (1) + 1); tt_bad = 1; end if ($bits(hp) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_p %m slab %0d pin %0d", $bits(hp), (1) + 1); tt_bad = 1; end if ($bits(hd) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_d %m slab %0d pin %0d", $bits(hd), (63) + 1); tt_bad = 1; end if ($bits(hf) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.p_f %m slab %0d pin %0d", $bits(hf), (1) + 1); tt_bad = 1; end if ($bits(kr_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.r_v %m slab %0d pin %0d", $bits(kr_v), (0) + 1); tt_bad = 1; end if ($bits(kr_d) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.r_d %m slab %0d pin %0d", $bits(kr_d), (31) + 1); tt_bad = 1; end if ($bits(rf) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnr.o_f %m slab %0d pin %0d", $bits(rf), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else if (((NKH) == (4)) && ((1) == (1)) && ((KV_N) == (512)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt1_u_kvr
wire [31:0] tt_mut;
dsfd_su_t_kvr u_kvr (.ck(sk), .rst(rst[0]), .i_go(go), .i_eps(eps), .p_v(hv), .p_p(hp), .p_d(hd), .p_f(hf), .r_v(kr_v), .r_d(tt_mut), .o_f(rf));
assign kr_d = tt_mut ^ ((tmut == 8'd5) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(go) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.i_go %m slab %0d pin %0d", $bits(go), (0) + 1); tt_bad = 1; end if ($bits(eps) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.i_eps %m slab %0d pin %0d", $bits(eps), (31) + 1); tt_bad = 1; end if ($bits(hv) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_v %m slab %0d pin %0d", $bits(hv), (3) + 1); tt_bad = 1; end if ($bits(hp) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_p %m slab %0d pin %0d", $bits(hp), (3) + 1); tt_bad = 1; end if ($bits(hd) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_d %m slab %0d pin %0d", $bits(hd), (127) + 1); tt_bad = 1; end if ($bits(hf) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.p_f %m slab %0d pin %0d", $bits(hf), (3) + 1); tt_bad = 1; end if ($bits(kr_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.r_v %m slab %0d pin %0d", $bits(kr_v), (0) + 1); tt_bad = 1; end if ($bits(kr_d) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.r_d %m slab %0d pin %0d", $bits(kr_d), (31) + 1); tt_bad = 1; end if ($bits(rf) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvr.o_f %m slab %0d pin %0d", $bits(rf), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_kvr initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qnr u_kvr line 303 %m"); $display("  NE = %0d", (NKH)); $display("  NV = %0d", (1)); $display("  D = %0d", (KV_N)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rf (.clk(sk), .rst_n(rst[0]), .d(rf), .q(kv_f[NKE]));
    end endgenerate
    genvar kb;
    generate for (kb = 0; kb < NKQ; kb = kb + 1) begin : g_kvq
        // block kb = norm engines 4 kb .. 4 kb + 3; e gather of blocks 8 (kb / 8) .. into engine kb % 8 == 7
        wire rv; wire [1023:0] ry; wire [13:0] rob; wire [7:0] gv; wire [79:0] ge;
        ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[0]), .d(ky_v[4 * kb]), .q(rv));
        ot_hdc_delay #(.W(1024 + 14), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[0]), .d({ky_d[1024 * kb +: 1024], kt_ob}),
                                                    .q({ry, rob}));
        if (kb % 8 == 7) begin : g_gl
            ot_hdc_delay #(.W(8), .D(ERL), .RESET(1)) u_gv (.clk(sk), .rst_n(rst[0]), .d(kq_ev[kb - 7 +: 8]), .q(gv));
            ot_hdc_delay #(.W(80), .D(ERL)) u_ge (.clk(sk), .rst_n(rst[0]), .d(kq_ee[10 * (kb - 7) +: 80]), .q(ge));
        end else begin : g_g0
            assign gv = 8'd0; assign ge = 80'd0;
        end
        wire [3:0] CB = kb;
        wire ov, ofu, ofo, oal, ode, ord; wire [13:0] oa; wire [15:0] om; wire [511:0] od; wire [7:0] orj;
        /* SU_TILE_TOPS: ot_s81_su_kvq u_kvq (slab line 323) */
if (((KV_N) == (512)) && ((LM) == (5))) begin : g_tt0_u_kvq
wire [511:0] tt_mut;
dsfd_su_t_kvq u_kvq (.ck(sk), .rst(rst[0]), .cfg_b(CB), .i_v(rv), .i_y(ry), .i_ob(rob), .nx_i_v(kqxv[kb ^ 1]), .nx_i_q(kqxq[kb ^ 1]), .nx_o_v(kqxv[kb]), .nx_o_q(kqxq[kb]), .e_o_v(kq_ev[kb]), .e_o_e(kq_ee[10 * kb +: 10]), .g_i_v(gv), .g_i_e(ge), .o_v(ov), .o_a(oa), .o_m(om), .o_d(tt_mut), .o_fu(ofu), .o_fo(ofo), .o_alive(oal), .o_den(ode), .o_rdy(ord), .o_rjid(orj));
assign od = tt_mut ^ ((tmut == 8'd4) ? ((511) >= 30 ? ((511) + 1)'(64'h4000_4000) : (511) >= 14 ? ((511) + 1)'(64'h4000) : ((511) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(CB) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.cfg_b %m slab %0d pin %0d", $bits(CB), (3) + 1); tt_bad = 1; end if ($bits(rv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.i_v %m slab %0d pin %0d", $bits(rv), (0) + 1); tt_bad = 1; end if ($bits(ry) != (1023) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.i_y %m slab %0d pin %0d", $bits(ry), (1023) + 1); tt_bad = 1; end if ($bits(rob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.i_ob %m slab %0d pin %0d", $bits(rob), (13) + 1); tt_bad = 1; end if ($bits(kqxv[kb ^ 1]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.nx_i_v %m slab %0d pin %0d", $bits(kqxv[kb ^ 1]), (0) + 1); tt_bad = 1; end if ($bits(kqxq[kb ^ 1]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.nx_i_q %m slab %0d pin %0d", $bits(kqxq[kb ^ 1]), (255) + 1); tt_bad = 1; end if ($bits(kqxv[kb]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.nx_o_v %m slab %0d pin %0d", $bits(kqxv[kb]), (0) + 1); tt_bad = 1; end if ($bits(kqxq[kb]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.nx_o_q %m slab %0d pin %0d", $bits(kqxq[kb]), (255) + 1); tt_bad = 1; end if ($bits(kq_ev[kb]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.e_o_v %m slab %0d pin %0d", $bits(kq_ev[kb]), (0) + 1); tt_bad = 1; end if ($bits(kq_ee[10 * kb +: 10]) != (9) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.e_o_e %m slab %0d pin %0d", $bits(kq_ee[10 * kb +: 10]), (9) + 1); tt_bad = 1; end if ($bits(gv) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.g_i_v %m slab %0d pin %0d", $bits(gv), (7) + 1); tt_bad = 1; end if ($bits(ge) != (79) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.g_i_e %m slab %0d pin %0d", $bits(ge), (79) + 1); tt_bad = 1; end if ($bits(ov) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_v %m slab %0d pin %0d", $bits(ov), (0) + 1); tt_bad = 1; end if ($bits(oa) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_a %m slab %0d pin %0d", $bits(oa), (13) + 1); tt_bad = 1; end if ($bits(om) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_m %m slab %0d pin %0d", $bits(om), (15) + 1); tt_bad = 1; end if ($bits(od) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_d %m slab %0d pin %0d", $bits(od), (511) + 1); tt_bad = 1; end if ($bits(ofu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_fu %m slab %0d pin %0d", $bits(ofu), (0) + 1); tt_bad = 1; end if ($bits(ofo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_fo %m slab %0d pin %0d", $bits(ofo), (0) + 1); tt_bad = 1; end if ($bits(oal) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_alive %m slab %0d pin %0d", $bits(oal), (0) + 1); tt_bad = 1; end if ($bits(ode) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_den %m slab %0d pin %0d", $bits(ode), (0) + 1); tt_bad = 1; end if ($bits(ord) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_rdy %m slab %0d pin %0d", $bits(ord), (0) + 1); tt_bad = 1; end if ($bits(orj) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvq.o_rjid %m slab %0d pin %0d", $bits(orj), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_kvq initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_kvq u_kvq line 323 %m"); $display("  N = %0d", (KV_N)); $display("  MLAT = %0d", (LM)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        // to the KV stop: equal-depth relays + (S_WR < NKQ, reduced shapes only) a phase of 8 cycles a slot group so
        // the engines sharing slot kb % S_WR never write in the same cycle (full shape: 0)
        localparam integer PH = ERL + 8 * (kb / S_WR);
        ot_hdc_delay #(.W(5), .D(PH), .RESET(1)) u_ov (.clk(sk), .rst_n(rst[0]), .d({ov, ofu, ofo, oal, ode}),
            .q({kq_v[kb], kq_fu[kb], kq_fo[kb], kq_al[kb], kq_de[kb]}));
        ot_hdc_delay #(.W(14 + 16 + 512), .D(PH)) u_od (.clk(sk), .rst_n(rst[0]), .d({oa, om, od}),
            .q({kq_a[14 * kb +: 14], kq_m[16 * kb +: 16], kq_d[512 * kb +: 512]}));
    end endgenerate

    // ------------------------------------------------------------------ SW: lane engines (off the spine, chains)
    genvar sch, sp;
    generate for (sch = 0; sch < SNCH; sch = sch + 1) begin : g_swc
        // chain sch = pass row sch / SEPR, chunk sch % SEPR; engine P of the chain owns that chunk of pass P
        for (sp = 0; sp < SNPS; sp = sp + 1) begin : g_swe
            localparam integer E = sch * SNPS + sp;
            wire gv, uv; wire [32*SLPE-1:0] d; wire [11:0] et; wire [31:0] ew, el;
            ot_hdc_delay #(.W(2), .D(ERS), .RESET(1)) u_iv (.clk(sk), .rst_n(rst[0]), .d({sw_gv[sp], sw_uv[sp]}), .q({gv, uv}));
            ot_hdc_delay #(.W(32 * SLPE + 12 + 64), .D(ERS)) u_id (.clk(sk), .rst_n(rst[0]),
                .d({sw_d[512 * (sch / SEPR) + 32 * SLPE * (sch % SEPR) +: 32 * SLPE], sw_t, sw_w, sw_lim}), .q({d, et, ew, el}));
            wire civ, cif; wire [16*SLPE-1:0] cid; wire [11:0] cit;
            if (sp == SNPS - 1) begin : g_tail
                assign civ = 1'b0; assign cif = 1'b0; assign cid = 0; assign cit = 12'd0;
            end else begin : g_link
                assign civ = sc_v[E + 1]; assign cif = sc_f[E + 1]; assign cid = sc_d[16 * SLPE * (E + 1) +: 16 * SLPE];
                assign cit = sc_t[12 * (E + 1) +: 12];
            end
            /* SU_TILE_TOPS: ot_s81_su_swe u_swe (slab line 354) */
if (((SLPE) == (8)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt0_u_swe
wire [127:0] tt_mut;
dsfd_su_t_swe u_swe (.ck(sk), .rst(rst[0]), .i_gv(gv), .i_uv(uv), .i_d(d), .i_t(et), .i_w(ew), .i_lim(el), .c_iv(civ), .c_id(cid), .c_it(cit), .c_if(cif), .c_ov(sc_v[E]), .c_od(tt_mut), .c_ot(sc_t[12 * E +: 12]), .c_of(sc_f[E]));
assign sc_d[16 * SLPE * E +: 16 * SLPE] = tt_mut ^ ((tmut == 8'd20) ? ((127) >= 30 ? ((127) + 1)'(64'h4000_4000) : (127) >= 14 ? ((127) + 1)'(64'h4000) : ((127) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.rst %m slab %0d pin %0d", $bits(rst[0]), (0) + 1); tt_bad = 1; end if ($bits(gv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.i_gv %m slab %0d pin %0d", $bits(gv), (0) + 1); tt_bad = 1; end if ($bits(uv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.i_uv %m slab %0d pin %0d", $bits(uv), (0) + 1); tt_bad = 1; end if ($bits(d) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.i_d %m slab %0d pin %0d", $bits(d), (255) + 1); tt_bad = 1; end if ($bits(et) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.i_t %m slab %0d pin %0d", $bits(et), (11) + 1); tt_bad = 1; end if ($bits(ew) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.i_w %m slab %0d pin %0d", $bits(ew), (31) + 1); tt_bad = 1; end if ($bits(el) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.i_lim %m slab %0d pin %0d", $bits(el), (31) + 1); tt_bad = 1; end if ($bits(civ) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_iv %m slab %0d pin %0d", $bits(civ), (0) + 1); tt_bad = 1; end if ($bits(cid) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_id %m slab %0d pin %0d", $bits(cid), (127) + 1); tt_bad = 1; end if ($bits(cit) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_it %m slab %0d pin %0d", $bits(cit), (11) + 1); tt_bad = 1; end if ($bits(cif) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_if %m slab %0d pin %0d", $bits(cif), (0) + 1); tt_bad = 1; end if ($bits(sc_v[E]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_ov %m slab %0d pin %0d", $bits(sc_v[E]), (0) + 1); tt_bad = 1; end if ($bits(sc_d[16 * SLPE * E +: 16 * SLPE]) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_od %m slab %0d pin %0d", $bits(sc_d[16 * SLPE * E +: 16 * SLPE]), (127) + 1); tt_bad = 1; end if ($bits(sc_t[12 * E +: 12]) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_ot %m slab %0d pin %0d", $bits(sc_t[12 * E +: 12]), (11) + 1); tt_bad = 1; end if ($bits(sc_f[E]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swe.c_of %m slab %0d pin %0d", $bits(sc_f[E]), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_swe initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_swe u_swe line 354 %m"); $display("  LPE = %0d", (SLPE)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        end
        ot_hdc_delay #(.W(1), .D(ERS), .RESET(1)) u_fr (.clk(sk), .rst_n(rst[0]), .d(sc_f[sch * SNPS]), .q(sw_f[sch]));
    end endgenerate

    // ------------------------------------------------------------------ engine tiles
    // norm rungs: the group partial of tile t (TI 1) to its head (t - 1), the head's rstd back (registered relays)
    wire        xpv [0:NTL]; wire [7:0] xpi [0:NTL]; wire [31:0] xpd [0:NTL];   // tile t's outputs
    wire        xrv [0:NTL]; wire [31:0] xrd [0:NTL];
    genvar t;
    generate for (t = 0; t < NTL; t = t + 1) begin : g_t
        localparam integer B1 = NQN, B2 = NQN + 1, B3 = B2 + NQB, B4 = B3 + NSWS;
        // TK 2: the QB tap (no write slots), TK 5: QB engine TI (slots 2 TI, 2 TI + 1)
        // TK 6: the QN tap (no write slots), TK 7: QN quant engine TI (slot TI), TK 8: the KV stop (tap + all S_WR slots)
        // TK 12: the SW tap (no write slots), TK 13: SW quant engine TI (the QB master; slots 2 TI, 2 TI + 1)
        localparam integer TK = (t == 0) ? 6 : (t < B1) ? 7 : (t < B2) ? 8 : (t == B2) ? 2 : (t < B3) ? 5 : (t == B3) ? 12 : (t < B4) ? 13 : 4;
        localparam integer TI = (t < B1) ? (t == 0 ? 0 : t - 1) : (t < B2) ? t - B1 : (t < B3) ? (t == B2 ? 0 : t - B2 - 1) : (t < B4) ? (t == B3 ? 0 : t - B3 - 1) : t - B4;
        localparam integer NT = (t < B1) ? NQQ : (t < B2) ? 1 : (t < B3) ? NPB : (t < B4) ? NSWQ : NSM;
        localparam integer WS = (TK == 2 || TK == 6 || TK == 12) ? 0 : (TK == 7) ? 1 : (TK == 8) ? S_WR : S_WR / NT, W0 = TI * WS;
        localparam integer WSX = (WS > 0) ? WS : 1;
        wire [WSX-1:0] o_v; wire [WSX*14-1:0] o_a; wire [WSX*16-1:0] o_m; wire [WSX*512-1:0] o_d;
        wire o_fu, o_fo, o_alive, o_den, o_rdy; wire [7:0] o_rjid;
        // rung relays: into a head (TK <= 1, TI 0) from t + 1; into a member (TI 1) from t - 1
        reg ipv, irv; reg [7:0] ipi; reg [31:0] ipd, ird;
        if (TK <= 1 && TI == 0 && NT == 2) begin : g_rh
            wire v; wire [39:0] d;
            ot_hdc_delay #(.W(1), .D(SRD), .RESET(1)) u_v (.clk(sk), .rst_n(rst[t]), .d(xpv[t + 1]), .q(v));
            ot_hdc_delay #(.W(40), .D(SRD)) u_d (.clk(sk), .rst_n(rst[t]), .d({xpi[t + 1], xpd[t + 1]}), .q(d));
            always @(*) begin ipv = v; {ipi, ipd} = d; end
        end else begin : g_rh0
            always @(*) begin ipv = 1'b0; ipi = 8'd0; ipd = 32'd0; end
        end
        if (TK <= 1 && TI == 1) begin : g_rm
            wire v; wire [31:0] d;
            ot_hdc_delay #(.W(1), .D(SRD), .RESET(1)) u_v (.clk(sk), .rst_n(rst[t]), .d(xrv[t - 1]), .q(v));
            ot_hdc_delay #(.W(32), .D(SRD)) u_d (.clk(sk), .rst_n(rst[t]), .d(xrd[t - 1]), .q(d));
            always @(*) begin irv = v; ird = d; end
        end else begin : g_rm0
            always @(*) begin irv = 1'b0; ird = 32'd0; end
        end
        if (TK == 6) begin : g_qnt
            assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            // two data halves, identical control; half 0 carries the job fields, the status and the faults
            genvar h;
            for (h = 0; h < 2; h = h + 1) begin : g_h
                wire [S_RD*256-1:0] dh;
                genvar s2;
                for (s2 = 0; s2 < S_RD; s2 = s2 + 1) begin : g_s
                    assign dh[256 * s2 +: 256] = dd[t][512 * s2 + 256 * h +: 256];
                end
                wire hgq, hgo, hfu, hfo, hal, hde, hrd; wire [1:0] hgr, hgw; wire [13:0] hob; wire [31:0] hep; wire [7:0] hrj;
                /* SU_TILE_TOPS: ot_s81_su_qnt u_qnt (slab line 409) */
if (((QN_N) == (256)) && ((S_RD) == (16)) && ((NQE + 1) == (33)) && ((MUT) == (0)) && ((32) == (32))) begin : g_tt0_u_qnt
wire [4095:0] tt_mut;
dsfd_su_t_qnt u_qnt (.ck(sk), .rst(rst[t]), .dn_st(dst[t]), .dn_kind(dkd[t]), .dn_gsel(dgs[t]), .dn_jid(dji[t]), .dn_v(dv[t]), .dn_d(dh), .i_f(h == 0 ? qn_f : {(NQE + 1){1'b0}}), .e_v(qt_v[h]), .e_d(tt_mut), .e_t(qt_t[h]), .e_gq(hgq), .e_gr(hgr), .e_gw(hgw), .e_go(hgo), .e_ob(hob), .e_eps(hep), .o_fu(hfu), .o_fo(hfo), .o_alive(hal), .o_den(hde), .o_rdy(hrd), .o_rjid(hrj));
assign qt_d[h] = tt_mut ^ ((tmut == 8'd14) ? ((4095) >= 30 ? ((4095) + 1)'(64'h4000_4000) : (4095) >= 14 ? ((4095) + 1)'(64'h4000) : ((4095) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(dst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.dn_st %m slab %0d pin %0d", $bits(dst[t]), (0) + 1); tt_bad = 1; end if ($bits(dkd[t]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.dn_kind %m slab %0d pin %0d", $bits(dkd[t]), (3) + 1); tt_bad = 1; end if ($bits(dgs[t]) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.dn_gsel %m slab %0d pin %0d", $bits(dgs[t]), (1) + 1); tt_bad = 1; end if ($bits(dji[t]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.dn_jid %m slab %0d pin %0d", $bits(dji[t]), (7) + 1); tt_bad = 1; end if ($bits(dv[t]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.dn_v %m slab %0d pin %0d", $bits(dv[t]), (15) + 1); tt_bad = 1; end if ($bits(dh) != (4095) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.dn_d %m slab %0d pin %0d", $bits(dh), (4095) + 1); tt_bad = 1; end if ($bits(h == 0 ? qn_f : {(NQE + 1){1'b0}}) != (32) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.i_f %m slab %0d pin %0d", $bits(h == 0 ? qn_f : {(NQE + 1){1'b0}}), (32) + 1); tt_bad = 1; end if ($bits(qt_v[h]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_v %m slab %0d pin %0d", $bits(qt_v[h]), (15) + 1); tt_bad = 1; end if ($bits(qt_d[h]) != (4095) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_d %m slab %0d pin %0d", $bits(qt_d[h]), (4095) + 1); tt_bad = 1; end if ($bits(qt_t[h]) != (127) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_t %m slab %0d pin %0d", $bits(qt_t[h]), (127) + 1); tt_bad = 1; end if ($bits(hgq) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_gq %m slab %0d pin %0d", $bits(hgq), (0) + 1); tt_bad = 1; end if ($bits(hgr) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_gr %m slab %0d pin %0d", $bits(hgr), (1) + 1); tt_bad = 1; end if ($bits(hgw) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_gw %m slab %0d pin %0d", $bits(hgw), (1) + 1); tt_bad = 1; end if ($bits(hgo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_go %m slab %0d pin %0d", $bits(hgo), (0) + 1); tt_bad = 1; end if ($bits(hob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_ob %m slab %0d pin %0d", $bits(hob), (13) + 1); tt_bad = 1; end if ($bits(hep) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.e_eps %m slab %0d pin %0d", $bits(hep), (31) + 1); tt_bad = 1; end if ($bits(hfu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.o_fu %m slab %0d pin %0d", $bits(hfu), (0) + 1); tt_bad = 1; end if ($bits(hfo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.o_fo %m slab %0d pin %0d", $bits(hfo), (0) + 1); tt_bad = 1; end if ($bits(hal) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.o_alive %m slab %0d pin %0d", $bits(hal), (0) + 1); tt_bad = 1; end if ($bits(hde) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.o_den %m slab %0d pin %0d", $bits(hde), (0) + 1); tt_bad = 1; end if ($bits(hrd) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.o_rdy %m slab %0d pin %0d", $bits(hrd), (0) + 1); tt_bad = 1; end if ($bits(hrj) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnt.o_rjid %m slab %0d pin %0d", $bits(hrj), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qnt initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qnt u_qnt line 409 %m"); $display("  N = %0d", (QN_N)); $display("  S_RD = %0d", (S_RD)); $display("  NFI = %0d", (NQE + 1)); $display("  MUT = %0d", (MUT)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
                if (h == 0) begin : g_h0
                    assign qt_gq = hgq; assign qt_gr = hgr; assign qt_gw = hgw; assign qt_go = hgo; assign qt_ob = hob;
                    assign qt_eps = hep;
                    assign o_fu = hfu; assign o_fo = hfo; assign o_alive = hal; assign o_den = hde; assign o_rdy = hrd;
                    assign o_rjid = hrj;
                end
            end
        end else if (TK == 7) begin : g_qnq
            // the y of norm engines 4 TI .. 4 TI + 3 (equal-depth relays) and the obase
            wire rv; wire [7:0] rt; wire [1023:0] ry; wire [13:0] rob;
            ot_hdc_delay #(.W(1), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[t]), .d(qy_v[4 * TI]), .q(rv));
            ot_hdc_delay #(.W(8 + 1024 + 14), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[t]),
                .d({qy_i[8 * 4 * TI +: 8], qy_d[1024 * TI +: 1024], qt_ob}), .q({rt, ry, rob}));
            localparam integer PN = TI ^ 1;
            wire [3:0] CB = TI;
            /* SU_TILE_TOPS: ot_s81_su_qnq u_qnq (slab line 430) */
if (((QN_N) == (256)) && ((LM) == (5))) begin : g_tt0_u_qnq
wire [511:0] tt_mut;
dsfd_su_t_qnq u_qnq (.ck(sk), .rst(rst[t]), .cfg_b(CB), .i_v(rv), .i_t(rt), .i_y(ry), .i_ob(rob), .nx_i_v(qnxv[PN]), .nx_i_q(qnxq[PN]), .nx_i_e(qnxe[PN]), .nx_o_v(qnxv[TI]), .nx_o_q(qnxq[TI]), .nx_o_e(qnxe[TI]), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(tt_mut), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
assign o_d = tt_mut ^ ((tmut == 8'd12) ? ((511) >= 30 ? ((511) + 1)'(64'h4000_4000) : (511) >= 14 ? ((511) + 1)'(64'h4000) : ((511) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(CB) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.cfg_b %m slab %0d pin %0d", $bits(CB), (3) + 1); tt_bad = 1; end if ($bits(rv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.i_v %m slab %0d pin %0d", $bits(rv), (0) + 1); tt_bad = 1; end if ($bits(rt) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.i_t %m slab %0d pin %0d", $bits(rt), (7) + 1); tt_bad = 1; end if ($bits(ry) != (1023) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.i_y %m slab %0d pin %0d", $bits(ry), (1023) + 1); tt_bad = 1; end if ($bits(rob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.i_ob %m slab %0d pin %0d", $bits(rob), (13) + 1); tt_bad = 1; end if ($bits(qnxv[PN]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.nx_i_v %m slab %0d pin %0d", $bits(qnxv[PN]), (0) + 1); tt_bad = 1; end if ($bits(qnxq[PN]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.nx_i_q %m slab %0d pin %0d", $bits(qnxq[PN]), (255) + 1); tt_bad = 1; end if ($bits(qnxe[PN]) != (9) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.nx_i_e %m slab %0d pin %0d", $bits(qnxe[PN]), (9) + 1); tt_bad = 1; end if ($bits(qnxv[TI]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.nx_o_v %m slab %0d pin %0d", $bits(qnxv[TI]), (0) + 1); tt_bad = 1; end if ($bits(qnxq[TI]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.nx_o_q %m slab %0d pin %0d", $bits(qnxq[TI]), (255) + 1); tt_bad = 1; end if ($bits(qnxe[TI]) != (9) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.nx_o_e %m slab %0d pin %0d", $bits(qnxe[TI]), (9) + 1); tt_bad = 1; end if ($bits(o_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_v %m slab %0d pin %0d", $bits(o_v), (0) + 1); tt_bad = 1; end if ($bits(o_a) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_a %m slab %0d pin %0d", $bits(o_a), (13) + 1); tt_bad = 1; end if ($bits(o_m) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_m %m slab %0d pin %0d", $bits(o_m), (15) + 1); tt_bad = 1; end if ($bits(o_d) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_d %m slab %0d pin %0d", $bits(o_d), (511) + 1); tt_bad = 1; end if ($bits(o_fu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_fu %m slab %0d pin %0d", $bits(o_fu), (0) + 1); tt_bad = 1; end if ($bits(o_fo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_fo %m slab %0d pin %0d", $bits(o_fo), (0) + 1); tt_bad = 1; end if ($bits(o_alive) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_alive %m slab %0d pin %0d", $bits(o_alive), (0) + 1); tt_bad = 1; end if ($bits(o_den) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_den %m slab %0d pin %0d", $bits(o_den), (0) + 1); tt_bad = 1; end if ($bits(o_rdy) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_rdy %m slab %0d pin %0d", $bits(o_rdy), (0) + 1); tt_bad = 1; end if ($bits(o_rjid) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qnq.o_rjid %m slab %0d pin %0d", $bits(o_rjid), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qnq initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qnq u_qnq line 430 %m"); $display("  N = %0d", (QN_N)); $display("  MLAT = %0d", (LM)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
        end else if (TK == 8) begin : g_kv
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            // four data quarters, identical control; quarter 0 carries the job fields, the status and the faults
            wire tfu, tfo, tal, tde, trd; wire [7:0] trj;
            genvar u;
            for (u = 0; u < 4; u = u + 1) begin : g_u
                wire [S_RD*128-1:0] dq;
                genvar s2;
                for (s2 = 0; s2 < S_RD; s2 = s2 + 1) begin : g_s
                    assign dq[128 * s2 +: 128] = dd[t][512 * s2 + 128 * u +: 128];
                end
                wire ugk, ugo, ufu, ufo, ual, ude, urd; wire [1:0] ugr, ugw; wire [13:0] uob; wire [31:0] uep; wire [7:0] urj;
                /* SU_TILE_TOPS: ot_s81_su_kvt u_kvt (slab line 448) */
if (((KV_N) == (512)) && ((S_RD) == (16)) && ((NKE + 1) == (65)) && ((MUT) == (0))) begin : g_tt0_u_kvt
wire [4095:0] tt_mut;
dsfd_su_t_kvt u_kvt (.ck(sk), .rst(rst[t]), .dn_st(dst[t]), .dn_kind(dkd[t]), .dn_gsel(dgs[t]), .dn_jid(dji[t]), .dn_v(dv[t]), .dn_d(dq), .i_f(u == 0 ? kv_f : {(NKE + 1){1'b0}}), .e_v(kt_v[u]), .e_d(tt_mut), .e_gk(ugk), .e_gr(ugr), .e_gw(ugw), .e_go(ugo), .e_ob(uob), .e_eps(uep), .e_cs(kt_cs[u]), .o_fu(ufu), .o_fo(ufo), .o_alive(ual), .o_den(ude), .o_rdy(urd), .o_rjid(urj));
assign kt_d[u] = tt_mut ^ ((tmut == 8'd6) ? ((4095) >= 30 ? ((4095) + 1)'(64'h4000_4000) : (4095) >= 14 ? ((4095) + 1)'(64'h4000) : ((4095) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(dst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.dn_st %m slab %0d pin %0d", $bits(dst[t]), (0) + 1); tt_bad = 1; end if ($bits(dkd[t]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.dn_kind %m slab %0d pin %0d", $bits(dkd[t]), (3) + 1); tt_bad = 1; end if ($bits(dgs[t]) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.dn_gsel %m slab %0d pin %0d", $bits(dgs[t]), (1) + 1); tt_bad = 1; end if ($bits(dji[t]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.dn_jid %m slab %0d pin %0d", $bits(dji[t]), (7) + 1); tt_bad = 1; end if ($bits(dv[t]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.dn_v %m slab %0d pin %0d", $bits(dv[t]), (15) + 1); tt_bad = 1; end if ($bits(dq) != (2047) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.dn_d %m slab %0d pin %0d", $bits(dq), (2047) + 1); tt_bad = 1; end if ($bits(u == 0 ? kv_f : {(NKE + 1){1'b0}}) != (64) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.i_f %m slab %0d pin %0d", $bits(u == 0 ? kv_f : {(NKE + 1){1'b0}}), (64) + 1); tt_bad = 1; end if ($bits(kt_v[u]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_v %m slab %0d pin %0d", $bits(kt_v[u]), (31) + 1); tt_bad = 1; end if ($bits(kt_d[u]) != (4095) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_d %m slab %0d pin %0d", $bits(kt_d[u]), (4095) + 1); tt_bad = 1; end if ($bits(ugk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_gk %m slab %0d pin %0d", $bits(ugk), (0) + 1); tt_bad = 1; end if ($bits(ugr) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_gr %m slab %0d pin %0d", $bits(ugr), (1) + 1); tt_bad = 1; end if ($bits(ugw) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_gw %m slab %0d pin %0d", $bits(ugw), (1) + 1); tt_bad = 1; end if ($bits(ugo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_go %m slab %0d pin %0d", $bits(ugo), (0) + 1); tt_bad = 1; end if ($bits(uob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_ob %m slab %0d pin %0d", $bits(uob), (13) + 1); tt_bad = 1; end if ($bits(uep) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_eps %m slab %0d pin %0d", $bits(uep), (31) + 1); tt_bad = 1; end if ($bits(kt_cs[u]) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.e_cs %m slab %0d pin %0d", $bits(kt_cs[u]), (511) + 1); tt_bad = 1; end if ($bits(ufu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.o_fu %m slab %0d pin %0d", $bits(ufu), (0) + 1); tt_bad = 1; end if ($bits(ufo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.o_fo %m slab %0d pin %0d", $bits(ufo), (0) + 1); tt_bad = 1; end if ($bits(ual) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.o_alive %m slab %0d pin %0d", $bits(ual), (0) + 1); tt_bad = 1; end if ($bits(ude) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.o_den %m slab %0d pin %0d", $bits(ude), (0) + 1); tt_bad = 1; end if ($bits(urd) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.o_rdy %m slab %0d pin %0d", $bits(urd), (0) + 1); tt_bad = 1; end if ($bits(urj) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_kvt.o_rjid %m slab %0d pin %0d", $bits(urj), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_kvt initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_kvt u_kvt line 448 %m"); $display("  N = %0d", (KV_N)); $display("  S_RD = %0d", (S_RD)); $display("  NFI = %0d", (NKE + 1)); $display("  MUT = %0d", (MUT)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
                if (u == 0) begin : g_u0
                    assign kt_gk = ugk; assign kt_gr = ugr; assign kt_gw = ugw; assign kt_go = ugo; assign kt_ob = uob;
                    assign kt_eps = uep;
                    assign tfu = ufu; assign tfo = ufo; assign tal = ual; assign tde = ude; assign trd = urd; assign trj = urj;
                end
            end
            // the quant engines' slots: engine b on slot b % S_WR (phased apart when shared)
            reg [S_WR-1:0] mv; reg [S_WR*14-1:0] ma; reg [S_WR*16-1:0] mm; reg [S_WR*512-1:0] md;
            always @(*) begin : mrg
                integer b;
                mv = 0; ma = 0; mm = 0; md = 0;
                for (b = 0; b < NKQ; b = b + 1) if (kq_v[b]) begin
                    mv[b % S_WR] = 1'b1;
                    ma[14 * (b % S_WR) +: 14] = ma[14 * (b % S_WR) +: 14] | kq_a[14 * b +: 14];
                    mm[16 * (b % S_WR) +: 16] = mm[16 * (b % S_WR) +: 16] | kq_m[16 * b +: 16];
                    md[512 * (b % S_WR) +: 512] = md[512 * (b % S_WR) +: 512] | kq_d[512 * b +: 512];
                end
            end
            assign o_v = mv; assign o_a = ma; assign o_m = mm; assign o_d = md;
            assign o_fu = tfu | (|kq_fu); assign o_fo = tfo | (|kq_fo); assign o_alive = tal & (&kq_al);
            assign o_den = tde & (&kq_de); assign o_rdy = trd; assign o_rjid = trj;
`ifndef SYNTHESIS
            always @(posedge sk) if (rst[t]) begin : sc
                integer b, c;
                for (b = 0; b < NKQ; b = b + 1) for (c = b + 1; c < NKQ; c = c + 1)
                    if (kq_v[b] && kq_v[c] && (b % S_WR) == (c % S_WR))
                        $fatal(1, "dsfd_sp_su_h: KV quant engines %0d and %0d write slot %0d in one cycle", b, c, b % S_WR);
            end
`endif
        end else if (TK == 2) begin : g_qbt
            assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            /* SU_TILE_TOPS: ot_s81_su_qbt u_qbt (slab line 486) */
if (((QB_NB) == (32)) && ((S_RD) == (16)) && ((NPB) == (8))) begin : g_tt0_u_qbt
wire [8191:0] tt_c_dn_d_i;
wire [8191:0] tt_c_e_d;
wire [191:0] tt_mut;
dsfd_su_t_qbt u_qbt (.ck(sk), .rst(rst[t]), .dn_st(dst[t]), .dn_kind(dkd[t]), .dn_gsel(dgs[t]), .dn_fp4(df4[t]), .dn_jid(dji[t]), .dn_v(dv[t]), .dn_dh(tt_c_dn_d_i[8191:4096]), .dn_dl(tt_c_dn_d_i[4095:0]), .e_v(qe_v), .e_dh(tt_c_e_d[8191:4096]), .e_dl(tt_c_e_d[4095:0]), .e_t(tt_mut), .e_ob(qe_ob), .e_f4(qe_f4), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
assign tt_c_dn_d_i = dd[t];
assign qe_d = tt_c_e_d;
assign qe_t = tt_mut ^ ((tmut == 8'd9) ? ((191) >= 30 ? ((191) + 1)'(64'h4000_4000) : (191) >= 14 ? ((191) + 1)'(64'h4000) : ((191) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(dst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.dn_st %m slab %0d pin %0d", $bits(dst[t]), (0) + 1); tt_bad = 1; end if ($bits(dkd[t]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.dn_kind %m slab %0d pin %0d", $bits(dkd[t]), (3) + 1); tt_bad = 1; end if ($bits(dgs[t]) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.dn_gsel %m slab %0d pin %0d", $bits(dgs[t]), (1) + 1); tt_bad = 1; end if ($bits(df4[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.dn_fp4 %m slab %0d pin %0d", $bits(df4[t]), (0) + 1); tt_bad = 1; end if ($bits(dji[t]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.dn_jid %m slab %0d pin %0d", $bits(dji[t]), (7) + 1); tt_bad = 1; end if ($bits(dv[t]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.dn_v %m slab %0d pin %0d", $bits(dv[t]), (15) + 1); tt_bad = 1; end if ($bits(dd[t]) != 8192) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt core port dn_d_i %m slab %0d pins %0d", $bits(dd[t]), 8192); tt_bad = 1; end if ($bits(qe_v) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.e_v %m slab %0d pin %0d", $bits(qe_v), (15) + 1); tt_bad = 1; end if ($bits(qe_d) != 8192) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt core port e_d %m slab %0d pins %0d", $bits(qe_d), 8192); tt_bad = 1; end if ($bits(qe_t) != (191) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.e_t %m slab %0d pin %0d", $bits(qe_t), (191) + 1); tt_bad = 1; end if ($bits(qe_ob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.e_ob %m slab %0d pin %0d", $bits(qe_ob), (13) + 1); tt_bad = 1; end if ($bits(qe_f4) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.e_f4 %m slab %0d pin %0d", $bits(qe_f4), (0) + 1); tt_bad = 1; end if ($bits(o_fu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.o_fu %m slab %0d pin %0d", $bits(o_fu), (0) + 1); tt_bad = 1; end if ($bits(o_fo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.o_fo %m slab %0d pin %0d", $bits(o_fo), (0) + 1); tt_bad = 1; end if ($bits(o_alive) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.o_alive %m slab %0d pin %0d", $bits(o_alive), (0) + 1); tt_bad = 1; end if ($bits(o_den) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.o_den %m slab %0d pin %0d", $bits(o_den), (0) + 1); tt_bad = 1; end if ($bits(o_rdy) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.o_rdy %m slab %0d pin %0d", $bits(o_rdy), (0) + 1); tt_bad = 1; end if ($bits(o_rjid) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbt.o_rjid %m slab %0d pin %0d", $bits(o_rjid), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qbt initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qbt u_qbt line 486 %m"); $display("  QB_NB = %0d", (QB_NB)); $display("  S_RD = %0d", (S_RD)); $display("  NPB = %0d", (NPB)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        end else if (TK == 5) begin : g_qbe
            // equal-depth relays from the tap (every engine ERL stations: lockstep), positions 2 TI / 2 TI + 1
            wire [1:0] rv; wire [1023:0] rd; wire [23:0] rt; wire [13:0] rob; wire rf4;
            ot_hdc_delay #(.W(2), .D(ERL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[t]), .d(qe_v[2 * TI +: 2]), .q(rv));
            ot_hdc_delay #(.W(1024 + 24 + 15), .D(ERL)) u_rd (.clk(sk), .rst_n(rst[t]),
                .d({qe_d[1024 * TI +: 1024], qe_t[24 * TI +: 24], qe_ob, qe_f4}), .q({rd, rt, rob, rf4}));
            localparam integer PN = TI ^ 1;              // the pair neighbour
            wire [3:0] CB = TI;
            /* SU_TILE_TOPS: ot_s81_su_qbe u_qbe (slab line 499) */
if (((QB_NB) == (32)) && ((NPB) == (8))) begin : g_tt0_u_qbe
wire [1023:0] tt_mut;
dsfd_su_t_qbe u_qbe (.ck(sk), .rst(rst[t]), .cfg_b(CB), .i_vlo(rv[0]), .i_vhi(rv[1]), .i_lo(rd[511:0]), .i_hi(rd[1023:512]), .i_tlo(rt[11:0]), .i_thi(rt[23:12]), .i_ob(rob), .i_f4(rf4), .nx_i_v(nxv[PN]), .nx_i_q(nxq[PN]), .nx_i_e(nxe[PN]), .nx_o_v(nxv[TI]), .nx_o_q(nxq[TI]), .nx_o_e(nxe[TI]), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(tt_mut), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
assign o_d = tt_mut ^ ((tmut == 8'd8) ? ((1023) >= 30 ? ((1023) + 1)'(64'h4000_4000) : (1023) >= 14 ? ((1023) + 1)'(64'h4000) : ((1023) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(CB) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.cfg_b %m slab %0d pin %0d", $bits(CB), (3) + 1); tt_bad = 1; end if ($bits(rv[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_vlo %m slab %0d pin %0d", $bits(rv[0]), (0) + 1); tt_bad = 1; end if ($bits(rv[1]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_vhi %m slab %0d pin %0d", $bits(rv[1]), (0) + 1); tt_bad = 1; end if ($bits(rd[511:0]) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_lo %m slab %0d pin %0d", $bits(rd[511:0]), (511) + 1); tt_bad = 1; end if ($bits(rd[1023:512]) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_hi %m slab %0d pin %0d", $bits(rd[1023:512]), (511) + 1); tt_bad = 1; end if ($bits(rt[11:0]) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_tlo %m slab %0d pin %0d", $bits(rt[11:0]), (11) + 1); tt_bad = 1; end if ($bits(rt[23:12]) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_thi %m slab %0d pin %0d", $bits(rt[23:12]), (11) + 1); tt_bad = 1; end if ($bits(rob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_ob %m slab %0d pin %0d", $bits(rob), (13) + 1); tt_bad = 1; end if ($bits(rf4) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_f4 %m slab %0d pin %0d", $bits(rf4), (0) + 1); tt_bad = 1; end if ($bits(nxv[PN]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_i_v %m slab %0d pin %0d", $bits(nxv[PN]), (0) + 1); tt_bad = 1; end if ($bits(nxq[PN]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_i_q %m slab %0d pin %0d", $bits(nxq[PN]), (255) + 1); tt_bad = 1; end if ($bits(nxe[PN]) != (9) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_i_e %m slab %0d pin %0d", $bits(nxe[PN]), (9) + 1); tt_bad = 1; end if ($bits(nxv[TI]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_o_v %m slab %0d pin %0d", $bits(nxv[TI]), (0) + 1); tt_bad = 1; end if ($bits(nxq[TI]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_o_q %m slab %0d pin %0d", $bits(nxq[TI]), (255) + 1); tt_bad = 1; end if ($bits(nxe[TI]) != (9) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_o_e %m slab %0d pin %0d", $bits(nxe[TI]), (9) + 1); tt_bad = 1; end if ($bits(o_v) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_v %m slab %0d pin %0d", $bits(o_v), (1) + 1); tt_bad = 1; end if ($bits(o_a) != (27) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_a %m slab %0d pin %0d", $bits(o_a), (27) + 1); tt_bad = 1; end if ($bits(o_m) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_m %m slab %0d pin %0d", $bits(o_m), (31) + 1); tt_bad = 1; end if ($bits(o_d) != (1023) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_d %m slab %0d pin %0d", $bits(o_d), (1023) + 1); tt_bad = 1; end if ($bits(o_fu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_fu %m slab %0d pin %0d", $bits(o_fu), (0) + 1); tt_bad = 1; end if ($bits(o_fo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_fo %m slab %0d pin %0d", $bits(o_fo), (0) + 1); tt_bad = 1; end if ($bits(o_alive) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_alive %m slab %0d pin %0d", $bits(o_alive), (0) + 1); tt_bad = 1; end if ($bits(o_den) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_den %m slab %0d pin %0d", $bits(o_den), (0) + 1); tt_bad = 1; end if ($bits(o_rdy) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_rdy %m slab %0d pin %0d", $bits(o_rdy), (0) + 1); tt_bad = 1; end if ($bits(o_rjid) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_rjid %m slab %0d pin %0d", $bits(o_rjid), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qbe initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qbe u_qbe line 499 %m"); $display("  QB_NB = %0d", (QB_NB)); $display("  NPB = %0d", (NPB)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
        end else if (TK == 4) begin : g_sm
            // SM (el1011-s81su-sm, spec v3): tap/out smt + per head 16 lanes sml, sum smc, root smr, 8 divide smd;
            // every intra-stop link through SRL equal-depth relays (lanes in lockstep)
            localparam integer NPS = (S_RD < 5) ? S_RD : 5;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            wire s_v, p_v, c_v, cs_v, e_v, o_vv, den_v, f_any; wire [1023:0] e_d; wire [511:0] o_dd;
            wire [6:0] c_nv; wire [2:0] c_lt; wire [31:0] c_scale; wire [63:0] c_sink; wire [4:0] cs_i; wire [63:0] cs_d;
            wire [1:0] hden_v; wire [15:0] hf;
            wire [3:0] CTI = TI;
            /* SU_TILE_TOPS: ot_s81_su_smt u_smt (slab line 516) */
if (((SM_H) == (16)) && ((SM_LPH) == (16)) && ((S_RD) == (16)) && ((WS) == (2)) && ((MUT) == (0))) begin : g_tt0_u_smt
wire [1023:0] tt_mut;
dsfd_su_t_smt u_smt (.ck(sk), .rst(rst[t]), .cfg_ti(CTI), .dn_st(dst[t]), .dn_kind(dkd[t]), .dn_jid(dji[t]), .dn_v(dv[t]), .dn_p(dd[t][0 +: NPS * 512]), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale), .c_sink(c_sink), .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .e_v(e_v), .e_d(e_d), .o_vi(o_vv), .o_di(o_dd), .den_v(hden_v[0]), .f_i(f_any), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(tt_mut), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
assign o_d = tt_mut ^ ((tmut == 8'd19) ? ((1023) >= 30 ? ((1023) + 1)'(64'h4000_4000) : (1023) >= 14 ? ((1023) + 1)'(64'h4000) : ((1023) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(CTI) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.cfg_ti %m slab %0d pin %0d", $bits(CTI), (3) + 1); tt_bad = 1; end if ($bits(dst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.dn_st %m slab %0d pin %0d", $bits(dst[t]), (0) + 1); tt_bad = 1; end if ($bits(dkd[t]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.dn_kind %m slab %0d pin %0d", $bits(dkd[t]), (3) + 1); tt_bad = 1; end if ($bits(dji[t]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.dn_jid %m slab %0d pin %0d", $bits(dji[t]), (7) + 1); tt_bad = 1; end if ($bits(dv[t]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.dn_v %m slab %0d pin %0d", $bits(dv[t]), (15) + 1); tt_bad = 1; end if ($bits(dd[t][0 +: NPS * 512]) != (2559) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.dn_p %m slab %0d pin %0d", $bits(dd[t][0 +: NPS * 512]), (2559) + 1); tt_bad = 1; end if ($bits(s_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.s_v %m slab %0d pin %0d", $bits(s_v), (0) + 1); tt_bad = 1; end if ($bits(p_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.p_v %m slab %0d pin %0d", $bits(p_v), (0) + 1); tt_bad = 1; end if ($bits(c_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.c_v %m slab %0d pin %0d", $bits(c_v), (0) + 1); tt_bad = 1; end if ($bits(c_nv) != (6) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.c_nv %m slab %0d pin %0d", $bits(c_nv), (6) + 1); tt_bad = 1; end if ($bits(c_lt) != (2) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.c_lt %m slab %0d pin %0d", $bits(c_lt), (2) + 1); tt_bad = 1; end if ($bits(c_scale) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.c_scale %m slab %0d pin %0d", $bits(c_scale), (31) + 1); tt_bad = 1; end if ($bits(c_sink) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.c_sink %m slab %0d pin %0d", $bits(c_sink), (63) + 1); tt_bad = 1; end if ($bits(cs_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.cs_v %m slab %0d pin %0d", $bits(cs_v), (0) + 1); tt_bad = 1; end if ($bits(cs_i) != (4) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.cs_i %m slab %0d pin %0d", $bits(cs_i), (4) + 1); tt_bad = 1; end if ($bits(cs_d) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.cs_d %m slab %0d pin %0d", $bits(cs_d), (63) + 1); tt_bad = 1; end if ($bits(e_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.e_v %m slab %0d pin %0d", $bits(e_v), (0) + 1); tt_bad = 1; end if ($bits(e_d) != (1023) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.e_d %m slab %0d pin %0d", $bits(e_d), (1023) + 1); tt_bad = 1; end if ($bits(o_vv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_vi %m slab %0d pin %0d", $bits(o_vv), (0) + 1); tt_bad = 1; end if ($bits(o_dd) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_di %m slab %0d pin %0d", $bits(o_dd), (511) + 1); tt_bad = 1; end if ($bits(hden_v[0]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.den_v %m slab %0d pin %0d", $bits(hden_v[0]), (0) + 1); tt_bad = 1; end if ($bits(f_any) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.f_i %m slab %0d pin %0d", $bits(f_any), (0) + 1); tt_bad = 1; end if ($bits(o_v) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_v %m slab %0d pin %0d", $bits(o_v), (1) + 1); tt_bad = 1; end if ($bits(o_a) != (27) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_a %m slab %0d pin %0d", $bits(o_a), (27) + 1); tt_bad = 1; end if ($bits(o_m) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_m %m slab %0d pin %0d", $bits(o_m), (31) + 1); tt_bad = 1; end if ($bits(o_d) != (1023) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_d %m slab %0d pin %0d", $bits(o_d), (1023) + 1); tt_bad = 1; end if ($bits(o_fu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_fu %m slab %0d pin %0d", $bits(o_fu), (0) + 1); tt_bad = 1; end if ($bits(o_fo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_fo %m slab %0d pin %0d", $bits(o_fo), (0) + 1); tt_bad = 1; end if ($bits(o_alive) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_alive %m slab %0d pin %0d", $bits(o_alive), (0) + 1); tt_bad = 1; end if ($bits(o_den) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_den %m slab %0d pin %0d", $bits(o_den), (0) + 1); tt_bad = 1; end if ($bits(o_rdy) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_rdy %m slab %0d pin %0d", $bits(o_rdy), (0) + 1); tt_bad = 1; end if ($bits(o_rjid) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smt.o_rjid %m slab %0d pin %0d", $bits(o_rjid), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_smt initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_smt u_smt line 516 %m"); $display("  SM_H = %0d", (SM_H)); $display("  SM_LPH = %0d", (SM_LPH)); $display("  S_RD = %0d", (S_RD)); $display("  WS = %0d", (WS)); $display("  MUT = %0d", (MUT)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
            assign f_any = |hf;
            // relayed copies (SRL stations) of the tap's outputs: one copy per destination group
            wire rs_v, rp_v, rc_v, rcs_v; wire [1023:0] rd_d; wire [6:0] rc_nv; wire [2:0] rc_lt; wire [31:0] rc_scale;
            wire [63:0] rc_sink; wire [4:0] rcs_i; wire [63:0] rcs_d;
            ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_tv (.clk(sk), .rst_n(rst[t]), .d({s_v, p_v, c_v, cs_v}),
                .q({rs_v, rp_v, rc_v, rcs_v}));
            ot_hdc_delay #(.W(7 + 3 + 32 + 64 + 5 + 64), .D(SRL)) u_td (.clk(sk), .rst_n(rst[t]),
                .d({c_nv, c_lt, c_scale, c_sink, cs_i, cs_d}), .q({rc_nv, rc_lt, rc_scale, rc_sink, rcs_i, rcs_d}));
            // the stop's operand rows (spine slots 2 TI, 2 TI + 1) straight to the engines: SRL + 2 stations (the tap's
            // pin + valid registers), so they meet their valids at the engines' pin flops
            ot_hdc_delay #(.W(1024), .D(SRL + 2)) u_tdd (.clk(sk), .rst_n(rst[t]), .d(dd[t][1024 * TI +: 1024]), .q(rd_d));
            wire [1:0] he_v; wire [1:0] ho_v;
            genvar h, ln, pp;
            for (h = 0; h < 2; h = h + 1) begin : g_h
                wire [15:0] l_mxv, l_ev, l_es, l_el; wire [511:0] l_mx, l_e;
                wire mv, dv0; wire [31:0] nmb, den;
                wire rmv, rdv; wire [31:0] rnmb, rden;
                ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_rv (.clk(sk), .rst_n(rst[t]), .d({mv, dv0}), .q({rmv, rdv}));
                ot_hdc_delay #(.W(64), .D(SRL)) u_rd (.clk(sk), .rst_n(rst[t]), .d({nmb, den}), .q({rnmb, rden}));
                for (ln = 0; ln < 16; ln = ln + 1) begin : g_l
                    wire sken = (ln == 0);
                    /* SU_TILE_TOPS: ot_s81_su_sml u_sml (slab line 545) */
if (((SM_NVMAX) == (40)) && ((LM) == (5)) && ((LA) == (4))) begin : g_tt0_u_sml
wire [31:0] tt_mut;
dsfd_su_t_sml u_sml (.ck(sk), .rst(rst[t]), .sk_en(sken), .i_cv(rc_v), .i_nv(rc_nv), .i_scale(rc_scale), .i_sink(rc_sink[32 * h +: 32]), .i_sv(rs_v), .i_s(rd_d[512 * h + 32 * ln +: 32]), .i_mv(rmv), .i_nmb(rnmb), .o_mxv(l_mxv[ln]), .o_mx(tt_mut), .o_ev(l_ev[ln]), .o_es(l_es[ln]), .o_el(l_el[ln]), .o_e(l_e[32 * ln +: 32]));
assign l_mx[32 * ln +: 32] = tt_mut ^ ((tmut == 8'd17) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(sken) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.sk_en %m slab %0d pin %0d", $bits(sken), (0) + 1); tt_bad = 1; end if ($bits(rc_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_cv %m slab %0d pin %0d", $bits(rc_v), (0) + 1); tt_bad = 1; end if ($bits(rc_nv) != (6) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_nv %m slab %0d pin %0d", $bits(rc_nv), (6) + 1); tt_bad = 1; end if ($bits(rc_scale) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_scale %m slab %0d pin %0d", $bits(rc_scale), (31) + 1); tt_bad = 1; end if ($bits(rc_sink[32 * h +: 32]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_sink %m slab %0d pin %0d", $bits(rc_sink[32 * h +: 32]), (31) + 1); tt_bad = 1; end if ($bits(rs_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_sv %m slab %0d pin %0d", $bits(rs_v), (0) + 1); tt_bad = 1; end if ($bits(rd_d[512 * h + 32 * ln +: 32]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_s %m slab %0d pin %0d", $bits(rd_d[512 * h + 32 * ln +: 32]), (31) + 1); tt_bad = 1; end if ($bits(rmv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_mv %m slab %0d pin %0d", $bits(rmv), (0) + 1); tt_bad = 1; end if ($bits(rnmb) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.i_nmb %m slab %0d pin %0d", $bits(rnmb), (31) + 1); tt_bad = 1; end if ($bits(l_mxv[ln]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.o_mxv %m slab %0d pin %0d", $bits(l_mxv[ln]), (0) + 1); tt_bad = 1; end if ($bits(l_mx[32 * ln +: 32]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.o_mx %m slab %0d pin %0d", $bits(l_mx[32 * ln +: 32]), (31) + 1); tt_bad = 1; end if ($bits(l_ev[ln]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.o_ev %m slab %0d pin %0d", $bits(l_ev[ln]), (0) + 1); tt_bad = 1; end if ($bits(l_es[ln]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.o_es %m slab %0d pin %0d", $bits(l_es[ln]), (0) + 1); tt_bad = 1; end if ($bits(l_el[ln]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.o_el %m slab %0d pin %0d", $bits(l_el[ln]), (0) + 1); tt_bad = 1; end if ($bits(l_e[32 * ln +: 32]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_sml.o_e %m slab %0d pin %0d", $bits(l_e[32 * ln +: 32]), (31) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_sml initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_sml u_sml line 545 %m"); $display("  NVMAX = %0d", (SM_NVMAX)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
                end
                // lane outputs relayed to the sum / root / tap
                wire rl_mxv, rl_ev, rl_el, rl_skv; wire [511:0] rl_mx, rl_e; wire [31:0] rl_sk;
                ot_hdc_delay #(.W(4), .D(SRL), .RESET(1)) u_lv (.clk(sk), .rst_n(rst[t]),
                    .d({l_mxv[1], l_ev[1], l_el[1], l_ev[0] && l_es[0]}), .q({rl_mxv, rl_ev, rl_el, rl_skv}));
                ot_hdc_delay #(.W(512 + 512 + 32), .D(SRL)) u_ld (.clk(sk), .rst_n(rst[t]), .d({l_mx, l_e, l_e[31:0]}),
                    .q({rl_mx, rl_e, rl_sk}));
                wire c_ov, c_ol; wire [31:0] c_os; wire rc_ov, rc_ol; wire [31:0] rc_os;
                /* SU_TILE_TOPS: ot_s81_su_smc u_smc (slab line 558) */
if (((16) == (16)) && ((LA) == (4))) begin : g_tt0_u_smc
wire [31:0] tt_mut;
dsfd_su_t_smc u_smc (.ck(sk), .rst(rst[t]), .i_v(rl_ev), .i_l(rl_el), .i_e(rl_e), .o_v(c_ov), .o_l(c_ol), .o_s(tt_mut));
assign c_os = tt_mut ^ ((tmut == 8'd15) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(rl_ev) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.i_v %m slab %0d pin %0d", $bits(rl_ev), (0) + 1); tt_bad = 1; end if ($bits(rl_el) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.i_l %m slab %0d pin %0d", $bits(rl_el), (0) + 1); tt_bad = 1; end if ($bits(rl_e) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.i_e %m slab %0d pin %0d", $bits(rl_e), (511) + 1); tt_bad = 1; end if ($bits(c_ov) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.o_v %m slab %0d pin %0d", $bits(c_ov), (0) + 1); tt_bad = 1; end if ($bits(c_ol) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.o_l %m slab %0d pin %0d", $bits(c_ol), (0) + 1); tt_bad = 1; end if ($bits(c_os) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smc.o_s %m slab %0d pin %0d", $bits(c_os), (31) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_smc initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_smc u_smc line 558 %m"); $display("  LPH = %0d", (16)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
                ot_hdc_delay #(.W(2), .D(SRL), .RESET(1)) u_cv (.clk(sk), .rst_n(rst[t]), .d({c_ov, c_ol}), .q({rc_ov, rc_ol}));
                ot_hdc_delay #(.W(32), .D(SRL)) u_cd (.clk(sk), .rst_n(rst[t]), .d(c_os), .q(rc_os));
                /* SU_TILE_TOPS: ot_s81_su_smr u_smr (slab line 562) */
if (((16) == (16)) && ((LA) == (4))) begin : g_tt0_u_smr
wire [31:0] tt_mut;
dsfd_su_t_smr u_smr (.ck(sk), .rst(rst[t]), .i_cv(rc_v), .i_lt(rc_lt), .i_mxv(rl_mxv), .i_mx(rl_mx), .i_skv(rl_skv), .i_sk(rl_sk), .i_vv(rc_ov), .i_vl(rc_ol), .i_vs(rc_os), .o_mv(mv), .o_nmb(tt_mut), .o_dv(dv0), .o_den(den));
assign nmb = tt_mut ^ ((tmut == 8'd18) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(rc_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_cv %m slab %0d pin %0d", $bits(rc_v), (0) + 1); tt_bad = 1; end if ($bits(rc_lt) != (2) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_lt %m slab %0d pin %0d", $bits(rc_lt), (2) + 1); tt_bad = 1; end if ($bits(rl_mxv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_mxv %m slab %0d pin %0d", $bits(rl_mxv), (0) + 1); tt_bad = 1; end if ($bits(rl_mx) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_mx %m slab %0d pin %0d", $bits(rl_mx), (511) + 1); tt_bad = 1; end if ($bits(rl_skv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_skv %m slab %0d pin %0d", $bits(rl_skv), (0) + 1); tt_bad = 1; end if ($bits(rl_sk) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_sk %m slab %0d pin %0d", $bits(rl_sk), (31) + 1); tt_bad = 1; end if ($bits(rc_ov) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_vv %m slab %0d pin %0d", $bits(rc_ov), (0) + 1); tt_bad = 1; end if ($bits(rc_ol) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_vl %m slab %0d pin %0d", $bits(rc_ol), (0) + 1); tt_bad = 1; end if ($bits(rc_os) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.i_vs %m slab %0d pin %0d", $bits(rc_os), (31) + 1); tt_bad = 1; end if ($bits(mv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.o_mv %m slab %0d pin %0d", $bits(mv), (0) + 1); tt_bad = 1; end if ($bits(nmb) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.o_nmb %m slab %0d pin %0d", $bits(nmb), (31) + 1); tt_bad = 1; end if ($bits(dv0) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.o_dv %m slab %0d pin %0d", $bits(dv0), (0) + 1); tt_bad = 1; end if ($bits(den) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smr.o_den %m slab %0d pin %0d", $bits(den), (31) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_smr initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_smr u_smr line 562 %m"); $display("  LPH = %0d", (16)); $display("  LA = %0d", (LA)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
                assign hden_v[h] = rdv;
                // divide engines (one RoPE pair each)
                wire [7:0] d_ov, d_f; wire [255:0] d_o;
                for (pp = 0; pp < 8; pp = pp + 1) begin : g_p
                    wire [2:0] CP = pp;
                    /* SU_TILE_TOPS: ot_s81_su_smd u_smd (slab line 570) */
if (((16) == (16)) && ((LM) == (5)) && ((LA) == (4)) && ((MUT == 5) == (0))) begin : g_tt0_u_smd
wire [31:0] tt_mut;
dsfd_su_t_smd u_smd (.ck(sk), .rst(rst[t]), .cfg_p(CP), .i_pv(rp_v), .i_pa(rd_d[512 * h + 64 * pp +: 64]), .i_dv(rdv), .i_den(rden), .i_csv(rcs_v), .i_csi(rcs_i), .i_csd(rcs_d), .o_ov(d_ov[pp]), .o_o(tt_mut), .o_f(d_f[pp]));
assign d_o[32 * pp +: 32] = tt_mut ^ ((tmut == 8'd16) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(CP) != (2) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.cfg_p %m slab %0d pin %0d", $bits(CP), (2) + 1); tt_bad = 1; end if ($bits(rp_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.i_pv %m slab %0d pin %0d", $bits(rp_v), (0) + 1); tt_bad = 1; end if ($bits(rd_d[512 * h + 64 * pp +: 64]) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.i_pa %m slab %0d pin %0d", $bits(rd_d[512 * h + 64 * pp +: 64]), (63) + 1); tt_bad = 1; end if ($bits(rdv) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.i_dv %m slab %0d pin %0d", $bits(rdv), (0) + 1); tt_bad = 1; end if ($bits(rden) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.i_den %m slab %0d pin %0d", $bits(rden), (31) + 1); tt_bad = 1; end if ($bits(rcs_v) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.i_csv %m slab %0d pin %0d", $bits(rcs_v), (0) + 1); tt_bad = 1; end if ($bits(rcs_i) != (4) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.i_csi %m slab %0d pin %0d", $bits(rcs_i), (4) + 1); tt_bad = 1; end if ($bits(rcs_d) != (63) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.i_csd %m slab %0d pin %0d", $bits(rcs_d), (63) + 1); tt_bad = 1; end if ($bits(d_ov[pp]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.o_ov %m slab %0d pin %0d", $bits(d_ov[pp]), (0) + 1); tt_bad = 1; end if ($bits(d_o[32 * pp +: 32]) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.o_o %m slab %0d pin %0d", $bits(d_o[32 * pp +: 32]), (31) + 1); tt_bad = 1; end if ($bits(d_f[pp]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_smd.o_f %m slab %0d pin %0d", $bits(d_f[pp]), (0) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_smd initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_smd u_smd line 570 %m"); $display("  LPH = %0d", (16)); $display("  LM = %0d", (LM)); $display("  LA = %0d", (LA)); $display("  STALEDEN = %0d", (MUT == 5)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
                end
                assign hf[8 * h +: 8] = d_f;
                // e / o rows to the tap
                wire [255:0] rd_o; wire rd_ov;
                ot_hdc_delay #(.W(1), .D(SRL), .RESET(1)) u_ov (.clk(sk), .rst_n(rst[t]), .d(d_ov[0]), .q(rd_ov));
                ot_hdc_delay #(.W(256), .D(SRL)) u_od (.clk(sk), .rst_n(rst[t]), .d(d_o), .q(rd_o));
                assign e_d[512 * h +: 512] = rl_e;
                assign o_dd[256 * h +: 256] = rd_o;
                assign he_v[h] = rl_ev;
                assign ho_v[h] = rd_ov;
            end
            assign e_v = he_v[0];
            assign o_vv = ho_v[0];
            assign den_v = hden_v[0];
        end else if (TK == 12) begin : g_swt
            assign o_v = 1'b0; assign o_a = 0; assign o_m = 0; assign o_d = 0;
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
            /* SU_TILE_TOPS: ot_s81_su_swt u_swt (slab line 591) */
if (((SW_W) == (1024)) && ((S_RD) == (16)) && ((NSWQ) == (8)) && ((SNCH) == (32))) begin : g_tt0_u_swt
wire [8191:0] tt_c_dn_d_i;
wire [8191:0] tt_c_e_d;
wire [31:0] tt_mut;
dsfd_su_t_swt u_swt (.ck(sk), .rst(rst[t]), .dn_st(dst[t]), .dn_kind(dkd[t]), .dn_gsel(dgs[t]), .dn_fp4(df4[t]), .dn_jid(dji[t]), .dn_v(dv[t]), .dn_dh(tt_c_dn_d_i[8191:4096]), .dn_dl(tt_c_dn_d_i[4095:0]), .i_f(sw_f), .e_dh(tt_c_e_d[8191:4096]), .e_dl(tt_c_e_d[4095:0]), .e_gv(sw_gv), .e_uv(sw_uv), .e_t(sw_t), .e_w(tt_mut), .e_lim(sw_lim), .e_ob(sw_ob), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
assign tt_c_dn_d_i = dd[t];
assign sw_d = tt_c_e_d;
assign sw_w = tt_mut ^ ((tmut == 8'd21) ? ((31) >= 30 ? ((31) + 1)'(64'h4000_4000) : (31) >= 14 ? ((31) + 1)'(64'h4000) : ((31) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(dst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.dn_st %m slab %0d pin %0d", $bits(dst[t]), (0) + 1); tt_bad = 1; end if ($bits(dkd[t]) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.dn_kind %m slab %0d pin %0d", $bits(dkd[t]), (3) + 1); tt_bad = 1; end if ($bits(dgs[t]) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.dn_gsel %m slab %0d pin %0d", $bits(dgs[t]), (1) + 1); tt_bad = 1; end if ($bits(df4[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.dn_fp4 %m slab %0d pin %0d", $bits(df4[t]), (0) + 1); tt_bad = 1; end if ($bits(dji[t]) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.dn_jid %m slab %0d pin %0d", $bits(dji[t]), (7) + 1); tt_bad = 1; end if ($bits(dv[t]) != (15) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.dn_v %m slab %0d pin %0d", $bits(dv[t]), (15) + 1); tt_bad = 1; end if ($bits(dd[t]) != 8192) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt core port dn_d_i %m slab %0d pins %0d", $bits(dd[t]), 8192); tt_bad = 1; end if ($bits(sw_f) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.i_f %m slab %0d pin %0d", $bits(sw_f), (31) + 1); tt_bad = 1; end if ($bits(sw_d) != 8192) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt core port e_d %m slab %0d pins %0d", $bits(sw_d), 8192); tt_bad = 1; end if ($bits(sw_gv) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.e_gv %m slab %0d pin %0d", $bits(sw_gv), (3) + 1); tt_bad = 1; end if ($bits(sw_uv) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.e_uv %m slab %0d pin %0d", $bits(sw_uv), (3) + 1); tt_bad = 1; end if ($bits(sw_t) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.e_t %m slab %0d pin %0d", $bits(sw_t), (11) + 1); tt_bad = 1; end if ($bits(sw_w) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.e_w %m slab %0d pin %0d", $bits(sw_w), (31) + 1); tt_bad = 1; end if ($bits(sw_lim) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.e_lim %m slab %0d pin %0d", $bits(sw_lim), (31) + 1); tt_bad = 1; end if ($bits(sw_ob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.e_ob %m slab %0d pin %0d", $bits(sw_ob), (13) + 1); tt_bad = 1; end if ($bits(o_fu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.o_fu %m slab %0d pin %0d", $bits(o_fu), (0) + 1); tt_bad = 1; end if ($bits(o_fo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.o_fo %m slab %0d pin %0d", $bits(o_fo), (0) + 1); tt_bad = 1; end if ($bits(o_alive) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.o_alive %m slab %0d pin %0d", $bits(o_alive), (0) + 1); tt_bad = 1; end if ($bits(o_den) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.o_den %m slab %0d pin %0d", $bits(o_den), (0) + 1); tt_bad = 1; end if ($bits(o_rdy) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.o_rdy %m slab %0d pin %0d", $bits(o_rdy), (0) + 1); tt_bad = 1; end if ($bits(o_rjid) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_swt.o_rjid %m slab %0d pin %0d", $bits(o_rjid), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_swt initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_swt u_swt line 591 %m"); $display("  SW_W = %0d", (SW_W)); $display("  S_RD = %0d", (S_RD)); $display("  NSQ = %0d", (NSWQ)); $display("  NCH = %0d", (SNCH)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
        end else if (TK == 13) begin : g_swq
            // quant engine TI: lo = the chain heads of pass row 2 TI, hi = row 2 TI + 1 (words {bf16, 16'h0})
            wire [1023:0] x; wire [13:0] rob;
            genvar hc, hj;
            for (hc = 0; hc < 2 * SEPR; hc = hc + 1) begin : g_c
                for (hj = 0; hj < SLPE; hj = hj + 1) begin : g_j
                    assign x[32 * (SLPE * hc + hj) +: 32] =
                        {sc_d[((2 * TI * SEPR + hc) * SNPS) * 16 * SLPE + 16 * hj +: 16], 16'h0000};
                end
            end
            ot_hdc_delay #(.W(14), .D(ERS)) u_ob (.clk(sk), .rst_n(rst[t]), .d(sw_ob), .q(rob));
            localparam integer PN = TI ^ 1;
            localparam integer HL = (2 * TI * SEPR) * SNPS, HH = ((2 * TI + 1) * SEPR) * SNPS;
            wire [3:0] CB = TI;
            /* SU_TILE_TOPS: ot_s81_su_qbe u_qbe (slab line 611) */
if (((SW_W / 32) == (32)) && ((NSWQ) == (8))) begin : g_tt0_u_qbe
wire [1023:0] tt_mut;
dsfd_su_t_qbe u_qbe (.ck(sk), .rst(rst[t]), .cfg_b(CB), .i_vlo(sc_v[HL]), .i_vhi(sc_v[HH]), .i_lo(x[511:0]), .i_hi(x[1023:512]), .i_tlo(sc_t[12 * HL +: 12]), .i_thi(sc_t[12 * HH +: 12]), .i_ob(rob), .i_f4(1'b0), .nx_i_v(snxv[PN]), .nx_i_q(snxq[PN]), .nx_i_e(snxe[PN]), .nx_o_v(snxv[TI]), .nx_o_q(snxq[TI]), .nx_o_e(snxe[TI]), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(tt_mut), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
assign o_d = tt_mut ^ ((tmut == 8'd8) ? ((1023) >= 30 ? ((1023) + 1)'(64'h4000_4000) : (1023) >= 14 ? ((1023) + 1)'(64'h4000) : ((1023) + 1)'(1)) : '0);
bit tt_bad = 0; initial begin if ($bits(sk) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.ck %m slab %0d pin %0d", $bits(sk), (0) + 1); tt_bad = 1; end if ($bits(rst[t]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.rst %m slab %0d pin %0d", $bits(rst[t]), (0) + 1); tt_bad = 1; end if ($bits(CB) != (3) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.cfg_b %m slab %0d pin %0d", $bits(CB), (3) + 1); tt_bad = 1; end if ($bits(sc_v[HL]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_vlo %m slab %0d pin %0d", $bits(sc_v[HL]), (0) + 1); tt_bad = 1; end if ($bits(sc_v[HH]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_vhi %m slab %0d pin %0d", $bits(sc_v[HH]), (0) + 1); tt_bad = 1; end if ($bits(x[511:0]) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_lo %m slab %0d pin %0d", $bits(x[511:0]), (511) + 1); tt_bad = 1; end if ($bits(x[1023:512]) != (511) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_hi %m slab %0d pin %0d", $bits(x[1023:512]), (511) + 1); tt_bad = 1; end if ($bits(sc_t[12 * HL +: 12]) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_tlo %m slab %0d pin %0d", $bits(sc_t[12 * HL +: 12]), (11) + 1); tt_bad = 1; end if ($bits(sc_t[12 * HH +: 12]) != (11) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_thi %m slab %0d pin %0d", $bits(sc_t[12 * HH +: 12]), (11) + 1); tt_bad = 1; end if ($bits(rob) != (13) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_ob %m slab %0d pin %0d", $bits(rob), (13) + 1); tt_bad = 1; end if ($bits(1'b0) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.i_f4 %m slab %0d pin %0d", $bits(1'b0), (0) + 1); tt_bad = 1; end if ($bits(snxv[PN]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_i_v %m slab %0d pin %0d", $bits(snxv[PN]), (0) + 1); tt_bad = 1; end if ($bits(snxq[PN]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_i_q %m slab %0d pin %0d", $bits(snxq[PN]), (255) + 1); tt_bad = 1; end if ($bits(snxe[PN]) != (9) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_i_e %m slab %0d pin %0d", $bits(snxe[PN]), (9) + 1); tt_bad = 1; end if ($bits(snxv[TI]) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_o_v %m slab %0d pin %0d", $bits(snxv[TI]), (0) + 1); tt_bad = 1; end if ($bits(snxq[TI]) != (255) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_o_q %m slab %0d pin %0d", $bits(snxq[TI]), (255) + 1); tt_bad = 1; end if ($bits(snxe[TI]) != (9) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.nx_o_e %m slab %0d pin %0d", $bits(snxe[TI]), (9) + 1); tt_bad = 1; end if ($bits(o_v) != (1) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_v %m slab %0d pin %0d", $bits(o_v), (1) + 1); tt_bad = 1; end if ($bits(o_a) != (27) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_a %m slab %0d pin %0d", $bits(o_a), (27) + 1); tt_bad = 1; end if ($bits(o_m) != (31) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_m %m slab %0d pin %0d", $bits(o_m), (31) + 1); tt_bad = 1; end if ($bits(o_d) != (1023) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_d %m slab %0d pin %0d", $bits(o_d), (1023) + 1); tt_bad = 1; end if ($bits(o_fu) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_fu %m slab %0d pin %0d", $bits(o_fu), (0) + 1); tt_bad = 1; end if ($bits(o_fo) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_fo %m slab %0d pin %0d", $bits(o_fo), (0) + 1); tt_bad = 1; end if ($bits(o_alive) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_alive %m slab %0d pin %0d", $bits(o_alive), (0) + 1); tt_bad = 1; end if ($bits(o_den) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_den %m slab %0d pin %0d", $bits(o_den), (0) + 1); tt_bad = 1; end if ($bits(o_rdy) != (0) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_rdy %m slab %0d pin %0d", $bits(o_rdy), (0) + 1); tt_bad = 1; end if ($bits(o_rjid) != (7) + 1) begin $display("SU_TILE_TOPS_WIDTH dsfd_su_t_qbe.o_rjid %m slab %0d pin %0d", $bits(o_rjid), (7) + 1); tt_bad = 1; end if (tt_bad) begin #1 $fatal(1, "SU_TILE_TOPS width"); end end
end
else begin : g_ttx_u_qbe initial begin $display("SU_TILE_TOPS_NOMATCH ot_s81_su_qbe u_qbe line 611 %m"); $display("  QB_NB = %0d", (SW_W / 32)); $display("  NPB = %0d", (NSWQ)); #1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end
            assign xpv[t] = 1'b0; assign xpi[t] = 8'd0; assign xpd[t] = 32'd0; assign xrv[t] = 1'b0; assign xrd[t] = 32'd0;
        end else begin : g_tl
            initial $display("SU_TILE_TOPS_UNWRAPPED ot_s81_su_tile u_tile %m");
ot_s81_su_tile #(.TK(TK), .TI(TI), .NT(NT), .QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H),
                             .SM_LPH(SM_LPH), .SM_NVMAX(SM_NVMAX), .S_RD(S_RD), .S_WR(S_WR), .LM(LM), .LA(LA), .MUT(MUT)) u_tile (
                .clk(sk), .rst_in(rst[t]),
                .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
                .dn_v_i(dv[t]), .dn_d_i(dd[t]),
                .x_pp_v_i(ipv), .x_pp_i_i(ipi), .x_pp_d_i(ipd), .x_rb_v_i(irv), .x_rb_d_i(ird),
                .x_pp_v_o(xpv[t]), .x_pp_i_o(xpi[t]), .x_pp_d_o(xpd[t]), .x_rb_v_o(xrv[t]), .x_rb_d_o(xrd[t]),
                .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
                .o_rdy(o_rdy), .o_rjid(o_rjid));
        end
        // reset spine station
        reg rs_q;
        always @(posedge sk or negedge rst[t]) if (!rst[t]) rs_q <= 1'b0; else rs_q <= 1'b1;
        assign rst[t + 1] = rs_q;
        // down spine relay station
        ot_hdc_delay #(.W(1 + S_RD), .D(SRD), .RESET(1)) u_dsc (.clk(sk), .rst_n(rst[t]), .d({dst[t], dv[t]}),
                                                               .q({dst[t + 1], dv[t + 1]}));
        ot_hdc_delay #(.W(15 + S_RD * 512), .D(SRD)) u_dsd (.clk(sk), .rst_n(rst[t]),
            .d({dkd[t], dgs[t], df4[t], dji[t], dd[t]}), .q({dkd[t + 1], dgs[t + 1], df4[t + 1], dji[t + 1], dd[t + 1]}));
        // up spine relay station: the tile's window merged in
        integer s;
        reg [S_WR-1:0] uv_q; reg [S_WR*14-1:0] ua_q; reg [S_WR*16-1:0] um_q; reg [S_WR*512-1:0] ud_q;
        reg ufu_q, ufo_q, ual_q, ude_q, urd_q; reg [7:0] urj_q;
        ot_hdc_delay #(.W(S_WR + 13), .D(SRD - 1), .RESET(1)) u_usc (.clk(sk), .rst_n(rst[t]),
            .d({uv_q, ufu_q, ufo_q, ual_q, ude_q, urd_q, urj_q}), .q({uv[t], ufu[t], ufo[t], ual[t], ude[t], urd[t], urj[t]}));
        ot_hdc_delay #(.W(S_WR * 542), .D(SRD - 1)) u_usd (.clk(sk), .rst_n(rst[t]), .d({ua_q, um_q, ud_q}),
                                                          .q({ua[t], um[t], ud[t]}));
        always @(posedge sk) begin
            for (s = 0; s < S_WR; s = s + 1)
                if (s >= W0 && s < W0 + WS && o_v[s - W0]) begin
                    ua_q[14 * s +: 14] <= o_a[14 * (s - W0) +: 14]; um_q[16 * s +: 16] <= o_m[16 * (s - W0) +: 16];
                    ud_q[512 * s +: 512] <= o_d[512 * (s - W0) +: 512];
                end else begin
                    ua_q[14 * s +: 14] <= ua[t + 1][14 * s +: 14]; um_q[16 * s +: 16] <= um[t + 1][16 * s +: 16];
                    ud_q[512 * s +: 512] <= ud[t + 1][512 * s +: 512];
                end
        end
        always @(posedge sk or negedge rst[t]) begin
            if (!rst[t]) begin uv_q <= 0; ufu_q <= 0; ufo_q <= 0; ual_q <= 0; ude_q <= 0; urd_q <= 0; urj_q <= 0; end
            else begin
                for (s = 0; s < S_WR; s = s + 1) uv_q[s] <= uv[t + 1][s] || (s >= W0 && s < W0 + WS && o_v[s - W0]);
                ufu_q <= ufu[t + 1] || o_fu; ufo_q <= ufo[t + 1] || o_fo; ual_q <= ual[t + 1] && o_alive;
                ude_q <= ude[t + 1] && o_den; urd_q <= urd[t + 1] || o_rdy; urj_q <= o_rdy ? o_rjid : urj[t + 1];
            end
        end
    end endgenerate
    assign xpv[NTL] = 1'b0; assign xpi[NTL] = 8'd0; assign xpd[NTL] = 32'd0;
endmodule
