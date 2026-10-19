`timescale 1ns/1ps
// KV-DCAL-OVL-CODEX: independent TX/RX static list players plus registered boot/runtime config producer.
// Derived from bootcfg 7167b4ab7 and OVL 95d11133f. Images/list ROMs must come from one codec2 seam compile.
// ROM addresses are already player registers at the face; ROM q inputs are captured once (two-edge round trip).
// EP_SKEW-2 compensates the control input/output registers; no runtime schedule edge is added.
// Lists are external hard ROMs, never runtime-indexed flop arrays. Reset release uses two registered stages.
module qkd_d2d_cal_seq_ovl_bc_core #(parameter integer AW = 11, parameter integer FIRST_OFS = 1176,
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
    `include "ovl_release/ovl_release_img.svh"
    initial if (EP_SKEW < 2) $error("EP_SKEW >= 2 needed (input capture + output stage)");
    // ---- input capture (as qkd_d2d_cal_seq_pin) + the boot cfg pin registers
    reg [1:0] release_q;
    reg reload_q, epoch_go_q, halt_q;
    reg b_tx_q, b_rx_q;
    reg [5:0] b_addr_q;
    reg [31:0] b_data_q;
    reg [31:0] tx_q, rx_q;
    always @(posedge ck) begin tx_q <= tx_rom_q; rx_q <= rx_rom_q; end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            release_q <= 0; reload_q <= 0; epoch_go_q <= 0; halt_q <= 1;
            b_tx_q <= 0; b_rx_q <= 0; b_addr_q <= 0; b_data_q <= 0;
        end else begin
            release_q <= {release_q[0], 1'b1};
            reload_q <= reload; epoch_go_q <= epoch_go; halt_q <= halt;
            b_tx_q <= bcfg_tx_we; b_rx_q <= bcfg_rx_we; b_addr_q <= bcfg_addr; b_data_q <= bcfg_data;
        end
    end
    wire rl = release_q[1];
    wire s_tx, s_rx, s_cs, s_seg, s_rdy, s_run, s_adm, s_fault, s_crs, s_crg;
    wire [5:0] s_addr;
    wire [1:0] s_ut, s_ur;
    wire [31:0] s_data;
    ot_qwen_d2d_ovl_seq #(.AW(AW), .MUT_HALT_REWIND(MUT_HALT_REWIND), .TX_IMG(OVL_K_TX_IMG), .RX_IMG(OVL_K_RX_IMG),
        .TX_SEG1(OVL_K_TX_SEG1), .RX_SEG1(OVL_K_RX_SEG1), .TX_SEG2(32'd16), .RX_SEG2(32'd16),
        .ADM(1), .ADM_OFS(ADM_OFS), .ADM_LEN(ADM_LEN), .FIRST_OFS(FIRST_OFS), .EP_SKEW(EP_SKEW - 2)) u_seq (
        .ck(ck), .rst_n(rl), .reload(reload_q), .epoch_go(epoch_go_q), .halt(halt_q),
        .cfg_tx_we(s_tx), .cfg_rx_we(s_rx), .cfg_addr(s_addr), .cfg_data(s_data),
        .cal_start(s_cs), .cal_seg(s_seg), .cal_ready(s_rdy), .running(s_run),
        .cal_start_rx(s_crs), .cal_seg_rx(s_crg), .cal_user_tx(s_ut), .cal_user_rx(s_ur),
        .tx_rom_addr(tx_rom_addr), .tx_rom_q(tx_q), .rx_rom_addr(rx_rom_addr), .rx_rom_q(rx_q),
        .adm_done(s_adm), .fault(s_fault));
    // ---- merge: the sequencer's own writes only after its init stream.  The init's last write and cal_ready rise on the
    // same edge, so "after init" = cal_ready now AND one edge ago (a reload drops cal_ready with its first init write).
    reg rdy_q, adm_act, btx_seen, brx_seen;
    reg f_col, f_run, f_stale, f_early;      // fault cause (bench observability; `fault` is their OR with the sequencer's)
    wire s_we = (MUT == 1) ? 1'b0 : ((s_tx || s_rx) && s_rdy && rdy_q);
    wire b_we = b_tx_q || b_rx_q;
    wire b_base = b_we && (b_addr_q == 6'b100000);
    wire n_col = b_we && s_we;
    wire n_run = b_we && (s_run || adm_act);
    wire n_stale = b_base && (b_tx_q ? (b_data_q != 32'd16) : (b_data_q != 32'd16));
    wire n_early = (s_cs || s_crs) && !(btx_seen && brx_seen);
    always @(posedge ck or negedge rl) begin
        if (!rl) begin
            cfg_tx_we <= 0; cfg_rx_we <= 0; cfg_addr <= 0; cfg_data <= 0;
            cal_start <= 0; cal_seg <= 0; cal_ready <= 0; running <= 0; adm_done <= 0; cal_start_rx <= 0; cal_seg_rx <= 0; cal_user_tx <= 0; cal_user_rx <= 0;
            rdy_q <= 0; adm_act <= 0; btx_seen <= 0; brx_seen <= 0;
            f_col <= 0; f_run <= 0; f_stale <= 0; f_early <= 0; fault <= 0;
        end else begin
            cal_start <= s_cs; cal_seg <= s_seg; cal_ready <= s_rdy; running <= s_run;
            cal_start_rx <= s_crs; cal_seg_rx <= s_crg; cal_user_tx <= s_ut; cal_user_rx <= s_ur;
            adm_done <= s_adm;
            rdy_q <= s_rdy;
            if (b_we) begin
                cfg_tx_we <= b_tx_q; cfg_rx_we <= b_rx_q; cfg_addr <= b_addr_q; cfg_data <= b_data_q;
            end else begin
                cfg_tx_we <= s_we && s_tx; cfg_rx_we <= s_we && s_rx;
                if (s_we) begin cfg_addr <= s_addr; cfg_data <= s_data; end
            end
            // admission run: from its start (layer 63) until adm_done; the token programme is the sequencer's `running`
            if (s_cs && s_seg && !s_adm) adm_act <= 1'b1;
            else if (s_adm || halt_q) adm_act <= 1'b0;
            if (reload_q) begin btx_seen <= 1'b0; brx_seen <= 1'b0; end
            else begin
                if (b_base && b_tx_q) btx_seen <= 1'b1;
                if (b_base && b_rx_q) brx_seen <= 1'b1;
            end
            if (n_col) f_col <= 1'b1;
            if (n_run) f_run <= 1'b1;
            if (n_stale) f_stale <= 1'b1;
            if (n_early) f_early <= 1'b1;
            fault <= fault || s_fault || n_col || n_run || n_stale || n_early;
        end
    end
endmodule

// Hardened top owns both list ROM macros.  No extra address stage: player's register drives ROM addr.
module qkd_d2d_cal_seq_pin_ovl_bc #(parameter ROM_DIR = "", parameter integer AW=11, parameter integer MUT=0, parameter integer MUT_HALT_REWIND=0) (
    input wire ck, rst_n, reload, epoch_go, halt,
    input wire bcfg_tx_we, bcfg_rx_we,
    input wire [5:0] bcfg_addr, input wire [31:0] bcfg_data,
    output wire cfg_tx_we, cfg_rx_we, output wire [5:0] cfg_addr, output wire [31:0] cfg_data,
    output wire cal_start, cal_seg, cal_start_rx, cal_seg_rx,
    output wire [1:0] cal_user_tx, cal_user_rx,
    output wire cal_ready, adm_done, running, fault
);
    initial if (AW < 1 || AW > 12) $error("physical list ROM supports AW1..12");
    wire [AW-1:0] ta, ra;
    wire [71:0] tq, rq;
`ifdef SYNTHESIS
    ot_rom_4096x72_m8 u_tx_rom (.clk(ck),.ce_in(1'b1),.addr_in({{(12-AW){1'b0}},ta}),.rd_out(tq));
    ot_rom_4096x72_m8 u_rx_rom (.clk(ck),.ce_in(1'b1),.addr_in({{(12-AW){1'b0}},ra}),.rd_out(rq));
`else
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_tx.viamap.hex"}),.INSTANCE("ovl_k_tx")) u_tx_rom
        (.clk(ck),.ce_in(1'b1),.addr_in({{(12-AW){1'b0}},ta}),.rd_out(tq));
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_k_rx.viamap.hex"}),.INSTANCE("ovl_k_rx")) u_rx_rom
        (.clk(ck),.ce_in(1'b1),.addr_in({{(12-AW){1'b0}},ra}),.rd_out(rq));
`endif
    qkd_d2d_cal_seq_ovl_bc_core #(.AW(AW),.MUT(MUT),.MUT_HALT_REWIND(MUT_HALT_REWIND)) u_core (
        .ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
        .bcfg_tx_we(bcfg_tx_we),.bcfg_rx_we(bcfg_rx_we),.bcfg_addr(bcfg_addr),.bcfg_data(bcfg_data),
        .cfg_tx_we(cfg_tx_we),.cfg_rx_we(cfg_rx_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .cal_start(cal_start),.cal_seg(cal_seg),.cal_start_rx(cal_start_rx),.cal_seg_rx(cal_seg_rx),
        .cal_user_tx(cal_user_tx),.cal_user_rx(cal_user_rx),.cal_ready(cal_ready),.adm_done(adm_done),
        .running(running),.fault(fault),.tx_rom_addr(ta),.tx_rom_q(tq[31:0]),.rx_rom_addr(ra),.rx_rom_q(rq[31:0]));
endmodule
