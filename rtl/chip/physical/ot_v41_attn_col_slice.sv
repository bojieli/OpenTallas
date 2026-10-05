`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One 265-bit GROUP COLUMN of the V4.1 full-shape attention neighborhood
// (H16/D512/T640, NL = 4): the four packed WINDOW banks of
// ot_chip_v41x_window_stage4, its bank-to-lane rotation register, the ordered
// merge beat of ot_chip_v41x_attn_row_merge, and the engine's packed-row
// staging (ot_hdc_v41x_attn_staging), all restricted to group g of every row.
//
// The 4224-bit window row splits exactly by group: group g is FP8 code sector g
// (256 bits) and scale byte g of sector 16.  The 265-bit engine group word is
// {fmt, scale, codes} (window: {0, scale[g], codes[g]}; selected CKV:
// {1, 120'b0, scales16[g], codes128[g]}).  Every datapath bit of the four
// modules therefore lives in exactly one of D/32 = 16 identical columns; no
// 4224-bit row, 16,896-bit bank response or 16,960-bit engine beat crosses a
// column.  The column-independent control (tags, valid, hazard, lane_ok, bank
// selection, merge FSM, staging pointers) stays in one control block
// (ot_v41_attn_stage_ctl) and reaches the columns as decoded strobes.
//
// Cycle behaviour is that of the adopted modules (proved by
// tb_v41_attn_neighborhood_equiv against ot_chip_v41x_window_stage4 +
// merge beat + ot_hdc_v41x_attn_staging):
//   bank read   : q <= mem[raddr] on req_v (read-before-write), held otherwise
//   rotation    : rot[l] <= lane_ok[l] ? q[bank_of_lane[l]] : 0, every cycle
//   merge beat  : clear / full 4-lane load / one-lane load from rot lane 0 or CKV
//   staging     : per-lane write at stg_waddr, all-lane read, 1-cycle latency
//
// Physical mapping (SRAM_MACRO = 1): each bank is one ASAP7 1R1W 128x256
// macro (32 of 128 rows used; the scale byte lives in flops), each staging
// lane's codes are one 1R1W 256x256 macro (160 of 256 rows), and the four
// lanes' 9-bit {fmt, scale} side fields share one 1R1W 512x128 macro with
// per-lane write masks (common address, as in the engine).
// ---------------------------------------------------------------------------
module ot_v41_attn_col_slice #(
    parameter bit SRAM_MACRO = 1,
    parameter integer STG_DEPTH = 160       // TROWS / NL
) (
    input  wire          clk,
    input  wire          rst_n,
    // WINDOW fill (sector g codes, and byte g of the scale sector)
    input  wire [3:0]    fill_code_we,      // per bank: fill of this column's code sector
    input  wire [3:0]    fill_scale_we,     // per bank: fill of the scale sector
    input  wire [4:0]    fill_slot,
    input  wire [255:0]  fill_code,
    input  wire [7:0]    fill_scale,
    // bank read (stage4 first register)
    input  wire          req_v,
    input  wire [19:0]   req_raddr,         // 4 banks x 5-bit slot
    // rotation (stage4 second register)
    input  wire [7:0]    rot_bank,          // 4 lanes x 2-bit source bank
    input  wire [3:0]    rot_ok,            // per lane: lane_ok
    // merge beat
    input  wire          beat_clr,
    input  wire          beat_full,         // all four lanes from the rotation register
    input  wire [3:0]    beat_lane,         // one-hot: load this lane
    input  wire          beat_ckv,          // lane source: CKV (else rotation lane 0)
    input  wire [143:0]  ckv_group,         // {scales16[g], codes128[g]}
    // engine staging
    input  wire [3:0]    stg_we,
    input  wire [7:0]    stg_waddr,
    input  wire [7:0]    stg_raddr,
    output wire [4*265-1:0] stg_q
);
    localparam integer GW = 265;

    // ------------------------------------------------ four WINDOW banks
    wire [255:0] bank_code [0:3];
    reg  [7:0]   bank_scale [0:3];
    genvar b;
    generate for (b = 0; b < 4; b = b + 1) begin : g_bank
        wire [4:0] raddr = req_raddr[5*b +: 5];
        reg  [7:0] scale_mem [0:31];
        always @(posedge clk) begin
            if (fill_scale_we[b]) scale_mem[fill_slot] <= fill_scale;
            if (req_v) bank_scale[b] <= scale_mem[raddr];
        end
        if (SRAM_MACRO) begin : g_macro
            ot_sram_1r1w_128x256_m1_r2c2 u_bank (
                .clk(clk), .r_ce_in(req_v), .r_addr_in({2'b00, raddr}),
                .rd_out(bank_code[b]),
                .w_ce_in(fill_code_we[b]), .w_addr_in({2'b00, fill_slot}),
                .wd_in(fill_code), .w_mask_in({256{fill_code_we[b]}}),
                .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end else begin : g_beh
            reg [255:0] mem [0:31];
            reg [255:0] q;
            always @(posedge clk) begin
                if (fill_code_we[b]) mem[fill_slot] <= fill_code;
                if (req_v) q <= mem[raddr];
            end
            assign bank_code[b] = q;
        end
    end endgenerate

    // ------------------------------------------------ rotation register
    reg [263:0] rot [0:3];                  // {scale, codes} of lane l
    genvar l;
    generate for (l = 0; l < 4; l = l + 1) begin : g_rot
        wire [1:0] sb = rot_bank[2*l +: 2];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rot[l] <= '0;
            else rot[l] <= rot_ok[l] ? {bank_scale[sb], bank_code[sb]} : 264'd0;
    end endgenerate

    // ------------------------------------------------ merge beat
    wire [GW-1:0] cfmt = {1'b1, 120'b0, ckv_group};
    reg  [GW-1:0] beat [0:3];
    generate for (l = 0; l < 4; l = l + 1) begin : g_beat
        always @(posedge clk or negedge rst_n)
            if (!rst_n) beat[l] <= '0;
            else if (beat_clr) beat[l] <= '0;
            else if (beat_full) beat[l] <= {1'b0, rot[l]};
            else if (beat_lane[l]) beat[l] <= beat_ckv ? cfmt : {1'b0, rot[0]};
    end endgenerate

    // ------------------------------------------------ engine staging
    wire [255:0] stg_code [0:3];
    wire [4*9-1:0] stg_side;
    generate if (SRAM_MACRO) begin : g_stg_macro
        wire [127:0] side_q;
        wire [127:0] side_d, side_m;
        for (l = 0; l < 4; l = l + 1) begin : g_lane
            ot_sram_1r1w_256x256_m2_r2c2 u_stg (
                .clk(clk), .r_ce_in(1'b1), .r_addr_in(stg_raddr),
                .rd_out(stg_code[l]),
                .w_ce_in(stg_we[l]), .w_addr_in(stg_waddr),
                .wd_in(beat[l][255:0]), .w_mask_in({256{stg_we[l]}}),
                .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
            // unused columns carry copies of the same field so no macro input is a
            // tie-off (tie fan-out onto one-sided pins blocked detailed route)
            assign side_d[32*l +: 32] = {beat[l][260:256], {3{beat[l][264:256]}}};
            assign side_m[32*l +: 32] = {32{stg_we[l]}};
            assign stg_side[9*l +: 9] = side_q[32*l +: 9];
        end
        ot_sram_1r1w_512x128_m4_r2c2 u_side (
            .clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0, stg_raddr}),
            .rd_out(side_q),
            .w_ce_in(|stg_we), .w_addr_in({1'b0, stg_waddr}),
            .wd_in(side_d), .w_mask_in(side_m),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(14'b0));
    end else begin : g_stg_beh
        for (l = 0; l < 4; l = l + 1) begin : g_lane
            reg [GW-1:0] mem [0:STG_DEPTH-1];
            reg [GW-1:0] q;
            always @(posedge clk) begin
                if (stg_we[l]) mem[stg_waddr] <= beat[l];
                q <= mem[stg_raddr];
            end
            assign stg_code[l] = q[255:0];
            assign stg_side[9*l +: 9] = q[264:256];
        end
    end endgenerate
    generate for (l = 0; l < 4; l = l + 1) begin : g_out
        assign stg_q[GW*l +: GW] = {stg_side[9*l +: 9], stg_code[l]};
    end endgenerate
endmodule
