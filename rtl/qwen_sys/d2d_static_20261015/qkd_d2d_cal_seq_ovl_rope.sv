`timescale 1ns/1ps
// KV-DCAL-OVL-CODEX: independent TX/RX static list players plus registered boot/runtime config producer.
// Derived from bootcfg 7167b4ab7 and OVL 95d11133f. Images/list ROMs must come from one codec2 seam compile.
// ROM addresses are already player registers at the face; ROM q inputs are captured once (two-edge round trip).
// EP_SKEW-2 compensates the control input/output registers; no runtime schedule edge is added.
// Lists are external hard ROMs, never runtime-indexed flop arrays. Reset release uses two registered stages.
//
// KDIE4-LP 2026-10-22 NATIVE-SAFE STRUCTURE (rope list player only; the shared ot_qwen_d2d_ovl_seq /
// ot_qwen_d2d_list_play / ot_qwen_d2d_cal_seq used by the CLOSED qkd_d2d_cal_seq_pin_ovl_bc are untouched).
// The 015489b01 gate failed the mapped native census (<= 32 loads a driver): release_q[1] reset 348 loads, the landed
// rst_n 45 (the boot data pin flops), halt|reload 129, list prefetch enables 64, boot/sequencer cfg write selects 38-43,
// epoch-rise 35.  This core is the same machine, cycle for cycle (ot_qwen_d2d_ovl_seq with ADM 1, AUTO 0, tok_go 0,
// NL 1, inner EP_SKEW-2, specialised in place; the dead token-run state of ot_qwen_d2d_cal_seq is not built), with:
//   * halt / reload pin flops: one kept same-edge copy per list player (qkdlp_kffs / kffr, same pin, same reset);
//     init / ip: kept same-edge register copies per cfg_data byte / half / write group (same next-state nets).
//   * reset: release_q0 -> NRL KEPT same-edge copies of release_q[1] (qkdlp_kffr, D = release_q0, async clear from
//     rst_n): the same assert / release edges as release_q[1]; each copy clears one register group (<= 26 flops).
//     bcfg_addr / bcfg_data pin flops carry no reset (read only under the reset-cleared b_tx_q / b_rx_q).
//   * every high-fanout select of a wide register (halt|reload, list load, prefetch capture, epoch rise, boot and
//     sequencer cfg write) is a KEPT real-gate copy per <= 11-bit slice (qkdlp_kor / kand / kandn,
//     route.synth_keep_modules), so synthesis cannot merge the copies back; inverters / buffers are transparent to
//     the census and are never used as copies.
// Bench: tools/qwen_static_kv/run_dcal_ovl_rope.sh (independent ot_qwen_d2d_ovl_seq reference, cycle-exact edges);
// lockstep random equivalence against the 015489b01 core: tools/qwen_static_kv/run_dcal_ovl_rope_eq.sh.
module qkdlp_kor (input wire a, b, output wire y);
    assign y = a | b;
endmodule
module qkdlp_kand (input wire a, b, output wire y);
    assign y = a & b;
endmodule
module qkdlp_kandn (input wire a, bn, output wire y);
    assign y = a & ~bn;
endmodule
module qkdlp_kffr (input wire ck, rst_n, d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
module qkdlp_kffs (input wire ck, rst_n, d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b1; else q <= d;
endmodule

// One static start-list player (ot_qwen_d2d_list_play semantics, MIN_DT 4), register groups with own reset copies:
//   rl[0] nxt[15:0], nv, age   rl[1] nxt[31:16]   rl[2] addr, cur, start, seg, user, running, fault   rl[3] cnt
module qkdlp_list_play #(parameter integer AW = 11, parameter integer MUT_HALT_REWIND = 0) (
    input  wire          ck,
    input  wire [3:0]    rl,
    input  wire          go,
    input  wire          hlt, rld,      // player halt = hlt | rld (as ot_qwen_d2d_ovl_seq); own pin-flop copies
    output wire [AW-1:0] rom_addr,
    input  wire [31:0]   rom_q,
    output reg           start,
    output reg           seg,
    output reg  [1:0]    user,
    output reg           running,
    output reg           fault
);
    localparam integer MIN_DT = 4;
    localparam integer MHR = MUT_HALT_REWIND;
    reg [AW-1:0] addr;
    reg [31:0]   nxt;
    reg          nv;
    reg [1:0]    age;
    reg [19:0]   cnt;
    reg [31:0]   cur;
    assign rom_addr = addr;
    wire bad_n = (nxt[31:12] < MIN_DT) || (|nxt[6:0]);
    wire run1  = running && cnt == 20'd1;
    wire age2  = age == 2'd2;
    // kept select copies: [3:0] nxt bytes, [4] nv/age, [5] addr, [7:6] cnt halves, [8] cur/flags
    wire [8:0] hp;                  // hlt | rld (hlt / rld are this player's own kept pin-flop copies)
    wire [8:4] ld;                  // go | run1
    wire [4:0] pf;                  // !nv && age == 2 (prefetch capture)
    genvar g;
    generate
        for (g = 0; g < 9; g = g + 1) begin : g_hp
            qkdlp_kor u_hp (.a(hlt), .b(rld), .y(hp[g]));
        end
        for (g = 4; g < 9; g = g + 1) begin : g_ld
            qkdlp_kor u_ld (.a(go), .b(run1), .y(ld[g]));
        end
        for (g = 0; g < 5; g = g + 1) begin : g_pf
            qkdlp_kandn u_pf (.a(age2), .bn(nv), .y(pf[g]));
        end
        // prefetched next word, byte slices
        for (g = 0; g < 4; g = g + 1) begin : g_nxt
            wire r = rl[g / 2];
            always @(posedge ck or negedge r)
                if (!r) nxt[8*g +: 8] <= 8'd0;
                else begin
                    if (pf[g]) nxt[8*g +: 8] <= rom_q[8*g +: 8];
                    if (hp[g] && !MHR) nxt[8*g +: 8] <= 8'd0;
                end
        end
        // remaining count, two 10-bit halves
        for (g = 0; g < 2; g = g + 1) begin : g_cnt
            always @(posedge ck or negedge rl[3])
                if (!rl[3]) cnt[10*g +: 10] <= 10'd0;
                else if (hp[6+g]) begin
                    if (!MHR) cnt[10*g +: 10] <= 10'd0;
                end else if (ld[6+g]) cnt[10*g +: 10] <= nxt[12+10*g +: 10];
                else if (running) cnt[10*g +: 10] <= (cnt - 20'd1) >> (10*g);
        end
    endgenerate
    // prefetch state (nv, age)
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin nv <= 1'b0; age <= 2'd0; end
        else begin
            if (!nv) begin
                if (pf[4]) nv <= 1'b1;
                else age <= age + 2'd1;
            end
            if (hp[4]) begin
                if (!MHR) begin nv <= 1'b0; age <= 2'd0; end
            end else if (ld[4]) begin nv <= 1'b0; age <= 2'd0; end
        end
    // address
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) addr <= '0;
        else if (hp[5]) begin
            if (!MHR) addr <= '0;
        end else if (ld[5]) addr <= nxt[7] ? '0 : addr + 1'b1;
    // current word, start outputs
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) begin
            cur <= 32'd0; start <= 1'b0; seg <= 1'b0; user <= 2'd0; running <= 1'b0; fault <= 1'b0;
        end else begin
            start <= 1'b0;
            if (hp[8]) begin
                running <= 1'b0;
                if (!MHR) begin cur <= 32'd0; seg <= 1'b0; user <= 2'd0; end
            end else if (ld[8]) begin
                if (go && running) fault <= 1'b1;
                if (!go && cur[11]) begin start <= 1'b1; seg <= cur[10]; user <= cur[9:8]; end
                if (!nv || bad_n) fault <= 1'b1;
                running <= 1'b1;
                cur <= nxt;
            end
        end
endmodule

module qkd_d2d_cal_seq_ovl_rope_bc_core #(parameter integer AW = 11, parameter integer FIRST_OFS = 1176,
                                parameter integer ADM_OFS = 72, parameter integer ADM_LEN = 1100,
                                parameter integer EP_SKEW = 3, parameter integer MUT = 0, parameter integer MUT_HALT_REWIND=0) (
    input  wire        ck, rst_n, reload, epoch_go, halt,
    input  wire        bcfg_tx_we, bcfg_rx_we,
    input  wire [5:0]  bcfg_addr,
    input  wire [31:0] bcfg_data,
    output reg         cfg_tx_we, cfg_rx_we,
    output reg  [5:0]  cfg_addr,
    output reg  [31:0] cfg_data,
    output reg         cal_start, cal_seg, cal_ready, running,
    output wire [AW-1:0] tx_rom_addr, rx_rom_addr,
    input wire [31:0] tx_rom_q, rx_rom_q,
    output reg cal_start_rx, cal_seg_rx,
    output reg [1:0] cal_user_tx, cal_user_rx,
    output reg         adm_done,
    output reg         fault);
    `include "ovl_release_rope/ovl_release_img.svh"
    initial if (EP_SKEW < 2) $error("EP_SKEW >= 2 needed (input capture + output stage)");
    // ---- inner sequencer constants (ot_qwen_d2d_ovl_seq / ot_qwen_d2d_cal_seq at EP_SKEW - 2, NE 32, ADM 1)
    localparam integer EPI = EP_SKEW - 2;
    localparam integer NE = 32, NI = 2 * NE + 2;
    localparam integer E_ADM = EPI + ADM_OFS, E_SW = E_ADM + ADM_LEN, E_GO = EPI + FIRST_OFS;
    localparam [31:0] TXB0 = 32'd16, RXB0 = 32'd16;          // ADM 1: admission segment bases (TX_SEG2 / RX_SEG2)
    localparam [31:0] TX_SEG1 = OVL_K_TX_SEG1, RX_SEG1 = OVL_K_RX_SEG1;
    initial if (ADM_OFS <= NI + 4) $error("ADM_OFS must exceed the image load (2 NE + 2) + 2");
    // ---- reset: release_q0 + NRL kept same-edge copies of release_q[1]
    //   rl  0 e[15:0] + epoch state   1 e[31:16] + init / ip / ready / fault   2 cs cfg_data[31:16] + addr + we
    //       3 cs cfg_data[15:0] + start   4 anchor e[15:0] + act   5 anchor e[31:16] + ovl fault
    //       6..9 TX player   10..13 RX player   14 merge cfg_data[15:0] + addr + we   15 merge cfg_data[31:16] + state
    //      16 merge outputs + fault causes   17 init / ip copies
    localparam integer NRL = 18;
    reg release_q0;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) release_q0 <= 1'b0; else release_q0 <= 1'b1;
    wire [NRL-1:0] rl;
    genvar g;
    generate for (g = 0; g < NRL; g = g + 1) begin : g_rl
        qkdlp_kffr u_rl (.ck(ck), .rst_n(rst_n), .d(release_q0), .q(rl[g]));
    end endgenerate
    // ---- input capture (as qkd_d2d_cal_seq_pin) + the boot cfg pin registers
    reg reload_q, epoch_go_q, halt_q;
    reg b_tx_q, b_rx_q;
    reg [5:0] b_addr_q;
    reg [31:0] b_data_q;
    reg [31:0] tx_q, rx_q;
    always @(posedge ck) begin tx_q <= tx_rom_q; rx_q <= rx_rom_q; b_addr_q <= bcfg_addr; b_data_q <= bcfg_data; end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            reload_q <= 0; epoch_go_q <= 0; halt_q <= 1; b_tx_q <= 0; b_rx_q <= 0;
        end else begin
            reload_q <= reload; epoch_go_q <= epoch_go; halt_q <= halt;
            b_tx_q <= bcfg_tx_we; b_rx_q <= bcfg_rx_we;
        end
    end
    wire hlt = halt_q, rld = reload_q, ego = epoch_go_q;
    wire [1:0] hlt_p, rld_p;        // per list player (TX, RX): kept copies of halt_q / reload_q
    generate for (g = 0; g < 2; g = g + 1) begin : g_pc
        qkdlp_kffs u_h (.ck(ck), .rst_n(rst_n), .d(halt), .q(hlt_p[g]));
        qkdlp_kffr u_r (.ck(ck), .rst_n(rst_n), .d(reload), .q(rld_p[g]));
    end endgenerate

    // =================================================================================================================
    // calendar sequencer (ot_qwen_d2d_cal_seq, ADM 1, AUTO 0, tok_go 0, NL 1: never `running`, no token run)
    // =================================================================================================================
    reg        init;
    reg [6:0]  ip;
    reg        s_rdy, s_fault, s_tx, s_rx, s_cs, s_seg;
    reg [5:0]  s_addr;
    reg [31:0] s_data;
    reg        ep_q, eact, tokbase, adm_pend, adm_run, s_adm;
    reg [31:0] e;
    wire ep_rise = ego && !ep_q;
    wire e_b12 = eact && (e == 32'd1 || e == 32'd2) && tokbase;
    wire e_adm = eact && e == E_ADM && adm_pend;
    wire e_sw  = eact && (e == E_SW || e == E_SW + 1) && adm_run;
    wire nb    = !init && !hlt;
    wire c_b12 = nb && e_b12;
    wire c_adm = nb && !e_b12 && e_adm;
    wire c_sw  = nb && !e_b12 && !e_adm && e_sw;
    wire c_rld = nb && !e_b12 && !e_adm && !e_sw && rld;
    wire e_is1 = e == 32'd1, e_is2 = e == 32'd2, e_issw = e == E_SW, e_issw1 = e == E_SW + 1;
    wire init_last = ip == NI - 1;
    // kept same-edge init copies ([3:0] cfg_data bytes, [4] ip / ready, [5] cfg_addr / we) and ip copies (one per
    // cfg_data half: image decode); D = the init / ip next-state nets of the block below
    wire init_d = init ? !init_last : (c_rld ? 1'b1 : init);
    wire [6:0] ip_d = init ? ip + 7'd1 : (c_rld ? 7'd0 : ip);
    wire [5:0] i_c;
    wire [6:0] ipc [0:1];
    generate
        for (g = 0; g < 6; g = g + 1) begin : g_ic
            qkdlp_kffs u_i (.ck(ck), .rst_n(rl[17]), .d(init_d), .q(i_c[g]));
        end
        for (g = 0; g < 14; g = g + 1) begin : g_ipc
            qkdlp_kffr u_p (.ck(ck), .rst_n(rl[17]), .d(ip_d[g % 7]), .q(ipc[g / 7][g % 7]));
        end
    endgenerate
    // image word of the init stream: TX entry i (even step), RX entry i (odd step), then the two segment-1 bases
    reg [31:0] img_w;
    reg [6:0] ih;
    integer x, hh;
    always @* begin
        for (hh = 0; hh < 2; hh = hh + 1) begin
            ih = ipc[hh];
            x = ih >> 1;
            if (ih < 2 * NE) img_w[16*hh +: 16] = ih[0] ? OVL_K_RX_IMG[32*x + 16*hh +: 16] : OVL_K_TX_IMG[32*x + 16*hh +: 16];
            else img_w[16*hh +: 16] = (ih[0] ? RXB0 : TXB0) >> (16*hh);
        end
    end
    // epoch counter e, byte slices (kept epoch-rise / epoch-active copies)
    wire [3:0] e_rise;
    generate for (g = 0; g < 4; g = g + 1) begin : g_e
        qkdlp_kandn u_r (.a(ego), .bn(ep_q), .y(e_rise[g]));
        wire r = rl[g / 2];
        always @(posedge ck or negedge r)
            if (!r) e[8*g +: 8] <= 8'd0;
            else if (e_rise[g]) e[8*g +: 8] <= (g == 0) ? 8'd1 : 8'd0;
            else if (eact) e[8*g +: 8] <= (e + 32'd1) >> (8*g);
    end endgenerate
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin
            ep_q <= 1'b0; eact <= 1'b0; tokbase <= 1'b0; adm_pend <= 1'b0; adm_run <= 1'b0; s_adm <= 1'b0;
        end else begin
            ep_q <= ego;
            if (ep_rise) begin eact <= 1'b1; adm_pend <= 1'b1; s_adm <= 1'b0; end
            if (hlt) begin eact <= 1'b0; adm_run <= 1'b0; end
            if (init) begin
                if (init_last) tokbase <= 1'b0;
            end else if (c_b12) begin
                if (e_is2) tokbase <= 1'b0;
            end else if (c_adm) adm_run <= 1'b1;
            else if (c_sw) begin
                if (e_issw1) begin tokbase <= 1'b1; adm_run <= 1'b0; adm_pend <= 1'b0; s_adm <= 1'b1; end
            end else if (c_rld) tokbase <= 1'b0;
        end
    always @(posedge ck or negedge rl[1])
        if (!rl[1]) begin init <= 1'b1; ip <= 7'd0; s_rdy <= 1'b0; s_fault <= 1'b0; end
        else if (i_c[4]) begin
            ip <= ip + 1'b1;
            if (init_last) begin init <= 1'b0; s_rdy <= 1'b1; end
        end else if (c_adm) begin
            if (!s_rdy || tokbase) s_fault <= 1'b1;
        end else if (c_rld) begin init <= 1'b1; ip <= 7'd0; s_rdy <= 1'b0; end
    // cfg write stream: data byte slices with kept init / b12 / switch copies
    generate for (g = 0; g < 4; g = g + 1) begin : g_sd
        wire r = rl[3 - g / 2];
        always @(posedge ck or negedge r)
            if (!r) s_data[8*g +: 8] <= 8'd0;
            else if (i_c[g]) s_data[8*g +: 8] <= img_w[8*g +: 8];
            else if (c_b12) s_data[8*g +: 8] <= TXB0 >> (8*g);   // TX_SEG2 = RX_SEG2 = 16
            else if (c_sw) s_data[8*g +: 8] <= (e_issw ? TX_SEG1 : RX_SEG1) >> (8*g);
    end endgenerate
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) begin s_tx <= 1'b0; s_rx <= 1'b0; s_addr <= 6'd0; end
        else begin
            s_tx <= 1'b0; s_rx <= 1'b0;
            if (i_c[5]) begin
                s_addr <= (ip < 2 * NE) ? {1'b0, ip[5:1]} : 6'b100000;
                s_tx <= ~ip[0]; s_rx <= ip[0];
            end else if (c_b12) begin
                s_addr <= 6'b100000; s_tx <= e_is1; s_rx <= e_is2;
            end else if (c_sw) begin
                s_addr <= 6'b100000; s_tx <= e_issw; s_rx <= e_issw1;
            end
        end
    always @(posedge ck or negedge rl[3])
        if (!rl[3]) begin s_cs <= 1'b0; s_seg <= 1'b0; end
        else begin s_cs <= c_adm; s_seg <= c_adm; end

    // =================================================================================================================
    // list anchor + players (ot_qwen_d2d_ovl_seq)
    // =================================================================================================================
    reg act;
    reg [31:0] ae;
    wire go = act && ae == E_GO;
    wire [3:0] a_rise;
    generate for (g = 0; g < 4; g = g + 1) begin : g_ae
        qkdlp_kandn u_r (.a(ego), .bn(ep_q), .y(a_rise[g]));
        wire r = rl[4 + g / 2];
        always @(posedge ck or negedge r)
            if (!r) ae[8*g +: 8] <= 8'd0;
            else if (hlt) ;
            else if (a_rise[g]) ae[8*g +: 8] <= (g == 0) ? 8'd1 : 8'd0;
            else if (act) ae[8*g +: 8] <= (ae + 32'd1) >> (8*g);
    end endgenerate
    always @(posedge ck or negedge rl[4])
        if (!rl[4]) act <= 1'b0;
        else if (hlt) act <= 1'b0;
        else if (ep_rise) act <= 1'b1;
        else if (act && go) act <= 1'b0;
    wire t_start, t_seg, r_start, r_seg, t_run, r_run, t_f, r_f; wire [1:0] t_u, r_u;
    qkdlp_list_play #(.AW(AW), .MUT_HALT_REWIND(MUT_HALT_REWIND)) u_tx (.ck(ck), .rl(rl[9:6]), .go(go), .hlt(hlt_p[0]),
        .rld(rld_p[0]), .rom_addr(tx_rom_addr), .rom_q(tx_q), .start(t_start), .seg(t_seg), .user(t_u), .running(t_run),
        .fault(t_f));
    qkdlp_list_play #(.AW(AW), .MUT_HALT_REWIND(MUT_HALT_REWIND)) u_rx (.ck(ck), .rl(rl[13:10]), .go(go), .hlt(hlt_p[1]),
        .rld(rld_p[1]), .rom_addr(rx_rom_addr), .rom_q(rx_q), .start(r_start), .seg(r_seg), .user(r_u), .running(r_run),
        .fault(r_f));
    wire s_crs = s_cs | r_start, s_crg = s_cs ? s_seg : r_seg;
    wire s_cst = s_cs | t_start, s_csg = s_cs ? s_seg : t_seg;
    wire [1:0] s_ut = s_cs ? 2'd0 : t_u, s_ur = s_cs ? 2'd0 : r_u;
    wire s_run = t_run | r_run;
    reg o_fault;
    always @(posedge ck or negedge rl[5])
        if (!rl[5]) o_fault <= 1'b0;
        else if (s_fault || t_f || r_f || (s_cs && (t_start || r_start)) || (go && (!s_rdy || !s_adm || t_run || r_run)))
            o_fault <= 1'b1;

    // =================================================================================================================
    // merge: the sequencer's own writes only after its init stream.  The init's last write and cal_ready rise on the
    // same edge, so "after init" = cal_ready now AND one edge ago (a reload drops cal_ready with its first init write).
    // =================================================================================================================
    reg rdy_q, adm_act, btx_seen, brx_seen;
    reg f_col, f_run, f_stale, f_early;      // fault cause (bench observability; `fault` is their OR with the sequencer's)
    wire s_or = s_tx || s_rx, s_rr = s_rdy && rdy_q;
    // kept boot / sequencer write-select copies: [3:0] cfg_data bytes, [4] cfg_addr + we, [5] fault causes
    wire [5:0] m_b, m_s;
    generate for (g = 0; g < 6; g = g + 1) begin : g_m
        qkdlp_kor u_b (.a(b_tx_q), .b(b_rx_q), .y(m_b[g]));
        if (MUT == 1) begin : g_mut
            assign m_s[g] = 1'b0;
        end else begin : g_ok
            qkdlp_kand u_s (.a(s_or), .b(s_rr), .y(m_s[g]));
        end
        if (g < 4) begin : g_d
            wire r = rl[14 + g / 2];
            always @(posedge ck or negedge r)
                if (!r) cfg_data[8*g +: 8] <= 8'd0;
                else if (m_b[g]) cfg_data[8*g +: 8] <= b_data_q[8*g +: 8];
                else if (m_s[g]) cfg_data[8*g +: 8] <= s_data[8*g +: 8];
        end
    end endgenerate
    wire b_we = m_b[5], s_we = m_s[5];
    wire b_base = b_we && (b_addr_q == 6'b100000);
    wire n_col = b_we && s_we;
    wire n_run = b_we && (s_run || adm_act);
    wire n_stale = b_base && (b_tx_q ? (b_data_q != 32'd16) : (b_data_q != 32'd16));
    wire n_early = (s_cst || s_crs) && !(btx_seen && brx_seen);
    always @(posedge ck or negedge rl[14])
        if (!rl[14]) begin cfg_tx_we <= 0; cfg_rx_we <= 0; cfg_addr <= 0; end
        else if (m_b[4]) begin
            cfg_tx_we <= b_tx_q; cfg_rx_we <= b_rx_q; cfg_addr <= b_addr_q;
        end else begin
            cfg_tx_we <= m_s[4] && s_tx; cfg_rx_we <= m_s[4] && s_rx;
            if (m_s[4]) cfg_addr <= s_addr;
        end
    always @(posedge ck or negedge rl[15])
        if (!rl[15]) begin rdy_q <= 0; adm_act <= 0; btx_seen <= 0; brx_seen <= 0; end
        else begin
            rdy_q <= s_rdy;
            // admission run: from its start (layer 63) until adm_done; the token programme is the sequencer's `running`
            if (s_cst && s_csg && !s_adm) adm_act <= 1'b1;
            else if (s_adm || hlt) adm_act <= 1'b0;
            if (rld) begin btx_seen <= 1'b0; brx_seen <= 1'b0; end
            else begin
                if (b_base && b_tx_q) btx_seen <= 1'b1;
                if (b_base && b_rx_q) brx_seen <= 1'b1;
            end
        end
    always @(posedge ck or negedge rl[16])
        if (!rl[16]) begin
            cal_start <= 0; cal_seg <= 0; cal_ready <= 0; running <= 0; adm_done <= 0; cal_start_rx <= 0; cal_seg_rx <= 0;
            cal_user_tx <= 0; cal_user_rx <= 0;
            f_col <= 0; f_run <= 0; f_stale <= 0; f_early <= 0; fault <= 0;
        end else begin
            cal_start <= s_cst; cal_seg <= s_csg; cal_ready <= s_rdy; running <= s_run;
            cal_start_rx <= s_crs; cal_seg_rx <= s_crg; cal_user_tx <= s_ut; cal_user_rx <= s_ur;
            adm_done <= s_adm;
            if (n_col) f_col <= 1'b1;
            if (n_run) f_run <= 1'b1;
            if (n_stale) f_stale <= 1'b1;
            if (n_early) f_early <= 1'b1;
            fault <= fault || o_fault || n_col || n_run || n_stale || n_early;
        end
endmodule

// Hardened top owns both list ROM macros.  No extra address stage: player's register drives ROM addr.
module qkd_d2d_cal_seq_pin_ovl_rope #(parameter ROM_DIR = "", parameter integer MUT=0, parameter integer MUT_HALT_REWIND=0) (
    input wire ck, rst_n, reload, epoch_go, halt,
    input wire bcfg_tx_we, bcfg_rx_we,
    input wire [5:0] bcfg_addr, input wire [31:0] bcfg_data,
    output wire cfg_tx_we, cfg_rx_we, output wire [5:0] cfg_addr, output wire [31:0] cfg_data,
    output wire cal_start, cal_seg, cal_start_rx, cal_seg_rx,
    output wire [1:0] cal_user_tx, cal_user_rx,
    output wire cal_ready, adm_done, running, fault
);
    `include "ovl_release_rope/ovl_wrapper_params.svh"
    localparam EFFECTIVE_ROM_DIR = ROM_DIR == "" ? ROPE_OVL_ROM_DIR : ROM_DIR;
    wire [10:0] ta, ra;
    wire [71:0] tq, rq;
`ifdef SYNTHESIS
    ot_rom_4096x72_m8 u_tx_rom (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ta}),.rd_out(tq));
    ot_rom_4096x72_m8 u_rx_rom (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ra}),.rd_out(rq));
`else
    ot_rom_4096x72_m8 #(.VIAMAP({EFFECTIVE_ROM_DIR,"/ovl_k_tx.viamap.hex"}),.INSTANCE("ovl_k_tx")) u_tx_rom
        (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ta}),.rd_out(tq));
    ot_rom_4096x72_m8 #(.VIAMAP({EFFECTIVE_ROM_DIR,"/ovl_k_rx.viamap.hex"}),.INSTANCE("ovl_k_rx")) u_rx_rom
        (.clk(ck),.ce_in(1'b1),.addr_in({1'b0,ra}),.rd_out(rq));
`endif
    qkd_d2d_cal_seq_ovl_rope_bc_core #(.FIRST_OFS(ROPE_OVL_FIRST_OFS), .ADM_OFS(ROPE_OVL_ADM_OFS),
        .ADM_LEN(ROPE_OVL_ADM_LEN), .MUT(MUT),.MUT_HALT_REWIND(MUT_HALT_REWIND)) u_core (
        .ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
        .bcfg_tx_we(bcfg_tx_we),.bcfg_rx_we(bcfg_rx_we),.bcfg_addr(bcfg_addr),.bcfg_data(bcfg_data),
        .cfg_tx_we(cfg_tx_we),.cfg_rx_we(cfg_rx_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .cal_start(cal_start),.cal_seg(cal_seg),.cal_start_rx(cal_start_rx),.cal_seg_rx(cal_seg_rx),
        .cal_user_tx(cal_user_tx),.cal_user_rx(cal_user_rx),.cal_ready(cal_ready),.adm_done(adm_done),
        .running(running),.fault(fault),.tx_rom_addr(ta),.tx_rom_q(tq[31:0]),.rx_rom_addr(ra),.rx_rom_q(rq[31:0]));
endmodule
