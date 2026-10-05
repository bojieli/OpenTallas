`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// G2 array staging: the four operand memories the LQ8 datapath array reads,
// as six ASAP7 macros.
//
// docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2, decision (a): "16 KiB of tile
// staging is two fakeram_512x128".  That is the WEIGHT ring below.  Section
// 11.2's staging row prices only the weight ring; the array also reads an
// activation window, an activation E8M0 scale table and a weight E8M0 scale
// table (rtl/abi3/ot_a3_lq8.sv, "shared activation operand and scale ports",
// "weight scale table port"), which the vehicle memory plan does not name.
// Those three are mapped here onto the smallest parts of the same image whose
// word width is exactly the port width, so that none of them needs a beat
// adapter or a width mux:
//
//   port                LQ8 signal      width   part                capacity
//   weight stream       w_rd_data       128 b   2 x fakeram_512x128   16 KiB
//   activation operand  a_rd_data        64 b   1 x fakeram_256x64     2 KiB
//   activation scale    s_rd_data        32 b   1 x fakeram7_256x32    1 KiB
//   weight scale table  ws_rd_data       64 b   1 x fakeram_256x64     2 KiB
//
// Every one of the four is a plain one-cycle registered read, which is
// exactly the contract rtl/abi3/ot_a3_lq8.sv states for all four of its
// ports ("one cycle of read latency"), so the array is wired to the macros
// with no adapter logic in the read path at all.  The only adapter here is
// the weight ring's depth ganging: two 512-row parts make 1,024 rows, the
// bank is address bit 9 and the read-data mux is driven by that bit
// registered, which costs one flop and a 128-bit 2:1 mux.
//
// THE WINDOW.  The LQ8's addresses are 32-bit stream/element indices and the
// staging arrays are windows into those streams, so the low bits address the
// macro and an address above the window is a real error: it is counted per
// port in window_faults rather than silently wrapped, in the same spirit as
// ot_a3_tile64's DETAIL_TILE_STAGING_UNDERRUN.  The array has no
// back-pressure, so a window fault cannot stall it; it marks the operation's
// result as unsound and the top reports the count.
//
// WRITES.  One 128-bit host/SDN write port, target-selected.  The array wins
// every conflict: a write offered in a cycle in which the addressed array is
// being read is refused, and refusals are counted.  This is the store-side
// half of the credit discipline ot_a3_tile64 keeps in stg_space; the credit
// itself belongs to the delivery network and is not modelled here.
// ---------------------------------------------------------------------------
module ot_a3_g2_array_staging (
    input  wire          clk,
    input  wire          rst_n,

    // -- LQ8 read ports (one cycle of latency, no back-pressure) --------
    input  wire          w_rd_en,
    input  wire [31:0]   w_rd_addr,
    output wire [127:0]  w_rd_data,
    input  wire          a_rd_en,
    input  wire [31:0]   a_rd_addr,
    output wire [63:0]   a_rd_data,
    input  wire          s_rd_en,
    input  wire [31:0]   s_rd_addr,
    output wire [31:0]   s_rd_data,
    input  wire          ws_rd_en,
    input  wire [31:0]   ws_rd_addr,
    output wire [63:0]   ws_rd_data,

    // -- host / store-delivery write port -------------------------------
    input  wire          host_we,
    input  wire [1:0]    host_sel,     // 0 weight ring, 1 activation,
                                       // 2 activation scale, 3 weight scale
    input  wire [9:0]    host_row,
    input  wire [127:0]  host_wdata,
    output wire          host_accept,

    // -- observation -----------------------------------------------------
    output reg  [31:0]   window_faults,
    output reg  [31:0]   write_refusals,
    output reg  [31:0]   weight_words_read
);
    // -- weight ring: two 512-row parts ganged in depth -------------------
    wire         w_bank    = w_rd_addr[9];
    wire         w_beyond  = (w_rd_addr[31:10] != 22'd0);
    wire         host_w    = host_we && (host_sel == 2'd0);
    wire         w_busy    = w_rd_en;
    wire         w_hostok  = host_w && !w_busy;

    wire         wr0_ce    = (w_rd_en && !w_bank) || (w_hostok && !host_row[9]);
    wire         wr1_ce    = (w_rd_en &&  w_bank) || (w_hostok &&  host_row[9]);
    wire         wr0_we    = w_hostok && !host_row[9] && !w_rd_en;
    wire         wr1_we    = w_hostok &&  host_row[9] && !w_rd_en;
    wire [8:0]   wr_addr   = w_rd_en ? w_rd_addr[8:0] : host_row[8:0];

    wire [127:0] wr0_rdata, wr1_rdata;
    reg          w_bank_q;
    assign w_rd_data = w_bank_q ? wr1_rdata : wr0_rdata;

    fakeram_512x128 stage_w0 (
        .clk(clk), .addr_in(wr_addr), .ce_in(wr0_ce), .we_in(wr0_we),
        .wd_in(host_wdata), .rd_out(wr0_rdata)
    );
    fakeram_512x128 stage_w1 (
        .clk(clk), .addr_in(wr_addr), .ce_in(wr1_ce), .we_in(wr1_we),
        .wd_in(host_wdata), .rd_out(wr1_rdata)
    );

    // -- activation window -------------------------------------------------
    wire       host_a   = host_we && (host_sel == 2'd1);
    wire       a_hostok = host_a && !a_rd_en;
    wire       a_ce     = a_rd_en || a_hostok;
    wire       a_we     = a_hostok;
    wire [7:0] a_addr   = a_rd_en ? a_rd_addr[7:0] : host_row[7:0];
    wire       a_beyond = (a_rd_addr[31:8] != 24'd0);

    fakeram_256x64 stage_a (
        .clk(clk), .addr_in(a_addr), .ce_in(a_ce), .we_in(a_we),
        .wd_in(host_wdata[63:0]), .rd_out(a_rd_data)
    );

    // -- activation E8M0 scale table --------------------------------------
    wire       host_s   = host_we && (host_sel == 2'd2);
    wire       s_hostok = host_s && !s_rd_en;
    wire       s_ce     = s_rd_en || s_hostok;
    wire       s_we     = s_hostok;
    wire [7:0] s_addr   = s_rd_en ? s_rd_addr[7:0] : host_row[7:0];
    wire       s_beyond = (s_rd_addr[31:8] != 24'd0);

    fakeram7_256x32 stage_s (
        .clk(clk), .addr_in(s_addr), .ce_in(s_ce), .we_in(s_we),
        .wd_in(host_wdata[31:0]), .rd_out(s_rd_data)
    );

    // -- weight E8M0 scale table ------------------------------------------
    wire       host_ws   = host_we && (host_sel == 2'd3);
    wire       ws_hostok = host_ws && !ws_rd_en;
    wire       ws_ce     = ws_rd_en || ws_hostok;
    wire       ws_we     = ws_hostok;
    wire [7:0] ws_addr   = ws_rd_en ? ws_rd_addr[7:0] : host_row[7:0];
    wire       ws_beyond = (ws_rd_addr[31:8] != 24'd0);

    fakeram_256x64 stage_ws (
        .clk(clk), .addr_in(ws_addr), .ce_in(ws_ce), .we_in(ws_we),
        .wd_in(host_wdata[63:0]), .rd_out(ws_rd_data)
    );

    assign host_accept = (host_w  && !w_rd_en)  || (host_a  && !a_rd_en) ||
                         (host_s  && !s_rd_en)  || (host_ws && !ws_rd_en);

    wire fault_now = (w_rd_en  && w_beyond)  || (a_rd_en  && a_beyond) ||
                     (s_rd_en  && s_beyond)  || (ws_rd_en && ws_beyond);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            w_bank_q          <= 1'b0;
            window_faults     <= 32'd0;
            write_refusals    <= 32'd0;
            weight_words_read <= 32'd0;
        end else begin
            if (w_rd_en)
                w_bank_q <= w_bank;
            if (fault_now)
                window_faults <= window_faults + 32'd1;
            if (host_we && !host_accept)
                write_refusals <= write_refusals + 32'd1;
            if (w_rd_en)
                weight_words_read <= weight_words_read + 32'd1;
        end
    end
endmodule
