`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_stage_guard (stream ds-control, 2026-10-08): the S81 successor of ot_dsrom_stage_guard (pinned, unchanged):
// the stage-handoff identity guard between the link receiver and ot_s81_pkg_ctrl.  Zero-latency pass-through; it
// observes every message header and latches the first violation (the no-ECC policy, AGENTS.md 2026-10-02, keeps
// configuration / descriptor validity, address bounds and transaction identity checks mandatory).  S81 changes:
// the ot_s81_hdr.svh header (12-bit ids and lengths, 21-bit positions); the sender check is a RANGE of fabric ids
// (the previous stage's 4 TP dies, or the head dies at the SOURCE) instead of a 64-bit mask, which cannot name 492
// dies; multicast groups are an id range [GRP_LO, GRP_HI].  Per message:
//   * dest == MY_ID or in [GRP_LO, GRP_HI];       * src in [SRC_LO, SRC_HI] or [SRC2_LO, SRC2_HI];
//   * type in TYPE_MASK (bit 1 HIDDEN, 2 RESULT, 3 SIDE);
//   * len == LEN_HID (HIDDEN), <= LEN_SIDE_MAX (SIDE), 0 (RESULT); framing: last exactly on flit len;
//   * user < cfg_users;   * HIDDEN / RESULT position == the user's next expected one at this stage, or 0 (a new
//     request for that user slot restarts its sequence; the reduced-array guard allowed one run per reset).
// FAIL-CLOSED (S81): a message whose header violates a check is DROPPED (all its flits are consumed and not
// forwarded) and the fault is latched; the reduced-array guard only observed.  The check sits in the header
// flit's valid path (combinational compares of the pin-flopped header; no added cycle).
// ---------------------------------------------------------------------------
module ot_s81_stage_guard #(
    parameter integer FLIT = 512, NW = 21, MAXU = 16, MY_ID = 0,
    parameter integer SRC_LO = 0, SRC_HI = 0, SRC2_LO = 4095, SRC2_HI = 0,
    parameter integer GRP_LO = 4095, GRP_HI = 0,
    parameter [15:0]  TYPE_MASK = 16'h0002,
    parameter integer LEN_HID = 640, LEN_SIDE_MAX = 64, CHECK_POS = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [11:0]     cfg_users,
    input  wire            in_valid,
    output wire            in_ready,
    input  wire [FLIT-1:0] in_data,
    input  wire            in_last,
    output wire            out_valid,
    input  wire            out_ready,
    output wire [FLIT-1:0] out_data,
    output wire            out_last,
    output reg             fault,
    output reg  [3:0]      fault_code,
    output reg  [127:0]    fault_hdr,
    output reg  [31:0]     st_msgs,
    output reg  [31:0]     st_flits
);
`include "ot_s81_hdr.svh"
    localparam [3:0] F_DEST = 1, F_SRC = 2, F_TYPE = 3, F_LEN = 4, F_FRAME = 5, F_USER = 6, F_POS = 7;
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    reg        in_msg;
    reg        drop;                   // the current message is being dropped
    wire       hdr_bad;
    wire       blk = in_msg ? drop : hdr_bad;     // this flit is not forwarded
    assign out_valid = in_valid && !blk;
    assign in_ready  = blk ? 1'b1 : out_ready;
    assign out_data  = in_data;
    assign out_last  = in_last;
    wire beat = in_valid && in_ready;
    reg [11:0] left;
    reg [NW-1:0] exp_pos [0:MAXU-1];
    wire [11:0] h_dest = in_data[SH_DEST +: 12];
    wire [11:0] h_src  = in_data[SH_SRC +: 12];
    wire [3:0]  h_type = in_data[SH_TYPE +: 4];
    wire [11:0] h_len  = in_data[SH_LEN +: 12];
    wire [11:0] h_user = in_data[SH_USER +: 12];
    wire [NW-1:0] h_pos = in_data[SH_POS +: NW];
    wire dest_ok = (h_dest == 12'(MY_ID)) || (h_dest >= 12'(GRP_LO) && h_dest <= 12'(GRP_HI));
`ifndef S81_GUARD_MUTANT_NOSRC
    wire src_ok  = (h_src >= 12'(SRC_LO) && h_src <= 12'(SRC_HI)) || (h_src >= 12'(SRC2_LO) && h_src <= 12'(SRC2_HI));
`else
    wire src_ok  = 1'b1;
`endif
    wire type_ok = TYPE_MASK[h_type];
    wire len_ok  = (h_type == MT_HIDDEN) ? (h_len == 12'(LEN_HID)) :
                   (h_type == MT_SIDE)   ? (h_len <= 12'(LEN_SIDE_MAX)) : (h_len == 12'd0);
    wire pos_chk = CHECK_POS && (h_type == MT_HIDDEN || h_type == MT_RESULT);
    wire pos_ok  = !pos_chk || h_pos == exp_pos[h_user[UB-1:0]] || h_pos == 0;
    wire user_ok = h_user < cfg_users && h_user < MAXU;
    wire frm_ok  = (h_len == 0) == in_last;
`ifndef S81_GUARD_MUTANT_NOSRC
    assign hdr_bad = !(dest_ok && src_ok && type_ok && len_ok && user_ok && pos_ok && frm_ok);
`else
    assign hdr_bad = !(dest_ok && type_ok && len_ok && user_ok && pos_ok && frm_ok);
`endif
    task automatic flag(input [3:0] c);
        begin
            if (!fault) begin fault_code <= c; fault_hdr <= in_data[127:0]; end
            fault <= 1'b1;
        end
    endtask
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_msg <= 1'b0; drop <= 1'b0; left <= 0; fault <= 1'b0; fault_code <= 0; fault_hdr <= 0; st_msgs <= 0; st_flits <= 0;
            for (i = 0; i < MAXU; i = i + 1) exp_pos[i] <= 0;
        end else if (beat) begin
            st_flits <= st_flits + 1;
            if (!in_msg) begin
                st_msgs <= st_msgs + 1;
                if (!dest_ok) flag(F_DEST);
                else if (!src_ok) flag(F_SRC);
                else if (!type_ok) flag(F_TYPE);
                else if (!len_ok) flag(F_LEN);
                else if (h_user >= cfg_users || h_user >= MAXU) flag(F_USER);
                else if (!pos_ok) flag(F_POS);
                else if (!frm_ok) flag(F_FRAME);
                if (pos_chk && user_ok && !hdr_bad) exp_pos[h_user[UB-1:0]] <= h_pos + 1'b1;
                in_msg <= !in_last;
                drop <= hdr_bad;
                left <= h_len;
            end else begin
                left <= left - 1'b1;
                if ((left == 12'd1) != in_last) flag(F_FRAME);
                if (in_last) in_msg <= 1'b0;
            end
        end
    end
endmodule
