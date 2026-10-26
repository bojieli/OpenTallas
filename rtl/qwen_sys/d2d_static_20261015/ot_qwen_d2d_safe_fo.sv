`timescale 1ns/1ps
// =====================================================================================================================
// KV-D2D SAFE FAN-OUT link end (claude/kv-d2d-1019, 2026-10-19).  Opt-in structural successor of ot_qwen_d2d_static_end
// for the KV-die masters qkd_d2d_static / qkd_d2d_static_ovl #(.SAFE_FO(1)); SAFE_FO = 0 (default) builds the as-built
// modules unchanged, so every closed view still binds.
//
// WHY (SAFE-DESIGN checklist item 3, owner 10-19): the codec2 source 353123a8d had 417 / 402 BUF/INV-transparent nets over
// 32 terminal loads (max 1,096): the slot-store bypass selects hit_age0/1, the calendar segment-1 base seg1 and pointer ptr
// (32:1 read muxes of the 32 x 32 b image), the producer capture strobes fire[p] (548-b payload select), epoch_begin, the
// pin flops cal_start / cal_seg / cfg_*, the image write decode and the STATUS capture enable.  A gate-level fork of that
// netlist (58f622b46 / c9c068a71) could not prove its copies equal at power-up: copies that HOLD their own state are not
// convergent at the first edge (SAT: 19 seg1[1] copies).
//
// RULE USED HERE FOR EVERY COPY: a copy's D input is the SAME NET as its master's D input (or the same pin), never the copy's
// own Q.  After one clock edge every copy equals its master from ANY initial state; copies of reset registers also share the
// master's reset, so they are equal while reset is asserted too.  Copies are (* keep *) registers (ot_keep_regs keeps the
// cells, opt_merge cannot fold them).  No register, edge, latency or calendar slot is added: every output is cycle-identical
// to the as-built end (proved by the lockstep miter rtl/test/qwen_split/tb_kv_d2d_sfo_miter.sv on the full 66-write cold
// sequence; OT_FO_CHECK asserts copy == master on every edge from random initial state).
//
// Structure (loads are logical terminal pins after BUF/INV collapse; target <= 32, typically <= 24):
//   * calendar: segment-1 base kept ONE-HOT (2 copies, 16 output bits each) and the pointer kept one-hot + lap bit
//     (2 copies); tbl[seg1] / tbl[ptr] become AND-OR selects; image halves take their own cfg_data pin copy; start / seg
//     arrive as 4 pin copies, each loading one field group.
//   * slot store: registered one-hot bypass selects (dq / dqq / macro) in groups of 16 bits; each bank compares its OWN
//     copies of the write / read slot counters, so the four banks' select cones stay distinct after ABC.
//   * producer capture: the last stage of every port's fixed delay line is copied per 24 payload bits.
//   * epoch_begin: copies from the recovery (ot_qwen_d2d_recovery NEB); written-map quarters, the slot pipes, the end's
//     control and the STATUS consumer each take their own copy.
//   * STATUS capture: the end registers per-group copies of (rx_event[2], rx_slot[2]) from the same D nets as the
//     originals; the 156 captured bits are written in 10 groups, each enabled by its own copies.
// MUTFO (bench only): 1 = calendar seg1 copy 1 holds its OWN state (the non-convergent form; OT_FO_CHECK must fail),
// 2 = slot-store bank 0 group 3 swaps its dq / dqq selects, 3 = port-0 capture copy 5 samples one stage early,
// 4 = the end's control copy of epoch_begin (eb_c[8]) is dropped (slot counters survive an epoch).
// =====================================================================================================================

// ---------------------------------------------------------------------------------------------------------------------
// Calendar (function of ot_qwen_d2d_cal, NE = 32): one-hot base / pointer, pin copies per field group.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_cal_sf #(parameter integer NE = 32, parameter integer AW = $clog2(NE), parameter integer MUTFO = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_we,
    input  wire [AW:0]   cfg_addr,       // [AW] = 1: segment-1 base register (cfg_data[AW-1:0])
    input  wire [63:0]   cfg_data_c,     // two identical pin copies: [31:0] entries 0..NE/2-1, [63:32] the rest
    input  wire [AW-1:0] cfg_base_c,     // a third pin copy of cfg_data[AW-1:0]: the segment-1 base decode
    input  wire [3:0]    start_c,        // four identical pin copies of the compiled start strobe
    input  wire [3:0]    seg_c,          // four identical pin copies of start_seg
    input  wire [3:0]    halt_c,         // copies of halt: [0] pointer low half, [1] pointer high half, [2] cnt, [3] run state
    output reg           ev_v,
    output reg  [2:0]    ev_port,
    output reg  [3:0]    ev_kind,
    output reg  [4:0]    ev_beat,
    output reg           running,
    output reg           fault
);
    generate if (NE != 32) begin : g_ne_unsupported
        OT_QWEN_D2D_CAL_SF_SUPPORTS_NE32_ONLY u_ne ();
    end endgenerate
    localparam integer H = NE / 2;
    // ---- compiler image: one 32-b register per entry, written only while stopped (as built) ----
    wire [32*NE-1:0] tv;
    genvar gi;
    for (gi = 0; gi < NE; gi = gi + 1) begin : g_e
        reg [31:0] e;
        always @(posedge ck)
            if (cfg_we && !running && !cfg_addr[AW] && cfg_addr[AW-1:0] == gi)
                e <= (gi < H) ? cfg_data_c[31:0] : cfg_data_c[63:32];
        assign tv[32*gi +: 32] = e;
    end
    // ---- segment-1 base, one-hot.  Copy 0 is the master; copy 1 takes the SAME D net (sel1_d) ----
    wire seg_we = cfg_we && !running && cfg_addr[AW];
    wire [NE-1:0] sel1_dec = {{(NE-1){1'b0}}, 1'b1} << cfg_base_c;
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] sel1_c0;
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] sel1_c1;
    wire [NE-1:0] sel1_d = seg_we ? sel1_dec : sel1_c0;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck) begin
        sel1_c0 <= sel1_d;
        sel1_c1 <= (MUTFO == 1) ? (seg_we ? sel1_dec : sel1_c1) : sel1_d;
    end
    // ---- AND-OR selects: bits [H-1:0]... of the selected word from copy 0, the upper word half from copy 1 ----
    reg [31:0] f1_lo, f1_hi, nx_lo, nx_hi;
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] pc0;   // one-hot ptr[AW-1:0], master (advance, fault, rotate)
    (* keep = "true", dont_touch = "true" *) reg [NE-1:0] pc1;   // copy: same D net, selects the upper word half
    reg ph;                                                     // ptr[AW]
    integer k;
    always @* begin
        f1_lo = 32'd0; f1_hi = 32'd0; nx_lo = 32'd0; nx_hi = 32'd0;
        for (k = 0; k < NE; k = k + 1) begin
            f1_lo = f1_lo | ({32{sel1_c0[k]}} & tv[32*k +: 32]);
            f1_hi = f1_hi | ({32{sel1_c1[k]}} & tv[32*k +: 32]);
            nx_lo = nx_lo | ({32{pc0[k]}} & tv[32*k +: 32]);
            nx_hi = nx_hi | ({32{pc1[k]}} & tv[32*k +: 32]);
        end
    end
    wire [31:0] f1  = {f1_hi[31:16], f1_lo[15:0]};               // = tbl[seg1]
    wire [31:0] nxt = {nx_hi[31:16], nx_lo[15:0]};               // = tbl[ptr[AW-1:0]]
    // Prefetch both first entries while the compiler image is stable (as built: same edges, same cfg_recent rule).
    reg [31:0] first0_q, first1_q;
    reg cfg_recent;
    always @(posedge ck) begin
        first0_q <= tv[31:0]; first1_q <= f1;
        cfg_recent <= cfg_we;
    end
    // first word fields: [17:0] by seg copy 0, [31:18] (dt) by seg copy 1
    wire [31:0] first = {seg_c[1] ? first1_q[31:18] : first0_q[31:18], seg_c[0] ? first1_q[17:0] : first0_q[17:0]};
    reg [31:0] cur;
    reg [13:0] cnt;
    reg [4:0]  rep, bcur;
    // running and a KEPT copy share one D net (run_d); the pointer's upper half advances on the copy
    (* keep = "true", dont_touch = "true" *) reg run_c;
    wire run_d = halt_c[3] ? 1'b0 : start_c[0] ? 1'b1 : (running && cnt == 14'd1 && rep == 5'd0 && cur[17]) ? 1'b0 : running;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_n)
        if (!rst_n) begin running <= 1'b0; run_c <= 1'b0; end
        else begin running <= run_d; run_c <= run_d; end
    wire adv   = running && cnt == 14'd1 && rep == 5'd0 && !cur[17];
    wire adv_h = run_c && cnt == 14'd1 && rep == 5'd0 && !cur[17];
    // ---- pointer: one-hot + lap bit, ONE D net for master and copy (ptr <= {0,sb}+1 / ptr+1 / hold) ----
    wire [NE-1:0] sel1_h = {sel1_c1[NE-1:H], sel1_c0[H-1:0]};
    wire [NE-1:0] st_s1  = {sel1_h[NE-2:0], sel1_h[NE-1]};       // one-hot (seg1 + 1) mod NE
    wire [NE-1:0] rot    = {pc0[NE-2:0], pc0[NE-1]};
    reg  [NE-1:0] pd;
    reg           phd;
    always @* begin
        for (k = 0; k < NE; k = k + 1) begin
            if ((k < H) ? halt_c[0] : halt_c[1]) pd[k] = pc0[k];
            else if ((k < H) ? start_c[2] : start_c[3]) pd[k] = ((k < H) ? seg_c[2] : seg_c[3]) ? st_s1[k] : (k == 1);
            else if ((k < H) ? adv : adv_h) pd[k] = rot[k];
            else pd[k] = pc0[k];
        end
        if (halt_c[1]) phd = ph;
        else if (start_c[3]) phd = seg_c[3] & sel1_c1[NE-1];
        else if (adv_h) phd = ph ^ pc0[NE-1];
        else phd = ph;
    end
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pc0 <= {{(NE-1){1'b0}}, 1'b1}; pc1 <= {{(NE-1){1'b0}}, 1'b1}; ph <= 1'b0; end
        else begin pc0 <= pd; pc1 <= pd; ph <= phd; end
    // ---- run state (as built; start copy 0) ----
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            ev_v <= 1'b0; ev_port <= 3'd0; ev_kind <= 4'd0; ev_beat <= 5'd0;
            cur <= 32'd0; fault <= 1'b0; rep <= 5'd0; bcur <= 5'd0;
        end else begin
            ev_v <= 1'b0;
            if (cfg_we && running) fault <= 1'b1;
            if (halt_c[3]) ;                                                       // running: run_d
            else if (start_c[0]) begin
                if (running || cfg_we || cfg_recent) fault <= 1'b1;
                cur <= first; rep <= first[4:0]; bcur <= first[9:5];
                if (first[31:18] == 14'd0 || {1'b0, first[9:5]} + {1'b0, first[4:0]} > 6'd31) fault <= 1'b1;
            end else if (running) begin
                if (cnt == 14'd1) begin
                    ev_v <= 1'b1; ev_port <= cur[16:14]; ev_kind <= cur[13:10]; ev_beat <= bcur;
                    if (rep != 5'd0) begin rep <= rep - 5'd1; bcur <= bcur + 5'd1; end   // burst: next cycle
                    else if (cur[17]) ;                                            // running: run_d
                    else begin
                        if (ph && pc0[0]) fault <= 1'b1;                               // ptr == NE
                        if (nxt[31:18] == 14'd0 || {1'b0, nxt[9:5]} + {1'b0, nxt[4:0]} > 6'd31) fault <= 1'b1;
                        cur <= nxt; rep <= nxt[4:0]; bcur <= nxt[9:5];
                    end
                end
            end
        end
    end
    // ---- interval counter (as built; start copy 1) ----
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) cnt <= 14'd0;
        else if (halt_c[2]) cnt <= cnt;
        else if (start_c[1]) cnt <= first[31:18];
        else if (running) begin
            if (cnt == 14'd1) begin
                if (rep == 5'd0 && !cur[17]) cnt <= nxt[31:18];
            end else cnt <= cnt - 1'b1;
        end
    end
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck) begin
        if (fo_armed && (sel1_c1 !== sel1_c0 || pc1 !== pc0 || run_c !== running))
            $display("FO_COPY_MISMATCH %m t=%0t sel1 %h/%h pc %h/%h", $time, sel1_c0, sel1_c1, pc0, pc1);
        fo_armed <= 1'b1;
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Slot-store bank (function of ot_qkvd_llr_replay_sram_leaf): registered one-hot bypass selects per GB-bit group.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_llr_replay_sram_leaf_sf #(
    parameter integer W = 137, QD = 64,
    parameter integer QA = $clog2(QD), MUT = 0, GB = 16, MUTFO = 0
) (
    input wire ck, we,
    input wire [QA-1:0] wa, ra,
    input wire [W-1:0] din,
    output reg [W-1:0] dout
);
    localparam integer NG = (W + GB - 1) / GB;
    (* keep = "true", dont_touch = "true" *) reg wq;
    (* keep = "true", dont_touch = "true" *) reg [QA-1:0] aq;
    reg [W-1:0] dq, dqq;
    wire [511:0] mr;
`ifdef OT_QKD_REPLAY_HIT_MUT
    wire h0 = we && wa != ra;   // negative control: corrupt current-age selection
`else
    wire h0 = we && wa == ra;
`endif
    wire h1 = wq && aq == ra;
    // as built: dout <= hit_age0 ? dq : hit_age1 ? dqq : macro, with hit_age0 <= h0, hit_age1 <= h1 at this edge
    (* keep = "true", dont_touch = "true" *) reg [NG-1:0] s_dq;
    (* keep = "true", dont_touch = "true" *) reg [NG-1:0] s_dqq;
    (* keep = "true", dont_touch = "true" *) reg [NG-1:0] s_mr;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck) begin
        wq <= we; aq <= wa; dq <= din; dqq <= dq;
        s_dq <= {NG{h0}}; s_dqq <= {NG{!h0 && h1}}; s_mr <= {NG{!h0 && !h1}};
    end
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}},dq}),
        .w_mask_in({{(512-W){1'b0}},{W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    genvar g;
    for (g = 0; g < NG; g = g + 1) begin : g_sel
        localparam integer LO = g * GB;
        localparam integer WG = (LO + GB <= W) ? GB : W - LO;
        wire a = (MUTFO == 2 && g == 3) ? s_dqq[g] : s_dq[g];
        wire b = (MUTFO == 2 && g == 3) ? s_dq[g] : s_dqq[g];
        always @(posedge ck)
            dout[LO +: WG] <= (({WG{a}} & dq[LO +: WG]) | ({WG{b}} & dqq[LO +: WG]) | ({WG{s_mr[g]}} & mr[LO +: WG])) ^
                ((MUT != 0 && g == 0) ? {{(WG-1){1'b0}}, 1'b1} : {WG{1'b0}});
    end
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck) begin
        if (fo_armed && (s_dq !== {NG{s_dq[0]}} || s_dqq !== {NG{s_dqq[0]}} || s_mr !== {NG{s_mr[0]}}))
            $display("FO_COPY_MISMATCH %m t=%0t", $time);
        fo_armed <= 1'b1;
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Slot-link control (function of ot_qwen_static_slot_ctl): written map in four quarters, each with its own epoch_begin
// copy and its own copies of the write / read slot; slot / epoch pipes on their own epoch_begin copies.
// eb_c: [0] control, [1] slot pipe s1..s4, [2] epoch pipe e1..e3, [3] RX expectation es / re, [4..7] written quarters.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_static_slot_ctl_sf #(
    parameter integer FW=548, CW=16, PW=FW+19+CW, MUTFO=0
)(
    input wire clk,
    input wire rst_n,
    input wire [7:0] eb_c,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot,
    input wire [FW-1:0] q_data,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output reg p_tx_v,
    output reg [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output reg rx_v,
    output wire rx_v_nx,            // rx_v's D outside reset / epoch_begin (STATUS capture copies in the end)
    output reg [FW-1:0] rx_flit,
    output reg epoch_abort,
    output wire [8:0] ab_c,         // copies of epoch_abort for the end's halt copies (same D net)
    output reg [7:0] fault_cause
);
    reg [63:0] written;
    reg v1,v2,v3,v4,cmd_wv;
    reg cmd_ov;
    reg [5:0] cmd_ws;
    (* keep = "true", dont_touch = "true" *) reg [23:0] cws_c;   // 4 copies of cmd_ws (same D: wr_slot)
    reg [5:0] s1,s2,s3,s4;
    (* keep = "true", dont_touch = "true" *) reg [23:0] s1_c;    // 4 copies of s1 (same D net s1_d)
    reg [7:0] e1,e2,e3;
    reg [FW-1:0] q_pin;
    wire [FW+18:0] body={1'b0,e3,1'b0,1'b1,2'b00,s3,q_pin};
    reg rv,ev;
    reg [5:0] es;
    reg [7:0] re;
    reg [PW-1:0] rf;
    wire [CW-1:0] tx_crc, rx_crc;
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_tx_crc(.d(body),.q(tx_crc));
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(rf[FW+18:0]),.q(rx_crc));
    wire crc_bad=rv && ev && (rx_crc!==rf[PW-1-:CW]);
    wire slot_bad=rv && ev && (rf[FW+7:FW]!=={2'b00,es} || rf[FW+17-:8]!==re ||
                         rf[FW+8]!==1'b1 || rf[FW+9]!==1'b0 || rf[FW+18]!==1'b0);
    // written[cmd_ws] / written[s1], each quarter read through its own slot copies
    wire [3:0] w_at_ws, w_at_s1;
    genvar q;
    for (q = 0; q < 4; q = q + 1) begin : g_rd
        wire [5:0] wsq = cws_c[6*q +: 6], s1q = s1_c[6*q +: 6];
        wire [15:0] wq = written[16*q +: 16];
        assign w_at_ws[q] = wsq[5:4] == q && wq[wsq[3:0]];
        assign w_at_s1[q] = s1q[5:4] == q && wq[s1q[3:0]];
    end
    wire write_collision=cmd_wv && ((v2 && cmd_ws==s2)||(v3 && cmd_ws==s3)||(v4 && cmd_ws==s4)||
        ((|w_at_ws) && !(v1 && s1==cmd_ws)));
    wire unread_slot=v1 && !(|w_at_s1) && !(cmd_wv && cmd_ws==s1);
    wire [7:0] new_fault={cmd_wv && (cmd_ov!==1'b1),write_collision,unread_slot,v3 && !p_tx_up,
                          rv && !ev,ev && !rv,slot_bad,crc_bad};
    assign rx_v_nx = ev && rv && !slot_bad && !crc_bad && !epoch_abort;
    // epoch_abort / cmd_wv / v1 copies on their masters' D nets: [12:4] -> ab_c (end halt), [3:0] written quarters
    wire ab_d  = eb_c[0] ? 1'b0 : (epoch_abort | (|new_fault));
    wire cwv_d = eb_c[0] ? 1'b0 : (wr_v && !epoch_abort);
    wire v1_d  = eb_c[0] ? 1'b0 : (rd_v && !epoch_abort);
    (* keep = "true", dont_touch = "true" *) reg [12:0] abc;
    (* keep = "true", dont_touch = "true" *) reg [3:0] cwv_c;
    (* keep = "true", dont_touch = "true" *) reg [3:0] v1_c;
    (* keep = "true", dont_touch = "true" *) always @(posedge clk or negedge rst_n)
        if (!rst_n) begin abc <= 13'd0; cwv_c <= 4'd0; v1_c <= 4'd0; end
        else begin abc <= {13{ab_d}}; cwv_c <= {4{cwv_d}}; v1_c <= {4{v1_d}}; end
    assign ab_c = abc[12:4];
    always @(posedge clk)begin
        cmd_ws<=wr_slot;cmd_ov<=wr_observed_v;
        q_pin<=q_data;
        rf<=p_rx_flit;
        p_tx_flit<={tx_crc,body};
        rx_flit<=rf[FW-1:0];
    end
    (* keep = "true", dont_touch = "true" *) always @(posedge clk) cws_c <= {4{wr_slot}};
    // s1 master and copies share one D net (hold on epoch_begin, as built)
    wire [5:0] s1_d = eb_c[1] ? s1 : rd_slot;
    (* keep = "true", dont_touch = "true" *) always @(posedge clk or negedge rst_n)
        if (!rst_n) s1_c <= 24'd0; else s1_c <= {4{s1_d}};
    // control (as built, eb copy 0)
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;rv<=0;ev<=0;
            p_tx_v<=0;rx_v<=0;
            epoch_abort<=0;fault_cause<=0;
        end else if(eb_c[0])begin
            cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;rv<=0;ev<=0;
            p_tx_v<=0;rx_v<=0;epoch_abort<=0;fault_cause<=0;
        end else begin
            cmd_wv<=wr_v && !epoch_abort;
            v1<=rd_v && !epoch_abort;v2<=v1;v3<=v2;v4<=v3;
            p_tx_v<=v3 && !epoch_abort;
            rv<=p_rx_v;ev<=rx_expect_v;
            rx_v<=rx_v_nx;
            if(!epoch_abort)begin
                fault_cause<=fault_cause|new_fault;
                if(|new_fault)epoch_abort<=1'b1;
            end
        end
    end
    // slot pipe (hold on epoch_begin, eb copy 1)
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin s1<=0;s2<=0;s3<=0;s4<=0; end
        else if(!eb_c[1])begin s1<=rd_slot;s2<=s1;s3<=s2;s4<=s3; end
    // epoch pipe (eb copy 2) and RX expectation (eb copy 3)
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin e1<=0;e2<=0;e3<=0; end
        else if(!eb_c[2])begin e1<=epoch;e2<=e1;e3<=e2; end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin es<=0;re<=0; end
        else if(!eb_c[3])begin es<=rx_expect_slot;re<=epoch; end
    // written map: quarter q clears on eb copy 4+q; set by a captured write, cleared by a compiled read (as built order)
    for (q = 0; q < 4; q = q + 1) begin : g_wm
        wire ebq = eb_c[4+q];
        wire [5:0] wsq = cws_c[6*q +: 6], s1q = s1_c[6*q +: 6];
        integer j;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) written[16*q +: 16] <= 16'd0;
            else if(ebq) written[16*q +: 16] <= 16'd0;
            else for (j = 0; j < 16; j = j + 1) begin
                if(cwv_c[q] && !abc[q] && wsq == 16*q + j) written[16*q + j] <= 1'b1;
                if(v1_c[q] && !abc[q] && s1q == 16*q + j) written[16*q + j] <= 1'b0;
            end
    end
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge clk) begin
        if (fo_armed && (cws_c !== {4{cmd_ws}} || s1_c !== {4{s1}} || abc !== {13{epoch_abort}} || cwv_c !== {4{cmd_wv}} ||
                         v1_c !== {4{v1}}))
            $display("FO_COPY_MISMATCH %m t=%0t", $time);
        fo_armed <= 1'b1;
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Slot link (function of ot_qwen_static_slot_link): bank b uses its own write / read slot copies (wr_slot_c / rd_slot_c
// [6b+:6]); the control uses copy 4.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_static_slot_link_sf #(
    parameter integer FW=548, CW=16, PW=FW+19+CW, MUT=0, MUTFO=0
)(
    input wire [4:0] ck,
    input wire rst_n,
    input wire [7:0] eb_c,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [29:0] wr_slot_c,
    input wire [FW-1:0] wr_flit,
    input wire rd_v,
    input wire [29:0] rd_slot_c,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output wire p_tx_v,
    output wire [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output wire rx_v,
    output wire rx_v_nx,
    output wire [FW-1:0] rx_flit,
    output wire epoch_abort,
    output wire [8:0] ab_c,
    output wire [7:0] fault_cause
);
    localparam integer BW=137;
    wire [4*BW-1:0] wd={{(4*BW-FW){1'b0}},wr_flit};
    wire [4*BW-1:0] rd;
    wire issue_write=wr_v && !epoch_abort && !eb_c[0];
    for(genvar b=0;b<4;b=b+1)begin:g_bank
        ot_qkvd_llr_replay_sram_leaf_sf #(.W(BW),.MUT(MUT==3 && b==0),.MUTFO(b==0 ? MUTFO : 0)) u_store(
            .ck(ck[b+1]),.we(issue_write),.wa(wr_slot_c[6*b +: 6]),.ra(rd_slot_c[6*b +: 6]),
            .din(wd[b*BW+:BW]),.dout(rd[b*BW+:BW]));
    end
    ot_qwen_static_slot_ctl_sf #(.FW(FW),.CW(CW),.PW(PW),.MUTFO(MUTFO)) u_ctl (
        .clk(ck[0]),.q_data(rd[FW-1:0]),
        .rst_n(rst_n), .eb_c(eb_c), .epoch(epoch), .wr_v(wr_v), .wr_observed_v(wr_observed_v), .wr_slot(wr_slot_c[24 +: 6]),
        .rd_v(rd_v), .rd_slot(rd_slot_c[24 +: 6]), .rx_expect_v(rx_expect_v), .rx_expect_slot(rx_expect_slot),
        .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit), .rx_v(rx_v),
        .rx_v_nx(rx_v_nx), .rx_flit(rx_flit), .epoch_abort(epoch_abort), .ab_c(ab_c), .fault_cause(fault_cause));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Link end (function of ot_qwen_d2d_static_end with NRC 4 reset copies).  Extra ports: start / seg / cfg pin copies, epoch
// begin copies (eb_c: [7:0] slot link, [8] end control, [9] end pipes), STATUS capture copies (st_ev_c / st_rs_c).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_static_end_sf #(
    parameter integer NT = 4, NR = 4, FW = 548, CW = 16, PW = FW + 19 + CW, NE = 32,
    parameter [8*4-1:0] TXD = {8'd1, 8'd1, 8'd2, 8'd1},
    parameter integer MUT = 0,
    parameter integer OVL = 0,
    parameter integer NRC = 4,
    parameter integer NG2 = 10,     // STATUS capture groups
    parameter integer FGB = 24,     // payload bits per producer capture copy
    parameter integer MUTFO = 0
) (
    input  wire [4:0]       ck,
    input  wire [NRC-1:0]   rst_n,
    input  wire             cfg_tx_we, cfg_rx_we,
    input  wire [11:0]      cfg_addr_c,   // [5:0] TX calendar, [11:6] RX calendar (pin copies)
    input  wire [127:0]     cfg_data_c,   // [63:0] TX calendar halves, [127:64] RX calendar halves (pin copies)
    input  wire [9:0]       cfg_base_c,   // [4:0] TX, [9:5] RX: pin copies of cfg_data[4:0] for the base decode
    input  wire [9:0]       eb_c,
    input  wire             epoch_begin,
    input  wire [7:0]       epoch,
    input  wire             cal_start,    // OVL user tag only (the calendars use start_c)
    input  wire             cal_start_rx,
    input  wire [7:0]       start_c,      // [3:0] TX calendar, [7:4] RX calendar (OVL: the RX start pin)
    input  wire [7:0]       seg_c,
    input  wire [1:0]       cal_user_tx,
    input  wire [1:0]       cal_user_rx,
    output wire [1:0]       tx_user,
    output reg  [1:0]       rx_user,
    output wire [NT-1:0]    tx_slot,
    output wire [3:0]       tx_kind,
    output wire [4:0]       tx_beat,
    input  wire [NT-1:0]    tx_valid,
    input  wire [NT*FW-1:0] tx_payload,
    output reg  [NR-1:0]    rx_event,
    output reg  [NR-1:0]    rx_slot,
    output reg  [3:0]       rx_kind,
    output reg  [4:0]       rx_beat,
    output wire [FW-1:0]    rx_payload,
    output wire [NG2-1:0]   st_ev_c,      // copies of rx_event[2] (same D nets as the link's rx_v and r2p)
    output wire [NG2-1:0]   st_rs_c,      // copies of rx_slot[2]
    input  wire             p_tx_up,
    output wire             p_tx_v,
    output wire [PW-1:0]    p_tx_flit,
    input  wire             p_rx_v,
    input  wire [PW-1:0]    p_rx_flit,
    output wire             epoch_abort,
    output wire [7:0]       fault_cause,
    output reg              end_fault,
    output wire             cal_running
);
    generate if (NRC != 4) begin : g_nrc_unsupported
        OT_QWEN_D2D_END_SF_NEEDS_NRC4 u_nrc ();
    end endgenerate
    // halt = epoch_abort | end_fault as 9 copies: [3:0] TX calendar, [7:4] RX calendar, [8] this end (capture / write gate)
    wire [8:0] ab_x;
    (* keep = "true", dont_touch = "true" *) reg [8:0] efc;   // end_fault copies (same D net, below)
    wire [8:0] halt_c = ab_x | efc;
    wire halt = halt_c[8];
    wire rst_tc = rst_n[0], rst_cl = rst_n[1], rst_lk = rst_n[2], rst_rc = rst_n[3];
    wire tv, rv; wire [2:0] tp, rp; wire [3:0] tk, rk; wire [4:0] tb, rb; wire tf, rf, trun, rrun;
    ot_qwen_d2d_cal_sf #(.NE(NE), .MUTFO(MUTFO)) u_txcal (.ck(ck[0]), .rst_n(rst_tc), .cfg_we(cfg_tx_we),
        .cfg_addr(cfg_addr_c[5:0]), .cfg_data_c(cfg_data_c[63:0]), .cfg_base_c(cfg_base_c[4:0]), .start_c(start_c[3:0]),
        .seg_c(seg_c[3:0]), .halt_c(halt_c[3:0]),
        .ev_v(tv), .ev_port(tp), .ev_kind(tk), .ev_beat(tb), .running(trun), .fault(tf));
    ot_qwen_d2d_cal_sf #(.NE(NE)) u_rxcal (.ck(ck[0]), .rst_n(rst_rc), .cfg_we(cfg_rx_we),
        .cfg_addr(cfg_addr_c[11:6]), .cfg_data_c(cfg_data_c[127:64]), .cfg_base_c(cfg_base_c[9:5]), .start_c(start_c[7:4]),
        .seg_c(seg_c[7:4]), .halt_c(halt_c[7:4]),
        .ev_v(rv), .ev_port(rp), .ev_kind(rk), .ev_beat(rb), .running(rrun), .fault(rf));
    assign cal_running = trun | rrun;
    reg [1:0] utx, urx, r1u;
    generate if (OVL != 0) begin : g_ovl_user
        always @(posedge ck[0] or negedge rst_cl)
            if (!rst_cl) begin utx <= 2'd0; urx <= 2'd0; end
            else begin if (cal_start) utx <= cal_user_tx; if (cal_start_rx) urx <= cal_user_rx; end
        assign tx_user = utx;
    end else begin : g_one_user
        always @* begin utx = 2'd0; urx = 2'd0; end
        assign tx_user = 2'd0;
    end endgenerate
    genvar p, g;
    for (p = 0; p < NT; p = p + 1) begin : g_slot
        assign tx_slot[p] = tv && tp == p;
    end
    assign tx_kind = tk;
    assign tx_beat = tb;
    // per-port fixed capture delay (as built) + NFC copies of its last stage, D = the master's last-stage D net
    localparam integer NFC = (FW + FGB - 1) / FGB;
    reg [NT-1:0] fire;
    wire [NT*NFC-1:0] fire_c;
    for (p = 0; p < NT; p = p + 1) begin : g_dly
        localparam integer D = TXD[8*p +: 8];
        reg [D-1:0] sr;
        wire last_d = (D > 1) ? sr[(D > 1) ? D-2 : 0] : (tx_slot[p] & ~halt);
        wire early_d = (D > 2) ? sr[(D > 2) ? D-3 : 0] : last_d;
        (* keep = "true", dont_touch = "true" *) reg [NFC-1:0] fc;
        always @(posedge ck[0] or negedge rst_cl)
            if (!rst_cl) sr <= {D{1'b0}};
            else sr <= {sr, tx_slot[p] & ~halt};
        for (g = 0; g < NFC; g = g + 1) begin : g_fc
            (* keep = "true", dont_touch = "true" *) always @(posedge ck[0] or negedge rst_cl)
                if (!rst_cl) fc[g] <= 1'b0;
                else fc[g] <= (MUTFO == 3 && p == 0 && g == 5) ? early_d : last_d;
        end
        always @* fire[p] = sr[D-1];
        assign fire_c[NFC*p +: NFC] = fc;
    end
    integer i, j, k;
    reg [FW-1:0] wsel;
    reg          wobs;
    wire         multi = |(fire & (fire - 1'b1));
    always @* begin
        wsel = {FW{1'b0}}; wobs = 1'b0;
        for (j = 0; j < NT; j = j + 1) begin
            for (k = 0; k < FW; k = k + 1)
                if (fire_c[NFC*j + k/FGB]) wsel[k] = wsel[k] | tx_payload[j*FW + k];
            if (fire[j]) wobs = wobs | tx_valid[j];
        end
    end
    wire wr_v = |fire;
    wire stray = |(tx_valid & ~fire);
    wire bad_port;
    if (NT < 4) begin : g_bad_port
        assign bad_port = tv && tp >= NT;
    end else begin : g_all_ports
        assign bad_port = 1'b0;
    end
    // write / read slot counters: master + 5 copies (4 store banks + link control) on ONE D net each
    reg [5:0] wcnt, rslot; reg rd_v;
    wire [5:0] wslot = (MUT == 1) ? wcnt + 6'd1 : wcnt;
    wire eb8 = (MUTFO == 4) ? 1'b0 : eb_c[8];
    wire [5:0] wcnt_d = eb8 ? 6'd0 : (wr_v ? wcnt + 6'd1 : wcnt);
    wire [5:0] rslot_d = eb8 ? rslot : wslot;
    (* keep = "true", dont_touch = "true" *) reg [29:0] wc_c;
    (* keep = "true", dont_touch = "true" *) reg [29:0] rs_c;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck[0] or negedge rst_cl)
        if (!rst_cl) begin wcnt <= 6'd0; rslot <= 6'd0; wc_c <= 30'd0; rs_c <= 30'd0; end
        else begin wcnt <= wcnt_d; rslot <= rslot_d; wc_c <= {5{wcnt_d}}; rs_c <= {5{rslot_d}}; end
    wire [29:0] ws_c;
    for (g = 0; g < 5; g = g + 1) begin : g_ws
        assign ws_c[6*g +: 6] = (MUT == 1) ? wc_c[6*g +: 6] + 6'd1 : wc_c[6*g +: 6];
    end
    // RX expectation and its 2-edge alignment with the slot link's checked output (as built; eb copies 8 / 9)
    reg [5:0] ecnt;
    reg       r1v, r2v; reg [2:0] r1p, r2p; reg [3:0] r1k; reg [4:0] r1b;
    always @(posedge ck[0] or negedge rst_cl) begin
        if (!rst_cl) begin
            rd_v <= 0; ecnt <= 0; end_fault <= 0; r1v <= 0; r2v <= 0; rx_slot <= 0;
        end else if (eb8) begin
            rd_v <= 0; ecnt <= 0; end_fault <= 0; r1v <= 0; r2v <= 0; rx_slot <= 0;
        end else begin
            rd_v <= wr_v & ~halt;
            if (rv) ecnt <= ecnt + 6'd1;
            if (stray | multi | tf | rf | bad_port) end_fault <= 1'b1;
            r1v <= rv; r2v <= r1v;
            for (i = 0; i < NR; i = i + 1) rx_slot[i] <= r1v && r1p == i;
        end
    end
    wire ef_d = eb8 ? 1'b0 : (end_fault | stray | multi | tf | rf | bad_port);
    (* keep = "true", dont_touch = "true" *) always @(posedge ck[0] or negedge rst_cl)
        if (!rst_cl) efc <= 9'd0; else efc <= {9{ef_d}};
    wire [2:0] r2p_n = (MUT == 2 && r1p < 2) ? r1p ^ 3'd1 : r1p;
    always @(posedge ck[0] or negedge rst_cl) begin
        if (!rst_cl) begin
            r1p <= 0; r2p <= 0; r1k <= 0; r1b <= 0; rx_kind <= 0; rx_beat <= 0; r1u <= 0; rx_user <= 0;
        end else if (!eb_c[9]) begin
            r1p <= rp; r1k <= rk; r1b <= rb; r1u <= urx; rx_user <= r1u;
            r2p <= r2p_n;
            rx_kind <= r1k; rx_beat <= r1b;
        end
    end
    // STATUS (port 2) capture copies: rx_event[2] = rx_v && r2p == 2, rx_slot[2]; same D nets, same resets
    wire lrx_v, lrx_v_nx;
    wire ev2_d = !eb_c[9] && lrx_v_nx && r2p_n == 3'd2;
    wire rs2_d = !eb8 && r1v && r1p == 3'd2;
    (* keep = "true", dont_touch = "true" *) reg [NG2-1:0] ev2_c;
    (* keep = "true", dont_touch = "true" *) reg [NG2-1:0] rs2_c;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck[0] or negedge rst_lk)
        if (!rst_lk) ev2_c <= {NG2{1'b0}}; else ev2_c <= {NG2{ev2_d}};
    (* keep = "true", dont_touch = "true" *) always @(posedge ck[0] or negedge rst_cl)
        if (!rst_cl) rs2_c <= {NG2{1'b0}}; else rs2_c <= {NG2{rs2_d}};
    assign st_ev_c = ev2_c;
    assign st_rs_c = rs2_c;
    always @* for (k = 0; k < NR; k = k + 1) rx_event[k] = lrx_v && r2p == k;
    ot_qwen_static_slot_link_sf #(.FW(FW), .CW(CW), .PW(PW), .MUTFO(MUTFO)) u_link (
        .ck(ck), .rst_n(rst_lk), .eb_c(eb_c[7:0]), .epoch(epoch),
        .wr_v(wr_v & ~halt), .wr_observed_v(wobs), .wr_slot_c(ws_c), .wr_flit(wsel),
        .rd_v(rd_v), .rd_slot_c(rs_c),
        .rx_expect_v(rv), .rx_expect_slot(ecnt),
        .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit),
        .rx_v(lrx_v), .rx_v_nx(lrx_v_nx), .rx_flit(rx_payload), .epoch_abort(epoch_abort), .ab_c(ab_x), .fault_cause(fault_cause));
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck[0]) begin
        if (fo_armed && (wc_c !== {5{wcnt}} || rs_c !== {5{rslot}} || ev2_c !== {NG2{rx_event[2]}} ||
                         rs2_c !== {NG2{rx_slot[2]}} || efc !== {9{end_fault}} || ab_x !== {9{epoch_abort}}))
            $display("FO_COPY_MISMATCH %m t=%0t", $time);
        for (j = 0; j < NT; j = j + 1)
            if (fo_armed && fire_c[NFC*j +: NFC] !== {NFC{fire[j]}}) $display("FO_COPY_MISMATCH %m fire%0d t=%0t", j, $time);
        fo_armed <= 1'b1;
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// STATUS / RESULT record consumer (function of ot_qwen_d2d_status_rx): the 156 captured bits are written in NG groups,
// group g enabled by its own (rx_event, rx_slot, fault) copies.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_status_rx_sf #(parameter integer NG = 10, parameter integer OBS1_COMPAT = 0) (
    input  wire         ck, rst_n,
    input  wire [15:0]  epoch16,
    input  wire         rx_event, rx_slot,
    input  wire [NG-1:0] ev_c, rs_c,
    input  wire [547:0] rx_payload,
    output wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    output reg          status_fresh,
    output reg          result_v,
    output wire         result_done, result_fault,
    output wire [3:0]   result_cause,
    output wire [58:0]  result_tag,
    output wire [1:0]   result_gen,
    output wire [17:0]  result_token,
    output wire [31:0]  result_value, result_cycles,
    input  wire         epoch_begin,
    output wire         fault
);
    wire [511:0] d = rx_payload[511:0];
    // Opt-in compatibility with the existing STATUS-v1 observer codec. Lower status/result fields and
    // capture edges are unchanged. Legacy zero extension remains legal; nonzero extensions use the
    // same validator as ot_qwen_d2d_status_rx_sfm3_obs1. No reserved bits become payload.
    wire bad_extension;
    generate if (OBS1_COMPAT) begin : g_obs1_compat
        wire extension_good;
        ot_qwen_status_obs_v1_valid u_ext_check(.x(d[511:304]), .good(extension_good));
        assign bad_extension = |d[303:156] || ((|d[511:304]) && !extension_good);
    end else begin : g_legacy
        assign bad_extension = |d[511:156];
    end endgenerate
    wire bad_hdr = rx_payload[547:543] != 0 || rx_payload[542:539] != 4'd15 || rx_payload[538:533] != 6'd63 ||
                   rx_payload[532:517] != epoch16 || rx_payload[516:512] != 0 || bad_extension;
    // sticky fault: master + NG copies on one D net
    (* keep = "true", dont_touch = "true" *) reg [NG:0] fc;      // fc[0] = master
    wire fault_d = (rx_event != rx_slot || (rx_event && bad_hdr)) ? 1'b1 : fc[0];
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_n)
        if (!rst_n) fc <= {(NG+1){1'b0}}; else fc <= {(NG+1){fault_d}};
    assign fault = fc[0];
    // captured image: cap[5:0] = d[5:0] (status levels), cap[155:7] = d[155:7] (result fields); bit 6 unused (result_v)
    reg [155:0] cap;
    localparam integer GB = (156 + NG - 1) / NG;
    genvar g;
    for (g = 0; g < NG; g = g + 1) begin : g_cap
        localparam integer LO = g * GB;
        localparam integer WG = (LO + GB <= 156) ? GB : 156 - LO;
        wire en = ev_c[g] && rs_c[g] && !bad_hdr && !fc[g+1];
        always @(posedge ck or negedge rst_n)
            if (!rst_n) cap[LO +: WG] <= {WG{1'b0}};
            else if (en) cap[LO +: WG] <= d[LO +: WG];
    end
    wire en0 = ev_c[0] && rs_c[0] && !bad_hdr && !fc[1];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin status_fresh <= 1'b0; result_v <= 1'b0; end
        else begin
            result_v <= en0 && d[6];
            if (en0) status_fresh <= 1'b1;
            else if (epoch_begin) status_fresh <= 1'b0;
        end
    assign {admit_ready, execution_active, crom_fault, collective_busy, collective_drained, vm_drained} = cap[5:0];
    assign {result_cycles, result_value, result_token, result_gen, result_tag, result_cause, result_fault, result_done} =
        cap[155:7];
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck) begin
        if (fo_armed && (fc !== {(NG+1){fc[0]}} || ev_c !== {NG{rx_event}} || rs_c !== {NG{rx_slot}}))
            $display("FO_COPY_MISMATCH %m t=%0t", $time);
        fo_armed <= 1'b1;
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Exceptional-mode recovery (function of ot_qwen_d2d_recovery, MASTER build): the state / counting next-state is written
// as nets so that KEPT copies share it; epoch_begin has NEB copies (same D: begin_now); the 32-b recovery_cycles
// counter is cleared / advanced in two 16-b halves, each by its own (state, counting, epoch_begin) copies.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_recovery_sf #(
    parameter integer MASTER = 1, DRAIN = 32, RSTC = 16, BUMP = 3, NEB = 12
) (
    input  wire       ck,
    input  wire       por_n,
    input  wire       rst_n,
    input  wire       abort,
    input  wire [7:0] fault_cause,
    input  wire       end_fault,
    input  wire       p_tx_up,
    input  wire       p_tx_v, p_rx_v,
    input  wire       reset_req,
    input  wire       recovery_clear,
    input  wire       boot_begin,
    input  wire       fwd_epoch_i,
    output wire       fwd_epoch_o,
    output wire       fwd_link_rst_n,
    output wire       phy_rst_n,
    output wire       epoch_begin,      // = KEPT eb_m (never merged into its copies ebc)
    output reg  [7:0] epoch,
    output reg        link_up,
    output wire       links_drained,
    output wire       link_reset_seen,
    output wire       retrained,
    output reg  [7:0] transport_fault,
    output wire       recovering,
    output wire [31:0] recovery_cycles,
    output wire [NEB-1:0] epoch_begin_c
);
    localparam [2:0] S_RUN = 0, S_DRAIN = 1, S_DRAINED = 2, S_RST = 3, S_TRAIN = 4, S_READY = 5;
    reg [2:0] st; reg [15:0] n; reg seen, lrst, fep, bq;
    reg [BUMP-1:0] eq;
    reg [BUMP-1:0] fq;
    reg counting;
    (* keep = "true", dont_touch = "true" *) reg eb_m;
    assign epoch_begin = eb_m;
    assign fwd_epoch_o = fep;
    assign fwd_link_rst_n = ~lrst;
    assign phy_rst_n = rst_n & ~lrst;
    assign links_drained = (st == S_DRAINED) || (st == S_RST) || (st == S_TRAIN) || (st == S_READY);
    assign link_reset_seen = seen;
    assign retrained = (st == S_READY);
    assign recovering = (st != S_RUN);
    wire begin_now = MASTER ? eq[BUMP-1] : fq[BUMP-1];
    always @(posedge ck or negedge por_n)
        if (!por_n) begin epoch <= 8'd0; end
        else if (epoch_begin) epoch <= epoch + 8'd1;
    (* keep = "true", dont_touch = "true" *) reg [5:0] stc;      // 2 copies of st (same D net st_d)
    (* keep = "true", dont_touch = "true" *) reg [1:0] cntc;     // 2 copies of counting
    (* keep = "true", dont_touch = "true" *) reg [NEB+2:0] ebc;  // NEB external + 3 internal copies of epoch_begin
    // ---- next state of st / counting (the as-built priority: begin_now first, the state case last) ----
    reg [2:0] st_d; reg cnt_d;
    always @* begin
        st_d = st; cnt_d = counting;
        if (begin_now) begin st_d = S_RUN; cnt_d = 1'b0; end
        case (st)
        S_RUN:     if (abort && !ebc[NEB+2]) begin st_d = MASTER ? S_DRAIN : S_READY; cnt_d = 1'b1; end
        S_DRAIN:   if (!(p_tx_v || p_rx_v) && n == DRAIN - 1) st_d = S_DRAINED;
        S_DRAINED: if (reset_req) st_d = S_RST;
        S_RST:     if (n == RSTC - 1) st_d = S_TRAIN;
        S_TRAIN:   if (seen && p_tx_up) st_d = S_READY;
        S_READY:   ;
        default:   st_d = S_RUN;
        endcase
    end
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_n)
        if (!rst_n) begin st <= S_RUN; counting <= 1'b0; stc <= {2{S_RUN}}; cntc <= 2'd0; ebc <= {(NEB+3){1'b0}}; end
        else begin st <= st_d; counting <= cnt_d; stc <= {2{st_d}}; cntc <= {2{cnt_d}}; ebc <= {(NEB+3){begin_now}}; end
    assign epoch_begin_c = ebc[NEB-1:0];
    // ---- recovery_cycles: as built rc <= (S_RUN && abort && !epoch_begin) ? 0 : counting ? rc + 1 : rc; two halves ----
    reg [15:0] rc_lo, rc_hi;
    wire clr_lo = stc[2:0] == S_RUN && abort && !ebc[NEB];
    wire clr_hi = stc[5:3] == S_RUN && abort && !ebc[NEB+1];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) rc_lo <= 16'd0;
        else if (clr_lo) rc_lo <= 16'd0;
        else if (cntc[0]) rc_lo <= rc_lo + 16'd1;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) rc_hi <= 16'd0;
        else if (clr_hi) rc_hi <= 16'd0;
        else if (cntc[1] && rc_lo == 16'hffff) rc_hi <= rc_hi + 16'd1;
    assign recovery_cycles = {rc_hi, rc_lo};
    // ---- everything else as built ----
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; seen <= 0; lrst <= 0; fep <= 0; eq <= 0; fq <= 0; eb_m <= 0; bq <= 0; link_up <= 0;
            transport_fault <= 0;
        end else begin
            fep <= 1'b0; eb_m <= begin_now; bq <= boot_begin;
            link_up <= p_tx_up && (st == S_RUN) && !abort;
            eq <= {eq, fep}; fq <= {fq, fwd_epoch_i};
            if (begin_now) begin seen <= 0; transport_fault <= 0; end
            case (st)
            S_RUN: begin
                if (MASTER && boot_begin && !bq) fep <= 1'b1;
                if (abort && !ebc[NEB+2]) begin
                    n <= 0; transport_fault <= fault_cause | {end_fault, 7'd0};
                end
            end
            S_DRAIN: if (p_tx_v || p_rx_v) n <= 0; else if (n == DRAIN - 1) ; else n <= n + 1;
            S_DRAINED: if (reset_req) begin n <= 0; lrst <= 1; end
            S_RST: begin
                if (!p_tx_up) seen <= 1;
                if (n == RSTC - 1) lrst <= 0; else n <= n + 1;
            end
            S_TRAIN: ;
            S_READY: if (MASTER && recovery_clear) fep <= 1'b1;
            default: ;
            endcase
        end
    end
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck) begin
        if (fo_armed && (stc !== {2{st}} || cntc !== {2{counting}} || ebc !== {(NEB+3){epoch_begin}}))
            $display("FO_COPY_MISMATCH %m t=%0t", $time);
        fo_armed <= 1'b1;
    end
`endif
endmodule
