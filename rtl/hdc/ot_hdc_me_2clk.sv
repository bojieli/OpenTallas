`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_me_2clk: the matrix engine (ot_hdc_matvec) of the Qwen3-8B ROM decode
// core, optionally moved into the 1.2 GHz streaming domain (AGENTS.md clock
// domains: the ROM field runs at 1.2 GHz, the serial-chain units -- the stream
// unit, SFU and reducers -- and the sequencer/vector memory at 0.9 GHz, 3:4 off
// one PLL).  Port-for-port a drop-in for ot_hdc_matvec plus `fclk` and one
// fast-domain weight port (f_wrom_*).
//
// ME_CDC = 0 (default): a plain ot_hdc_matvec on `clk`; f_wrom_* are tied off.
// Nothing about the pinned core changes.
//
// ME_CDC = 1: the engine runs on `fclk`.  Every slow<->fast transfer goes
// through ot_ratio_cdc_fifo (rtl/common), the related-clock crossing whose
// cross-domain arcs are all flop -> flop:
//   * command FIFO (slow -> fast): the descriptor the sequencer issues with
//     go; `ready` is the FIFO's write-ready, so the sequencer may run up to
//     CDC_DEPTH ops ahead of the engine (its hazards still resolve through
//     idle/progress below, which only ever report LATER than the engine);
//   * result FIFO (fast -> slow): one entry per engine cycle that carries a
//     result write (ov, o_*, mx_*) or changes the engine's reported state
//     (argmax, per-op progress, started/completed op counters, fault).  The
//     slow side pops every entry the cycle it is visible, so the vector-memory
//     writes keep the engine's order and contents exactly;
//   * a full result FIFO stops the engine clock (ot_hdc_cg) for that cycle --
//     the ME_STALL mechanism: an exact pause.  Every engine read enable is ANDed
//     with the clock enable, so a read-response register loads only on edges
//     that clock the engine (the ME_STALL supply contract).
// Slow-side status: idle = every issued op's completion marker has been popped
// (the engine is idle and all its writes are in the vector memory); progress =
// the latest op's progress as carried with its writes; am_* = the engine's
// argmax as of the last popped entry.  Values never change -- only when they
// arrive (tools/two_clock_crossing_model.py, results/rtl/two_clock_crossing_20261003).
//
// Memory domains with ME_CDC = 1: the weight ROM (f_wrom_*, or the INT8 code
// port), the scale ROM, the KV read port and the x read port of the vector
// memory are served on fclk.  The KV and vector memories are therefore 1R1W
// with a fast read clock and a slow write clock; the program orders every
// write before the dependent read through the crossings above, and the
// integration bench counts reads that land within two slow cycles of a write
// to the same word (must be 0).
// ---------------------------------------------------------------------------
module ot_hdc_me_2clk #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_WEIGHT = 0,
    parameter integer INT8_SCALE_WCS_BASE = 0,
    parameter integer SMIN = 0,
    parameter integer ORD = 0,
    parameter integer ME_CDC = 0,        // 1: engine on fclk behind ratio-FIFO crossings
    parameter integer CDC_DEPTH = 4,
    parameter integer TAGW = 8
) (
    input  wire              fclk,
    output wire              f_wrom_re,
    output wire [AW-1:0]     f_wrom_addr,
    input  wire [G*W*16-1:0] f_wrom_q,
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_amax,
    input  wire              i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [G*W*((INT8_WEIGHT != 0) ? 8 : 16)-1:0] wrom_q,
    output wire              scale_re,
    output wire [G-1:0]      scale_gre,
    output wire [G*AW-1:0]   scale_addr,
    input  wire [G*W*16-1:0] scale_q,
    output wire              kv_re,
    output wire [G*AW-1:0]   kv_addr,
    input  wire [G*W*32-1:0] kv_q,
    output wire [G-1:0]      x_re,
    output wire [G*AW-1:0]   x_addr,
    input  wire [G*32-1:0]   x_q,
    output wire              ov,
    output wire [G-1:0]      o_we,
    output wire [G*AW-1:0]   o_addr,
    output wire [G*W-1:0]    o_mask,
    output wire [G*W*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output wire [15:0]       progress,
    output wire              fault
);
    localparam integer WQ = G * W * ((INT8_WEIGHT != 0) ? 8 : 16);
    generate if (ME_CDC == 0) begin : g_direct
        ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(INT8_WEIGHT),
                        .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .SMIN(SMIN), .ORD(ORD)) u_me (
            .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
            .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), .i_wbase(i_wbase),
            .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js), .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs),
            .i_xcs(i_xcs), .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
            .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
            .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
            .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
            .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
            .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr), .scale_q(scale_q),
            .kv_re(kv_re), .kv_addr(kv_addr), .kv_q(kv_q),
            .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
            .ov(ov), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data),
            .am_idx(am_idx), .am_val(am_val), .am_any(am_any), .progress(progress), .fault(fault));
        assign f_wrom_re = 1'b0;
        assign f_wrom_addr = {AW{1'b0}};
    end else begin : g_cdc
        // ---------------- fast-domain reset ----------------
        // rst_n is synchronous to clk (the core's reset); the clocks are related, so one fclk flop captures it
        // with STA-timed setup/hold (no synchroniser chain is needed or used).
        reg frst_q;
        always @(posedge fclk) frst_q <= rst_n;
        wire frst_n = frst_q;

        // ---------------- command crossing (slow -> fast) ----------------
        localparam integer CMDW = 3*NW + 1 + 8*AW + 3 + 4 + AW + 1 + 3*AW + 4 + AW;   // nout,tiles,k | wsrc | wbase,ts,ks,js,xbase,xks,xjs,xcs | jsh | split | wcs | round | obase,ots,ojs | mmode,oen,amax,rmax | mbase
        wire [CMDW-1:0] cmd_w = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs,
                                 i_xcs, i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs,
                                 i_mmode, i_oen, i_amax, i_rmax, i_mbase};
        wire [CMDW-1:0] cmd_r;
        wire cmd_wrdy, cmd_v, cmd_pop;
        ot_ratio_cdc_fifo #(.W(CMDW), .DEPTH(CDC_DEPTH)) u_cmd (
            .wclk(clk), .wrst_n(rst_n), .w_v(go), .w_rdy(cmd_wrdy), .w_d(cmd_w),
            .rclk(fclk), .rrst_n(frst_n), .r_v(cmd_v), .r_rdy(cmd_pop), .r_d(cmd_r), .w_live(), .r_live());
        wire [NW-1:0] f_nout, f_tiles, f_k;
        wire f_wsrc, f_round, f_mmode, f_oen, f_amax, f_rmax;
        wire [AW-1:0] f_wbase, f_ts, f_ks, f_js, f_xbase, f_xks, f_xjs, f_xcs, f_wcs, f_obase, f_ots, f_ojs, f_mbase;
        wire [2:0] f_jsh;
        wire [3:0] f_split;
        assign {f_nout, f_tiles, f_k, f_wsrc, f_wbase, f_ts, f_ks, f_js, f_xbase, f_xks, f_xjs,
                f_xcs, f_jsh, f_split, f_wcs, f_round, f_obase, f_ots, f_ojs,
                f_mmode, f_oen, f_amax, f_rmax, f_mbase} = cmd_r;

        // ---------------- the engine on the gated fast clock ----------------
        wire en, gclk;
        ot_hdc_cg u_me_cg (.clk(fclk), .en(en), .gclk(gclk));
        wire me_ready, me_idle, me_ov, me_mx_we, me_am_any, me_fault, me_wrom_re;
        wire [G-1:0] me_o_we;
        wire [G*AW-1:0] me_o_addr;
        wire [G*W-1:0] me_o_mask;
        wire [G*W*32-1:0] me_o_data;
        wire [AW-1:0] me_mx_addr, me_wrom_addr;
        wire [W-1:0] me_mx_mask;
        wire [W*32-1:0] me_mx_data;
        wire [NW-1:0] me_am_idx;
        wire [31:0] me_am_val;
        wire [15:0] me_progress;
        wire [WQ-1:0] me_wrom_q;
        wire me_scale_re, me_kv_re;
        wire [G-1:0] me_scale_gre, me_x_re;
        //: ME_STALL contract: a read-response register may load only on the edges that clock the engine, so the
        //: engine finds, after a held edge, the word it requested before it.  Every engine read enable is ANDed with
        //: the engine clock enable (a ROM/SRAM macro holds Q while its read enable is low), which costs no state.
        assign scale_re = me_scale_re && en;
        assign scale_gre = me_scale_gre & {G{en}};
        assign kv_re = me_kv_re && en;
        assign x_re = me_x_re & {G{en}};
        ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(INT8_WEIGHT),
                        .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .SMIN(SMIN), .ORD(ORD)) u_me (
            .clk(gclk), .rst_n(frst_n), .go(cmd_v), .ready(me_ready), .idle(me_idle),
            .i_nout(f_nout), .i_tiles(f_tiles), .i_k(f_k), .i_wsrc(f_wsrc), .i_wbase(f_wbase),
            .i_ts(f_ts), .i_ks(f_ks), .i_js(f_js), .i_xbase(f_xbase), .i_xks(f_xks), .i_xjs(f_xjs),
            .i_xcs(f_xcs), .i_jsh(f_jsh), .i_split(f_split), .i_wcs(f_wcs), .i_round(f_round),
            .i_obase(f_obase), .i_ots(f_ots), .i_ojs(f_ojs),
            .i_mmode(f_mmode), .i_oen(f_oen), .i_amax(f_amax), .i_rmax(f_rmax), .i_mbase(f_mbase),
            .mx_we(me_mx_we), .mx_addr(me_mx_addr), .mx_mask(me_mx_mask), .mx_data(me_mx_data),
            .wrom_re(me_wrom_re), .wrom_addr(me_wrom_addr), .wrom_q(me_wrom_q),
            .scale_re(me_scale_re), .scale_gre(me_scale_gre), .scale_addr(scale_addr), .scale_q(scale_q),
            .kv_re(me_kv_re), .kv_addr(kv_addr), .kv_q(kv_q),
            .x_re(me_x_re), .x_addr(x_addr), .x_q(x_q),
            .ov(me_ov), .o_we(me_o_we), .o_addr(me_o_addr), .o_mask(me_o_mask), .o_data(me_o_data),
            .am_idx(me_am_idx), .am_val(me_am_val), .am_any(me_am_any), .progress(me_progress), .fault(me_fault));
        if (INT8_WEIGHT != 0) begin : g_wq_int8          // the INT8 code port is the engine's own (fast) port
            assign wrom_re = me_wrom_re && en; assign wrom_addr = me_wrom_addr; assign me_wrom_q = wrom_q;
            assign f_wrom_re = 1'b0; assign f_wrom_addr = {AW{1'b0}};
        end else begin : g_wq_bf16                        // the shared BF16 port stays the stream unit's (slow)
            assign f_wrom_re = me_wrom_re && en; assign f_wrom_addr = me_wrom_addr; assign me_wrom_q = f_wrom_q[WQ-1:0];
            assign wrom_re = 1'b0; assign wrom_addr = {AW{1'b0}};
        end

        // ---------------- fast-side bookkeeping and result entries ----------------
        reg [TAGW-1:0] f_go, f_done;                      // ops started / ops known complete (engine idle)
        reg [TAGW-1:0] l_tag, l_done;
        reg [15:0] l_prog;
        reg [NW-1:0] l_am_idx;
        reg [31:0] l_am_val;
        reg l_am_any, l_fault;
        wire chg = (f_go != l_tag) || (f_done != l_done) || (me_progress != l_prog) || (me_am_idx != l_am_idx) ||
                   (me_am_val != l_am_val) || (me_am_any != l_am_any) || (me_fault != l_fault);
        wire pend = me_ov || (|me_o_we) || me_mx_we || chg;
        localparam integer RESW = 1 + G + G*AW + G*W + G*W*32 + 1 + AW + W + W*32 + NW + 32 + 1 + 16 + TAGW + TAGW + 1;
        wire [RESW-1:0] res_w = {me_ov, me_o_we, me_o_addr, me_o_mask, me_o_data, me_mx_we, me_mx_addr, me_mx_mask,
                                 me_mx_data, me_am_idx, me_am_val, me_am_any, me_progress, f_go, f_done, me_fault};
        wire res_wrdy, res_v;
        wire [RESW-1:0] res_r;
        //: the engine advances on an fclk edge unless an entry is pending and the result FIFO is full; reset edges
        //: always pass (ot_hdc_cg: every user ORs !rst_n into en)
        assign en = !frst_n || !pend || res_wrdy;
        wire push = frst_n && pend && res_wrdy;
        assign cmd_pop = frst_n && cmd_v && me_ready && en;
        always @(posedge fclk) begin
            if (!frst_n) begin
                f_go <= 0; f_done <= 0; l_tag <= 0; l_done <= 0; l_prog <= 0;
                l_am_idx <= 0; l_am_val <= 0; l_am_any <= 1'b0; l_fault <= 1'b0;
            end else begin
                if (en) begin
                    if (cmd_pop) f_go <= f_go + 1'b1;
                    if (me_idle) f_done <= f_go;           // registered idle: every op started before is done
                end
                if (push) begin
                    l_tag <= f_go; l_done <= f_done; l_prog <= me_progress;
                    l_am_idx <= me_am_idx; l_am_val <= me_am_val; l_am_any <= me_am_any; l_fault <= me_fault;
                end
            end
        end
        ot_ratio_cdc_fifo #(.W(RESW), .DEPTH(CDC_DEPTH)) u_res (
            .wclk(fclk), .wrst_n(frst_n), .w_v(pend && frst_n), .w_rdy(res_wrdy), .w_d(res_w),
            .rclk(clk), .rrst_n(rst_n), .r_v(res_v), .r_rdy(1'b1), .r_d(res_r), .w_live(), .r_live());

        // ---------------- slow side ----------------
        wire r_ov, r_mx_we, r_am_any, r_fault;
        wire [G-1:0] r_we;
        wire [G*AW-1:0] r_addr;
        wire [G*W-1:0] r_mask;
        wire [G*W*32-1:0] r_data;
        wire [AW-1:0] r_mx_addr;
        wire [W-1:0] r_mx_mask;
        wire [W*32-1:0] r_mx_data;
        wire [NW-1:0] r_am_idx;
        wire [31:0] r_am_val;
        wire [15:0] r_prog;
        wire [TAGW-1:0] r_tag, r_done;
        assign {r_ov, r_we, r_addr, r_mask, r_data, r_mx_we, r_mx_addr, r_mx_mask, r_mx_data,
                r_am_idx, r_am_val, r_am_any, r_prog, r_tag, r_done, r_fault} = res_r;
        reg [TAGW-1:0] s_go, s_done;
        reg [15:0] s_prog;
        reg s_idle, s_am_any, s_fault;
        reg [NW-1:0] s_am_idx;
        reg [31:0] s_am_val;
        wire go_acc = go && cmd_wrdy;
        wire [TAGW-1:0] s_go_n = s_go + (go_acc ? 1'b1 : 1'b0);
        wire [TAGW-1:0] s_done_n = res_v ? r_done : s_done;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                s_go <= 0; s_done <= 0; s_prog <= 0; s_idle <= 1'b1;
                s_am_any <= 1'b0; s_am_idx <= 0; s_am_val <= 0; s_fault <= 1'b0;
            end else begin
                s_go <= s_go_n; s_done <= s_done_n;
                s_idle <= (s_go_n == s_done_n);
                if (go_acc) s_prog <= 16'd0;
                else if (res_v && r_tag == s_go) s_prog <= r_prog;
                if (res_v) begin s_am_any <= r_am_any; s_am_idx <= r_am_idx; s_am_val <= r_am_val; end
                if (res_v && r_fault) s_fault <= 1'b1;
            end
        end
        assign ready = cmd_wrdy;
        assign idle = s_idle;
        assign progress = s_prog;
        assign am_idx = s_am_idx;
        assign am_val = s_am_val;
        assign am_any = s_am_any;
        assign fault = s_fault;
        assign ov = res_v && r_ov;
        assign o_we = res_v ? r_we : {G{1'b0}};
        assign o_addr = r_addr;
        assign o_mask = r_mask;
        assign o_data = r_data;
        assign mx_we = res_v && r_mx_we;
        assign mx_addr = r_mx_addr;
        assign mx_mask = r_mx_mask;
        assign mx_data = r_mx_data;
    end endgenerate
endmodule
