`timescale 1ns/1ps
// New memory component only. The passed nearHBM simulator is linked unchanged.
// REAL_MEM service and actual four HBM timing/WR_ACK models, plus the exact
// registered tile SRAM write path from ot_qwen_rom_tile_w12 (no tile arithmetic).
module ot_qwen_nearhbm_realmem_tb(
    input wire clk,rst_n,start,input wire [17:0] pos,input wire [7:0] layer,
    input wire [63:0] kv_we,input wire [64*24-1:0] kv_waddr,input wire [64*32-1:0] kv_wdata,
    input wire [31:0] row_valid,row_v,row_g,input wire [32*13-1:0] row_t,
    output wire [31:0] row_rsp_valid,output wire [32*1024-1:0] row_rsp_data,
    output wire kv_ok,kv_write_drained,fault,row_drained,
    output wire [15:0] kv_fault_code,
    output wire [127:0] rows_retired,read_bursts,
    output wire [31:0] st_fill_cycles,st_fill_sectors,st_wr_sectors,st_wr_lat_max,
    input wire probe_re,input wire [10:0] probe_tile,input wire [6:0] probe_addr,
    output wire [511:0] probe_data
);
    wire [1535:0] kvw_ce;wire [1536*7-1:0] kvw_addr;wire [1536*512-1:0] kvw_data,kvw_mask;
    wire [3:0] mv,mr,mw;wire [95:0] ma;wire [19:0] ml;wire [51:0] mt;wire [1023:0] md;
    wire [127:0] pv,pr,pw,room;wire [128*13-1:0] pt;wire [511:0] pb;wire [128*256-1:0] pd;
    ot_qwen_nearhbm_realmem_service #(.ENABLE(1)) mem_service(
        .clk(clk),.rst_n(rst_n),.start(start),.pos(pos),.layer(layer),
        .kvd_v(1'b0),.kvd_kindk(1'b0),.kvd_pos(pos),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_ok(kv_ok),.kv_write_drained(kv_write_drained),.kvw_ce(kvw_ce),.kvw_addr(kvw_addr),.kvw_data(kvw_data),.kvw_mask(kvw_mask),
        .row_valid(row_valid),.row_v(row_v),.row_g(row_g),.row_t(row_t),.row_rsp_valid(row_rsp_valid),.row_rsp_data(row_rsp_data),
        .m_req_v(mv),.m_req_ready(mr),.m_req_we(mw),.m_req_addr(ma),.m_req_len(ml),.m_req_tag(mt),.m_req_wdata(md),
        .m_pc_room(room),.m_rsp_v(pv),.m_rsp_ready(pr),.m_rsp_wr(pw),.m_rsp_tag(pt),.m_rsp_beat(pb),.m_rsp_data(pd),
        .fault(fault),.kv_fault_code(kv_fault_code),.row_drained(row_drained),.rows_retired(rows_retired),.read_bursts(read_bursts),
        .st_fill_cycles(st_fill_cycles),.st_fill_sectors(st_fill_sectors),.st_wr_sectors(st_wr_sectors),.st_rsp_stall(),
        .st_kvok_low_desc(),.st_drain_low(),.st_wr_lat_max(st_wr_lat_max));
    genvar s,t,h;
    for(s=0;s<4;s=s+1)begin:g_hbm
        ot_qwen_hbm_model_ack #(.NPC(32),.AW(24),.DW(256),.MEM_WORDS(131072),.TAGW(13),.LENW(5),.BEATW(4),.CLK_PS(1024),.PC_RDY(1),.WR_ACK(1)) hbm(
            .clk(clk),.rst_n(rst_n),.req_v(mv[s]),.req_rdy(mr[s]),.pc_room(room[s*32 +: 32]),
            .req_we(mw[s]),.req_addr(ma[s*24 +: 24]),.req_len(ml[s*5 +: 5]),.req_tag(mt[s*13 +: 13]),.req_wdata(md[s*256 +: 256]),
            .rsp_v(pv[s*32 +: 32]),.rsp_rdy(pr[s*32 +: 32]),.rsp_wr(pw[s*32 +: 32]),.rsp_tag(pt[s*32*13 +: 32*13]),.rsp_beat(pb[s*32*4 +: 32*4]),.rsp_data(pd[s*32*256 +: 32*256]));
    end
    wire [511:0] slice_data[0:1535];
    for(t=0;t<1536;t=t+1)begin:g_tile
        reg ce;reg [6:0] a;reg [511:0] d,mask;
        always @(posedge clk or negedge rst_n)if(!rst_n)ce<=0;else ce<=kvw_ce[t];
        always @(posedge clk)begin a<=kvw_addr[t*7 +: 7];d<=kvw_data[t*512 +: 512];mask<=kvw_mask[t*512 +: 512];end
        for(h=0;h<2;h=h+1)begin:g_half
            ot_sram_1r1w_128x256_m1_r2c2 ram(.clk(clk),.r_ce_in(probe_re&&probe_tile==t),.r_addr_in(probe_addr),.rd_out(slice_data[t][h*256 +: 256]),
                .w_ce_in(ce),.w_addr_in(a),.wd_in(d[h*256 +: 256]),.w_mask_in(mask[h*256 +: 256]),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
        end
    end
    assign probe_data=slice_data[probe_tile];
endmodule
