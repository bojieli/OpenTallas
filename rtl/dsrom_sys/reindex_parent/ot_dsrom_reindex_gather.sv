module ot_dsrom_reindex_gather #(
    parameter integer OPT_PARENT=0,
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer AW   = 28,
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer DF   = 8,
    parameter integer LSW  = 0,          // list slots = 2^LSW (0: the as-built single list)
    localparam integer SLW = (LSW > 0) ? LSW : 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 lw_v,
    input  wire [SLW-1:0]       lw_slot,
    input  wire [LMW-1:0]       lw_addr,
    input  wire [LBW-1:0]       lw_blk,
    input  wire                 cmd_v,
    input  wire [SLW-1:0]       cmd_slot,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,
    input  wire [LMW:0]         cmd_n,
    output wire                 busy,
    output wire                 fault,
    output wire [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output wire [NPC*AW-1:0]    req_addr,
    output wire [NPC*LENW-1:0]  req_len,
    output wire [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*DW-1:0]    rsp_data,
    output wire                 o_valid,
    input  wire                 o_ready,
    output wire [15:0]          o_kv,
    output wire [16*544-1:0]    o_key,
    output wire [2*LBW-1:0]     o_blk,
    output reg  [47:0]          cnt_keys_streamed,
    output reg  [47:0]          cnt_hbm_beats
);
 generate if(OPT_PARENT!=0)begin:g_parent
 ot_dsrom_reindex_gather_parent #(.NPC(NPC),.WB(WB),.AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW),.LBW(LBW),.LMW(LMW),.DF(DF),.LSW(LSW)) u_parent (.clk(clk),.rst_n(rst_n),.lw_v(lw_v),.lw_slot(lw_slot),.lw_addr(lw_addr),.lw_blk(lw_blk),.cmd_v(cmd_v),.cmd_slot(cmd_slot),.cmd_base(cmd_base),.cmd_skip(cmd_skip),.cmd_n(cmd_n),.busy(busy),.fault(fault),.req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),.req_len(req_len),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),.o_valid(o_valid),.o_ready(o_ready),.o_kv(o_kv),.o_key(o_key),.o_blk(o_blk),.cnt_keys_streamed(cnt_keys_streamed),.cnt_hbm_beats(cnt_hbm_beats));
 end else begin:g_asbuilt
 ot_hdc_v41x_idx_kgather_ps #(.NPC(NPC),.WB(WB),.AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW),.LBW(LBW),.LMW(LMW),.DF(DF),.LSW(LSW)) u_asbuilt (.clk(clk),.rst_n(rst_n),.lw_v(lw_v),.lw_slot(lw_slot),.lw_addr(lw_addr),.lw_blk(lw_blk),.cmd_v(cmd_v),.cmd_slot(cmd_slot),.cmd_base(cmd_base),.cmd_skip(cmd_skip),.cmd_n(cmd_n),.busy(busy),.fault(fault),.req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),.req_len(req_len),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),.o_valid(o_valid),.o_ready(o_ready),.o_kv(o_kv),.o_key(o_key),.o_blk(o_blk),.cnt_keys_streamed(cnt_keys_streamed),.cnt_hbm_beats(cnt_hbm_beats));
 end endgenerate
endmodule
