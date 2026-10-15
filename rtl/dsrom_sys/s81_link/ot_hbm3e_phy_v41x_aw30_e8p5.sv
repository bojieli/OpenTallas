`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_hbm3e_phy_v41x_aw30_e8p5 (s81-die-rtl-bind 2026-10-14, die item F10 / HBM): the S81 die's HBM3E macro as REAL
// controller RTL over a behavioural PHY + device -- same name and ports as the hard-macro abstract
// physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/*_bb.v ('PHY + controller abstract').
//   K port: 32 pseudo-channels, each ot_s81_hbm_pcc (queue, open-page in-order scheduler, per-bank refresh, JEDEC-style
//           timers, response queue with read credits) driving ot_s81_hbm3e_dev_bm (the analog PHY + DRAM model, which
//           checks the timing); request len 4 b (sectors), tag 17 b, beat 4 b.
//   W port: the QE weight region, NPC_W = 8 pseudo-channels of the same controller (read only): a request {addr 24,
//           len 6, tag 10} goes to pseudo-channel addr[2:0] with in-channel sector addr[23:3] (+ i); w_room[p] = free
//           queue entries of p; responses per channel.  (The S81 die does not use the W port: weights are in the ROM
//           field; dsfd_ctrl keeps it idle.)
//   status: k_oor = sticky K request past the 2^30-sector stack, w_oor = sticky invalid W request (len 0), refreshes =
//           REFpb commands of the K channels, w_reads = sectors read on the W channels.
// ---------------------------------------------------------------------------------------------------------------
module ot_hbm3e_phy_v41x_aw30_e8p5 #(parameter integer MUT = 0, parameter integer TREFI_PB = 240) (
    input  wire clk,
    input  wire rst_n,
    input  wire [31:0] k_v,
    output wire [31:0] k_rdy,
    input  wire [959:0] k_addr,
    input  wire [127:0] k_len,
    input  wire [543:0] k_tag,
    input  wire [31:0] k_we,
    input  wire [8191:0] k_wdata,
    input  wire [1023:0] k_wstrb,
    output wire [31:0] k_wr_done,
    output wire [31:0] kr_v,
    input  wire [31:0] kr_rdy,
    output wire [543:0] kr_tag,
    output wire [127:0] kr_beat,
    output wire [8191:0] kr_data,
    input  wire w_v,
    output wire w_rdy,
    input  wire [23:0] w_addr,
    input  wire [5:0] w_len,
    input  wire [9:0] w_tag,
    output wire [7:0] w_room,
    output wire [7:0] wr_v,
    input  wire [7:0] wr_rdy,
    output wire [79:0] wr_tag,
    output wire [39:0] wr_beat,
    output wire [2047:0] wr_data,
    output reg  k_oor,
    output reg  w_oor,
    output wire [63:0] refreshes,
    output wire [31:0] w_reads
);
    wire [31:0] kref [0:31]; wire [31:0] krd [0:31]; wire [31:0] wref [0:7]; wire [31:0] wrd [0:7];
    wire [31:0] kviol, wviol;
    genvar p;
    generate for (p = 0; p < 32; p = p + 1) begin : g_k
        wire [2:0] c; wire [3:0] b; wire [20:0] r; wire [4:0] col; wire [255:0] wd, rd; wire [31:0] ws; wire rv; wire [3:0] vc;
        ot_s81_hbm_pcc #(.AW(30), .LENW(4), .TAGW(17), .BEATW(4), .TREFI_PB(TREFI_PB), .MUT(MUT)) u_c (.clk(clk), .rst_n(rst_n),
            .q_v(k_v[p]), .q_rdy(k_rdy[p]), .q_addr(k_addr[30*p +: 30]), .q_len(k_len[4*p +: 4]), .q_tag(k_tag[17*p +: 17]),
            .q_we(k_we[p]), .q_wdata(k_wdata[256*p +: 256]), .q_wstrb(k_wstrb[32*p +: 32]), .wr_done(k_wr_done[p]),
            .r_v(kr_v[p]), .r_rdy(kr_rdy[p]), .r_tag(kr_tag[17*p +: 17]), .r_beat(kr_beat[4*p +: 4]), .r_data(kr_data[256*p +: 256]),
            .d_cmd(c), .d_bank(b), .d_row(r), .d_col(col), .d_wdata(wd), .d_wstrb(ws), .d_rv(rv), .d_rdata(rd),
            .n_ref(kref[p]), .n_rd(krd[p]));
        ot_s81_hbm3e_dev_bm #(.AW(30)) u_d (.clk(clk), .rst_n(rst_n), .d_cmd(c), .d_bank(b), .d_row(r), .d_col(col),
            .d_wdata(wd), .d_wstrb(ws), .d_rv(rv), .d_rdata(rd), .viol(kviol[p]), .viol_code(vc));
    end endgenerate
    // W port: request to channel w_addr[2:0]
    wire [7:0] wq_rdy;
    assign w_rdy = wq_rdy[w_addr[2:0]] && w_len != 0;
    generate for (p = 0; p < 8; p = p + 1) begin : g_w
        wire [2:0] c; wire [3:0] b; wire [11:0] r; wire [4:0] col; wire [255:0] wd, rd; wire [31:0] ws; wire rv; wire [3:0] vc;
        wire wdn;
        ot_s81_hbm_pcc #(.AW(21), .LENW(6), .TAGW(10), .BEATW(5), .QD(8), .TREFI_PB(TREFI_PB), .MUT(MUT)) u_c (.clk(clk), .rst_n(rst_n),
            .q_v(w_v && w_addr[2:0] == p && w_len != 0), .q_rdy(wq_rdy[p]), .q_addr(w_addr[23:3]), .q_len(w_len), .q_tag(w_tag),
            .q_we(1'b0), .q_wdata(256'd0), .q_wstrb(32'd0), .wr_done(wdn),
            .r_v(wr_v[p]), .r_rdy(wr_rdy[p]), .r_tag(wr_tag[10*p +: 10]), .r_beat(wr_beat[5*p +: 5]), .r_data(wr_data[256*p +: 256]),
            .d_cmd(c), .d_bank(b), .d_row(r), .d_col(col), .d_wdata(wd), .d_wstrb(ws), .d_rv(rv), .d_rdata(rd),
            .n_ref(wref[p]), .n_rd(wrd[p]));
        ot_s81_hbm3e_dev_bm #(.AW(21)) u_d (.clk(clk), .rst_n(rst_n), .d_cmd(c), .d_bank(b), .d_row(r), .d_col(col),
            .d_wdata(wd), .d_wstrb(ws), .d_rv(rv), .d_rdata(rd), .viol(wviol[p]), .viol_code(vc));
        assign w_room[p] = wq_rdy[p];
    end endgenerate
    integer i;
    reg [63:0] rs; reg [31:0] wr_s;
    always @* begin
        rs = 64'd0; wr_s = 32'd0;
        for (i = 0; i < 32; i = i + 1) rs = rs + kref[i];
        for (i = 0; i < 8; i = i + 1) wr_s = wr_s + wrd[i];
    end
    assign refreshes = rs; assign w_reads = wr_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin k_oor <= 1'b0; w_oor <= 1'b0; end
        else begin
            for (i = 0; i < 32; i = i + 1)
                if (k_v[i] && k_rdy[i] && ({1'b0, k_addr[30*i +: 30]} + k_len[4*i +: 4] > 31'h40000000)) k_oor <= 1'b1;
            if (w_v && w_len == 0) w_oor <= 1'b1;
        end
endmodule
