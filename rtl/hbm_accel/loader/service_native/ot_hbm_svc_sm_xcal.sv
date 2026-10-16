`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/attn 2026-10-16: the attention SM's EXTENSION CALENDAR, the second half of the 192-bit SM command plus the
// 64-bit KV_DESC of ot_hbm_accel_smh_attn (G-SMVM-KVDESC).  One instance per SM (xc_<q><k>) beside its service group
// svg_<q><k> = ot_hbm_svc_sm_group.
//   die nets: sm.command[82:0]   <- svg.sm_command          (the legacy 83-bit SM schedule, unchanged)
//             sm.command[191:83] <- xcal.cmd_ext[108:0]     (revisioned fields, magic 0xa2 at [191:184])
//             sm.kv_desc[63:0]   <- xcal.kv_desc            (line-run descriptor, loaded on command[115])
// The svg programme envelope is 135 b (ot_hbm_svc_sm_feed_programmed); 135 + 109 = 244 b does not fit one protected
// programme word (ot_smh_calendar_static W <= 223), so the extension is a SECOND real programme calendar
// (ot_smh_calendar_static W=173, its own 1024x256 SRAM): word = {kv_desc[63:0], cmd_ext[108:0]}.
// LOCKSTEP, no handshake: the svg issuer launches its programme calendar on a COMPILER SLOT (FIXED_GO=1): descriptor i
// [142:119] go_at = the stream edge counted from the run launch, base/limit/loops in [91:82]/[102:92]/[118:103].
// This leaf receives the SAME descriptor-table writes and the SAME run launch as the svg (fan-out of the svg's host
// collar cp_svg_<q><k> b_* / run_*), keeps its own copy of the table (real 128x256 SRAM, as the issuer), and starts
// its calendar with the same base/limit/loops on the same edge (rc == go_at), so both calendars present word pc on
// the same output edge: cmd_ext / kv_desc are the calendar's output flops, issued in the same cycle as svg.sm_command.
// Run launch pin flop: rc counts 1 at the first edge after the pin, i.e. exactly the issuer's rc (bench-proved).
// Faults (sticky, never a stall): run while running or count 0, bad table word (magic 5d15 / row identity / non-zero
// [232:143]), a go slot that passes before its entry is staged (late), calendar fault (bad programme word / start
// while busy).  Pin rule: every input lands in a flop (programme cfg in the calendar's own pin rung), every output is
// a flop.  Fixed latency: identical to the svg programme path (go edge -> start_v_q -> macro -> capture -> calendar).
// MUT (bench negative controls): 1 rc off by one (calendar one edge late); 2 kv_desc / cmd_ext from the wrong field.
module ot_hbm_svc_sm_xcal #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          cfg_we,
    input  wire [9:0]    cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_we,
    input  wire [6:0]    desc_addr,
    input  wire [255:0]  desc_data,
    input  wire          run_v,
    input  wire [6:0]    run_base,
    input  wire [7:0]    run_count,
    output wire [108:0]  cmd_ext,
    output wire [63:0]   kv_desc,
    output reg           active,
    output reg           done,
    output reg           fault
);
    // ---------------- reset relay at the rst_n pin (H-SM 10-16: r1 native FAIL capture 254.0 ps on rst_n only -- the port
    // net reached every async clear deep in the clock tree).  The port now drives only this relay (2 sync + 1 relay flop,
    // placed at the W pin next to the clock entry); release is 3 edges later, before any host run launch.
    wire rn;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    // ---------------- pin flops
    reg desc_we_q, run_q;
    reg [6:0] desc_addr_q, run_base_q;
    reg [255:0] desc_data_q;
    reg [7:0] run_count_q;
    always @(posedge clk) begin desc_addr_q <= desc_addr; desc_data_q <= desc_data; run_base_q <= run_base; run_count_q <= run_count; end
    always @(posedge clk or negedge rn)
        if (!rn) begin desc_we_q <= 1'b0; run_q <= 1'b0; end
        else begin desc_we_q <= desc_we; run_q <= run_v; end
    // ---------------- go table (copy of the svg issuer's descriptor table)
    reg running, rd_q, ent_v;
    reg [6:0] rp, rp_q;
    reg [7:0] n_rd, n_go;
    reg [23:0] rc;
    reg [23:0] e_at; reg [9:0] e_base; reg [10:0] e_limit; reg [15:0] e_loops;
    wire [255:0] rd;
    wire rd_go = running && n_rd != 8'd0 && !ent_v && !rd_q;
    ot_sram_1r1w_128x256_m1_r2c2 u_tab (.clk(clk), .r_ce_in(rd_go), .r_addr_in(rp), .rd_out(rd),
        .w_ce_in(desc_we_q && !running), .w_addr_in(desc_addr_q), .wd_in(desc_data_q), .w_mask_in({256{1'b1}}),
        .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    wire go = ent_v && rc == e_at;
    // ---------------- extension programme calendar (same leaf as the svg feed's programme calendar)
    wire [172:0] word;
    wire cal_v, cal_active, cal_done, cal_fault;
    ot_smh_calendar_static #(.W(173)) u_cal (.clk(clk), .rst_n(rn), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start_v(go), .start_base(e_base), .start_limit(e_limit), .start_loops(e_loops),
        .calendar(word), .calendar_v(cal_v), .ordinal(), .active(cal_active), .done(cal_done), .fault(cal_fault));
    assign cmd_ext = (MUT == 2) ? word[172:64] : word[108:0];
    assign kv_desc = (MUT == 2) ? word[63:0] : word[172:109];
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            running <= 1'b0; rd_q <= 1'b0; ent_v <= 1'b0; rp <= 7'd0; rp_q <= 7'd0; n_rd <= 8'd0; n_go <= 8'd0;
            rc <= 24'd0; e_at <= 24'd0; e_base <= 10'd0; e_limit <= 11'd0; e_loops <= 16'd0;
            active <= 1'b0; done <= 1'b0; fault <= 1'b0;
        end else begin
            done <= 1'b0;
            active <= running || cal_active;
            if (run_q) begin
                if (running || run_count_q == 8'd0) fault <= 1'b1;
                else begin
                    running <= 1'b1; rp <= run_base_q; n_rd <= run_count_q; n_go <= run_count_q;
                    rc <= (MUT == 1) ? 24'd0 : 24'd1;
                end
            end else if (running) rc <= rc + 24'd1;
            rd_q <= rd_go; rp_q <= rp;
            if (rd_go) begin rp <= rp + 7'd1; n_rd <= n_rd - 8'd1; end
            if (rd_q) begin
                ent_v <= 1'b1;
                e_at <= rd[142:119]; e_base <= rd[91:82]; e_limit <= rd[102:92]; e_loops <= rd[118:103];
                if (rd[255:240] != 16'h5d15 || rd[239:233] != rp_q || rd[232:143] != 0) fault <= 1'b1;
            end
            if (go) begin
                ent_v <= 1'b0; n_go <= n_go - 8'd1;
                if (n_go == 8'd1) running <= 1'b0;
            end
            if (ent_v && rc > e_at) fault <= 1'b1;            // missed compiler slot: never a late start
            if (cal_fault) fault <= 1'b1;
            if (cal_done && !running) done <= 1'b1;          // the run's last programme has issued its last word
        end
    end
    wire unused_ok = &{1'b0, cal_v};
endmodule
`default_nettype wire
