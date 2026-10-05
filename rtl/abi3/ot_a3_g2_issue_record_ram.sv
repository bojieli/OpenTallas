`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// G2 issue-record store payload memory: 32 slots x 8 lanes x 512 b in four
// ASAP7 macros.
//
// WHERE THIS DEPARTS FROM SECTION 11.2, AND WHY.  Decision (a) of
// docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2 says "the 8-slot IRS is eight
// fakeram_512x8 at exactly 512 B each".  That mapping is inherited from the
// sky130hd vehicle row "IRS | 32 x 512 B | 8 x 512 B = 4 macros", which sized
// the IRS as eight 512-byte SLOTS, 4 KiB in total.  The IRS payload port that
// rtl/abi3/ot_a3_microsequencer.sv actually exposes is not that memory:
//
//     output reg [4:0] irs_wslot;   // 32 slots
//     output reg [2:0] irs_wlane;   //  8 lanes
//     output reg [511:0] irs_wdata; // 512 bits per lane
//     input  wire [511:0] irs_rdata; // "A read returns the lane one cycle later"
//
// which is 32 x 8 x 64 B = 16 KiB behind a 512-bit port with one cycle of
// read latency.  Eight fakeram_512x8 ganged give a 64-bit port over 4 KiB:
// one quarter of the capacity and one eighth of the width, so a lane read
// would take eight beats and three quarters of the slots would have nowhere
// to live.  The mapping in section 11.2 does not fit and is not used.
//
// What is used instead: FOUR fakeram_256x128 ganged in width.  256 rows x
// 512 b = 16,384 B, addressed {slot[4:0], lane[2:0]} with no spare rows and
// none missing, and a one-cycle registered read that matches the sequencer's
// contract exactly -- so this bank needs no adapter at all.  It costs
// 4 x 1,375.941 = 5,503.8 um^2 against the 8 x 171.993 = 1,375.9 um^2 the
// section-11.2 row prices, for four times the capacity at eight times the
// width.  This is the reference model rtl/test/a3_microsequencer_top.sv
// already keeps as `irs_payload_mem[{irs_rslot, irs_rlane}]`, in macros.
//
// ONE PORT.  The parts are single-port: a cycle is a read or a write, never
// both.  ot_a3_microsequencer asserts irs_we only in S_ISSUE and in
// publish_view, and irs_re only in S_FAULT_DRAIN, which are disjoint states,
// so a collision cannot occur in the design as written.  It is nonetheless
// detected rather than assumed: the write wins and collisions increment
// conflict_count, which must read zero on any campaign that uses this bank.
// ---------------------------------------------------------------------------
module ot_a3_g2_issue_record_ram (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         irs_we,
    input  wire [4:0]   irs_wslot,
    input  wire [2:0]   irs_wlane,
    input  wire [511:0] irs_wdata,
    input  wire         irs_re,
    input  wire [4:0]   irs_rslot,
    input  wire [2:0]   irs_rlane,
    output wire [511:0] irs_rdata,

    output reg  [31:0]  conflict_count
);
    wire [7:0] waddr = {irs_wslot, irs_wlane};
    wire [7:0] raddr = {irs_rslot, irs_rlane};

    wire       ram_ce   = irs_we | irs_re;
    wire       ram_we   = irs_we;
    wire [7:0] ram_addr = irs_we ? waddr : raddr;

    wire [127:0] rd0, rd1, rd2, rd3;
    assign irs_rdata = {rd3, rd2, rd1, rd0};

    fakeram_256x128 irs_ram0 (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we),
        .wd_in(irs_wdata[127:0]),   .rd_out(rd0)
    );
    fakeram_256x128 irs_ram1 (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we),
        .wd_in(irs_wdata[255:128]), .rd_out(rd1)
    );
    fakeram_256x128 irs_ram2 (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we),
        .wd_in(irs_wdata[383:256]), .rd_out(rd2)
    );
    fakeram_256x128 irs_ram3 (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we),
        .wd_in(irs_wdata[511:384]), .rd_out(rd3)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            conflict_count <= 32'd0;
        else if (irs_we && irs_re)
            conflict_count <= conflict_count + 32'd1;
    end
endmodule
