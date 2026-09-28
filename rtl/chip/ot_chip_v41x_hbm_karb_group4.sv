`timescale 1ns/1ps
// Four-PC physical hierarchy: local request registers and grouped response buffers.
module ot_chip_v41x_hbm_karb_group4 #(
    parameter integer NPC  = 4,
    parameter integer AW   = 28,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer PIPE_OUT = 1,
    parameter integer PIPE_RSP = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // B: per pseudo-channel
    input  wire [NPC-1:0]       b_v,
    output wire [NPC-1:0]       b_rdy,
    input  wire [NPC*AW-1:0]    b_addr,
    input  wire [NPC*LENW-1:0]  b_len,
    input  wire [NPC*TAGW-1:0]  b_tag,
    input  wire [NPC-1:0]       b_we,
    input  wire [NPC*DW-1:0]    b_wdata,
    input  wire [NPC*DW/8-1:0]  b_wstrb,
    output wire [NPC-1:0]       b_wr_done,
    output wire [NPC-1:0]       b_rsp_v,
    input  wire [NPC-1:0]       b_rsp_rdy,
    output wire [NPC*TAGW-1:0]  b_rsp_tag,
    output wire [NPC*BEATW-1:0] b_rsp_beat,
    output wire [NPC*DW-1:0]    b_rsp_data,
    // K: one channel
    input  wire                 k_v,
    output wire                 k_rdy,
    input  wire [AW-1:0]        k_addr,
    input  wire [LENW-1:0]      k_len,
    input  wire [TAGW-1:0]      k_tag,
    input  wire                 k_we,
    input  wire [DW-1:0]        k_wdata,
    input  wire [DW/8-1:0]      k_wstrb,
    output wire                 k_wr_done,
    output wire                 k_rsp_v,
    input  wire                 k_rsp_rdy,
    output wire [TAGW-1:0]      k_rsp_tag,
    output wire [BEATW-1:0]     k_rsp_beat,
    output wire [DW-1:0]        k_rsp_data,
    // the stack
    output wire [NPC-1:0]       h_v,
    input  wire [NPC-1:0]       h_rdy,
    output wire [NPC*AW-1:0]    h_addr,
    output wire [NPC*LENW-1:0]  h_len,
    output wire [NPC*(TAGW+1)-1:0] h_tag,
    output wire [NPC-1:0]       h_we,
    output wire [NPC*DW-1:0]    h_wdata,
    output wire [NPC*DW/8-1:0]  h_wstrb,
    input  wire [NPC-1:0]       h_wr_done,
    input  wire [NPC-1:0]       r_v,
    output wire [NPC-1:0]       r_rdy,
    input  wire [NPC*(TAGW+1)-1:0] r_tag,
    input  wire [NPC*BEATW-1:0] r_beat,
    input  wire [NPC*DW-1:0]    r_data,
    // status
    output reg  [31:0]          k_grants,
    output reg  [31:0]          b_grants,
    output reg  [31:0]          contended
);
    // One four-PC physical group.  Its request register terminates the
    // long K broadcast before local address/data delivery.  A parent of eight
    // groups can pipeline that trunk separately without a flat 32-way mux.
    initial if (NPC != 4 || PIPE_OUT != 1 || PIPE_RSP != 1)
        $fatal(1, "group4 requires NPC=4, PIPE_OUT=1 and PIPE_RSP=1");
    function automatic [1:0] pc_of(input [AW-1:0] s);
        pc_of = 2'(((s >> 2) ^ (s >> 4) ^ (s >> 6)) & 3);
    endfunction
    reg in_v, in_we;
    reg [1:0] in_pc;
    reg [AW-1:0] in_addr;
    reg [LENW-1:0] in_len;
    reg [TAGW-1:0] in_tag;
    reg [DW-1:0] in_wdata;
    reg [DW/8-1:0] in_wstrb;
    wire [3:0] child_k_rdy, child_k_wr_done;
    wire [3:0] child_k_rsp_v, child_k_rsp_rdy;
    wire [4*TAGW-1:0] child_k_rsp_tag;
    wire [4*BEATW-1:0] child_k_rsp_beat;
    wire [4*DW-1:0] child_k_rsp_data;
    wire [31:0] kg [0:3], bg [0:3], ct [0:3];
    wire pop = in_v && child_k_rdy[in_pc];
    assign k_rdy = !in_v || pop;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            in_v <= 1'b0; in_we <= 1'b0; in_pc <= '0;
            in_addr <= '0; in_len <= '0; in_tag <= '0;
            in_wdata <= '0; in_wstrb <= '0;
        end else if (k_rdy) begin
            in_v <= k_v;
            if (k_v) begin
                in_pc <= pc_of(k_addr);
                in_addr <= k_addr; in_len <= k_len; in_tag <= k_tag;
                in_we <= k_we; in_wdata <= k_wdata; in_wstrb <= k_wstrb;
            end
        end
    genvar p;
    generate for (p = 0; p < 4; p = p + 1) begin : g_pc
        ot_chip_v41x_hbm_karb #(.NPC(1), .AW(AW), .TAGW(TAGW), .LENW(LENW),
                                 .BEATW(BEATW), .DW(DW), .PIPE_OUT(1)) u_local (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v[p]), .b_rdy(b_rdy[p]), .b_addr(b_addr[p*AW +: AW]),
            .b_len(b_len[p*LENW +: LENW]), .b_tag(b_tag[p*TAGW +: TAGW]),
            .b_we(b_we[p]), .b_wdata(b_wdata[p*DW +: DW]),
            .b_wstrb(b_wstrb[p*DW/8 +: DW/8]), .b_wr_done(b_wr_done[p]),
            .b_rsp_v(), .b_rsp_rdy(1'b0), .b_rsp_tag(), .b_rsp_beat(), .b_rsp_data(),
            .k_v(in_v && in_pc == 2'(p)), .k_rdy(child_k_rdy[p]),
            .k_addr(in_addr), .k_len(in_len), .k_tag(in_tag), .k_we(in_we),
            .k_wdata(in_wdata), .k_wstrb(in_wstrb), .k_wr_done(child_k_wr_done[p]),
            .k_rsp_v(child_k_rsp_v[p]), .k_rsp_rdy(1'b0),
            .k_rsp_tag(child_k_rsp_tag[p*TAGW +: TAGW]),
            .k_rsp_beat(child_k_rsp_beat[p*BEATW +: BEATW]),
            .k_rsp_data(child_k_rsp_data[p*DW +: DW]),
            .h_v(h_v[p]), .h_rdy(h_rdy[p]), .h_addr(h_addr[p*AW +: AW]),
            .h_len(h_len[p*LENW +: LENW]), .h_tag(h_tag[p*(TAGW+1) +: TAGW+1]),
            .h_we(h_we[p]), .h_wdata(h_wdata[p*DW +: DW]),
            .h_wstrb(h_wstrb[p*DW/8 +: DW/8]), .h_wr_done(h_wr_done[p]),
            // The group receive buffers own the HBM response handshake.
            .r_v(1'b0), .r_rdy(), .r_tag({(TAGW+1){1'b0}}),
            .r_beat({BEATW{1'b0}}), .r_data({DW{1'b0}}),
            .k_grants(kg[p]), .b_grants(bg[p]), .contended(ct[p]));
        assign b_rsp_v[p] = r_v[p] && !r_tag[p*(TAGW+1)+TAGW];
        assign b_rsp_tag[p*TAGW +: TAGW] = r_tag[p*(TAGW+1) +: TAGW];
        assign b_rsp_beat[p*BEATW +: BEATW] = r_beat[p*BEATW +: BEATW];
        assign b_rsp_data[p*DW +: DW] = r_data[p*DW +: DW];
    end endgenerate
    assign k_wr_done = |child_k_wr_done;
    ot_chip_v41x_hbm_rsp_pipe #(.NPC(4), .TAGW(TAGW), .BEATW(BEATW), .DW(DW), .NG(4)) u_rsp (
        .clk(clk), .rst_n(rst_n), .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag),
        .r_beat(r_beat), .r_data(r_data), .b_rsp_rdy(b_rsp_rdy),
        .k_rsp_rdy(k_rsp_rdy), .k_rsp_v(k_rsp_v), .k_rsp_tag(k_rsp_tag),
        .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data));
    always @(*) begin
        k_grants = kg[0] + kg[1] + kg[2] + kg[3];
        b_grants = bg[0] + bg[1] + bg[2] + bg[3];
        contended = ct[0] + ct[1] + ct[2] + ct[3];
    end
endmodule
