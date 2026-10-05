`timescale 1ns/1ps
// Standalone bench top (Verilator, driven by tb_qwen_rt_kv_service.cpp): the REAL_MEM KV
// service and the HBM timing model with write-done, and the 1,536 tiles' KV slices as
// behavioural registered-port memories (the hardened tile's kvw_* register, then the
// masked SRAM write).  The C++ host preloads HBM, writes token K/V like the stream unit,
// and checks every slice word and the written-back HBM sectors against an independent map.
module tb_qwen_rt_kv_service #(
    parameter integer NPC = 32,
    parameter integer KV_IDEAL = 0,
    parameter integer LAYERS = 2,
    parameter integer LKA = 512
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [17:0]       pos,
    input  wire [7:0]        layer,
    input  wire              kvd_v,
    input  wire [17:0]       kvd_pos,
    output wire              kv_ok,
    input  wire [63:0]       kv_we,
    input  wire [64*24-1:0]  kv_waddr,
    input  wire [64*32-1:0]  kv_wdata,
    output wire              kv_write_drained,
    output wire              fault,
    output wire [15:0]       fault_code,
    output wire [31:0]       st_fill_cycles, st_fill_sectors, st_wr_sectors, st_rsp_stall,
    output wire [31:0]       st_kvok_low_desc, st_drain_low, st_wr_lat_max
);
    localparam integer NT = 1536;
    wire [NT-1:0] kvw_ce; wire [NT*7-1:0] kvw_addr; wire [NT*512-1:0] kvw_data, kvw_mask;
    wire [NPC-1:0] h_pc_room;
    wire h_req_v, h_req_rdy, h_req_we; wire [23:0] h_req_addr; wire [4:0] h_req_len; wire [10:0] h_req_tag;
    wire [255:0] h_req_wdata; wire [NPC-1:0] h_rsp_v, h_rsp_rdy, h_rsp_wr; wire [NPC*11-1:0] h_rsp_tag;
    wire [NPC*4-1:0] h_rsp_beat; wire [NPC*256-1:0] h_rsp_data;
    ot_qwen_rt_kv_fill_service #(.NPC(NPC), .KV_IDEAL(KV_IDEAL), .NRD(256), .LKA(LKA)) u_svc (
        .clk(clk), .rst_n(rst_n), .start(start), .ideal_in(1'b0), .pos(pos), .layer(layer),
        .kvd_v(kvd_v), .kvd_pos(kvd_pos), .kvd_kindk(1'b0), .kv_ok(kv_ok),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .kv_write_drained(kv_write_drained),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask),
        .h_req_v(h_req_v), .h_req_rdy(h_req_rdy), .h_pc_room(h_pc_room), .h_req_we(h_req_we), .h_req_addr(h_req_addr),
        .h_req_len(h_req_len), .h_req_tag(h_req_tag), .h_req_wdata(h_req_wdata),
        .h_rsp_v(h_rsp_v), .h_rsp_rdy(h_rsp_rdy), .h_rsp_tag(h_rsp_tag), .h_rsp_beat(h_rsp_beat),
        .h_rsp_data(h_rsp_data), .h_rsp_wr(h_rsp_wr),
        .fault(fault), .fault_code(fault_code), .st_fill_cycles(st_fill_cycles), .st_fill_sectors(st_fill_sectors),
        .st_wr_sectors(st_wr_sectors), .st_rsp_stall(st_rsp_stall), .st_kvok_low_desc(st_kvok_low_desc),
        .st_drain_low(st_drain_low), .st_wr_lat_max(st_wr_lat_max));
    ot_qwen_hbm_model_ack #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(LAYERS * 131072), .TAGW(11), .LENW(5), .BEATW(4),
                            .CLK_PS(833), .PC_RDY(1), .WR_ACK(1)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(h_req_v), .req_rdy(h_req_rdy), .pc_room(h_pc_room),
        .req_we(h_req_we), .req_addr(h_req_addr), .req_len(h_req_len), .req_tag(h_req_tag), .req_wdata(h_req_wdata),
        .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy), .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat), .rsp_data(h_rsp_data),
        .rsp_wr(h_rsp_wr));
    // tile slices: the hardened tile's registered kvw port, then the masked write
    reg [511:0] slice [0:NT-1][0:127] /*verilator public_flat_rw*/;
    reg [NT-1:0] ce_q; reg [6:0] a_q [0:NT-1]; reg [511:0] d_q [0:NT-1]; reg [511:0] m_q [0:NT-1];
    integer i;
    always @(posedge clk) begin
        for (i = 0; i < NT; i = i + 1) begin
            ce_q[i] <= rst_n && kvw_ce[i];
            if (kvw_ce[i]) begin a_q[i] <= kvw_addr[i*7 +: 7]; d_q[i] <= kvw_data[i*512 +: 512]; m_q[i] <= kvw_mask[i*512 +: 512]; end
            if (ce_q[i]) slice[i][a_q[i]] <= (slice[i][a_q[i]] & ~m_q[i]) | (d_q[i] & m_q[i]);
        end
    end
endmodule
