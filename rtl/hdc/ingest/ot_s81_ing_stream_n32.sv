`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_ing_stream_n32 (S81-SHLK12 s10e, 2026-10-20): the native-32 structural successor of ot_hdc_kv_ingest's
// stream-only build used by dsdv_sh_lk (QKV 0, QPIPE 0, AW 32, APIPE 10 = SP stream pipe, with the s10b / s10c / s10d
// changes).  Same ports, same values on the same edges (cycle-exact; checked by tb_s81_ing_n32_lockstep against the
// original engine and by the seqhost / hnp benches).  It exists because the s10c / s10d routes carried 323 mapped roots
// over 32 load pins (native census, Codex 10-20 01:38): one-cycle decisions steering hundreds of flops.
//
// Native-32 discipline used throughout (each a STRUCTURE, not a buffer):
//   * an enabled flop costs TWO load pins on its enable root (the hold mux maps to AO22(en, d, !en, q)), so no enable
//     root steers more than 16 flops;
//   * a combinational root can only be split into REPLICAS computed from DISTINCT kept flop clones (ABC structurally
//     hashes identical logic), so every wide decision is computed per DOMAIN from that domain's own clone leaves;
//   * a clone takes its MASTER's next-state net as D (never an own enable or hold mux), so clones always equal their
//     master and the next-state net drives #clones (<= 30) loads;
//   * a decision that depends on registers only and whose next-state cone is shallow is itself registered (s_disp).
// Structure:
//   descriptor queue  4 x 138 used bits; WRITE-BEHIND: d_data is staged every edge, the entry is written one edge
//                     later through registered per-16-bit-slice enables, and the head reads the staged word when its
//                     entry is still in flight (registered bypass clones); dq_n / d_rdy / the head are unchanged.
//   dispatch          s_disp = (dq_n != 0) && !st_act is a REGISTER family (D = the same on the next state).
//   stream control    ND domains, each with kept clones of every control register (act, pad, mode, phase, ra_n,
//                     st_rem, st_sec, pitch, ap_ok, ap_mine, fq_n, p_wv, low nibbles, beat / left flags); domain d
//                     computes go / pop / kind / row_end / steps and drives one group of master registers.
//   realigner ring    256 B in two ot_sram_1r1w2c_16x257 macros (even / odd 32-B words, rows 0..3): a beat writes one
//                     word of each (same row); every edge both macros read the pair holding the head, so their
//                     registered outputs ARE the old stage-P window register (p_win).  The words being written on the
//                     same edge hold no live byte (the live region ends exactly at the write words), so a colliding
//                     read can only return bytes the head does not use.
//   stage P / O       P registers load every edge (they are read only under p_wv / p_sc); O selects the 40-byte window
//                     from the two macro words (8-way one-hot, 10 kept copies), the 32-byte head (8:1 byte select, 8
//                     kept fine-offset copies), masks / substitutes (4-way one-hot kind, 16 kept copies, 32 byte-mask
//                     flags) and writes the output FIFO.
//   output FIFO       4 x 288 b in 18 slices of 16 b: kept p_wv / one-hot write-pointer / one-hot read-pointer / fq_nz
//                     copies, and the host-side w_rdy as 18 kept copies (w_rdy_c, from ot_rom_host_ingest).
//   completion queue  8 x 40 b, write enables per 16-b slice from kept dq_e2 / one-hot cq_wr copies; three cq_go
//                     replicas (kept cq_n != 0, sp_acc and read-pointer copies).
// MUT (bench negative controls, `OT_N32_MUT_*`): BYP (descriptor bypass clone 3 stuck 0), GOD (domain 2 never steps
// st_row hi), WIN (window one-hot copy 4 selects the wrong pair word), KIND (kind copy 5 never substitutes sc_acc),
// FQS (write-pointer copy 7 never advances), CQR (completion replica C ignores the count).
// ---------------------------------------------------------------------------------------------------------------------
// S81-SHLK-1021 (default off): OT_S81_SH_P192 selects the Codex p192 contact-pitch masters (accd38c70; 0.192-um pin
// pitch = 5.2 pins/um on the side faces instead of ~10/um) under the same names' exact behaviour (body byte-equal).
`ifndef OT_SH_M257
`ifdef OT_S81_SH_P192
`define OT_SH_M257 ot_sram_1r1w2c_16x257_m1_p192
`define OT_SH_M289 ot_sram_1r1w2c_16x289_m1_p192
`else
`define OT_SH_M257 ot_sram_1r1w2c_16x257_m1
`define OT_SH_M289 ot_sram_1r1w2c_16x289_m1
`endif
`endif
module ot_s81_ing_stream_n32 #(
    parameter integer AW = 32,
    parameter integer NWR = 18                      // w_rdy copies = output-FIFO slices
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              d_v,
    output wire              d_rdy,
    input  wire [255:0]      d_data,
    input  wire              in_v,
    output wire              in_rdy,
    input  wire [511:0]      in_data,
    output wire              w_v,
    input  wire              w_rdy,
    input  wire [NWR-1:0]    w_rdy_c,               // kept copies of w_rdy (same value every cycle)
    output wire [AW-1:0]     w_addr,
    output wire [255:0]      w_data,
    output wire              r_v,
    input  wire              r_rdy,
    output wire [AW-1:0]     r_addr,
    input  wire              rd_v,
    input  wire [255:0]      rd_data,
    output wire              done_v,
    output wire [7:0]        done_tag,
    output wire              busy,
    output wire [31:0]       n_sectors,
    output reg  [31:0]       n_beats,
    // second-replica status for the host head's hx_pop replica B (same values as d_rdy / in_rdy / busy / w_v)
    output wire              drdy_b,
    output wire              inrdy_b,
    output wire              busy_b,
    output wire              wv_b
);
    localparam [3:0] M_RAW = 4'd0, M_ROWS = 4'd2, M_IKEY = 4'd3;
    genvar gi, gj;
    integer i, j;
`ifndef SYNTHESIS
    initial if (AW != 32 || NWR != 18) $fatal(1, "ot_s81_ing_stream_n32: AW 32 / NWR 18 only");
`endif
    assign r_v = 1'b0; assign r_addr = {AW{1'b0}};

    // =================================================================================================================
    // descriptor fields kept for the stream path (QKV absent): 138 bits
    //   [0] fence d[7]  [8:1] tag d[15:8]  [40:9] a0 d[47:16]  [72:41] a1 d[79:48]  [77:73] pitch d[84:80]
    //   [109:78] ring d[143:112]  [125:110] rb d[183:168]  [127:126] ldie d[217:216]  [135:128] die d[231:224]
    //   [137:136] lns d[233:232]
    // =================================================================================================================
    localparam integer SDW = 138, SDS = (SDW + 15) / 16;     // 9 slices
    function automatic [SDW-1:0] sd_pack(input [255:0] d);
        sd_pack = {d[233:232], d[231:224], d[217:216], d[183:168], d[143:112], d[84:80], d[79:48], d[47:16], d[15:8], d[7]};
    endfunction
    // queue entry = stream fields + mode d[3:0] + n0 d[167:144] + n2 d[199:184] + nb d[255:240] + 4 copies of (mode == RAW)
    // (+ a second n0 copy for the left load value)
    localparam integer HW = SDW + 4 + 24 + 16 + 16 + 6 + 24;  // 228
    localparam integer QS = 12;                              // queue slice: <= 12 flops a slice copy
    localparam integer HS = (HW + QS - 1) / QS;              // 19 slices
    function automatic [HW-1:0] h_pack(input [255:0] d);
        h_pack = {d[167:144], {6{d[3:0] == M_RAW}}, d[255:240], d[199:184], d[167:144], d[3:0], sd_pack(d)};
    endfunction

    // =================================================================================================================
    // descriptor queue (write-behind)
    // =================================================================================================================
    reg  [2:0]   dq_n;
    reg  [1:0]   dq_rd, dq_wr;
    reg          sdisp;                              // master s_disp (registered: (dq_n != 0) && !st_act)
    wire         d_we = d_v && (dq_n < 3'd4);
    assign       d_rdy = dq_n < 3'd4;
    wire [1:0]   dq_rd_nx = dq_rd + (sdisp ? 2'd1 : 2'd0);
    wire [2:0]   dq_n_nx  = dq_n + (d_we ? 3'd1 : 3'd0) - (sdisp ? 3'd1 : 3'd0);
    // kept: the duplicated fields (RAW flags, n0 copies) must stay distinct flops
    (* keep *) reg [HW-1:0]   dqs;                       // staged d_data (every edge)
    (* keep *) reg [4*HW-1:0] dqm;                       // entry e = dqm[e*HW +: HW]
    (* keep *) reg [4*HS-1:0] dq_we_c;                   // [e*HS + s]: entry e slice s written on this edge
    (* keep *) reg [HS-1:0]   dq_byp_c;                  // the head entry is the staged one (not yet written)
    (* keep *) reg [4*HS-1:0] dq_roh_c;                  // one-hot read pointer, one copy per slice
    always @(posedge clk) dqs <= h_pack(d_data);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            dq_we_c <= '0; dq_byp_c <= '0;
            for (i = 0; i < HS; i = i + 1) dq_roh_c[4*i +: 4] <= 4'b0001;
        end else begin
            for (i = 0; i < 4; i = i + 1) for (j = 0; j < HS; j = j + 1) dq_we_c[i*HS + j] <= d_we && (dq_wr == i);
`ifdef OT_N32_MUT_BYP
            for (j = 0; j < HS; j = j + 1) dq_byp_c[j] <= (j == 3) ? 1'b0 : (d_we && dq_wr == dq_rd_nx);   // mutant
`else
            dq_byp_c <= {HS{d_we && dq_wr == dq_rd_nx}};
`endif
            for (j = 0; j < HS; j = j + 1) dq_roh_c[4*j +: 4] <= 4'b0001 << dq_rd_nx;
        end
    for (gi = 0; gi < HS; gi = gi + 1) begin : g_dqw
        localparam integer LO = QS * gi, NB = (QS * gi + QS > HW) ? HW - QS * gi : QS;
        integer e;
        always @(posedge clk) for (e = 0; e < 4; e = e + 1) if (dq_we_c[e*HS + gi]) dqm[e*HW + LO +: NB] <= dqs[LO +: NB];
    end
    wire [HW-1:0] dh;
    for (gi = 0; gi < HS; gi = gi + 1) begin : g_dh
        localparam integer LO = QS * gi, NB = (QS * gi + QS > HW) ? HW - QS * gi : QS;
        wire [3:0] oh = dq_roh_c[4*gi +: 4];
        wire [NB-1:0] rq = ({NB{oh[0]}} & dqm[0*HW + LO +: NB]) | ({NB{oh[1]}} & dqm[1*HW + LO +: NB])
                         | ({NB{oh[2]}} & dqm[2*HW + LO +: NB]) | ({NB{oh[3]}} & dqm[3*HW + LO +: NB]);
        assign dh[LO +: NB] = dq_byp_c[gi] ? dqs[LO +: NB] : rq;
    end
    wire [SDW-1:0] dh_sd   = dh[SDW-1:0];
    wire [3:0]     dh_mode = dh[SDW +: 4];
    wire [23:0]    dh_n0   = dh[SDW + 4 +: 24];
    wire [15:0]    dh_n2   = dh[SDW + 28 +: 16];
    wire [15:0]    dh_nb   = dh[SDW + 44 +: 16];
    wire [5:0]     dh_raw  = dh[SDW + 60 +: 6];          // six copies of (mode == RAW), one per 8-b load group
    wire [23:0]    dh_n0l  = dh[SDW + 66 +: 24];         // second n0 copy (left load)
    wire           dh_v    = dq_n != 3'd0;

    // =================================================================================================================
    // stream control: master registers, registered dispatch family, ND clone domains
    // =================================================================================================================
    reg          st_act, st_pad;
    reg  [3:0]   st_mode;
    reg  [SDW-1:0] sdf;                                  // the segment's descriptor fields
    reg  [31:0]  st_row, st_left;
    reg  [15:0]  st_rem, st_beats;
    reg  [4:0]   st_sec;
    reg  [2:0]   st_ph;
    reg  [8:0]   ra_n;
    reg  [7:0]   ra_rp;
    reg  [1:0]   ra_wq;                                  // write pair (words 2 ra_wq, 2 ra_wq + 1)
    reg          done_r;
    reg  [7:0]   dtag_r;
    reg          ap_ok, ap_mine;
    reg  [2:0]   fq_n;
    reg          p_wv, p_sc;
    // s10b split row / left steps (registered hi +- 1)
    reg  [27:0]  sr_hp1, sl_hm1;
    reg  [13:0]  sr_alo, sr_ahi, sl_alo, sl_ahi, sr_asrc, sl_asrc;
    reg          sr_ac, sl_ac;
    // segment load values (four RAW-flag copies select the four 16-b / 8-b groups)
    wire [31:0]  row_ld  = {8'd0, dh_raw[2] ? 8'd0 : dh_n0[23:16], dh_raw[1] ? 8'd0 : dh_n0[15:8], dh_raw[0] ? 8'd0 : dh_n0[7:0]};
    wire [31:0]  left_ld = {8'd0, dh_raw[5] ? dh_n0l[23:16] : 8'd0, dh_raw[4] ? dh_n0l[15:8] : dh_n2[15:8], dh_raw[3] ? dh_n0l[7:0] : dh_n2[7:0]};
    // descriptor field views
    wire         f_fence = sdf[0];
    wire [7:0]   f_tag   = sdf[8:1];
    wire [31:0]  f_a0    = sdf[40:9];
    wire [31:0]  f_a1    = sdf[72:41];
    wire [4:0]   f_pitch = sdf[77:73];
    wire [31:0]  f_ring  = sdf[109:78];
    wire [15:0]  f_rb    = sdf[125:110];
    wire [7:0]   f_die   = sdf[135:128];

    // ---- master in-cycle signals (inputs and register-only terms)
    wire bnz      = st_beats != 16'd0;
    wire ra_push  = st_act && !st_pad && in_v && (ra_n <= 9'd192) && bnz;
    wire pad_take = st_act && st_pad && in_v && bnz;
    wire pad_end  = st_pad && (!bnz || (pad_take && st_beats == 16'd1));
    assign in_rdy = st_act && (st_pad ? bnz : ((ra_n <= 9'd192) && bnz));
    wire push_or_pad = ra_push || pad_take;

    // ---- clone domains: every leaf is a kept clone of a master (D = the master's next state)
    //   act pad raw rows ikey ph3 ran9 rem16 sec5 pitch5 mine apok fqn3 pwv rlo4 llo4 left1 left0
    localparam integer ND = 10;
    localparam integer LV = 1+1+3+3+9+16+5+5+1+1+3+1+4+4+1+1;   // 59
    (* keep *) reg [ND*LV-1:0] dl;
    wire [ND-1:0]     d_go, d_wv, d_step, d_pad_set, d_raw, d_rows, d_ikey, d_go_ikey_ph2, d_rlo_f, d_llo_0;
    wire [ND*6-1:0]   d_pop, d_take;
    wire [ND*2-1:0]   d_kind;
    wire [ND*16-1:0]  d_rem_nx;
    wire [ND*5-1:0]   d_sec_nx;
    wire [ND*3-1:0]   d_ph_nx;
    for (gi = 0; gi < ND; gi = gi + 1) begin : g_dom
        wire [LV-1:0] l = dl[gi*LV +: LV];
        wire       act = l[0], pad = l[1], raw = l[2], rows = l[3], ikey = l[4];
        wire [2:0] ph = l[7:5];
        wire [8:0] ran = l[16:8];
        wire [15:0] rem = l[32:17];
        wire [4:0] sec = l[37:33];
        wire [4:0] pit = l[42:38];
        wire       mine = l[43], apok = l[44];
        wire [2:0] fqn = l[47:45];
        wire       pwv = l[48];
        wire [3:0] rlo = l[52:49];
        wire [3:0] llo = l[56:53];
        wire       left1 = l[57], left0 = l[58];
        wire [5:0] take = (rem > 16'd32) ? 6'd32 : rem[5:0];
        wire       ap_go = apok || raw;
        reg  [5:0] pop; reg wv, adv; reg [1:0] kind;
        always @* begin
            pop = 6'd0; wv = 1'b0; adv = 1'b0; kind = 2'd0;
            if (act && !pad && ap_go) begin
                if (raw) begin
                    if (ran >= 9'd32) begin pop = 6'd32; wv = 1'b1; adv = 1'b1; end
                end else if (rows) begin
                    if (ran >= {3'd0, take}) begin pop = take; adv = 1'b1; wv = mine; kind = (take == 6'd32) ? 2'd0 : 2'd1; end
                end else if (ikey) begin
                    if (ph < 3'd2) begin
                        if (ran >= 9'd32) begin pop = 6'd32; adv = 1'b1; wv = mine; end
                    end else if (ph == 3'd2) begin
                        if (ran >= 9'd4) begin pop = 6'd4; adv = 1'b1; end
                    end else begin
                        adv = 1'b1; wv = mine; kind = ph[0] ? 2'd2 : 2'd3;
                    end
                end
            end
        end
        wire room = ({1'b0, fqn} + (pwv ? 4'd1 : 4'd0)) <= 4'd3;
        wire go = adv && (!wv || room);
        wire row_end = mine ? ({1'b0, sec} + 6'd1 >= {1'b0, pit}) : (rem <= 16'd32);
        wire ik_step = (ph == 3'd2 && rlo != 4'd15) || ph == 3'd4;
        wire step = go && (raw || (rows && row_end) || (ikey && ik_step));
        assign d_go[gi] = go; assign d_wv[gi] = wv; assign d_step[gi] = step;
        assign d_pad_set[gi] = go && left1 && (raw || (rows && row_end) || (ikey && ph == 3'd4));
        assign d_raw[gi] = raw; assign d_rows[gi] = rows; assign d_ikey[gi] = ikey;
        assign d_go_ikey_ph2[gi] = go && ikey && ph == 3'd2;
        assign d_rlo_f[gi] = rlo == 4'hf; assign d_llo_0[gi] = llo == 4'h0;
        assign d_pop[gi*6 +: 6] = go ? pop : 6'd0;
        assign d_take[gi*6 +: 6] = take;
        assign d_kind[gi*2 +: 2] = kind;
        assign d_rem_nx[gi*16 +: 16] = (rows && go) ? (row_end ? f_rb : rem - {10'd0, take}) : rem;
        assign d_sec_nx[gi*5 +: 5]   = (rows && go) ? (row_end ? 5'd0 : (mine ? sec + 5'd1 : sec)) : sec;
        assign d_ph_nx[gi*3 +: 3]    = (ikey && go) ? ((ph == 3'd2) ? ((rlo == 4'd15) ? 3'd3 : 3'd0) : (ph == 3'd4) ? 3'd0 : ph + 3'd1) : ph;
    end
    // domain roles: 0 ring / P stage / ap_inval, 1 st_row lo, 2 st_row hi, 3 st_left lo, 4 st_left hi, 5 st_rem,
    // 6 st_sec / st_ph / st_pad, 7 P-stage kind copies / byte mask, 8 st_row[3:0] / st_left[3:0]
    wire        go0 = d_go[0];
    wire [5:0]  pop0 = d_pop[0 +: 6];
    wire        ap_inval = sdisp || (d_step[0] && !d_raw[0]);

    // ---- registered dispatch family (D = (dq_n != 0) && !st_act of the next state)
    localparam integer NSD = SDS + 15;
    (* keep *) reg [NSD-1:0] sdc;
    wire sd_row_lo = sdc[SDS + 0], sd_row_hi = sdc[SDS + 1], sd_left_lo = sdc[SDS + 2], sd_left_hi = sdc[SDS + 3];
    wire sd_rem = sdc[SDS + 4], sd_beats = sdc[SDS + 5], sd_misc = sdc[SDS + 6];
    wire sd_sr0 = sdc[SDS + 7], sd_sr1 = sdc[SDS + 8], sd_sr2 = sdc[SDS + 9], sd_sr3 = sdc[SDS + 10];
    wire sd_cl = sdc[SDS + 11], sd_pit = sdc[SDS + 12], sd_cl1 = sdc[SDS + 13], sd_cl2 = sdc[SDS + 14];

    // ---- master next state (each register: its own dispatch copy + its own control domain)
    wire         st_act_nx   = sdisp ? 1'b1 : pad_end ? 1'b0 : st_act;
    wire         st_pad_nx   = sdisp ? 1'b0 : pad_end ? 1'b0 : (d_pad_set[6] || (st_act && !st_pad && st_left == 32'd0)) ? 1'b1 : st_pad;
    wire [3:0]   st_mode_nx  = sd_misc ? dh_mode : st_mode;
    wire [2:0]   st_ph_nx    = sd_misc ? 3'd0 : d_ph_nx[6*3 +: 3];
    wire [4:0]   st_sec_nx   = sd_misc ? 5'd0 : d_sec_nx[6*5 +: 5];
    wire [15:0]  st_rem_nx   = sd_rem ? dh_sd[125:110] : d_rem_nx[5*16 +: 16];
    wire [15:0]  st_beats_nx = sd_beats ? dh_nb : push_or_pad ? st_beats - 16'd1 : st_beats;
    wire [8:0]   ra_n_nx     = st_pad ? 9'd0 : ra_n + (ra_push ? 9'd64 : 9'd0) - {3'd0, pop0};
    wire [7:0]   ra_rp_nx    = st_pad ? 8'd0 : ra_rp + {2'd0, pop0};
    wire [4:0]   pit_nx      = sd_pit ? dh_sd[77:73] : f_pitch;
    // st_row / st_left: lo 16 bits by domains 1 / 3, hi 16 by 2 / 4 (each with its own hi-carry compare leaf)
    wire [15:4]  row_inc_lo  = d_rlo_f[1] ? sr_hp1[11:0] : st_row[15:4];
    wire [15:0]  row_inc_hi  = d_rlo_f[2] ? sr_hp1[27:12] : st_row[31:16];
    wire [15:4]  left_dec_lo = d_llo_0[3] ? sl_hm1[11:0] : st_left[15:4];
    wire [15:0]  left_dec_hi = d_llo_0[4] ? sl_hm1[27:12] : st_left[31:16];
    wire [31:0]  st_row_nx, st_left_nx;
    assign st_row_nx[3:0]    = sd_row_lo  ? row_ld[3:0]    : d_step[8] ? st_row[3:0] + 4'd1 : st_row[3:0];
    assign st_row_nx[15:4]   = sd_row_lo  ? row_ld[15:4]   : d_step[1] ? row_inc_lo  : st_row[15:4];
`ifdef OT_N32_MUT_GOD
    assign st_row_nx[31:16]  = sd_row_hi  ? row_ld[31:16]  : st_row[31:16];                    // mutant: hi never steps
`else
    assign st_row_nx[31:16]  = sd_row_hi  ? row_ld[31:16]  : d_step[2] ? row_inc_hi  : st_row[31:16];
`endif
    assign st_left_nx[3:0]   = sd_left_lo ? left_ld[3:0]   : d_step[8] ? st_left[3:0] - 4'd1 : st_left[3:0];
    assign st_left_nx[9:4]   = sd_left_lo ? left_ld[9:4]   : d_step[3] ? left_dec_lo[9:4]   : st_left[9:4];
    assign st_left_nx[15:10] = sd_left_lo ? left_ld[15:10] : d_step[9] ? left_dec_lo[15:10] : st_left[15:10];
    assign st_left_nx[31:16] = sd_left_hi ? left_ld[31:16] : d_step[4] ? left_dec_hi : st_left[31:16];
    wire sdisp_nx = (dq_n_nx != 3'd0) && !st_act_nx;

    // ---- master registers
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            dq_n <= 3'd0; dq_rd <= 2'd0; dq_wr <= 2'd0; sdisp <= 1'b0; sdc <= '0;
            st_act <= 1'b0; st_pad <= 1'b0; st_mode <= 4'd0; st_ph <= 3'd0; st_sec <= 5'd0; st_rem <= 16'd0;
            st_beats <= 16'd0; st_row <= 32'd0; st_left <= 32'd0; ra_n <= 9'd0; ra_rp <= 8'd0; ra_wq <= 2'd0;
            done_r <= 1'b0; dtag_r <= 8'd0; n_beats <= 32'd0;
        end else begin
            dq_n <= dq_n_nx; dq_rd <= dq_rd_nx; dq_wr <= dq_wr + (d_we ? 2'd1 : 2'd0);
            sdisp <= sdisp_nx; sdc <= {NSD{sdisp_nx}};
            st_act <= st_act_nx; st_pad <= st_pad_nx; st_mode <= st_mode_nx; st_ph <= st_ph_nx; st_sec <= st_sec_nx;
            st_rem <= st_rem_nx; st_beats <= st_beats_nx; st_row <= st_row_nx; st_left <= st_left_nx;
            ra_n <= ra_n_nx; ra_rp <= ra_rp_nx;
            ra_wq <= st_pad ? 2'd0 : ra_push ? ra_wq + 2'd1 : ra_wq;
            done_r <= pad_end && f_fence;
            if (pad_end && f_fence) dtag_r <= f_tag;
            if (push_or_pad) n_beats <= n_beats + 32'd1;
        end
    // the segment's descriptor fields: 16-bit slices, each loaded by its own dispatch copy
    for (gi = 0; gi < SDS; gi = gi + 1) begin : g_sdf
        localparam integer LO = 16 * gi, NB = (16 * gi + 16 > SDW) ? SDW - 16 * gi : 16;
        always @(posedge clk) if (sdc[gi]) sdf[LO +: NB] <= dh_sd[LO +: NB];
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && sdisp && dh_mode == 4'd1)
        $fatal(1, "ot_s81_ing_stream_n32: a QKV descriptor reached the stream-only engine (the host wrapper fails it closed)");
    always @(posedge clk) if (rst_n && (sdc != {NSD{sdisp}})) $fatal(1, "ot_s81_ing_stream_n32: dispatch copy diverged");
`endif

    // ---- s10b row / left hi +- 1 pipe (exact for all 32 bits); load / refresh enables per 14-bit slice
    (* keep *) reg [3:0] sr_hold_c;
    wire [27:0] sr_ld = row_ld[31:4] + 28'd1;
    wire [27:0] sl_ld = left_ld[31:4] - 28'd1;
    wire [27:0] sr_rf = {sr_ac ? sr_ahi : sr_asrc, sr_alo};
    wire [27:0] sl_rf = {sl_ac ? sl_ahi : sl_asrc, sl_alo};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            sr_hp1 <= 28'd1; sl_hm1 <= {28{1'b1}}; sr_hold_c <= 4'd0;
            sr_alo <= 14'd1; sr_ahi <= 14'd1; sr_asrc <= 14'd0; sr_ac <= 1'b0;
            sl_alo <= {14{1'b1}}; sl_ahi <= {14{1'b1}}; sl_asrc <= 14'd0; sl_ac <= 1'b1;
        end else begin
            sr_alo <= st_row[17:4] + 14'd1;  sr_ac <= &st_row[17:4];        sr_ahi <= st_row[31:18] + 14'd1;  sr_asrc <= st_row[31:18];
            sl_alo <= st_left[17:4] - 14'd1; sl_ac <= (st_left[17:4] == 14'd0); sl_ahi <= st_left[31:18] - 14'd1; sl_asrc <= st_left[31:18];
            sr_hold_c <= {4{sdisp}};
            if (sd_sr0) sr_hp1[13:0]  <= sr_ld[13:0];  else if (!sr_hold_c[0]) sr_hp1[13:0]  <= sr_rf[13:0];
            if (sd_sr1) sr_hp1[27:14] <= sr_ld[27:14]; else if (!sr_hold_c[1]) sr_hp1[27:14] <= sr_rf[27:14];
            if (sd_sr2) sl_hm1[13:0]  <= sl_ld[13:0];  else if (!sr_hold_c[2]) sl_hm1[13:0]  <= sl_rf[13:0];
            if (sd_sr3) sl_hm1[27:14] <= sl_ld[27:14]; else if (!sr_hold_c[3]) sl_hm1[27:14] <= sl_rf[27:14];
        end

    // =================================================================================================================
    // address pipeline (APIPE 10: A0 -> A1 -> X -> B0 -> B); each stage's hold enable as per-16-bit-slice clones
    // =================================================================================================================
    (* keep *) reg [31:0] row_c;                         // clone of st_row for the row decomposition
    // one-hot ldie / lns clones (3 each: shifter halves, masks) and 8 ring==0 clones, loaded with the segment
    (* keep *) reg [11:0] ldoh_c, lnoh_c;
    (* keep *) reg [9:0]  ringz_c;
    always @(posedge clk or negedge rst_n) if (!rst_n) row_c <= 32'd0; else row_c <= st_row_nx;
    always @(posedge clk) if (sd_cl)  ldoh_c <= {3{4'b0001 << dh_sd[127:126]}};
    always @(posedge clk) if (sd_cl1) lnoh_c <= {3{4'b0001 << dh_sd[137:136]}};
    always @(posedge clk) if (sd_cl2) ringz_c <= {10{dh_sd[109:78] == 32'd0}};
    wire [31:0] s_grp  = row_c >> 4;
    wire [31:0] ldm    = ldoh_c[9] ? 32'd1 : ldoh_c[10] ? 32'd3 : ldoh_c[11] ? 32'd7 : 32'd0;    // (1 << ldie) - 1
    wire        s_mine = ldoh_c[8] || ((s_grp & ldm) == {24'd0, f_die});
    wire [31:0] s_grp1 = s_grp >> 1, s_grp2 = s_grp >> 2, s_grp3 = s_grp >> 3;
    wire [31:0] s_gd;
    assign s_gd[15:0]  = ({16{ldoh_c[0]}} & s_grp[15:0])  | ({16{ldoh_c[1]}} & s_grp1[15:0])  | ({16{ldoh_c[2]}} & s_grp2[15:0])  | ({16{ldoh_c[3]}} & s_grp3[15:0]);
    assign s_gd[31:16] = ({16{ldoh_c[4]}} & s_grp[31:16]) | ({16{ldoh_c[5]}} & s_grp1[31:16]) | ({16{ldoh_c[6]}} & s_grp2[31:16]) | ({16{ldoh_c[7]}} & s_grp3[31:16]);
    wire [2:0]  lnm    = lnoh_c[9] ? 3'd1 : lnoh_c[10] ? 3'd3 : lnoh_c[11] ? 3'd7 : 3'd0;       // (1 << lns) - 1
    wire [2:0]  s_stk  = s_gd[2:0] & lnm;
    wire [31:0] s_gd1 = s_gd >> 1, s_gd2 = s_gd >> 2, s_gd3 = s_gd >> 3;
    wire [31:0] s_gs;
    assign s_gs[15:0]  = ({16{lnoh_c[0]}} & s_gd[15:0])  | ({16{lnoh_c[1]}} & s_gd1[15:0])  | ({16{lnoh_c[2]}} & s_gd2[15:0])  | ({16{lnoh_c[3]}} & s_gd3[15:0]);
    assign s_gs[31:16] = ({16{lnoh_c[4]}} & s_gd[31:16]) | ({16{lnoh_c[5]}} & s_gd1[31:16]) | ({16{lnoh_c[6]}} & s_gd2[31:16]) | ({16{lnoh_c[7]}} & s_gd3[31:16]);
    wire [31:0] s_lr = row_c & (f_ring - 32'd1), s_lg = (s_gs << 4) | (row_c & 32'd15);
    wire [31:0] s_local = {!ringz_c[9] ? s_lr[31:24] : s_lg[31:24], !ringz_c[8] ? s_lr[23:16] : s_lg[23:16],
                           !ringz_c[1] ? s_lr[15:8] : s_lg[15:8], !ringz_c[0] ? s_lr[7:0] : s_lg[7:0]};
    function automatic [31:0] ppx(input zl, input zh, input st, input [31:0] v);
        ppx = {(zh && st) ? v[31:16] : 16'd0, (zl && st) ? v[15:0] : 16'd0};
    endfunction
    reg ap_ok0, ap_ok1, ap_okx, ap_okb;
    wire ap_ok0_nx = ap_inval ? 1'b0 : st_act;
    wire ap_ok1_nx = ap_inval ? 1'b0 : (st_act && ap_ok0);
    wire ap_okx_nx = ap_inval ? 1'b0 : (st_act && ap_ok1);
    wire ap_okb_nx = ap_inval ? 1'b0 : (st_act && ap_okx);
    wire ap_ok_nx  = ap_inval ? 1'b0 : (st_act && ap_okb);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ap_ok0 <= 1'b0; ap_ok1 <= 1'b0; ap_okx <= 1'b0; ap_okb <= 1'b0; ap_ok <= 1'b0; end
        else begin ap_ok0 <= ap_ok0_nx; ap_ok1 <= ap_ok1_nx; ap_okx <= ap_okx_nx; ap_okb <= ap_okb_nx; ap_ok <= ap_ok_nx; end
    // stage A0: {pp2, pp1, pp0, mine, pitch, row, gs, local, stk, ringz, stride, base}
    localparam integer A0W = 32+32+1+3+32+32+32+5+1+32+32+32;   // 266
    wire [A0W-1:0] a0_in = {ppx(ringz_c[6], ringz_c[7], s_stk[2], f_a1 << 2), ppx(ringz_c[4], ringz_c[5], s_stk[1], f_a1 << 1),
                            ppx(ringz_c[2], ringz_c[3], s_stk[0], f_a1), s_mine, f_pitch, row_c, s_gs, s_local, s_stk,
                            1'b0, f_a1, f_a0};
    localparam integer AS = 12;                          // address-stage slice: <= 12 flops an enable copy
    localparam integer A0S = (A0W + AS - 1) / AS;        // 23 (+1 copy for the pitch clones)
    (* keep *) reg [A0S+1:0] ok0_c;
    reg [A0W-1:0] a0;
    always @(posedge clk or negedge rst_n) if (!rst_n) ok0_c <= '0; else ok0_c <= {(A0S+2){ap_ok0_nx}};
    for (gi = 0; gi < A0S; gi = gi + 1) begin : g_a0
        localparam integer LO = AS * gi, NB = (AS * gi + AS > A0W) ? A0W - AS * gi : AS;
        always @(posedge clk) if (!ok0_c[gi]) a0[LO +: NB] <= a0_in[LO +: NB];
    end
    wire [31:0] ap0_base = a0[31:0];
    wire [31:0] ap0_local = a0[99:68], ap0_gs = a0[131:100], ap0_row = a0[163:132];
    wire [4:0]  ap0_pitch = a0[168:164];
    wire        ap0_mine = a0[169];
    wire [31:0] ap0_pp0 = a0[201:170], ap0_pp1 = a0[233:202], ap0_pp2 = a0[265:234];
    (* keep *) reg [19:0] pitch_c;                       // pitch clones, one per product quarter (8 bits)
    always @(posedge clk) if (!ok0_c[A0S])   pitch_c[9:0]   <= {2{f_pitch}};
    always @(posedge clk) if (!ok0_c[A0S+1]) pitch_c[19:10] <= {2{f_pitch}};
    function automatic [31:0] pmul(input [31:0] v, input [19:0] pc, input integer k0, input integer k1);
        integer k; reg [31:0] acc, sh;
        begin
            acc = 32'd0;
            for (k = k0; k <= k1; k = k + 1) begin
                sh = v << (k - k0);
                acc = acc + {pc[15+k] ? sh[31:24] : 8'd0, pc[10+k] ? sh[23:16] : 8'd0, pc[5+k] ? sh[15:8] : 8'd0, pc[k] ? sh[7:0] : 8'd0};
            end
            pmul = acc;
        end
    endfunction
    // stage A1: {lph, lp, mine, pitch, row, gs, local, rbase}
    localparam integer A1W = 32+32+32+32+5+1+32+32;      // 198
    wire [A1W-1:0] a1_in = {pmul(ap0_local, pitch_c, 3, 4), pmul(ap0_local, pitch_c, 0, 2), ap0_mine, ap0_pitch,
                            ap0_row, ap0_gs, ap0_local, ap0_base + ap0_pp0 + ap0_pp1 + ap0_pp2};
    localparam integer A1S = (A1W + AS - 1) / AS;
    (* keep *) reg [A1S-1:0] ok1_c;
    reg [A1W-1:0] a1;
    always @(posedge clk or negedge rst_n) if (!rst_n) ok1_c <= '0; else ok1_c <= {A1S{ap_ok1_nx}};
    for (gi = 0; gi < A1S; gi = gi + 1) begin : g_a1
        localparam integer LO = AS * gi, NB = (AS * gi + AS > A1W) ? A1W - AS * gi : AS;
        always @(posedge clk) if (!ok1_c[gi]) a1[LO +: NB] <= a1_in[LO +: NB];
    end
    wire [31:0] ap1_rbase = a1[31:0], ap1_gs = a1[95:64], ap1_row = a1[127:96];
    wire        ap1_mine = a1[133];
    wire [31:0] ap1_lp = a1[165:134], ap1_lph = a1[197:166];
    wire [31:0] a2_sb    = ap1_gs >> 6;
    wire [5:0]  a2_q     = ap1_gs[5:0];
    wire [31:0] a2_raddr = ap1_rbase + ap1_lp + (ap1_lph << 3);
    // stage X: {mine, raddr, soff, koff, base, stride}
    localparam integer AXW = 32*5 + 1;
    wire [AXW-1:0] ax_in = {ap1_mine, a2_raddr, {26'd0, a2_q} << 1,
                            ((32'd1 + {28'd0, a2_q[5:2]}) << 7) + ({30'd0, a2_q[1:0]} << 5) + ((ap1_row & 32'd15) << 1),
                            ap1_rbase, (a2_sb << 11) + (a2_sb << 7)};
    localparam integer AXS = (AXW + AS - 1) / AS;
    (* keep *) reg [AXS-1:0] okx_c;
    reg [AXW-1:0] ax;
    always @(posedge clk or negedge rst_n) if (!rst_n) okx_c <= '0; else okx_c <= {AXS{ap_okx_nx}};
    for (gi = 0; gi < AXS; gi = gi + 1) begin : g_ax
        localparam integer LO = AS * gi, NB = (AS * gi + AS > AXW) ? AXW - AS * gi : AS;
        always @(posedge clk) if (!okx_c[gi]) ax[LO +: NB] <= ax_in[LO +: NB];
    end
    // stage B0: {mine, raddr, soff, koff, blk = base + stride}
    localparam integer ABW = 32*4 + 1;
    wire [ABW-1:0] ab_in = {ax[160], ax[159:128], ax[127:96], ax[95:64], ax[63:32] + ax[31:0]};
    localparam integer ABS = (ABW + AS - 1) / AS;
    (* keep *) reg [ABS-1:0] okb_c;
    reg [ABW-1:0] ab;
    always @(posedge clk or negedge rst_n) if (!rst_n) okb_c <= '0; else okb_c <= {ABS{ap_okb_nx}};
    for (gi = 0; gi < ABS; gi = gi + 1) begin : g_ab
        localparam integer LO = AS * gi, NB = (AS * gi + AS > ABW) ? ABW - AS * gi : AS;
        always @(posedge clk) if (!okb_c[gi]) ab[LO +: NB] <= ab_in[LO +: NB];
    end
    // stage B: {kscal = blk + soff, kcode = blk + koff, raddr}; ap_mine is a control master (domain leaf)
    localparam integer APW = 32*3;
    wire [APW-1:0] ap_in = {ab[31:0] + ab[95:64], ab[31:0] + ab[63:32], ab[127:96]};
    localparam integer APS = APW / AS;
    (* keep *) reg [APS-1:0] okp_c;
    reg [APW-1:0] apr;
    wire ap_mine_nx = !ap_ok ? ab[128] : ap_mine;
    always @(posedge clk or negedge rst_n) if (!rst_n) okp_c <= '0; else okp_c <= {APS{ap_ok_nx}};
    for (gi = 0; gi < APS; gi = gi + 1) begin : g_ap
        always @(posedge clk) if (!okp_c[gi]) apr[AS*gi +: AS] <= ap_in[AS*gi +: AS];
    end
    always @(posedge clk) ap_mine <= ap_mine_nx;
    wire [31:0] u_raddr = apr[31:0], u_kcode = apr[63:32], u_kscal = apr[95:64];

    // =================================================================================================================
    // output FIFO counters (domain leaves) and the leaf clones
    // =================================================================================================================
    reg  fq_nz;
    wire fq_pop = fq_nz && w_rdy;
    wire [2:0] fq_n_nx = fq_n + (p_wv ? 3'd1 : 3'd0) - (fq_pop ? 3'd1 : 3'd0);
    wire p_wv_nx = go0 && d_wv[0];
    wire p_sc_nx = d_go_ikey_ph2[0];
    wire [LV-1:0] dl_nx = {st_left_nx == 32'd0, st_left_nx == 32'd1, st_left_nx[3:0], st_row_nx[3:0], p_wv_nx, fq_n_nx,
                           ap_ok_nx, ap_mine_nx, pit_nx, st_sec_nx, st_rem_nx, ra_n_nx, st_ph_nx,
                           st_mode_nx == M_IKEY, st_mode_nx == M_ROWS, st_mode_nx == M_RAW, st_pad_nx, st_act_nx};
    localparam [LV-1:0] DL_RST = (59'd1 << 58) | (59'd1 << 2);  // st_left == 0, st_mode == RAW
    always @(posedge clk or negedge rst_n) if (!rst_n) dl <= {ND{DL_RST}}; else dl <= {ND{dl_nx}};
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n) for (i = 0; i < ND; i = i + 1)
        if (dl[i*LV +: 2] != {st_pad, st_act} || dl[i*LV + 8 +: 9] != ra_n || dl[i*LV + 17 +: 16] != st_rem ||
            dl[i*LV + 33 +: 5] != st_sec || dl[i*LV + 5 +: 3] != st_ph || dl[i*LV + 44] != ap_ok || dl[i*LV + 45 +: 3] != fq_n ||
            dl[i*LV + 48] != p_wv || dl[i*LV + 49 +: 4] != st_row[3:0] || dl[i*LV + 53 +: 4] != st_left[3:0] ||
            dl[i*LV + 57] != (st_left == 32'd1) || dl[i*LV + 58] != (st_left == 32'd0) ||
            dl[i*LV + 2 +: 3] != {st_mode == M_IKEY, st_mode == M_ROWS, st_mode == M_RAW} ||
            (st_act && dl[i*LV + 38 +: 5] != f_pitch) || (st_act && ap_ok && dl[i*LV + 43] != ap_mine))
            $fatal(1, "ot_s81_ing_stream_n32: domain %0d leaf diverged", i);
`endif

    // =================================================================================================================
    // realigner ring: two 16 x 257 dual-clock macros (both clocks clk), rows 0..3; even words in u_rae, odd in u_rao
    // =================================================================================================================
    wire [256:0] rq_e, rq_o;
    wire [2:0]   w0 = ra_rp[7:5];
    wire [2:0]   w0p1 = w0 + 3'd1;
    wire [1:0]   row_o = w0[2:1];
    wire [1:0]   row_e = w0p1[2:1];
    `OT_SH_M257 u_rae (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in({2'b00, row_e}), .rd_out(rq_e),
        .w_ce_in(ra_push), .w_addr_in({2'b00, ra_wq}), .wd_in({1'b0, in_data[255:0]}), .w_mask_in({257{1'b1}}));
    `OT_SH_M257 u_rao (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in({2'b00, row_o}), .rd_out(rq_o),
        .w_ce_in(ra_push), .w_addr_in({2'b00, ra_wq}), .wd_in({1'b0, in_data[511:256]}), .w_mask_in({257{1'b1}}));

    // =================================================================================================================
    // stage P (registered at every edge; meaningful only on a pop edge: p_wv / p_sc)
    // =================================================================================================================
    // st_wb / st_wo source one-hot (registered from the next mode / phase): 0 RAW, 1 ROWS, 2 IKEY code, 3 IKEY scale
    function automatic [3:0] wsel(input [3:0] m, input [2:0] ph);
        wsel = (m == M_RAW) ? 4'b0001 : (m == M_ROWS) ? 4'b0010 : (m == M_IKEY) ? ((ph < 3'd2) ? 4'b0100 : 4'b1000) : 4'b0000;
    endfunction
    (* keep *) reg [15:0] wsel_c;                        // 4 copies x 4 (16 bits of {wb, wo} each)
    always @(posedge clk or negedge rst_n) if (!rst_n) wsel_c <= {4{4'b0001}}; else wsel_c <= {4{wsel(st_mode_nx, st_ph_nx)}};
    wire [31:0] st_wb, st_wo;
    wire [31:0] wo_sec = {27'd0, st_sec}, wo_ph = {29'd0, st_ph}, wo_p4 = {31'd0, st_ph == 3'd4};
    for (gi = 0; gi < 2; gi = gi + 1) begin : g_wb
        wire [3:0] s = wsel_c[4*gi +: 4];
        wire [3:0] t = wsel_c[8 + 4*gi +: 4];
        assign st_wb[16*gi +: 16] = ({16{s[0]}} & f_a0[16*gi +: 16]) | ({16{s[1]}} & u_raddr[16*gi +: 16])
                                  | ({16{s[2]}} & u_kcode[16*gi +: 16]) | ({16{s[3]}} & u_kscal[16*gi +: 16]);
        assign st_wo[16*gi +: 16] = ({16{t[0]}} & st_row[16*gi +: 16]) | ({16{t[1]}} & wo_sec[16*gi +: 16])
                                  | ({16{t[2]}} & wo_ph[16*gi +: 16]) | ({16{t[3]}} & wo_p4[16*gi +: 16]);
    end
    reg  [31:0]  p_wb, p_wo;
    (* keep *) reg [23:0]  p_fo_c;                       // 8 copies of ra_rp[2:0] (4 head bytes each)
    (* keep *) reg [79:0]  p_gs_c;                       // 10 copies of the 8-way window select one-hot(ra_rp[5:3])
    (* keep *) reg [63:0]  p_kd_c;                       // 16 copies of the kind one-hot (16 output bits each)
    reg  [31:0]  p_mb;                                   // head byte b kept (b < k_take; kind 1 mask)
    (* keep *) reg [31:0]  p_sco_c;                      // scale-row write one-hot, two copies (low / high halves)
    (* keep *) reg [NWR-1:0] p_wv_c;
    wire [5:0]   take7 = d_take[7*6 +: 6];
    wire [1:0]   kind7 = d_kind[7*2 +: 2];
    always @(posedge clk) begin
        p_wb <= st_wb; p_wo <= st_wo;
        p_fo_c <= {8{ra_rp[2:0]}};
`ifdef OT_N32_MUT_WIN
        for (i = 0; i < 10; i = i + 1) p_gs_c[8*i +: 8] <= (i == 4) ? (8'd1 << (ra_rp[5:3] ^ 3'b100)) : (8'd1 << ra_rp[5:3]);
`else
        p_gs_c <= {10{8'd1 << ra_rp[5:3]}};
`endif
        p_kd_c <= {16{4'b0001 << kind7}};
        for (i = 0; i < 32; i = i + 1) p_mb[i] <= take7[5] || (i < take7[4:0]);
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin p_wv <= 1'b0; p_sc <= 1'b0; p_wv_c <= '0; p_sco_c <= '0; end
        else begin
            p_wv <= p_wv_nx; p_sc <= p_sc_nx; p_wv_c <= {NWR{p_wv_nx}};
            p_sco_c <= {2{p_sc_nx ? (16'd1 << st_row[3:0]) : 16'd0}};
        end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && kind7 != d_kind[1:0]) $fatal(1, "ot_s81_ing_stream_n32: kind domain diverged");
`endif

    // =================================================================================================================
    // stage O
    // =================================================================================================================
    wire [255:0] e_w = rq_e[255:0], o_w = rq_o[255:0];
    // window bits [32 gi +: 32] = window granule GJ = gi / 2, half H; select s = {par, G}: pair granule M = G + GJ;
    // M < 4: low word (par ? odd : even) granule M; M >= 4: high word (par ? even : odd) granule M - 4
    wire [319:0] win;
    for (gi = 0; gi < 10; gi = gi + 1) begin : g_win
        localparam integer GJ = gi / 2, H = gi % 2;
        wire [7:0] s = p_gs_c[8*gi +: 8];
        wire [255:0] c;
        for (gj = 0; gj < 8; gj = gj + 1) begin : g_c
            localparam integer PAR = gj / 4, G = gj % 4, M = G + GJ;
            localparam integer IDX = (M < 4) ? M : M - 4;
            localparam integer USE_O = (M < 4) ? PAR : 1 - PAR;
            if (USE_O != 0) begin : g_o
                assign c[32*gj +: 32] = o_w[64*IDX + 32*H +: 32];
            end else begin : g_e
                assign c[32*gj +: 32] = e_w[64*IDX + 32*H +: 32];
            end
        end
        assign win[32*gi +: 32] = ({32{s[0]}} & c[0 +: 32]) | ({32{s[1]}} & c[32 +: 32]) | ({32{s[2]}} & c[64 +: 32])
                                | ({32{s[3]}} & c[96 +: 32]) | ({32{s[4]}} & c[128 +: 32]) | ({32{s[5]}} & c[160 +: 32])
                                | ({32{s[6]}} & c[192 +: 32]) | ({32{s[7]}} & c[224 +: 32]);
    end
    wire [255:0] head;
    for (gi = 0; gi < 32; gi = gi + 1) begin : g_hb
        wire [2:0] fo = p_fo_c[3*(gi/4) +: 3];
        wire [7:0] fh = 8'd1 << fo;
        reg  [7:0] hb;
        integer k;
        always @* begin
            hb = 8'd0;
            for (k = 0; k < 8; k = k + 1) hb = hb | ({8{fh[k]}} & win[8*(gi + k) +: 8]);
        end
        assign head[8*gi +: 8] = hb;
    end
    reg  [255:0] sc_acc0, sc_acc1;
    wire [255:0] o_d;
    for (gi = 0; gi < 16; gi = gi + 1) begin : g_od
        wire [3:0] kd = p_kd_c[4*gi +: 4];
        wire [15:0] mk = {{8{p_mb[2*gi+1]}}, {8{p_mb[2*gi]}}};
`ifdef OT_N32_MUT_KIND
        wire k2 = (gi == 5) ? 1'b0 : kd[2];
`else
        wire k2 = kd[2];
`endif
        assign o_d[16*gi +: 16] = ({16{kd[0]}} & head[16*gi +: 16]) | ({16{kd[1]}} & head[16*gi +: 16] & mk)
                                | ({16{k2}} & sc_acc0[16*gi +: 16]) | ({16{kd[3]}} & sc_acc1[16*gi +: 16]);
    end
    // IKEY scales: row r -> sc_acc[r[3]][32 r[2:0] +: 32] = head[31:0]; each 16-bit half by its own one-hot copy
    for (gi = 0; gi < 8; gi = gi + 1) begin : g_sc
        always @(posedge clk) begin
            if (p_sco_c[gi])          sc_acc0[32*gi +: 16]      <= head[15:0];
            if (p_sco_c[16 + gi])     sc_acc0[32*gi + 16 +: 16] <= head[31:16];
            if (p_sco_c[8 + gi])      sc_acc1[32*gi +: 16]      <= head[15:0];
            if (p_sco_c[24 + gi])     sc_acc1[32*gi + 16 +: 16] <= head[31:16];
        end
    end
    wire [AW-1:0] p_wa = p_wb + p_wo;
    wire [AW+255:0] fqw = {p_wa, o_d};

    // =================================================================================================================
    // output FIFO: 4 x 288 b, 18 slices of 16 b
    // =================================================================================================================
    reg  [4*(AW+256)-1:0] fqf;
    (* keep *) reg [4*NWR-1:0] fq_wh_c, fq_rh_c;
    (* keep *) reg [NWR-1:0]   fq_nz_c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fq_wh_c <= {NWR{4'b0001}}; fq_rh_c <= {NWR{4'b0001}}; fq_nz_c <= '0; fq_nz <= 1'b0; fq_n <= 3'd0; end
        else begin
            for (i = 0; i < NWR; i = i + 1) begin
`ifdef OT_N32_MUT_FQS
                if (p_wv_c[i] && i != 7) fq_wh_c[4*i +: 4] <= {fq_wh_c[4*i +: 3], fq_wh_c[4*i + 3]};    // mutant
`else
                if (p_wv_c[i]) fq_wh_c[4*i +: 4] <= {fq_wh_c[4*i +: 3], fq_wh_c[4*i + 3]};
`endif
                if (fq_nz_c[i] && w_rdy_c[i]) fq_rh_c[4*i +: 4] <= {fq_rh_c[4*i +: 3], fq_rh_c[4*i + 3]};
            end
            fq_nz_c <= {NWR{fq_n_nx != 3'd0}}; fq_nz <= fq_n_nx != 3'd0; fq_n <= fq_n_nx;
        end
    always @(posedge clk)
        for (i = 0; i < 4; i = i + 1) for (j = 0; j < NWR; j = j + 1)
            if (p_wv_c[j] && fq_wh_c[4*j + i]) fqf[i*(AW+256) + 16*j +: 16] <= fqw[16*j +: 16];
    wire [AW+255:0] fq_h;
    for (gi = 0; gi < NWR; gi = gi + 1) begin : g_fr
        wire [3:0] oh = fq_rh_c[4*gi +: 4];
        assign fq_h[16*gi +: 16] = ({16{oh[0]}} & fqf[0*(AW+256) + 16*gi +: 16]) | ({16{oh[1]}} & fqf[1*(AW+256) + 16*gi +: 16])
                                 | ({16{oh[2]}} & fqf[2*(AW+256) + 16*gi +: 16]) | ({16{oh[3]}} & fqf[3*(AW+256) + 16*gi +: 16]);
    end
    assign w_v = fq_nz; assign wv_b = fq_nz_c[NWR-1];
    assign w_addr = fq_h[AW+255:256]; assign w_data = fq_h[255:0];
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && (w_rdy_c != {NWR{w_rdy}})) $fatal(1, "ot_s81_ing_stream_n32: w_rdy copies diverged");
`endif

    // =================================================================================================================
    // completion queue: entries {tag, issued count}; the head leaves when the accepted count reaches it
    // =================================================================================================================
    reg  [15:0] iss_lo, iss_hi, acc_lo, acc_hi;
    wire [31:0] sp_iss = {iss_hi, iss_lo};
    wire pop_a = fq_nz_c[0] && w_rdy_c[0], pop_b = fq_nz_c[1] && w_rdy_c[1];
    wire [31:0] sp_acc_nx = {acc_hi + ((pop_b && acc_lo == 16'hffff) ? 16'd1 : 16'd0), acc_lo + (pop_a ? 16'd1 : 16'd0)};
    reg         dq_e1, dq_e2;
    reg  [7:0]  dq_t1, dq_t2;
    reg  [31:0] dq_c2;
    wire [39:0] cqw = {dq_t2, dq_c2};
    reg  [39:0] cq [0:7];
    reg  [2:0]  cq_rd, cq_wr;
    reg  [3:0]  cq_n;
    // write enables: per (40-b slice, entry), registered from the next write (dq_e1 = the next dq_e2)
    (* keep *) reg [23:0] cq_we_c;                       // [s*8 + e]
    // read: one-hot copies of the read pointer (D = one-hot of the next read index; no enable):
    //   0 / 1 compare word lo / hi, 2 tag, 3 / 4 count out lo / hi
    (* keep *) reg [39:0] cq_roh_c;
    reg              cq_nz;
    reg  [31:0]      acc_q;                              // clone of sp_acc for the compare
    function automatic [15:0] cqsel(input [7:0] oh, input integer lo);
        integer k; reg [15:0] v;
        begin v = 16'd0; for (k = 0; k < 8; k = k + 1) v = v | ({16{oh[k]}} & cq[k][lo +: 16]); cqsel = v; end
    endfunction
    wire [31:0] hc = {cqsel(cq_roh_c[8 +: 8], 16), cqsel(cq_roh_c[0 +: 8], 0)};
`ifdef OT_N32_MUT_CQR
    wire cq_go = cq_nz && ({acc_q[31:16], 16'hffff} >= hc);                       // mutant: low compare half ignored
`else
    wire cq_go = cq_nz && (acc_q >= hc);
`endif
    wire [2:0] cq_rd_nx = cq_rd + (cq_go ? 3'd1 : 3'd0);
    wire [2:0] cq_wr_nx = cq_wr + (dq_e2 ? 3'd1 : 3'd0);
    wire [3:0] cq_n_nx = cq_n + (dq_e2 ? 4'd1 : 4'd0) - (cq_go ? 4'd1 : 4'd0);
    always @(posedge clk) begin dq_t1 <= dtag_r; dq_t2 <= dq_t1; dq_c2 <= sp_iss; end
    for (gi = 0; gi < 3; gi = gi + 1) begin : g_cqw
        localparam integer LO = 16 * gi, NB = (gi == 2) ? 8 : 16;
        integer k;
        always @(posedge clk)
            for (k = 0; k < 8; k = k + 1) if (cq_we_c[8*gi + k]) cq[k][LO +: NB] <= cqw[LO +: NB];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            iss_lo <= 16'd0; iss_hi <= 16'd0; acc_lo <= 16'd0; acc_hi <= 16'd0; dq_e1 <= 1'b0; dq_e2 <= 1'b0;
            cq_rd <= 3'd0; cq_wr <= 3'd0; cq_n <= 4'd0; cq_we_c <= 24'd0; cq_roh_c <= {5{8'd1}}; cq_nz <= 1'b0; acc_q <= 32'd0;
        end else begin
            if (p_wv_c[0]) iss_lo <= iss_lo + 16'd1;
            if (p_wv_c[1] && iss_lo == 16'hffff) iss_hi <= iss_hi + 16'd1;
            {acc_hi, acc_lo} <= sp_acc_nx; acc_q <= sp_acc_nx;
            dq_e1 <= done_r; dq_e2 <= dq_e1;
            cq_we_c <= {3{dq_e1 ? (8'd1 << cq_wr_nx) : 8'd0}};
            cq_wr <= cq_wr_nx; cq_rd <= cq_rd_nx; cq_n <= cq_n_nx; cq_nz <= cq_n_nx != 4'd0;
            cq_roh_c <= {5{8'd1 << cq_rd_nx}};
        end
    reg [7:0] tg;
    always @* begin tg = 8'd0; for (i = 0; i < 8; i = i + 1) tg = tg | ({8{cq_roh_c[16 + i]}} & cq[i][39:32]); end
    assign done_v = cq_go; assign done_tag = tg;
    assign n_sectors = {cqsel(cq_roh_c[32 +: 8], 16), cqsel(cq_roh_c[24 +: 8], 0)};
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && dq_e2 && cq_n == 4'd8 && !cq_go) $fatal(1, "ot_s81_ing_stream_n32: completion queue overflow");
`endif
    wire sp_busy = p_wv || p_sc || (fq_n != 3'd0);
    assign busy = dh_v || st_act || sp_busy;

    // ---- replica-B status for the host head (from kept clones: dq_n, act, ring / beat flags, p_wv, p_sc, fq_nz)
    (* keep *) reg [2:0] dqn_b;
    (* keep *) reg       act_b, pad_b, rale_b, bnz_b, pwv_b, psc_b, fqnz_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin dqn_b <= 3'd0; act_b <= 1'b0; pad_b <= 1'b0; rale_b <= 1'b1; bnz_b <= 1'b0; pwv_b <= 1'b0; psc_b <= 1'b0; fqnz_b <= 1'b0; end
        else begin
            dqn_b <= dq_n_nx; act_b <= st_act_nx; pad_b <= st_pad_nx; rale_b <= ra_n_nx <= 9'd192; bnz_b <= st_beats_nx != 16'd0;
            pwv_b <= p_wv_nx; psc_b <= p_sc_nx; fqnz_b <= fq_n_nx != 3'd0;
        end
    assign drdy_b  = dqn_b < 3'd4;
    assign inrdy_b = act_b && (pad_b ? bnz_b : (rale_b && bnz_b));
    assign busy_b  = (dqn_b != 3'd0) || act_b || pwv_b || psc_b || fqnz_b;
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && (drdy_b != d_rdy || inrdy_b != in_rdy || busy_b != busy || wv_b != w_v))
        $fatal(1, "ot_s81_ing_stream_n32: replica-B status diverged");
`endif
endmodule
