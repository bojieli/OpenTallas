`timescale 1ps/1fs
// Released-column bound: at most4 of24 columns intersect any one home.
// This successor compacts actual hash descriptors into4 home-local slots; all
// eight homes execute those slots concurrently and preserve global list tags.
// Source-bound interval proof is mandatory; generic arbitrary24-on-one-home
// input is not this released programme and faults on the fifth descriptor.
// One real Engram home: source-owned hash descriptors, fixed core issue slots,
// finite real CDCs, arbitrary native DRAM bank/refresh controller, actual SRAM.
// Runtime service variability is contained at this external-HBM staging boundary;
// done is a fixed compiler edge and never waits for a late return.
module ot_hbm_engram_home_fetch_shared_vehicle #(
    parameter integer HOME_RANK=0, SLOT_EDGES=1, GUARD_EDGES=8192, LOCAL_READ=0
)(
    input wire core_clk,hbm_clk,rst_n,epoch_begin,
    input wire descriptor_v,input wire[6:0]descriptor_rank,input wire[4:0]descriptor_index,input wire[36:0]descriptor_address,
    input wire fetch_start,
    input wire read_v,input wire[4:0]read_row,input wire[3:0]read_sector,
    input wire local_read_v,input wire[1:0]local_read_slot,input wire[3:0]local_read_sector,
    output reg slot_response_v,slot_response_present,output reg[4:0]slot_response_row,output reg[3:0]slot_response_sector,
    output wire raw_v,output wire[4:0]raw_row,output wire[3:0]raw_sector,output wire[255:0]raw_data,
    output reg done,output wire fault,
    output wire[3:0]owned_slot_valid,output wire[19:0]owned_slot_global_row,output wire[2:0]owned_row_count,
    output wire[31:0]row_v,output wire[95:0]row_op,output wire[159:0]row_bank,output wire[607:0]row_row,
    output wire[31:0]col_v,col_we,output wire[159:0]col_bank,col_col,
    output wire[8191:0]col_data,output wire[1023:0]col_strb,
    input wire[31:0]dram_rvalid,input wire[8191:0]dram_rdata
);
    wire[31:0]k_v,k_rdy,k_we,kr_v,kr_rdy,k_wr_done;
    wire[959:0]k_addr;wire[127:0]k_len,kr_beat;wire[543:0]k_tag,kr_tag;
    wire[8191:0]k_wdata,kr_data;wire[1023:0]k_wstrb;wire controller_fault;
    ot_hbm_engram_home_client #(.HOME_RANK(HOME_RANK),.SLOT_EDGES(SLOT_EDGES),.GUARD_EDGES(GUARD_EDGES),.LOCAL_READ(LOCAL_READ)) client(.*);
    ot_hbm_svc_native_sector_guarded_stack controller(.clk(hbm_clk),.pc_clk({32{hbm_clk}}),.rst_n(rst_n),
        .k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
        .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.k_wr_done(k_wr_done),
        .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
        .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
        .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(controller_fault));
endmodule
