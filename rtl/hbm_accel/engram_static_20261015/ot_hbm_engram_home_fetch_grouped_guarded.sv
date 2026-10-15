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
module ot_hbm_engram_home_fetch_grouped_guarded #(
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
    localparam integer TOTAL=36*SLOT_EDGES+GUARD_EDGES;
    reg[36:0]addresses[0:3];reg[4:0]indices[0:3];reg[3:0]present;
    reg[23:0]global_present;reg[2:0]owned_count;
    assign owned_slot_valid=present;assign owned_row_count=owned_count;
    for(genvar slot=0;slot<4;slot=slot+1)assign owned_slot_global_row[slot*5+:5]=indices[slot];
    reg active,sticky;reg[31:0]age;
    reg[15:0]slot_age;reg[4:0]row;reg[3:0]sector;
    reg[8:0]pending;
    wire req_issue=active && age<36*SLOT_EDGES && slot_age==0 && present[row];
    wire[36:0]req_address=addresses[row]+37'(sector*32);
    wire rq_full,rq_empty,rq_pop;
    wire[47:0]rq_data;
    wire req_end=active && age==36*SLOT_EDGES;
    wire req_we=fetch_start || req_end || req_issue;
    ot_hbm_accel_cdc_fifo #(.W(48),.AW(6))request_cdc(
        .wclk(core_clk),.wrst_n(rst_n),.we(req_we),.wdata({fetch_start?2'b10:req_end?2'b01:2'b00,req_address,indices[row],sector}),.full(rq_full),.rd_freed(),
        .rclk(hbm_clk),.rrst_n(rst_n),.re(rq_pop),.rdata(rq_data),.empty(rq_empty));
    wire[36:0]haddr=rq_data[45:9];wire[1:0]stack;wire[4:0]pc;wire[29:0]sa;wire mapped;
    ot_hbm_loader_kport_address #(.ENABLE(1))mapper(.byte_address(haddr),.stack_bytes(36'd22500000000),
        .stack(stack),.pc(pc),.sector_address(sa),.valid(mapped));
    reg[31:0]kv;wire[31:0]krdy,krv,krrdy,kwdone;
    reg[959:0]ka;reg[127:0]kl;reg[543:0]kt;wire[543:0]krt;wire[127:0]krb;wire[8191:0]krd;
    wire controller_fault;
    // Explicit physical-boundary buffer. Every PC can issue independently;
    // each PC exhausts one physical row before selecting another row.
    reg[29:0]request_address[0:35];reg[4:0]request_pc[0:35];reg[8:0]request_tag[0:35];
    reg[35:0]request_present;reg[5:0]request_count;
    reg collected,request_fault;reg[31:0]row_locked;reg[14:0]selected_row[0:31];
    reg[31:0]candidate_found;reg[5:0]candidate_index[0:31];reg[14:0]candidate_row[0:31];
    always @*begin
        kv=0;ka=0;kl=0;kt=0;candidate_found=0;
        for(integer p=0;p<32;p=p+1)begin
            candidate_index[p]=0;candidate_row[p]=selected_row[p];
            for(integer q=0;q<36;q=q+1)begin
                if(collected && request_present[q] && request_pc[q]==p && !candidate_found[p] &&
                   (!row_locked[p] || request_address[q][29:15]==selected_row[p]))begin
                    candidate_found[p]=1;candidate_index[p]=6'(q);candidate_row[p]=request_address[q][29:15];
                    kv[p]=1;ka[p*30+:30]=request_address[q];kl[p*4+:4]=1;kt[p*17+:17]={8'b0,request_tag[q]};
                end
            end
        end
    end
    assign rq_pop=!rq_empty;
    always @(posedge hbm_clk or negedge rst_n)begin
        if(!rst_n)begin
            request_present<=0;request_count<=0;collected<=0;request_fault<=0;row_locked<=0;
            for(integer p=0;p<32;p=p+1)selected_row[p]<=0;
        end else begin
            if(rq_pop)begin
                case(rq_data[47:46])
                  2'b10:begin
                    if(request_present!=0)request_fault<=1;
                    request_present<=0;request_count<=0;collected<=0;row_locked<=0;
                  end
                  2'b01:begin
                    if(collected)request_fault<=1;
                    collected<=1;
                  end
                  2'b00:begin
                    if(collected || request_count>=36 || !mapped || stack!=3)request_fault<=1;
                    else begin
                        request_address[request_count]<=sa;request_pc[request_count]<=pc;
                        request_tag[request_count]<=rq_data[8:0];request_present[request_count]<=1;
                        request_count<=request_count+1'b1;
                    end
                  end
                  default:request_fault<=1;
                endcase
            end
            for(integer p=0;p<32;p=p+1)begin
                if(candidate_found[p])begin
                    if(!row_locked[p])begin row_locked[p]<=1;selected_row[p]<=candidate_row[p];end
                    if(kv[p] && krdy[p])request_present[candidate_index[p]]<=0;
                end else if(collected)row_locked[p]<=0;
            end
        end
    end
    wire response_full,response_empty;
    reg[264:0]response_word;reg response_any;
    reg hbm_sticky;
    // One fair physical response per edge; other PC SRAM heads retain ownership.
    reg[4:0]response_rr,response_pc;
    reg[31:0]response_ready;
    integer arb_pc;
    always @*begin
        response_word=0;response_any=0;response_pc=response_rr;response_ready=0;
        for(integer off=0;off<32;off=off+1)begin
            arb_pc=(integer'(response_rr)+off)&31;
            if(!response_any && krv[arb_pc])begin
                response_word={krt[arb_pc*17+:9],krd[arb_pc*256+:256]};
                response_any=1;response_pc=5'(arb_pc);
                response_ready[arb_pc]=!response_full;
            end
        end
    end
    assign krrdy=response_ready;
    always @(posedge hbm_clk or negedge rst_n)begin
        if(!rst_n)response_rr<=0;
        else if(response_any && !response_full)response_rr<=response_pc+1'b1;
    end
    wire response_push=response_any && !response_full;
    wire[264:0]response_core;
    ot_hbm_accel_cdc_fifo #(.W(265),.AW(2))return_cdc(
        .wclk(hbm_clk),.wrst_n(rst_n),.we(response_push),.wdata(response_word),.full(response_full),.rd_freed(),
        .rclk(core_clk),.rrst_n(rst_n),.re(!response_empty),.rdata(response_core),.empty(response_empty));
    wire return_write=!response_empty;
    wire store_fault;
    reg[2:0]slot_vpipe,slot_present_pipe;
    reg[4:0]slot_row_pipe[0:2];reg[3:0]slot_sector_pipe[0:2];
    wire actual_read_v=LOCAL_READ ? local_read_v && present[local_read_slot] : read_v;
    wire[4:0]actual_read_row=LOCAL_READ ? indices[local_read_slot] : read_row;
    wire[3:0]actual_read_sector=LOCAL_READ ? local_read_sector : read_sector;
    always @(posedge core_clk or negedge rst_n)begin
        if(!rst_n)begin
            slot_vpipe<=0;slot_present_pipe<=0;slot_response_v<=0;slot_response_present<=0;slot_response_row<=0;slot_response_sector<=0;
            for(integer p=0;p<3;p=p+1)begin slot_row_pipe[p]<=0;slot_sector_pipe[p]<=0;end
        end else if(epoch_begin)begin slot_vpipe<=0;slot_present_pipe<=0;slot_response_v<=0;slot_response_present<=0;end
        else begin
            slot_vpipe<={slot_vpipe[1:0],LOCAL_READ && local_read_v};
            slot_present_pipe<={slot_present_pipe[1:0],present[local_read_slot]};
            slot_row_pipe[0]<=present[local_read_slot]?indices[local_read_slot]:5'b0;slot_sector_pipe[0]<=local_read_sector;
            for(integer p=1;p<3;p=p+1)begin slot_row_pipe[p]<=slot_row_pipe[p-1];slot_sector_pipe[p]<=slot_sector_pipe[p-1];end
            slot_response_v<=slot_vpipe[2];slot_response_present<=slot_present_pipe[2];
            slot_response_row<=slot_row_pipe[2];slot_response_sector<=slot_sector_pipe[2];
        end
    end
    ot_hbm_svc_native_sector_guarded_stack controller(.clk(hbm_clk),.pc_clk({32{hbm_clk}}),.rst_n(rst_n),
        .k_v(kv),.k_rdy(krdy),.k_we(32'b0),.k_addr(ka),.k_len(kl),.k_tag(kt),.k_wdata(8192'b0),.k_wstrb(1024'b0),
        .kr_v(krv),.kr_rdy(krrdy),.kr_tag(krt),.kr_beat(krb),.kr_data(krd),.k_wr_done(kwdone),
        .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
        .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
        .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(controller_fault));
    ot_hbm_engram_row_store_decode #(.DECODE_ENABLE(0))staging(.clk(core_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
        .write_v(return_write),.write_row(response_core[264:260]),.write_sector(response_core[259:256]),.write_data(response_core[255:0]),
        .read_v(actual_read_v),.read_row(actual_read_row),.read_sector(actual_read_sector),
        .raw_v(raw_v),.raw_row(raw_row),.raw_sector(raw_sector),.raw_data(raw_data),
        .out_v(),.out_row(),.out_block(),.out_data(),.fault(store_fault));
    (* async_reg="true" *)reg hb_bad1,hb_bad2;
    always @(posedge hbm_clk or negedge rst_n)begin
        if(!rst_n)hbm_sticky<=0;
        else begin
            if(controller_fault || request_fault || (|kwdone))hbm_sticky<=1;
            for(integer p=0;p<32;p=p+1)if(krv[p] && (krb[p*4+:4]!=0 || krt[p*17+9+:8]!=0))hbm_sticky<=1;
        end
    end
    always @(posedge core_clk or negedge rst_n)begin
        if(!rst_n)begin present<=0;global_present<=0;owned_count<=0;active<=0;sticky<=0;age<=0;slot_age<=0;row<=0;sector<=0;pending<=0;done<=0;hb_bad1<=0;hb_bad2<=0;end
        else begin
            hb_bad1<=hbm_sticky;hb_bad2<=hb_bad1;done<=0;
            if(epoch_begin)begin
                if(active || pending!=0 || return_write)sticky<=1;
                present<=0;global_present<=0;owned_count<=0;pending<=0;
            end
            if(descriptor_v && descriptor_rank==HOME_RANK)begin
                if(descriptor_index>=24 || global_present[descriptor_index] || owned_count>=4)sticky<=1;
                else begin addresses[owned_count]<=descriptor_address;indices[owned_count]<=descriptor_index;present[owned_count]<=1;global_present[descriptor_index]<=1;owned_count<=owned_count+1'b1;end
            end
            if(fetch_start)begin
                if(active || pending!=0)sticky<=1;
                active<=1;age<=0;slot_age<=0;row<=0;sector<=0;
            end else if(active)begin
                age<=age+1;
                if(age<36*SLOT_EDGES)begin
                    if(slot_age==SLOT_EDGES-1)begin
                        slot_age<=0;
                        if(sector==8)begin sector<=0;if(row!=3)row<=row+1'b1;end
                        else sector<=sector+1'b1;
                    end else slot_age<=slot_age+1'b1;
                end
                if(age==TOTAL-1)begin active<=0;done<=1;if(pending!=0 || return_write)sticky<=1;end
            end
            if(req_we && rq_full)sticky<=1;
            if(return_write && pending==0)sticky<=1;
            case({req_issue,return_write})
                2'b10:pending<=pending+1'b1;
                2'b01:pending<=pending-1'b1;
                default:;
            endcase
        end
    end
    assign fault=sticky || hb_bad2 || store_fault;
endmodule
