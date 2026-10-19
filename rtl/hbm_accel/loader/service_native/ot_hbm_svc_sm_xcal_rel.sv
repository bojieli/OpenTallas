`timescale 1ns/1ps
`default_nettype none
// HBM-SMBUDGET 2026-10-19 (coordinator decision 0jx): the attention-SM EXTENSION CALENDAR xc_<q><k> in lockstep with the
// relative SM service group (ot_hbm_svc_sm_group_rel_id).  = ot_hbm_svc_sm_xcal with
//   * PAW-bit programme store (2,048 words: ot_smh_calendar_static_x AW 11) and 11/12-bit prog_base/limit from the
//     relative descriptor layout ([189] prog_base[10], [190] prog_limit[11]; [232:191] must be zero; the relative address
//     fields [188:143] are the svg issuer's and are ignored here);
//   * the svg feed's RELOC stages mirrored (R +1 edge, C +2 edges): cmd_ext / kv_desc leave on the svg command edge; the
//     SM mode of magic words comes from the descriptor (mrel) and the format-launch edge gets {magic, mode} (fl), so one
//     programme serves FP8 / FP4 / BF16 bodies; no row / tag / epoch lives in [191:83];
//   * DD-row descriptor table copy (256: two 128x256 macros), identity [239:232] as the svg issuer.
// Faults and pin rules as ot_hbm_svc_sm_xcal.  MUT 1/2/3 as ot_hbm_svc_sm_xcal; MUT 4 = no RELOC stages (two edges early).
module ot_hbm_svc_sm_xcal_rel #(parameter integer MUT = 0, parameter integer PAW = 11, parameter integer PREL = 1,
    parameter integer DD = 256, parameter integer DAW = (DD > 128) ? 8 : 7) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          cfg_we,
    input  wire [PAW-1:0] cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_we,
    input  wire [DAW-1:0] desc_addr,
    input  wire [255:0]  desc_data,
    input  wire          run_v,
    input  wire [DAW-1:0] run_base,
    input  wire [DAW:0]  run_count,
    output wire [108:0]  cmd_ext,
    output wire [63:0]   kv_desc,
    output reg           active,
    output reg           done,
    output reg           fault
);
    // ---------------- local reset release at the rst_n pin (H-SM native capture repair, 2026-10-16): r1 measured
    // rst_n capture 254.0 ps > 190 (the pin fanned out to every async-clear flop here and in u_cal).  rst_n now lands
    // on ONE async-clear flop at the pin face (assert async, release synchronous, one edge later); every other flop
    // clears from rst_q, a reg->recovery path inside the leaf.  No operation edge changes (the host collar issues
    // descriptor/programme writes only after reset; release precedes them).  MUT 3: rst_q never releases.
    reg rst_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0;
        else        rst_q <= (MUT == 3) ? 1'b0 : 1'b1;
    // ---------------- pin flops
    reg desc_we_q, run_q;
    reg [DAW-1:0] desc_addr_q, run_base_q;
    reg [255:0] desc_data_q;
    reg [DAW:0] run_count_q;
    always @(posedge clk) begin desc_addr_q <= desc_addr; desc_data_q <= desc_data; run_base_q <= run_base; run_count_q <= run_count; end
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin desc_we_q <= 1'b0; run_q <= 1'b0; end
        else begin desc_we_q <= desc_we; run_q <= run_v; end
    // ---------------- go table (copy of the svg issuer's descriptor table)
    reg running, rd_q, ent_v;
    reg [DAW-1:0] rp, rp_q;
    reg [DAW:0] n_rd, n_go;
    reg [23:0] rc;
    reg [23:0] e_at; reg [PAW-1:0] e_base; reg [PAW:0] e_limit; reg [15:0] e_loops; reg [4:0] e_ctx;   // {mode3, mrel, fl}
    wire [255:0] rd;
    wire rd_go = running && n_rd != 0 && !ent_v && !rd_q;
    generate if (DD == 128) begin : g_t1
        ot_sram_1r1w_128x256_m1_r2c2 u_tab (.clk(clk), .r_ce_in(rd_go), .r_addr_in(rp[6:0]), .rd_out(rd),
            .w_ce_in(desc_we_q && !running), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end else begin : g_t2
        wire [255:0] rd_lo, rd_hi;
        ot_sram_1r1w_128x256_m1_r2c2 u_tab_lo (.clk(clk), .r_ce_in(rd_go && !rp[7]), .r_addr_in(rp[6:0]), .rd_out(rd_lo),
            .w_ce_in(desc_we_q && !running && !desc_addr_q[7]), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q),
            .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        ot_sram_1r1w_128x256_m1_r2c2 u_tab_hi (.clk(clk), .r_ce_in(rd_go && rp[7]), .r_addr_in(rp[6:0]), .rd_out(rd_hi),
            .w_ce_in(desc_we_q && !running && desc_addr_q[7]), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q),
            .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        assign rd = rp_q[7] ? rd_hi : rd_lo;
    end endgenerate
    wire go = ent_v && rc == e_at;
    // ---------------- extension programme calendar (same leaf as the svg feed's programme calendar)
    wire [172:0] word0;
    wire cal_v, cal_active, cal_done, cal_fault;
    wire [4:0] wctx; wire [31:0] word_ord;
    ot_smh_calendar_static_x #(.W(173), .AW(PAW), .XW(5)) u_cal (.clk(clk), .rst_n(rst_q), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start_v(go), .start_base(e_base), .start_limit(e_limit), .start_loops(e_loops), .start_ctx(e_ctx),
        .calendar(word0), .calendar_ctx(wctx), .calendar_iter(), .calendar_lastit(), .calendar_v(cal_v), .ordinal(word_ord),
        .active(cal_active), .done(cal_done), .fault(cal_fault));
    // RELOC mirror of the svg feed: R stage (+1 edge) = the svg cache-read edge, C stage (+2) = the svg command edge.
    // mrel: the SM mode [183:181] (cmd_ext [100:98]) of every magic word comes from the descriptor (P2: one programme for
    // FP8 / FP4 / BF16 bodies of a shape); fl: the format-launch edge (R edge of the programme's first word) carries
    // {magic, mode} as the svg carries {format_launch, mode[1:0]}.  PREL=0: one stage (absolute words, old envelope).
    localparam [7:0] MAGIC = 8'ha2;
    reg [172:0] word_r, word_c;
    always @(posedge clk) begin
        word_r <= word0;
        if (PREL != 0 && cal_v && wctx[1] && word0[108:101] == MAGIC) word_r[100:98] <= wctx[4:2];
        word_c <= word_r;
        if (PREL != 0 && cal_v && word_ord == 0 && wctx[0]) begin word_c[108:101] <= MAGIC; word_c[100:98] <= wctx[4:2]; end
    end
    wire [172:0] word = (MUT == 4) ? word0 : (PREL != 0) ? word_c : word_r;
    assign cmd_ext = (MUT == 2) ? word[172:64] : word[108:0];
    assign kv_desc = (MUT == 2) ? word[63:0] : word[172:109];
    always @(posedge clk or negedge rst_q) begin
        if (!rst_q) begin
            running <= 1'b0; rd_q <= 1'b0; ent_v <= 1'b0; rp <= 0; rp_q <= 0; n_rd <= 0; n_go <= 0;
            rc <= 24'd0; e_at <= 24'd0; e_base <= 0; e_limit <= 0; e_loops <= 16'd0; e_ctx <= 5'd0;
            active <= 1'b0; done <= 1'b0; fault <= 1'b0;
        end else begin
            done <= 1'b0;
            active <= running || cal_active;
            if (run_q) begin
                if (running || run_count_q == 0 || {1'b0, run_base_q} + run_count_q > DD) fault <= 1'b1;
                else begin
                    running <= 1'b1; rp <= run_base_q; n_rd <= run_count_q; n_go <= run_count_q;
                    rc <= (MUT == 1) ? 24'd0 : 24'd1;
                end
            end else if (running) rc <= rc + 24'd1;
            rd_q <= rd_go; rp_q <= rp;
            if (rd_go) begin rp <= rp + 1'b1; n_rd <= n_rd - 1'b1; end
            if (rd_q) begin
                ent_v <= 1'b1;
                e_at <= rd[142:119]; e_base <= PAW'({rd[189], rd[91:82]}); e_limit <= (PAW+1)'({rd[190], rd[102:92]}); e_loops <= rd[118:103];
                e_ctx <= {rd[197:195], rd[198], rd[199]};
                if (rd[255:240] != 16'h5d15 || rd[232 +: DAW] != rp_q || (DAW == 7 && rd[239]) || rd[231:200] != 0) fault <= 1'b1;
            end
            if (go) begin
                ent_v <= 1'b0; n_go <= n_go - 1'b1;
                if (n_go == 1) running <= 1'b0;
            end
            if (ent_v && rc > e_at) fault <= 1'b1;            // missed compiler slot: never a late start
            if (cal_fault) fault <= 1'b1;
            if (cal_done && !running) done <= 1'b1;          // the run's last programme has issued its last word
        end
    end
    wire unused_ok = &{1'b0, cal_v};
endmodule
`default_nettype wire
