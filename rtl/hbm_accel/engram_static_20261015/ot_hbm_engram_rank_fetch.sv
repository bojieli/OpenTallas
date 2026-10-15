`timescale 1ps/1fs
// Explicit rank-local target124 candidate. Every instantiated home has its own
// real programme SRAM and full48-column hash; no cross-rank descriptor/start wires.
// HOST cfg/C10/CID/context/reservation delivery are real input boundaries, not
// qualified distributed producers. Context events restore prior compressed-token
// history while the local programme is idle; their descriptor outputs are discarded.
// All hash column clocks are 1:1 same-phase with core_clk, all pc_clk with hbm_clk.
module ot_hbm_engram_rank_fetch #(
    parameter integer HOME_RANK=0,SLOT_EDGES=1,GUARD_EDGES=8192,LOCAL_READ=1,
    parameter integer FETCH_EDGES=18944
)(
    input wire core_clk,hbm_clk,rst_n,input wire[5:0]hash_column_clk,input wire[31:0]pc_clk,
    input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
    input wire desc_v,input wire[9:0]desc_base,desc_limit,input wire[15:0]desc_loops,input wire launch_v,
    input wire token_v,input wire[16:0]token_cid,input wire token_first,
    input wire context_v,input wire[16:0]context_cid,input wire context_first,
    input wire engram_reservation,output wire[31:0]owner_idle,
    input wire[63:0]other_k_v,other_k_we,output wire[63:0]other_k_rdy,
    input wire[1919:0]other_k_addr,input wire[255:0]other_k_len,input wire[1087:0]other_k_tag,
    input wire[16383:0]other_k_wdata,input wire[2047:0]other_k_wstrb,
    output wire[63:0]other_kr_v,input wire[63:0]other_kr_rdy,
    output wire[1087:0]other_kr_tag,output wire[255:0]other_kr_beat,output wire[16383:0]other_kr_data,
    output wire[63:0]other_k_wr_done,
    input wire read_v,input wire[4:0]read_row,input wire[3:0]read_sector,
    input wire local_read_v,input wire[1:0]local_read_slot,input wire[3:0]local_read_sector,
    output wire slot_response_v,slot_response_present,output wire[4:0]slot_response_row,output wire[3:0]slot_response_sector,
    output wire raw_v,output wire[4:0]raw_row,output wire[3:0]raw_sector,output wire[255:0]raw_data,
    output wire done,fault,output wire configured,programme_busy,programme_done,programme_fault,
    output wire programme_epoch,programme_fetch,programme_hash_v,programme_hash_first,output wire[16:0]programme_hash_cid,
    output wire hash_done,hash_fault,
    output wire[1:0]request_valid,output wire[13:0]request_rank,output wire[73:0]request_address,
    output wire[51:0]request_local_row,output wire[9:0]request_staging_slot,request_list_index,output wire[39:0]gather_slot_id,
    output wire[3:0]owned_slot_valid,output wire[19:0]owned_slot_global_row,output wire[2:0]owned_row_count,
    output wire[31:0]row_v,output wire[95:0]row_op,output wire[159:0]row_bank,output wire[607:0]row_row,
    output wire[31:0]col_v,col_we,output wire[159:0]col_bank,col_col,output wire[8191:0]col_data,output wire[1023:0]col_strb,
    input wire[31:0]dram_rvalid,input wire[8191:0]dram_rdata
);
    localparam integer LAYER=(HOME_RANK>=8)?1:0;
    localparam[7:0]LOCAL_PARTICIPANT=8'b1<<(HOME_RANK%8);
    wire home_fault;reg local_fault,local_complete;
    // This rank owns ONE participant. The other seven barrier positions are
    // statically inactive neutral AND terms; they do not represent remote status.
    // Retain actual local completion until EPOCH so a later programme fence does
    // not depend on coinciding with a one-edge local done pulse.
    wire[7:0]local_done_vector=(~LOCAL_PARTICIPANT)|({8{done|local_complete}}&LOCAL_PARTICIPANT);
    wire[7:0]local_fault_vector={8{home_fault|hash_fault|local_fault}}&LOCAL_PARTICIPANT;
    ot_hbm_engram_fetch_program #(.FETCH_EDGES(FETCH_EDGES)) programme(
        .clk_control(core_clk),.clk_mem(core_clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .token_v(token_v),.token_cid(token_cid),.token_first(token_first),.home_done(local_done_vector),.home_fault(local_fault_vector),
        .configured(configured),.init_busy(),.busy(programme_busy),.done(programme_done),.fault(programme_fault),
        .epoch_begin(programme_epoch),.hash_v(programme_hash_v),.hash_first(programme_hash_first),.fetch_start(programme_fetch),.hash_cid(programme_hash_cid),
        .instruction_v(),.instruction(),.instruction_pc());
    (* keep_hierarchy = "yes", keep = "true" *) ot_hbm_engram_hash_home_clock_roots hash(
        .clk(core_clk),.clk_columns(hash_column_clk),.rst_n(rst_n),.in_valid(context_v|programme_hash_v),
        .in_first(programme_hash_v?programme_hash_first:context_first),.in_cid(programme_hash_v?programme_hash_cid:context_cid),
        .request_valid(request_valid),.request_rank(request_rank),.request_address(request_address),.request_local_row(request_local_row),
        .request_staging_slot(request_staging_slot),.gather_slot_id(gather_slot_id),.request_list_index(request_list_index),.done(hash_done),.fault(hash_fault));
    always @(posedge core_clk or negedge rst_n)begin
        if(!rst_n)begin local_fault<=0;local_complete<=0;end
        else begin
            if(programme_epoch)local_complete<=0;
            else if(done)local_complete<=1;
            if((context_v&&programme_busy) || (programme_busy&&(HOME_RANK<0 || HOME_RANK>15)))local_fault<=1;
        end
    end
    wire descriptor_v=programme_busy&&request_valid[LAYER];
    wire[6:0]descriptor_rank=request_rank[LAYER*7+:7];
    wire[4:0]descriptor_index=request_list_index[LAYER*5+:5];
    wire[36:0]descriptor_address=request_address[LAYER*37+:37];
    wire epoch_begin=programme_epoch,fetch_start=programme_fetch;
    ot_hbm_engram_home_shared_stack #(.HOME_RANK(HOME_RANK),.SLOT_EDGES(SLOT_EDGES),.GUARD_EDGES(GUARD_EDGES),.LOCAL_READ(LOCAL_READ)) home(
        .core_clk(core_clk),.hbm_clk(hbm_clk),.pc_clk(pc_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.engram_reservation(engram_reservation),.owner_idle(owner_idle),
        .other_k_v(other_k_v),.other_k_we(other_k_we),.other_k_rdy(other_k_rdy),.other_k_addr(other_k_addr),.other_k_len(other_k_len),.other_k_tag(other_k_tag),.other_k_wdata(other_k_wdata),.other_k_wstrb(other_k_wstrb),
        .other_kr_v(other_kr_v),.other_kr_rdy(other_kr_rdy),.other_kr_tag(other_kr_tag),.other_kr_beat(other_kr_beat),.other_kr_data(other_kr_data),.other_k_wr_done(other_k_wr_done),
        .descriptor_v(descriptor_v),.descriptor_rank(descriptor_rank),.descriptor_index(descriptor_index),.descriptor_address(descriptor_address),.fetch_start(fetch_start),
        .read_v(read_v),.read_row(read_row),.read_sector(read_sector),.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),
        .slot_response_v(slot_response_v),.slot_response_present(slot_response_present),.slot_response_row(slot_response_row),.slot_response_sector(slot_response_sector),
        .raw_v(raw_v),.raw_row(raw_row),.raw_sector(raw_sector),.raw_data(raw_data),.done(done),.fault(home_fault),
        .owned_slot_valid(owned_slot_valid),.owned_slot_global_row(owned_slot_global_row),.owned_row_count(owned_row_count),
        .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
        .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
    assign fault=home_fault|programme_fault|hash_fault|local_fault;
endmodule
