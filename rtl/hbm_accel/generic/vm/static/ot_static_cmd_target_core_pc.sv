`timescale 1ns/1ps
`default_nettype none
// H-SM 1815 2026-10-16: ot_static_cmd_target_core with the host-face pin flops (cfg/desc/launch/tgt) on their own
// clock entry clk_pin.  Copy of ot_static_cmd_target_core (rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv,
// 236 kits consume that file, so it is not edited); the ONLY difference is the clock of the pin-flop block.  Same
// edges, same latencies: with clk_pin == clk it is cycle-identical.  Why (writer faces4 c8e94d78d native capture
// 213.2 > 190): on the 9.8k-sink core root the N-face pin-flop row is 66 ps late at its NE end (98 ps leaf), so FF
// hold repair put 6 BUFx2 on 164 inputs; a short face root (as the W/E data faces: R ~122, spread 12) removes that.
module ot_static_cmd_target_core_pc #(
    parameter [7:0]  TARGET = 8'd64,
    parameter integer MODE  = 0,     // 0 RUN, 1 SEQ
    parameter integer AWA   = 0,     // window A address width (0: absent)
    parameter integer AWB   = 0,     // window B address width (0: absent)
    parameter integer RBW   = 1,     // MODE 0 run_base width
    parameter integer RCW   = 1,     // MODE 0 run_count width
    parameter integer CW    = 1,     // MODE 1 payload width
    parameter integer RELF  = 0,     // MODE 1 launch-relative 32-bit payload fields (low end)
    parameter integer NA    = 1,
    parameter integer NF    = 1,
    parameter integer LEAD  = 8,
    parameter integer MUT   = 0,     // 1: fire one cycle late; 2: ignore the target id
    parameter integer TGT_PIN = 0    // 1: target id from the identity strap pin tgt (one master for all ids, H-NETLIST 0600)
)(
    input  wire clk, rst_n,
    input  wire clk_pin,             // host-face pin-flop clock entry (same PLL, fixed phase; own CTS root)
    input  wire [7:0] tgt,           // identity strap (die constant), used only when TGT_PIN = 1
    input  wire cfg_v,
    input  wire [7:0] cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire desc_v,
    input  wire [11:0] desc_base,
    input  wire [12:0] desc_limit,
    input  wire [15:0] desc_loops,
    input  wire launch_v,
    input  wire [NA-1:0] tgt_active,
    input  wire [NF-1:0] tgt_fault,
    output reg  a_we,
    output reg  [(AWA>0?AWA:1)-1:0] a_addr,
    output reg  [255:0] a_data,
    output reg  b_we,
    output reg  [(AWB>0?AWB:1)-1:0] b_addr,
    output reg  [255:0] b_data,
    output reg  run_v,
    output reg  [RBW-1:0] run_base,
    output reg  [RCW-1:0] run_count,
    output reg  cmd_v,
    output reg  [CW-1:0] cmd,
    output reg  [31:0] cycle,
    output reg  configured, fault, active,
    // command-table SRAM interface (H-HARDEN 2026-10-16): the table macros live OUTSIDE the core so a physical parent
    // can clock them from their own related entry; ot_static_cmd_target below binds them exactly as before the split.
    output wire tab_r_ce,
    output wire [6:0] tab_r_addr,
    input  wire [((MODE == 1) ? ((32 + CW + 255) / 256) : 1)*256-1:0] tab_rd_word,
    output wire [((MODE == 1) ? ((32 + CW + 255) / 256) : 1)-1:0] tab_w_ce,
    output wire [6:0] tab_w_addr,
    output wire [255:0] tab_w_data
);
    localparam integer EW = 32 + CW;
    localparam integer NW = (EW + 255) / 256;
    localparam integer DEPTH = 128;
    initial begin
        if (MODE != 0 && MODE != 1) $fatal(1, "ot_static_cmd_target: MODE 0|1");
        if (AWA > 10 || AWB > 10) $fatal(1, "ot_static_cmd_target: window width <= 10");
        if (MODE == 1 && NW > 4) $fatal(1, "ot_static_cmd_target: entry <= 4 rows");
        if (RELF * 32 > CW) $fatal(1, "ot_static_cmd_target: RELF fields exceed the payload");
        if (RBW > 12 || RCW > 13) $fatal(1, "ot_static_cmd_target: run widths");
    end
    // ---------------- pin flops ----------------
    reg cv, dv, lv;
    reg [NA-1:0] act_q;
    reg [NF-1:0] flt_q;
    reg [7:0] target_q;
    reg [11:0] addr_q, base_q;
    reg [12:0] limit_q;
    reg [15:0] loops_q;
    reg [255:0] data_q;
    // host-face pin flops on clk_pin (the face's own clock entry); internal state stays on clk
    always @(posedge clk_pin) begin
        target_q <= cfg_target; addr_q <= cfg_addr; data_q <= cfg_data;
        base_q <= desc_base; limit_q <= desc_limit; loops_q <= desc_loops;
    end
    always @(posedge clk_pin or negedge rst_n)
        if (!rst_n) begin cv <= 0; dv <= 0; lv <= 0; end
        else begin cv <= cfg_v; dv <= desc_v; lv <= launch_v; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin act_q <= 0; flt_q <= 0; end
        else begin act_q <= tgt_active; flt_q <= tgt_fault; end
    reg [7:0] tgt_q; always @(posedge clk_pin) tgt_q <= tgt;   // static strap captured at the pin
    wire [7:0] tid = (TGT_PIN != 0) ? tgt_q : TARGET;
    wire hit = (MUT == 2) ? 1'b1 : (target_q == tid);
    wire [1:0] win = addr_q[11:10];
    wire [9:0] row = addr_q[9:0];
    // ---------------- sequencer state ----------------
    reg [31:0] cyc, period, lbase, rd_lb, nxt_lb, head_fire;
    reg seq_on, rd_q, rd_end, nxt_v, head_v, fault_r;
    reg [6:0] idx;
    reg [12:0] s_limit, s_base;
    reg [15:0] s_loops, rem;
    reg [EW-1:0] nxt;
    reg [CW-1:0] head_pl;
    reg tw_we; reg [6:0] tw_addr; reg [1:0] tw_sel; reg [255:0] tw_data;
    wire busy_any = seq_on || (|act_q);
    wire rd_go = (MODE == 1) && seq_on && !rd_end && !nxt_v && !rd_q && !fault_r;
    wire [NW*256-1:0] rd_word;
    assign tab_r_ce = rd_go; assign tab_r_addr = idx; assign tab_w_addr = tw_addr; assign tab_w_data = tw_data;
    generate if (MODE == 1) begin : g_tab
        assign rd_word = tab_rd_word;
        for (genvar w = 0; w < NW; w = w + 1) begin : g_w
            assign tab_w_ce[w] = tw_we && tw_sel == 2'(w);
        end
    end else begin : g_notab
        assign rd_word = '0; assign tab_w_ce = '0;
    end endgenerate
    wire [31:0] fire_at = (MUT == 1) ? head_fire + 32'd1 : head_fire;
    wire fire = head_v && cyc == fire_at;
    wire late = head_v && $signed(fire_at - cyc) < 0;
    // payload of nxt with the launch-relative fields rebased
    wire [CW-1:0] nxt_pl;
    generate
        for (genvar f = 0; f < RELF; f = f + 1) begin : g_rel
            assign nxt_pl[f*32 +: 32] = nxt[32 + f*32 +: 32] + nxt_lb;
        end
        if (CW > RELF * 32) begin : g_abs
            assign nxt_pl[CW-1:RELF*32] = nxt[EW-1:32+RELF*32];
        end
    endgenerate
    // ---------------- control ----------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_we <= 0; b_we <= 0; run_v <= 0; cmd_v <= 0; configured <= 0; fault_r <= 0; fault <= 0; active <= 0;
            cyc <= 0; cycle <= 0; seq_on <= 0; rd_q <= 0; rd_end <= 0; nxt_v <= 0; head_v <= 0; tw_we <= 0;
            period <= 0; idx <= 0; rem <= 0; lbase <= 0;
        end else begin
            a_we <= 0; b_we <= 0; run_v <= 0; tw_we <= 0;
            cyc <= cyc + 32'd1; cycle <= cyc;
            // ---- configuration writes
            if (cv && hit) begin
                configured <= 0;
                if (busy_any || lv) fault_r <= 1;
                else case (win)
                    2'd0: if (AWA > 0 && {1'b0, row} < (11'd1 << AWA)) begin a_we <= 1; a_addr <= row[(AWA>0?AWA:1)-1:0]; a_data <= data_q; end
                          else fault_r <= 1;
                    2'd1: if (AWB > 0 && {1'b0, row} < (11'd1 << AWB)) begin b_we <= 1; b_addr <= row[(AWB>0?AWB:1)-1:0]; b_data <= data_q; end
                          else fault_r <= 1;
                    2'd2: if (MODE == 1 && {1'b0, row} < 11'(NW * DEPTH)) begin
                              tw_we <= 1; tw_addr <= 7'(32'(row) / NW); tw_sel <= 2'(32'(row) % NW); tw_data <= data_q;
                          end else fault_r <= 1;
                    default: if (MODE == 1 && row == 10'd0) period <= data_q[31:0]; else fault_r <= 1;
                endcase
            end
            // ---- descriptor (run window / calendar range)
            if (dv && hit) begin
                configured <= 0;
                if (busy_any || lv || cv) fault_r <= 1;
                else if (MODE == 0) begin
                    if (loops_q != 16'd1 || limit_q <= {1'b0, base_q} || limit_q > (13'd1 << RBW) ||
                        (limit_q - {1'b0, base_q}) >= (14'd1 << RCW)) fault_r <= 1;
                    else begin s_base <= {1'b0, base_q}; s_limit <= limit_q; configured <= 1; end
                end else begin
                    if (loops_q == 16'd0 || limit_q <= {1'b0, base_q} || limit_q > 13'(DEPTH) || (loops_q != 16'd1 && period == 0))
                        fault_r <= 1;
                    else begin s_base <= {1'b0, base_q}; s_limit <= limit_q; s_loops <= loops_q; configured <= 1; end
                end
            end
            // ---- launch
            if (lv && configured) begin
                configured <= 0;
                if (busy_any || fault_r || (|flt_q) || cv || dv) fault_r <= 1;
                else if (MODE == 0) begin
                    run_v <= 1; run_base <= RBW'(s_base); run_count <= RCW'(s_limit - s_base);
                end else begin
                    seq_on <= 1; rd_end <= 0; idx <= s_base[6:0]; rem <= s_loops; lbase <= cyc + 32'(LEAD);
                end
            end
            // ---- sequencer (MODE 1)
            if (rd_go) begin
                rd_q <= 1; rd_lb <= lbase;
                if ({6'd0, idx} == s_limit - 13'd1) begin
                    if (rem > 16'd1) begin idx <= s_base[6:0]; rem <= rem - 16'd1; lbase <= lbase + period; end
                    else rd_end <= 1;
                end else idx <= idx + 7'd1;
            end else rd_q <= 0;
            if (rd_q) begin nxt <= rd_word[EW-1:0]; nxt_lb <= rd_lb; nxt_v <= 1; end
            if (nxt_v && (!head_v || fire)) begin
                head_fire <= nxt_lb + nxt[31:0]; head_pl <= nxt_pl; head_v <= 1; nxt_v <= 0;
            end else if (fire) head_v <= 0;
            if (late) fault_r <= 1;
            cmd_v <= fire && !fault_r;
            if (fire) cmd <= head_pl;
            if (fault_r) begin seq_on <= 0; rd_end <= 1; nxt_v <= 0; head_v <= 0; end
            else if (seq_on && rd_end && !rd_go && !rd_q && !nxt_v && !(head_v && !fire)) seq_on <= 0;
            // ---- status
            fault <= fault_r || (|flt_q);
            active <= seq_on || (|act_q);
        end
    end
endmodule
`default_nettype wire
