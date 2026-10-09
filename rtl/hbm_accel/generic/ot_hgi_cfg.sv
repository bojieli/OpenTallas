`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-forks 2026-10-09: the HGI-1 v0.9 config path (docs/HBM_GENERIC_INTERFACE.md sections 1.2-1.4).
//
//   ot_hgi_cfg_master   in the command processor: the CFG window (the hardware-read MD words staged), the CFG_COMMIT
//                       interlock (E_BUSY) and section-C range check (E_RANGE; magic / version / CRC / reserved are the
//                       loader's software checks, REVIEW_20261009 F-2), the broadcast of the 9 section-C words
//                       on the registered config bus {cfg_v, cfg_addr[5:0], cfg_data[31:0], cfg_commit}, the settle
//                       hold-off (doorbells refused) and CFG_STATUS.  On an error nothing is broadcast and the active
//                       values stay.  Section D (entry offsets, image base / pages) is latched for the sequencer.
//   ot_hgi_cfg_stn      one registered station of the bus (every station it crosses; no logic).
//   ot_hgi_cfg_rx       the receiver a block instantiates: input pin flops, shadow words for its own addresses, and
//                       the ACTIVE words (*cfg_act*) copied from the shadow on cfg_commit.  Reset = DS (the encoder's
//                       reset values, ot_hgi_cfg_consts.svh), so a block that never sees a load is the legacy block.
// Quasi-static: active words change only while the die is idle (the master refuses a commit while busy and holds
// doorbells for SETTLE cycles after it), so timing treats them as constants: set_false_path -from [*cfg_act*]
// (physical/hbm_forks/hgi_cfg_static.sdc).  No mode register is a timed launch point on a 1.2 GHz path.
// Protection: none (REVIEW_20261009: no extra control protection; the loader validates the descriptor).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_cfg_stn (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [39:0] d,           // {cfg_commit, cfg_v, cfg_addr[5:0], cfg_data[31:0]}
    output reg  [39:0] q
);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 40'd0; else q <= d;
endmodule

module ot_hgi_cfg_rx #(
    parameter integer W0 = 40,      // first word this block decodes
    parameter integer NW = 9,       // number of words
    parameter [NW*32-1:0] RST = 0   // the words' reset (= DS) values: pass HGI_RST_* from ot_hgi_cfg_consts.svh
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [39:0]   bus,       // {cfg_commit, cfg_v, cfg_addr, cfg_data} from the last station
    output wire [NW*32-1:0] act     // active words (quasi-static)
);
    reg [39:0] b;                                   // pin flops: no logic between the bus pins and these
    always @(posedge clk or negedge rst_n) if (!rst_n) b <= 40'd0; else b <= bus;
    wire        c_commit = b[39];
    wire        c_v      = b[38];
    wire [5:0]  c_addr   = b[37:32];
    wire [31:0] c_data   = b[31:0];
    reg [NW*32-1:0] shadow;
    reg [NW*32-1:0] cfg_act_q;                      // the quasi-static registers (SDC: -from *cfg_act*)
    integer k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin shadow <= RST; cfg_act_q <= RST; end
        else begin
            for (k = 0; k < NW; k = k + 1)
                if (c_v && c_addr == W0 + k) shadow[k*32 +: 32] <= c_data;
            if (c_commit) cfg_act_q <= shadow;
        end
    assign act = cfg_act_q;
endmodule

module ot_hgi_cfg_master #(
    parameter integer SETTLE = 64   // cycles after cfg_commit before CFG_STATUS.loaded (>= deepest bus latency + 16)
) (
    input  wire        clk,
    input  wire        rst_n,
    // the CFG window of the host write port (cmd_we / cmd_addr / cmd_wdata with the window bit set)
    input  wire        w_en,
    input  wire [4:0]  w_pair,      // MD words 2*w_pair (bits 31:0) and 2*w_pair+1 (bits 63:32)
    input  wire [63:0] w_data,
    input  wire        commit,      // CFG_COMMIT
    input  wire        busy,        // a job runs or a unit queue is non-empty (E_BUSY)
    output wire [39:0] bus,         // registered config bus (to the first station)
    output reg         st_loaded,   // a load completed and settled (0 before any load: reset values = DS active)
    output reg  [2:0]  st_err,      // last commit's code: 0 OK, 4 E_BUSY, 5 E_RANGE
    output wire        st_hold,     // a commit is being checked / broadcast / settling: refuse doorbells
    output reg  [5*32-1:0] md_d     // section D as committed: {image_pages(61), image_base(60), draft(58), verify(57), ar(56)}
);
`include "ot_hgi_cfg_consts.svh"
    // REVIEW_20261009 F-2 (confirmed review-0342): the hardware keeps only the busy / settle interlock and the range
    // checks of section C; magic, version, CRC and reserved bits are validated by the loader in software
    // (tools/hbm_generic_iface.py hw_check / sw_check).  Only the hardware-read words are staged: section C (40-48) and
    // section D (56-61); other window writes are ignored.
    reg [31:0] wc [0:8];            // words 40 .. 48
    reg [31:0] wd [0:5];            // words 56 .. 61
    integer q;
    always @(posedge clk) if (w_en) begin
        for (q = 0; q < 9; q = q + 1) begin
            if ({w_pair, 1'b0} == 40 + q) wc[q] <= w_data[31:0];
            if ({w_pair, 1'b1} == 40 + q) wc[q] <= w_data[63:32];
        end
        for (q = 0; q < 6; q = q + 1) begin
            if ({w_pair, 1'b0} == 56 + q) wd[q] <= w_data[31:0];
            if ({w_pair, 1'b1} == 56 + q) wd[q] <= w_data[63:32];
        end
    end
    localparam [2:0] S_IDLE = 3'd0, S_CHK = 3'd1, S_DEC = 3'd2, S_BC = 3'd3, S_COMMIT = 3'd4, S_SETTLE = 3'd5;
    reg [2:0]  st;
    reg [3:0]  i;
    reg        f_rng;
    reg [9:0]  cnt;
    reg        bv, bc;
    reg [5:0]  ba;
    reg [31:0] bd;
    wire [31:0] wi = wc[i];
    assign st_hold = (st != S_IDLE);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; i <= 4'd0; f_rng <= 1'b0; cnt <= 10'd0; bv <= 1'b0; bc <= 1'b0; ba <= 6'd0; bd <= 32'd0;
            st_loaded <= 1'b0; st_err <= 3'd0; md_d <= {5*32{1'b0}};
        end else begin
            bv <= 1'b0; bc <= 1'b0;
            case (st)
                S_IDLE: if (commit) begin
                    if (busy) st_err <= 3'd4;                               // E_BUSY: refused, values kept
                    else begin st <= S_CHK; i <= 4'd0; f_rng <= 1'b0; end
                end
                S_CHK: begin                                                // the 9 section-C words, one a cycle
`ifndef OT_HGI_MUT_RANGE
                    if (!hgi_c_legal(6'd40 + i, wi)) f_rng <= 1'b1;
`endif
                    if (i == 4'd8) st <= S_DEC; else i <= i + 4'd1;
                end
                S_DEC: if (f_rng) begin st_err <= 3'd5; st <= S_IDLE; end   // E_RANGE: refused, values kept
                       else begin st <= S_BC; i <= 4'd0; end
                S_BC: begin
                    bv <= 1'b1; ba <= 6'd40 + i; bd <= wi;
                    if (i == 4'd8) st <= S_COMMIT; else i <= i + 4'd1;
                end
                S_COMMIT: begin
                    bc <= 1'b1; st_err <= 3'd0; cnt <= 10'd0; st <= S_SETTLE;
                    md_d <= {wd[5], wd[4], wd[2], wd[1], wd[0]};
                end
                S_SETTLE: begin
`ifdef OT_HGI_MUT_SETTLE
                    begin st_loaded <= 1'b1; st <= S_IDLE; end
`else
                    cnt <= cnt + 10'd1;
                    if (cnt == SETTLE - 1) begin st_loaded <= 1'b1; st <= S_IDLE; end
`endif
                end
                default: st <= S_IDLE;
            endcase
        end
    end
    assign bus = {bc, bv, ba, bd};
endmodule
`default_nettype wire
