`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// el1014-qwen-kvsys-elements 2026-10-14: the near-HBM attention hub as DIE LEAVES (Qwen two-die split, KV/system die).
//
// Why: ot_qwen_nearhbm_attn_hub_t routed as ONE cluster (13 hard children + ~8.2k parent flops over 1,171 x 760 um) failed
// six times; the last (q13e) had one cluster clock of 1,864 ps insertion / 266 ps spread and 2,253 input endpoints at
// FF -122 ps.  A cluster parent clock over hard children is the structural fault (owner rule: per-child clock entries).
// Here the parent's logic is ONE leaf, qkd_ahub_core, with its own clock root and a register at every pin, and the die
// binds it beside the 13 closed children (4 x ot_nhb_pbst, 4 x ot_nhb_pvlg, 4 x ot_nhb_zh, ot_qkh_recip_leaf).  Each
// leaf gets its own clock entry from the die tree (phi - R per leaf); nothing crosses a cluster clock any more.
//
// Arithmetic: identical to hub_t (same modules, same operands, same order).  Data that never needed the parent no longer
// passes through it: pi_beat / pi_data go from the die straight to the beat-store tiles (whose own pin flops are hub_p's
// _b stage), and the beat-store -> lane-group crossbar sr is a die net (hub_t's sr_r relay = die relay stages).
//
// Cycle changes against hub_t (values bit-identical; the layer bench measures the total):
//   Z issue {ziv, zg, zp} registered at the core pins (+1; ziv was combinational into the tiles), tile root captured at
//   the core pins (+1): the reciprocal read is issued 2 + ZW_RLY + ZR_RLY later (rv / ra chains) so it stays behind the
//   final tree write.  P.V read address registered at the pins (+1), y captured at the pins before out_data (+1): the
//   v / rz / tag chains are re-derived below from the die relay counts so v, s and rz meet at the lane-group pins exactly
//   as in hub_t.  Reciprocal path: latency-insensitive (rcnt counts rvo), any RX_RLY / RY_RLY.
// Copies: one registered copy a destination tile ((* keep *): synthesis must not merge them).
// Die contract (the composition ot_qwen_nearhbm_attn_hub_d below is the reference the die must reproduce):
//   ZW_RLY stages on EVERY core -> zh net (start / we / sid / issue), ZR_RLY on zh -> core (root / zerr), RA_RLY on core ->
//   pbst ra, SR_RLY on EVERY pbst -> pvlg sr net, PV_RLY on core -> pvlg v / rz, Y_RLY on pvlg -> core y / pf; pi_* to
//   the pbst tiles may lag the core's pi_valid / pi_g copy by 0..3 stages (store write stays ahead of the read).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ahub_core #(
    parameter integer HD = 128,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer ZW = 4,
    parameter integer ZW_RLY = 0,
    parameter integer ZR_RLY = 0,
    parameter integer RA_RLY = 0,
    parameter integer SR_RLY = 1,
    parameter integer PV_RLY = 0,
    parameter integer Y_RLY = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // hub boundary (same names / widths as ot_qwen_nearhbm_attn_hub_t; pi_beat / pi_data go to the pbst tiles)
    input  wire          start,
    input  wire [3:0]    si_valid,
    input  wire [7:0]    si_type,
    input  wire [3:0]    si_g,
    input  wire [7:0]    si_hh,
    input  wire [15:0]   si_k,
    input  wire [3:0]    si_any,
    input  wire [127:0]  si_data,
    input  wire [3:0]    pi_valid,
    input  wire [3:0]    pi_g,
    // lmax result, one registered copy a stack (die nets am_<st>: {valid, g, hh 2, data 32} = 36 b each, contract v1)
    (* keep = "true", dont_touch = "true" *) output reg  [143:0] am,
    output reg           out_valid,
    output reg           out_g,
    output reg  [5:0]    out_beat,
    output reg  [511:0]  out_data,
    output reg           fault,
    output reg  [7:0]    ev,
    // Z heads, split by face (Q-KVSYS-STRIP 2026-10-16, VIS-ROM QKV-07: 1,345 pins on ONE face at 8.9/um): heads 0 / 1 on
    // the W face (zw_*), heads 2 / 3 on the E face (ze_*); the pair's head j is bit group j of its port (= head 2 side + j).
    // Every output is the same output flop as before (a wire from the internal zh_* register), every input the same pin.
    output wire [1:0]    zw_start,  output wire [1:0]    ze_start,
    output wire [255:0]  zw_we,     output wire [255:0]  ze_we,      // head j: [128j +: 128]
    output wire [255:0]  zw_sid,    output wire [255:0]  ze_sid,     // head j: [128j +: 128]
    output wire [7:0]    zw_iv,     output wire [7:0]    ze_iv,      // head j: [4j +: 4]
    output wire [1:0]    zw_g,      output wire [1:0]    ze_g,
    output wire [11:0]   zw_p,      output wire [11:0]   ze_p,       // head j: [6j +: 6]
    input  wire [127:0]  zw_root,   input  wire [127:0]  ze_root,    // head j: [64j +: 64]
    input  wire [7:0]    zw_err,    input  wire [7:0]    ze_err,     // head j: [4j +: 4]
    // reciprocal leaf
    output reg           rc_v,
    output reg  [31:0]   rc_x,
    input  wire [31:0]   rc_y,
    input  wire          rc_vo,
    input  wire          rc_fault,
    // beat-store tiles (read address copy a tile)
    (* keep = "true", dont_touch = "true" *) output reg  [23:0]   pb_ra,              // tile s: [6s +: 6] = {pg, pp[4:0]}
    // lane-group tiles (copy a tile)
    (* keep = "true", dont_touch = "true" *) output reg  [3:0]    pl_v,
    (* keep = "true", dont_touch = "true" *) output reg  [127:0]  pl_rz,              // tile l: [32l +: 32]
    input  wire [511:0]  pl_y,               // tile l: [128l +: 128]
    input  wire [15:0]   pl_pf               // tile l: [4l +: 4]
);
    // the Z-head output registers (one copy a head, (* keep *)) and the joined input pins (head h = 0..3 as before)
    (* keep = "true", dont_touch = "true" *) reg  [3:0]    zh_start;
    reg  [511:0]  zh_we;
    (* keep = "true", dont_touch = "true" *) reg  [511:0]  zh_sid;
    (* keep = "true", dont_touch = "true" *) reg  [15:0]   zh_iv;
    (* keep = "true", dont_touch = "true" *) reg  [3:0]    zh_g;
    (* keep = "true", dont_touch = "true" *) reg  [23:0]   zh_p;
    wire [255:0]  zh_root = {ze_root, zw_root};
    wire [15:0]   zh_err  = {ze_err, zw_err};
    assign {ze_start, zw_start} = zh_start;  assign {ze_we, zw_we} = zh_we;  assign {ze_sid, zw_sid} = zh_sid;
    assign {ze_iv, zw_iv} = zh_iv;  assign {ze_g, zw_g} = zh_g;  assign {ze_p, zw_p} = zh_p;
    localparam integer NBEAT = 4 * HD / 16;
    localparam integer BPH = HD / 16;
    // derived chain lengths (hub_t: RV 4, RA 3, PR 4, RZ 17, TAG 26 with ZW/ZR/RA/PV/Y 0 and SR 1, no core pin stages)
    localparam integer EZ    = 2 + ZW_RLY + ZR_RLY;                 // extra Z read-back latency against hub_t
    localparam integer RVN   = 4 + EZ;                              // rv0 -> rc_v
    localparam integer RAN   = 3 + EZ;                              // ra0 -> root select
    localparam integer AS    = 3 + 1 + RA_RLY + SR_RLY;             // edge sr meets the pvlg pins (hub_t 4)
    localparam integer NPR   = AS - PV_RLY;                         // p_ready -> pl_v output flop (hub_t 4)
    localparam integer DRZ   = NPR + 13;                            // rz delay before the pl_rz output flop (hub_t 17)
    localparam integer DTAG  = AS + 23 + Y_RLY;                     // tag delay (hub_t 26 with no y pin stage)
    integer sd_, s_, s2_, s3_, i_, e4_, h_;
    function automatic fgt(input [31:0] a, input [31:0] b);
        fgt = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
    endfunction
    // reset: 0 input stage, 1 max, 2 Z control, 3 Z / P issue copies, 4 P control, 5 tag, 6 recip, 7 outputs
    wire [7:0] rl;
    ot_rst_pipe #(.REGIONS(8), .STAGES(2)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));

    // ---- boundary input registers (_a / _b) and decode stage (_c) ---------------------------------------------------
    reg          start_b;
    reg [3:0]    siv_b, piv_a, piv_b;
    reg [7:0]    sit_b;  reg [3:0] sig_b;  reg [7:0] sih_b;  reg [15:0] sik_b;  reg [3:0] sia_b;  reg [127:0] sid_b;
    reg [3:0]    pig_a, pig_b;
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) begin start_b <= 1'b0; siv_b <= 4'd0; piv_a <= 4'd0; piv_b <= 4'd0; end
        else begin start_b <= start; siv_b <= si_valid; piv_a <= pi_valid; piv_b <= piv_a; end
    always @(posedge clk) begin
        sit_b <= si_type; sig_b <= si_g; sih_b <= si_hh; sik_b <= si_k; sia_b <= si_any; sid_b <= si_data;
        pig_a <= pi_g; pig_b <= pig_a;
    end
    reg [31:0]  lm_we_n;
    reg [511:0] zs_we_n;
    always @* begin
        lm_we_n = 32'd0; zs_we_n = 512'd0;
        for (sd_ = 0; sd_ < 4; sd_ = sd_ + 1) begin
            if (siv_b[sd_] && sit_b[2*sd_ +: 2] == 2'd0) lm_we_n[{sig_b[sd_], sd_[1:0], sih_b[2*sd_ +: 2]}] = 1'b1;
            if (siv_b[sd_] && sit_b[2*sd_ +: 2] == 2'd1)
                zs_we_n[{sig_b[sd_], sih_b[2*sd_ +: 2], sik_b[4*sd_ +: 4], sd_[1:0]}] = 1'b1;
        end
    end
    reg          start_c;
    reg [3:0]    siv_c, piv_c;
    reg [7:0]    sit_c;  reg [3:0] sig_c;  reg [3:0] sia_c;  reg [127:0] sid_c;  reg [3:0] pig_c;
    reg [31:0]   lm_we;
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) begin start_c <= 1'b0; siv_c <= 4'd0; piv_c <= 4'd0; lm_we <= 32'd0; end
        else begin start_c <= start_b; siv_c <= siv_b; piv_c <= piv_b; lm_we <= lm_we_n; end
    always @(posedge clk) begin sit_c <= sit_b; sig_c <= sig_b; sia_c <= sia_b; sid_c <= sid_b; pig_c <= pig_b; end
    // Z write side to the heads: the _c stage IS the output pin flop (one copy a head)
    wire [127:0] we_h [0:3];
    genvar gh, ge;
    generate for (gh = 0; gh < 4; gh = gh + 1) begin : g_we
        for (ge = 0; ge < 128; ge = ge + 1) begin : g_b       // {g, k, sd} of head gh = zs_we[{g, gh, k, sd}]
            assign we_h[gh][ge] = zs_we_n[{ge[6], gh[1:0], ge[5:0]}];
        end
    end endgenerate
    // zh_we has no reset: it re-captures we_h (0 while siv_b is held in reset) on every edge, and the tiles clear their
    // valid bits on start (gate 1014 hd1: 569-load reset net)
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) zh_start <= 4'd0; else zh_start <= {4{start_b}};
    always @(posedge clk) begin
        for (h_ = 0; h_ < 4; h_ = h_ + 1) zh_we[128*h_ +: 128] <= we_h[h_];
        zh_sid <= {4{sid_b}};
    end

    // ---- max (unchanged) -------------------------------------------------------------------------------------------
    reg [31:0] lm [0:31];
    reg [7:0]  lany;
    reg [4:0]  lcnt0, lcnt1;
    reg [1:0]  msent;
    wire       mg = msent[0];
    reg [2:0]  mh;
    wire       mready = !msent[mg] && (mg ? (lcnt1 == 5'd16) : (lcnt0 == 5'd16));
    reg        ma_v, mb_v;
    reg        ma_g, mb_g;
    reg [1:0]  ma_h, mb_h;
    reg [127:0] ma_x;
    reg [3:0]  ma_a;
    reg [63:0] mb_x;
    reg [1:0]  mb_a;
    reg        mo_valid_i, mo_g_i;
    reg [1:0]  mo_hh_i;
    reg [31:0] mo_data_i;
    function automatic [32:0] fmax2(input [31:0] x, input ax, input [31:0] y, input ay);
        fmax2 = !ax ? {ay, y} : (!ay ? {1'b1, x} : {1'b1, (fgt(y, x) ? y : x)});
    endfunction
    wire [32:0] m01 = fmax2(ma_x[31:0], ma_a[0], ma_x[63:32], ma_a[1]);
    wire [32:0] m23 = fmax2(ma_x[95:64], ma_a[2], ma_x[127:96], ma_a[3]);
    wire [32:0] mfin = fmax2(mb_x[31:0], mb_a[0], mb_x[63:32], mb_a[1]);
    always @(posedge clk or negedge rl[1]) begin
        if (!rl[1]) begin ma_v <= 1'b0; mb_v <= 1'b0; end
        else begin ma_v <= mready && !start_c; mb_v <= ma_v && !start_c; end
    end
    always @(posedge clk) begin
        ma_g <= mg; ma_h <= mh[1:0];
        for (s2_ = 0; s2_ < 4; s2_ = s2_ + 1) begin
            ma_x[32*s2_ +: 32] <= lm[{mg, s2_[1:0], mh[1:0]}];
            ma_a[s2_] <= lany[4*mg + s2_];
        end
        mb_g <= ma_g; mb_h <= ma_h;
        mb_x <= {m23[31:0], m01[31:0]}; mb_a <= {m23[32], m01[32]};
        if (!start_c)
            for (e4_ = 0; e4_ < 32; e4_ = e4_ + 1)
                if (lm_we[e4_]) lm[e4_] <= sid_c[32*(e4_/4 % 4) +: 32];
    end
    always @(posedge clk or negedge rl[1]) begin
        if (!rl[1]) begin lcnt0 <= 0; lcnt1 <= 0; lany <= 0; msent <= 0; mh <= 0; mo_valid_i <= 1'b0; end
        else begin
            mo_valid_i <= 1'b0;
            if (start_c) begin lcnt0 <= 0; lcnt1 <= 0; lany <= 0; msent <= 0; mh <= 0; end
            else begin
                for (s3_ = 0; s3_ < 4; s3_ = s3_ + 1)
                    if (siv_c[s3_] && sit_c[2*s3_ +: 2] == 2'd0 && sia_c[s3_]) lany[4*sig_c[s3_] + s3_] <= 1'b1;
                lcnt0 <= lcnt0 + ((siv_c[0] && sit_c[1:0] == 0 && !sig_c[0]) ? 1 : 0)
                               + ((siv_c[1] && sit_c[3:2] == 0 && !sig_c[1]) ? 1 : 0)
                               + ((siv_c[2] && sit_c[5:4] == 0 && !sig_c[2]) ? 1 : 0)
                               + ((siv_c[3] && sit_c[7:6] == 0 && !sig_c[3]) ? 1 : 0);
                lcnt1 <= lcnt1 + ((siv_c[0] && sit_c[1:0] == 0 && sig_c[0]) ? 1 : 0)
                               + ((siv_c[1] && sit_c[3:2] == 0 && sig_c[1]) ? 1 : 0)
                               + ((siv_c[2] && sit_c[5:4] == 0 && sig_c[2]) ? 1 : 0)
                               + ((siv_c[3] && sit_c[7:6] == 0 && sig_c[3]) ? 1 : 0);
                if (mready) begin
                    if (mh == 3'd3) begin mh <= 0; msent[mg] <= 1'b1; end else mh <= mh + 3'd1;
                end
                if (mb_v) begin mo_valid_i <= 1'b1; mo_g_i <= mb_g; mo_hh_i <= mb_h; mo_data_i <= mfin[31:0]; end
            end
        end
    end

    // ---- Z control (issue to the head tiles, registered at the pins), reciprocal --------------------------------------
    reg [2:0]  zdc0, zdc1;
    reg        zrun, zg, zwait_recip;
    reg [1:0]  zdone_tree;
    reg [2:0]  zl;
    reg [5:0]  zp;
    reg [3:0]  zwt;
    reg        fault_i;
    wire [6:0] znp = 7'd64 >> zl;
    reg [ZW-1:0] ziv;
    reg [6:0]    pz;
    integer z;
    always @* begin
        for (z = 0; z < ZW; z = z + 1) begin
            pz = {1'b0, zp} + z;
            ziv[z] = zrun && (zwt == 0) && (pz < znp);
        end
    end
    always @(posedge clk or negedge rl[3])
        if (!rl[3]) zh_iv <= 16'd0; else zh_iv <= {4{ziv}};
    always @(posedge clk) begin zh_g <= {4{zg}}; zh_p <= {4{zp}}; end
    // tile roots / errors captured at the core pins
    reg [255:0] zroot_q;
    reg [15:0]  zerr_q;
    always @(posedge clk) zroot_q <= zh_root;
    always @(posedge clk or negedge rl[2]) if (!rl[2]) zerr_q <= 16'd0; else zerr_q <= zh_err;
    // reciprocal issue: rv0 / ra0 delayed RVN / RAN (hub_t 4 / 3) so the read stays behind the final tree write
    reg        rv0;
    reg [2:0]  ra0;
    reg [RVN-1:0] rvs;
    reg [3*RAN-1:0] ras;
    reg [2:0]  rh;
    always @(posedge clk or negedge rl[6])
        if (!rl[6]) begin rvs <= {RVN{1'b0}}; rc_v <= 1'b0; end
        else begin rvs <= {rvs[RVN-2:0], rv0}; rc_v <= rvs[RVN-2]; end
    wire [2:0] rac = ras[3*RAN-1 -: 3];
    always @(posedge clk) begin
        ras <= {ras[3*RAN-4:0], ra0};
        rc_x <= zroot_q[64*rac[1:0] + 32*rac[2] +: 32];
    end
    // reciprocal results captured at the core pins (rcnt counts results: no fixed latency)
    reg [31:0] ry_q;
    reg        rvo_q, rf_q;
    always @(posedge clk) ry_q <= rc_y;
    always @(posedge clk or negedge rl[6]) if (!rl[6]) begin rvo_q <= 1'b0; rf_q <= 1'b0; end
                                          else begin rvo_q <= rc_vo; rf_q <= rc_fault; end
    reg [2:0]  rcnt;
    reg [31:0] rz [0:7];
    reg [1:0]  rz_ok;
    reg        rg_out;
    always @(posedge clk) if (rvo_q) rz[{rg_out, rcnt[1:0]}] <= ry_q;
    reg [15:0] pf_q;
    always @(posedge clk or negedge rl[2]) begin
        if (!rl[2]) begin
            zdc0 <= 0; zdc1 <= 0; zrun <= 1'b0; zg <= 1'b0; zdone_tree <= 2'b00; zl <= 3'd1; zp <= 0; zwt <= 0;
            rv0 <= 1'b0; rh <= 0; rcnt <= 0; rz_ok <= 2'b00; zwait_recip <= 1'b0; fault_i <= 1'b0;
        end else begin
            rv0 <= 1'b0;
            if (|zerr_q || (rvo_q && rf_q) || (|pf_q)) fault_i <= 1'b1;
            if (start_c) begin
                zdc0 <= 0; zdc1 <= 0; zrun <= 1'b0; zg <= 1'b0; zdone_tree <= 2'b00; rz_ok <= 2'b00; rcnt <= 0;
                zwait_recip <= 1'b0; fault_i <= 1'b0;
            end else begin
                zdc0 <= zdc0 + ((siv_c[0] && sit_c[1:0] == 2 && !sig_c[0]) ? 1 : 0)
                             + ((siv_c[1] && sit_c[3:2] == 2 && !sig_c[1]) ? 1 : 0)
                             + ((siv_c[2] && sit_c[5:4] == 2 && !sig_c[2]) ? 1 : 0)
                             + ((siv_c[3] && sit_c[7:6] == 2 && !sig_c[3]) ? 1 : 0);
                zdc1 <= zdc1 + ((siv_c[0] && sit_c[1:0] == 2 && sig_c[0]) ? 1 : 0)
                             + ((siv_c[1] && sit_c[3:2] == 2 && sig_c[1]) ? 1 : 0)
                             + ((siv_c[2] && sit_c[5:4] == 2 && sig_c[2]) ? 1 : 0)
                             + ((siv_c[3] && sit_c[7:6] == 2 && sig_c[3]) ? 1 : 0);
                if (!zrun && !zwait_recip) begin
                    if (!zdone_tree[0] && zdc0 == 3'd4) begin zrun <= 1'b1; zg <= 1'b0; zl <= 3'd1; zp <= 0; zwt <= 0; end
                    else if (zdone_tree[0] && !zdone_tree[1] && zdc1 == 3'd4) begin
                        zrun <= 1'b1; zg <= 1'b1; zl <= 3'd1; zp <= 0; zwt <= 0;
                    end
                end else if (zrun) begin
                    if (zwt != 0) begin
                        zwt <= zwt - 4'd1;
                        if (zwt == 4'd1) begin
                            if (zl == 3'd6) begin zrun <= 1'b0; zwait_recip <= 1'b1; rh <= 0; end
                            else begin zl <= zl + 3'd1; zp <= 0; end
                        end
                    end else if ({1'b0, zp} + ZW >= znp) begin zp <= 0; zwt <= ADD_LAT + 3; end
                    else zp <= zp + ZW;
                end else if (zwait_recip) begin
                    if (rh < 3'd4) begin
                        rv0 <= 1'b1; ra0 <= {zg, rh[1:0]};
                        rh <= rh + 3'd1; rg_out <= zg;
                    end else if (rcnt == 3'd4) begin
                        rcnt <= 0; zwait_recip <= 1'b0; zdone_tree[zg] <= 1'b1; rz_ok[zg] <= 1'b1;
                    end
                end
                if (rvo_q) rcnt <= rcnt + 3'd1;
            end
        end
    end

    // ---- P.V control; read-address copies; v / rz to the lane groups; y back -----------------------------------------
    reg [5:0]   pc [0:7];
    reg         pg;
    reg [5:0]   pp;
    reg [1:0]   pdone;
    wire p_ready = rz_ok[pg] && !pdone[pg] && (pc[{pg, 2'd0}] > pp) && (pc[{pg, 2'd1}] > pp) &&
                   (pc[{pg, 2'd2}] > pp) && (pc[{pg, 2'd3}] > pp);
    always @(posedge clk or negedge rl[4]) begin
        if (!rl[4]) begin pg <= 1'b0; pp <= 0; pdone <= 2'b00; for (i_ = 0; i_ < 8; i_ = i_ + 1) pc[i_] <= 0; end
        else if (start_c) begin pg <= 1'b0; pp <= 0; pdone <= 2'b00; for (i_ = 0; i_ < 8; i_ = i_ + 1) pc[i_] <= 0; end
        else begin
            for (s_ = 0; s_ < 4; s_ = s_ + 1) if (piv_c[s_]) pc[{pig_c[s_], s_[1:0]}] <= pc[{pig_c[s_], s_[1:0]}] + 6'd1;
            if (p_ready) begin
                if (pp == NBEAT - 1) begin pp <= 0; pdone[pg] <= 1'b1; pg <= 1'b1; end
                else pp <= pp + 6'd1;
            end
        end
    end
    // read address, one registered copy a beat-store tile (hub_t drove {pg, pp} into the tiles' pin flops directly)
    always @(posedge clk) pb_ra <= {4{pg, pp[4:0]}};
    // v: p_ready delayed NPR (hub_t: pr0..pr3), the last stage is the output copy a lane group
    reg [NPR-2:0] prs;
    always @(posedge clk or negedge rl[3])
        if (!rl[3]) begin prs <= {(NPR-1){1'b0}}; pl_v <= 4'd0; end
        else begin prs <= {prs[NPR-3:0], p_ready}; pl_v <= {4{prs[NPR-2]}}; end
    wire [5:0]   phh6 = pp / BPH;
    wire [31:0]  rzv = rz[{pg, phh6[1:0]}];
    wire [31:0]  rz_d;
    wire [6:0]   tag_o;
    ot_hdc_delay #(.W(32), .D(DRZ)) u_rz (.clk(clk), .rst_n(rl[5]), .d(rzv), .q(rz_d));
    ot_hdc_delay #(.W(7), .D(DTAG), .RESET(1)) u_tag (.clk(clk), .rst_n(rl[5]), .d({p_ready, pg, pp[4:0]}), .q(tag_o));
    always @(posedge clk) pl_rz <= {4{rz_d}};
    reg [511:0] y_q;
    always @(posedge clk) y_q <= pl_y;
    always @(posedge clk or negedge rl[2]) if (!rl[2]) pf_q <= 16'd0; else pf_q <= pl_pf;

    // ---- registered outputs -----------------------------------------------------------------------------------------
    always @(posedge clk or negedge rl[7]) begin
        if (!rl[7]) begin for (h_ = 0; h_ < 4; h_ = h_ + 1) am[36*h_ + 35] <= 1'b0; out_valid <= 1'b0; fault <= 1'b0; ev <= 8'd0; end
        else begin
            for (h_ = 0; h_ < 4; h_ = h_ + 1) am[36*h_ + 35] <= mo_valid_i;
            out_valid <= tag_o[6]; fault <= fault_i;
            ev <= {tag_o[6], p_ready, rz_ok, msent, mo_valid_i, 1'b0};
        end
    end
    always @(posedge clk) begin
        for (h_ = 0; h_ < 4; h_ = h_ + 1) am[36*h_ +: 35] <= {mo_g_i, mo_hh_i, mo_data_i};
        out_g <= tag_o[5]; out_beat <= {1'b0, tag_o[4:0]}; out_data <= y_q;
    end
`ifndef SYNTHESIS
    initial if (NPR < 3 || RVN < 2 || RAN < 2) $error("qkd_ahub_core: relay counts give a chain shorter than its register");
`endif
endmodule

// ---- die relay model (bench / composition only): N plain flop stages, N = 0 is a wire --------------------------------
module ot_qkd_drly #(parameter integer W = 1, parameter integer N = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_w
        assign q = d;
    end else begin : g_r
        reg [W-1:0] r [0:N-1];
        integer k;
        always @(posedge clk) begin r[0] <= d; for (k = 1; k < N; k = k + 1) r[k] <= r[k-1]; end
        assign q = r[N-1];
    end endgenerate
endmodule

// ---- the die composition (kvsys-elements r2 2026-10-14; KV/system die qkd_ahub, lead queue v1.1 rank 5) ----------------
// Wires only: the hard core qkd_ahub_core + the 13 closed tiles (4 ot_nhb_zh, ot_qkh_recip_leaf, 4 ot_nhb_pbst,
// 4 ot_nhb_pvlg), each on its OWN clock entry (the die delivers phi - R_child), and the die relay stages between them
// (ot_qkd_drly N = the die's relay count on that bus, clocked here by the entry of the leaf they feed).  am[143:0] = the
// core's four registered per-stack lmax copies {am_EN, am_ES, am_WN, am_WS} = copies 3..0 (contract am_<st> 36 b each).
// ot_qwen_nearhbm_attn_hub_d (below) is this module with every entry on one clock and mo = copy 0 (the hub_t ports).
module ot_qkd_ahub_die #(
    parameter integer HD = 128,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer ZW = 4,
    parameter integer ZW_RLY = 0,
    parameter integer ZR_RLY = 0,
    parameter integer RA_RLY = 0,
    parameter integer SR_RLY = 1,
    parameter integer PV_RLY = 0,
    parameter integer Y_RLY = 0,
    parameter integer RX_RLY = 1,
    parameter integer RY_RLY = 1,
    parameter integer PI_RLY = 0       // extra stages of pi_* to the beat stores beyond the core's copy (0..3)
) (
    input  wire          ck_core,
    input  wire [3:0]    ck_zh,
    input  wire          ck_recip,
    input  wire [3:0]    ck_pbst,
    input  wire [3:0]    ck_pvlg,
    input  wire          rst_n,
    input  wire          start,
    input  wire [3:0]    si_valid,
    input  wire [7:0]    si_type,
    input  wire [3:0]    si_g,
    input  wire [7:0]    si_hh,
    input  wire [15:0]   si_k,
    input  wire [3:0]    si_any,
    input  wire [127:0]  si_data,
    input  wire [3:0]    pi_valid,
    input  wire [3:0]    pi_g,
    input  wire [23:0]   pi_beat,
    input  wire [2047:0] pi_data,
    output wire [143:0]  am,
    output wire          out_valid,
    output wire          out_g,
    output wire [5:0]    out_beat,
    output wire [511:0]  out_data,
    output wire          fault,
    output wire [7:0]    ev
);
    wire [3:0]   zh_start;  wire [511:0] zh_we, zh_sid;  wire [15:0] zh_iv;  wire [3:0] zh_g;  wire [23:0] zh_p;
    wire [255:0] zh_root;   wire [15:0]  zh_err;
    wire         rc_v, rc_vo, rc_fault;  wire [31:0] rc_x, rc_y;
    wire [23:0]  pb_ra;     wire [3:0] pl_v;  wire [127:0] pl_rz;  wire [511:0] pl_y;  wire [15:0] pl_pf;
    qkd_ahub_core #(.HD(HD), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .ZW(ZW), .ZW_RLY(ZW_RLY), .ZR_RLY(ZR_RLY),
                    .RA_RLY(RA_RLY), .SR_RLY(SR_RLY), .PV_RLY(PV_RLY), .Y_RLY(Y_RLY)) u_core (
        .clk(ck_core), .rst_n(rst_n), .start(start), .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh),
        .si_k(si_k), .si_any(si_any), .si_data(si_data), .pi_valid(pi_valid), .pi_g(pi_g),
        .am(am), .out_valid(out_valid), .out_g(out_g),
        .out_beat(out_beat), .out_data(out_data), .fault(fault), .ev(ev),
        .zw_start(zh_start[1:0]), .ze_start(zh_start[3:2]), .zw_we(zh_we[255:0]), .ze_we(zh_we[511:256]),
        .zw_sid(zh_sid[255:0]), .ze_sid(zh_sid[511:256]), .zw_iv(zh_iv[7:0]), .ze_iv(zh_iv[15:8]), .zw_g(zh_g[1:0]),
        .ze_g(zh_g[3:2]), .zw_p(zh_p[11:0]), .ze_p(zh_p[23:12]), .zw_root(zh_root[127:0]), .ze_root(zh_root[255:128]),
        .zw_err(zh_err[7:0]), .ze_err(zh_err[15:8]), .rc_v(rc_v), .rc_x(rc_x), .rc_y(rc_y), .rc_vo(rc_vo), .rc_fault(rc_fault),
        .pb_ra(pb_ra), .pl_v(pl_v), .pl_rz(pl_rz), .pl_y(pl_y), .pl_pf(pl_pf));
    // Z heads
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_zh
        wire [267:0] zi;  wire [67:0] zo;  wire [67:0] zo_t;
        ot_qkd_drly #(.W(268), .N(ZW_RLY)) u_ri (.clk(ck_zh[g]),
            .d({zh_start[g], zh_we[128*g +: 128], zh_sid[128*g +: 128], zh_iv[4*g +: 4], zh_g[g], zh_p[6*g +: 6]}), .q(zi));
        ot_nhb_zh u_zh (.clk(ck_zh[g]), .rst_n(rst_n), .start(zi[267]), .zs_we(zi[266:139]), .sid(zi[138:11]), .ziv(zi[10:7]),
                        .zg(zi[6]), .zp(zi[5:0]), .root(zo_t[63:0]), .zerr(zo_t[67:64]));
        ot_qkd_drly #(.W(68), .N(ZR_RLY)) u_ro (.clk(ck_core), .d(zo_t), .q(zo));
        assign zh_root[64*g +: 64] = zo[63:0];
        assign zh_err[4*g +: 4] = zo[67:64];
    end endgenerate
    // reciprocal leaf
    wire [32:0] rxi, ryo_t, ryo;  wire rf_t, rf;
    ot_qkd_drly #(.W(33), .N(RX_RLY)) u_rxi (.clk(ck_recip), .d({rc_v, rc_x}), .q(rxi));
    ot_qkh_recip_leaf u_recip (.clk(ck_recip), .rst_n(rst_n), .v(rxi[32]), .x(rxi[31:0]), .y(ryo_t[31:0]), .vo(ryo_t[32]),
                               .fault(rf_t));
    ot_qkd_drly #(.W(34), .N(RY_RLY)) u_ryo (.clk(ck_core), .d({rf_t, ryo_t}), .q({rf, ryo}));
    assign rc_y = ryo[31:0];  assign rc_vo = ryo[32];  assign rc_fault = rf;
    // beat stores and lane groups
    wire [2047:0] sr_t, sr;
    generate for (g = 0; g < 4; g = g + 1) begin : g_s
        wire [5:0] ra;  wire [519:0] pin;
        ot_qkd_drly #(.W(6), .N(RA_RLY)) u_ra (.clk(ck_pbst[g]), .d(pb_ra[6*g +: 6]), .q(ra));
        // pi_* to the tile: the core captures pi_valid / pi_g in its pin flop, the tile in its own pin flop (= hub_p _b)
        ot_qkd_drly #(.W(520), .N(PI_RLY)) u_pi (.clk(ck_pbst[g]),
            .d({pi_valid[g], pi_g[g], pi_beat[6*g +: 6], pi_data[512*g +: 512]}), .q(pin));
        ot_nhb_pbst u_pbst (.clk(ck_pbst[g]), .rst_n(rst_n), .pv(pin[519]), .pgi(pin[518]), .pbeat(pin[517:512]),
                            .pdata(pin[511:0]), .ra(ra), .sr(sr_t[512*g +: 512]));
        ot_qkd_drly #(.W(512), .N(SR_RLY)) u_sr (.clk(ck_pvlg[g]), .d(sr_t[512*g +: 512]), .q(sr[512*g +: 512]));
    end endgenerate
    generate for (g = 0; g < 4; g = g + 1) begin : g_pv
        wire [32:0] vi;  wire [131:0] yo_t, yo;
        ot_qkd_drly #(.W(33), .N(PV_RLY)) u_vi (.clk(ck_pvlg[g]), .d({pl_v[g], pl_rz[32*g +: 32]}), .q(vi));
        ot_nhb_pvlg u_pv (.clk(ck_pvlg[g]), .rst_n(rst_n), .v(vi[32]),
            .s0(sr[0    + 128*g +: 128]), .s1(sr[512  + 128*g +: 128]),
            .s2(sr[1024 + 128*g +: 128]), .s3(sr[1536 + 128*g +: 128]),
            .rz(vi[31:0]), .y(yo_t[127:0]), .pf(yo_t[131:128]));
        ot_qkd_drly #(.W(132), .N(Y_RLY)) u_yo (.clk(ck_core), .d(yo_t), .q(yo));
        assign pl_y[128*g +: 128] = yo[127:0];
        assign pl_pf[4*g +: 4] = yo[131:128];
    end endgenerate
endmodule

// ---- the die composition on ONE clock with the hub_t ports (mo = am copy 0): the reference every hub bench binds ---
module ot_qwen_nearhbm_attn_hub_d #(
    parameter integer HD = 128,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer ZW = 4,
    parameter integer ZW_RLY = 0,
    parameter integer ZR_RLY = 0,
    parameter integer RA_RLY = 0,
    parameter integer SR_RLY = 1,
    parameter integer PV_RLY = 0,
    parameter integer Y_RLY = 0,
    parameter integer RX_RLY = 1,
    parameter integer RY_RLY = 1,
    parameter integer PI_RLY = 0       // extra stages of pi_* to the beat stores beyond the core's copy (0..3)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire [3:0]    si_valid,
    input  wire [7:0]    si_type,
    input  wire [3:0]    si_g,
    input  wire [7:0]    si_hh,
    input  wire [15:0]   si_k,
    input  wire [3:0]    si_any,
    input  wire [127:0]  si_data,
    input  wire [3:0]    pi_valid,
    input  wire [3:0]    pi_g,
    input  wire [23:0]   pi_beat,
    input  wire [2047:0] pi_data,
    output wire          mo_valid,
    output wire          mo_g,
    output wire [1:0]    mo_hh,
    output wire [31:0]   mo_data,
    output wire          out_valid,
    output wire          out_g,
    output wire [5:0]    out_beat,
    output wire [511:0]  out_data,
    output wire          fault,
    output wire [7:0]    ev
);
    wire [143:0] am;
    assign {mo_valid, mo_g, mo_hh, mo_data} = am[35:0];
`ifndef SYNTHESIS
    always @(posedge clk) if (am[35:0] !== am[71:36] || am[35:0] !== am[107:72] || am[35:0] !== am[143:108])
        $display("AHUB_D am copies disagree at %0t", $time);
`endif
    ot_qkd_ahub_die #(.HD(HD), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .ZW(ZW), .ZW_RLY(ZW_RLY), .ZR_RLY(ZR_RLY), .RA_RLY(RA_RLY), .SR_RLY(SR_RLY), .PV_RLY(PV_RLY), .Y_RLY(Y_RLY), .RX_RLY(RX_RLY), .RY_RLY(RY_RLY), .PI_RLY(PI_RLY)) u_die (.ck_core(clk), .ck_zh({4{clk}}), .ck_recip(clk), .ck_pbst({4{clk}}),
        .ck_pvlg({4{clk}}), .rst_n(rst_n), .start(start), .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh),
        .si_k(si_k), .si_any(si_any), .si_data(si_data), .pi_valid(pi_valid), .pi_g(pi_g), .pi_beat(pi_beat),
        .pi_data(pi_data), .am(am), .out_valid(out_valid), .out_g(out_g), .out_beat(out_beat), .out_data(out_data),
        .fault(fault), .ev(ev));
endmodule
