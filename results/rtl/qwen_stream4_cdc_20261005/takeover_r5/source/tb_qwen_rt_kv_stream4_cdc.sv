`timescale 1ns/1ps
// CDC variant (same module name; compile ONE of the bench tops): the backend is ot_qwen_hbm_stream4_cdc
// (the same 4-stack controllers, DRAM checker and backing array, on an EXTERNAL periodic hclk input,
// every per-PC crossing the hardened gray-pointer element ot_qwen_stream4_cdc_pc), driven by
// tb_qwen_rt_kv_stream4.cpp built with -DCDC (hclk period KVB_HFS fs, phase KVB_HPHASE fs).
// Standalone bench top (Verilator, driven by tb_qwen_rt_kv_stream4.cpp): the 4-stack KV service
// ot_qwen_rt_kv_stream4_service and ot_qwen_hbm_stream4_ack (NSTK stacks, 32 * NSTK PCs), with the
// kv_free / early_go / posted_wb straps as inputs.  Derived from tb_qwen_rt_kv_stream.sv:
// the HBM_STREAM KV
// service (ot_qwen_rt_kv_stream_service) and the streaming HBM (ot_qwen_hbm_stream_ack: the
// near-HBM stream controller + DRAM checker, write-done), and the 1,536 tiles' KV slices as
// behavioural registered-port memories (the hardened tile's kvw_* register, then the
// masked SRAM write).  The C++ host preloads HBM, writes token K/V like the stream unit,
// and checks every slice word and the written-back HBM sectors against an independent map.
module tb_qwen_rt_kv_stream4 #(
    parameter integer NSTK = 4,
    parameter integer NPC = 32 * NSTK,
    parameter integer KV_IDEAL = 0,
    parameter integer LAYERS = 2,
    parameter integer WBW = 1,
    parameter integer PHASE = 0,
    parameter integer PULLIN = 0,
    parameter integer SYNC = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [17:0]       pos,
    input  wire [7:0]        layer,
    input  wire [7:0]        nx_layer,
    input  wire [17:0]       pos_hint,
    input  wire              kv_free,
    input  wire              early_go,
    input  wire              posted_wb,
    output wire              wb_busy,
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
    output wire [31:0]       st_kvok_low_desc, st_drain_low, st_wr_lat_max, st_fill_exposed,
    input  wire              hclk
);
    localparam integer NT = 1536;
    wire [NT-1:0] kvw_ce; wire [NT*7-1:0] kvw_addr; wire [NT*512-1:0] kvw_data, kvw_mask;
    wire hd_v, hd_rdy, h_go; wire [18:0] hd_row; wire [10:0] hd_n;
    wire [NPC-1:0] hl_v, hl_pop, hw_v, hw_room, hwd_v;
    wire [NPC*17-1:0] hl_sec; wire [NPC*8-1:0] hl_row; wire [NPC*256-1:0] hl_data, hw_data;
    wire [NPC*24-1:0] hw_sec; wire [NPC*9-1:0] hw_tag, hwd_tag;
    wire svc_fault, hbm_fault; wire [15:0] svc_code, hbm_code;
    ot_qwen_rt_kv_stream4_service #(.NSTK(NSTK), .NPC(NPC), .KV_IDEAL(KV_IDEAL), .WBW(WBW)) u_svc (
        .clk(clk), .rst_n(rst_n), .start(start), .ideal_in(1'b0), .pos(pos), .layer(layer),
        .nx_layer(nx_layer), .pos_hint(pos_hint),
        .kv_free(kv_free), .early_go_in(early_go), .posted_wb_in(posted_wb), .wb_busy(wb_busy),
        .kvd_v(kvd_v), .kvd_pos(kvd_pos), .kvd_kindk(1'b0), .kv_ok(kv_ok),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .kv_write_drained(kv_write_drained),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask),
        .d_v(hd_v), .d_rdy(hd_rdy), .d_row(hd_row), .d_n(hd_n), .go(h_go),
        .l_v(hl_v), .l_sec(hl_sec), .l_row(hl_row), .l_data(hl_data), .l_pop(hl_pop),
        .w_v(hw_v), .w_sec(hw_sec), .w_data(hw_data), .w_tag(hw_tag), .w_room(hw_room), .wd_v(hwd_v), .wd_tag(hwd_tag),
        .fault(svc_fault), .fault_code(svc_code), .st_fill_cycles(st_fill_cycles), .st_fill_sectors(st_fill_sectors),
        .st_wr_sectors(st_wr_sectors), .st_rsp_stall(st_rsp_stall), .st_kvok_low_desc(st_kvok_low_desc),
        .st_drain_low(st_drain_low), .st_wr_lat_max(st_wr_lat_max), .st_fill_exposed(st_fill_exposed));
    ot_qwen_hbm_stream4_cdc #(.NSTK(NSTK), .NPC(NPC), .MEM_WORDS(LAYERS * 131072), .TAGW(9), .PHASE(PHASE), .PULLIN(PULLIN),
        .SYNC(SYNC)) u_hbm (
        .clk(clk), .rst_n(rst_n), .hclk(hclk), .d_v(hd_v), .d_rdy(hd_rdy), .d_row(hd_row), .d_n(hd_n), .go(h_go),
        .l_v(hl_v), .l_sec(hl_sec), .l_row(hl_row), .l_data(hl_data), .l_pop(hl_pop),
        .w_v(hw_v), .w_sec(hw_sec), .w_data(hw_data), .w_tag(hw_tag), .w_room(hw_room), .wd_v(hwd_v), .wd_tag(hwd_tag),
        .fault(hbm_fault), .fault_code(hbm_code));
    assign fault = svc_fault | hbm_fault;
    assign fault_code = svc_code | (hbm_fault ? 16'h8000 : 16'h0);
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
