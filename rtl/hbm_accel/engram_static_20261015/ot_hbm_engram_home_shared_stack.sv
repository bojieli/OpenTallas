`timescale 1ps/1fs
// One physical stack owner shared by Engram (client0), DMA and prefetch.
// pc_clk roots must be synchronous same-phase HBM clocks. No client has private bank/REF state.
// Timing qualification requires an exclusive fixed Engram reservation and prior-client drain.
module ot_hbm_engram_home_shared_stack #(
    parameter integer HOME_RANK=0, SLOT_EDGES=1, GUARD_EDGES=8192, LOCAL_READ=0
)(
    input wire core_clk,hbm_clk,rst_n,epoch_begin,
    input wire[31:0]pc_clk,
    input wire engram_reservation,output wire[31:0]owner_idle,
    input wire[63:0]other_k_v,other_k_we,output wire[63:0]other_k_rdy,
    input wire[1919:0]other_k_addr,input wire[255:0]other_k_len,input wire[1087:0]other_k_tag,
    input wire[16383:0]other_k_wdata,input wire[2047:0]other_k_wstrb,
    output wire[63:0]other_kr_v,input wire[63:0]other_kr_rdy,
    output wire[1087:0]other_kr_tag,output wire[255:0]other_kr_beat,output wire[16383:0]other_kr_data,
    output wire[63:0]other_k_wr_done,
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
    wire[8191:0]k_wdata,kr_data;wire[1023:0]k_wstrb;wire controller_fault,master_fault,mux_fault;
    reg reserved_q,reservation_fault;
    // Reservation changes are same-phase HBM controls from the fixed calendar.
    // Counts cover every accepted native read beat until consumption and each
    // write until its actual physical posted completion. Open/REF state is retained.
    always @(posedge hbm_clk or negedge rst_n)begin
        if(!rst_n)begin reserved_q<=0;reservation_fault<=0;end
        else begin
            reserved_q<=engram_reservation;
            if(engram_reservation && !reserved_q && owner_idle!=32'hffffffff)reservation_fault<=1;
            if(!engram_reservation && reserved_q && (owner_idle!=32'hffffffff || |k_v))reservation_fault<=1;
            if(!engram_reservation && |k_v)reservation_fault<=1;
        end
    end
    assign controller_fault=master_fault|mux_fault|reservation_fault;
    ot_hbm_engram_home_client #(.HOME_RANK(HOME_RANK),.SLOT_EDGES(SLOT_EDGES),.GUARD_EDGES(GUARD_EDGES),.LOCAL_READ(LOCAL_READ)) client(.*);
    wire[31:0]m_k_v,m_k_rdy,m_k_we,m_kr_v,m_kr_rdy,m_k_wr_done;
    wire[959:0]m_k_addr;wire[127:0]m_k_len,m_kr_beat;wire[543:0]m_k_tag,m_kr_tag;
    wire[8191:0]m_k_wdata,m_kr_data;wire[1023:0]m_k_wstrb;
    ot_hbm_native_client_mux mux(.pc_clk(pc_clk),.rst_n(rst_n),
        .c_k_v({other_k_v & {64{!engram_reservation}},k_v & {32{engram_reservation}}}),.c_k_rdy({other_k_rdy,k_rdy}),.c_k_we({other_k_we,k_we}),
        .c_k_addr({other_k_addr,k_addr}),.c_k_len({other_k_len,k_len}),.c_k_tag({other_k_tag,k_tag}),
        .c_k_wdata({other_k_wdata,k_wdata}),.c_k_wstrb({other_k_wstrb,k_wstrb}),
        .c_kr_v({other_kr_v,kr_v}),.c_kr_rdy({other_kr_rdy,kr_rdy}),.c_kr_tag({other_kr_tag,kr_tag}),
        .c_kr_beat({other_kr_beat,kr_beat}),.c_kr_data({other_kr_data,kr_data}),.c_k_wr_done({other_k_wr_done,k_wr_done}),
        .k_v(m_k_v),.k_rdy(m_k_rdy),.k_we(m_k_we),.k_addr(m_k_addr),.k_len(m_k_len),.k_tag(m_k_tag),
        .k_wdata(m_k_wdata),.k_wstrb(m_k_wstrb),.kr_v(m_kr_v),.kr_rdy(m_kr_rdy),.kr_tag(m_kr_tag),
        .kr_beat(m_kr_beat),.kr_data(m_kr_data),.k_wr_done(m_k_wr_done),.fault(mux_fault),.owner_idle(owner_idle));
    ot_hbm_svc_native_sector_owned_stack #(.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1),.COLUMN_CLOSE_GUARD(1)) controller(.clk(hbm_clk),.pc_clk(pc_clk),.rst_n(rst_n),
        .k_v(m_k_v),.k_rdy(m_k_rdy),.k_we(m_k_we),.k_addr(m_k_addr),.k_len(m_k_len),.k_tag(m_k_tag),.k_wdata(m_k_wdata),.k_wstrb(m_k_wstrb),
        .kr_v(m_kr_v),.kr_rdy(m_kr_rdy),.kr_tag(m_kr_tag),.kr_beat(m_kr_beat),.kr_data(m_kr_data),.k_wr_done(m_k_wr_done),
        .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
        .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
        .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(master_fault));
endmodule
