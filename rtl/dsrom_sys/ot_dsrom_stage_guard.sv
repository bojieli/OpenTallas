`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_stage_guard -- stage-handoff identity guard on a package's inbound
// message stream (between the link receiver and ot_rom_pkg_ctrl_x).  Zero
// latency pass-through of valid/ready/data/last; it only observes and latches
// faults.  The no-ECC policy (AGENTS.md, 2026-10-02) keeps "configuration /
// descriptor validity, address bounds and transaction identity checks"
// mandatory; the controller checks a user's position order but not who sent a
// message, whether it was addressed here, or whether its length matches its
// framing.  Per message (header = first flit after a `last`):
//   * dest      == MY_ID, or a multicast group in DEST_OK_MASK (ids >= 32);
//   * src       in SRC_MASK (bit per package: the stages allowed to hand off here);
//   * type      in TYPE_MASK (bit 1 HIDDEN, 2 RESULT, 3 SIDE);
//   * len       == LEN_HID / LEN_SIDE for HIDDEN / SIDE, 0 for RESULT;
//   * framing   `last` exactly on flit len (no early/late last);
//   * user      < cfg_users;
//   * HIDDEN/RESULT position == the user's next expected one at this stage
//     (a stage hands off every position of a user once, in order).
// A violation latches fault/fault_code and the offending header.
// Header field offsets are those of ot_rom_pkg_ctrl_x.
// ---------------------------------------------------------------------------
module ot_dsrom_stage_guard #(
    parameter integer FLIT      = 512,
    parameter integer NW        = 16,
    parameter integer MAXU      = 16,
    parameter integer MY_ID     = 0,
    parameter [63:0]  SRC_MASK  = 64'h0,
    parameter [15:0]  TYPE_MASK = 16'h0002,
    parameter [63:0]  DEST_OK_MASK = 64'h0,   // multicast group ids accepted here (bit = id)
    parameter integer LEN_HID   = 1,
    parameter integer LEN_SIDE  = 1,
    parameter integer CHECK_POS = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [7:0]      cfg_users,
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
    output reg  [63:0]     fault_hdr,
    output reg  [31:0]     st_msgs,
    output reg  [31:0]     st_flits
);
    localparam integer HDR_DEST = 0, HDR_SRC = 8, HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32, HDR_POS = 40;
    localparam [3:0] F_DEST = 1, F_SRC = 2, F_TYPE = 3, F_LEN = 4, F_FRAME = 5, F_USER = 6, F_POS = 7;
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    assign out_valid = in_valid;
    assign in_ready  = out_ready;
    assign out_data  = in_data;
    assign out_last  = in_last;
    wire beat = in_valid && out_ready;

    reg        in_msg;                 // inside a message (header taken, last not yet seen)
    reg [7:0]  left;                   // payload flits still expected
    reg [NW-1:0] exp_pos [0:MAXU-1];

    wire [7:0]    h_dest = in_data[HDR_DEST +: 8];
    wire [7:0]    h_src  = in_data[HDR_SRC +: 8];
    wire [3:0]    h_type = in_data[HDR_TYPE +: 4];
    wire [7:0]    h_len  = in_data[HDR_LEN +: 8];
    wire [7:0]    h_user = in_data[HDR_USER +: 8];
    wire [NW-1:0] h_pos  = in_data[HDR_POS +: NW];
    wire dest_ok = (h_dest == MY_ID[7:0]) || (h_dest < 64 && DEST_OK_MASK[h_dest[5:0]]);
`ifndef DSROM_GUARD_MUTANT_NOSRC
    wire src_ok  = (h_src < 64) && SRC_MASK[h_src[5:0]];
`else
    wire src_ok  = 1'b1;                                   // mutant: sender identity unchecked
`endif
    wire type_ok = TYPE_MASK[h_type];
    wire [7:0] len_exp = (h_type == 4'd1) ? 8'(LEN_HID) : (h_type == 4'd3) ? 8'(LEN_SIDE) : 8'd0;
    wire pos_chk = CHECK_POS && (h_type == 4'd1 || h_type == 4'd2);

    task automatic flag(input [3:0] c);
        begin
            if (!fault) begin fault_code <= c; fault_hdr <= in_data[63:0]; end
            fault <= 1'b1;
        end
    endtask

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_msg <= 1'b0; left <= 0; fault <= 1'b0; fault_code <= 0; fault_hdr <= 0;
            st_msgs <= 0; st_flits <= 0;
            for (i = 0; i < MAXU; i = i + 1) exp_pos[i] <= 0;
        end else if (beat) begin
            st_flits <= st_flits + 1;
            if (!in_msg) begin
                st_msgs <= st_msgs + 1;
                if (!dest_ok) flag(F_DEST);
                else if (!src_ok) flag(F_SRC);
                else if (!type_ok) flag(F_TYPE);
                else if (h_len != len_exp) flag(F_LEN);
                else if (h_user >= cfg_users || h_user >= MAXU) flag(F_USER);
                else if (pos_chk && h_pos != exp_pos[h_user[UB-1:0]]) flag(F_POS);
                if (pos_chk && h_user < MAXU) exp_pos[h_user[UB-1:0]] <= h_pos + 1'b1;
                if ((h_len == 0) != in_last) flag(F_FRAME);
                in_msg <= !in_last;
                left <= h_len;
            end else begin
                left <= left - 1'b1;
                if ((left == 8'd1) != in_last) flag(F_FRAME);
                if (in_last) in_msg <= 1'b0;
            end
        end
    end
endmodule
