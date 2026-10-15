`timescale 1ps/1fs
// One real Engram home: source-owned hash descriptors, fixed core issue slots,
// finite real CDCs, arbitrary native DRAM bank/refresh controller, actual SRAM.
// Runtime service variability is contained at this external-HBM staging boundary;
// done is a fixed compiler edge and never waits for a late return.
module ot_hbm_engram_home_fetch #(
    parameter integer HOME_RANK=0, SLOT_EDGES=512, GUARD_EDGES=512
)(
    input wire core_clk,hbm_clk,rst_n,epoch_begin,
    input wire descriptor_v,input wire[6:0]descriptor_rank,input wire[4:0]descriptor_index,input wire[36:0]descriptor_address,
    input wire fetch_start,
    input wire read_v,input wire[4:0]read_row,input wire[3:0]read_sector,
    output wire raw_v,output wire[4:0]raw_row,output wire[3:0]raw_sector,output wire[255:0]raw_data,
    output reg done,output wire fault,
    output wire[31:0]row_v,output wire[95:0]row_op,output wire[159:0]row_bank,output wire[607:0]row_row,
    output wire[31:0]col_v,col_we,output wire[159:0]col_bank,col_col,
    output wire[8191:0]col_data,output wire[1023:0]col_strb,
    input wire[31:0]dram_rvalid,input wire[8191:0]dram_rdata
);
    localparam integer TOTAL=216*SLOT_EDGES+GUARD_EDGES;
    reg[36:0]addresses[0:23];reg[23:0]present;
    reg active,sticky;reg[31:0]age;
    reg[15:0]slot_age;reg[4:0]row;reg[3:0]sector;
    reg[8:0]pending;
    wire req_issue=active && age<216*SLOT_EDGES && slot_age==0 && present[row];
    wire[36:0]req_address=addresses[row]+37'(sector*32);
    wire rq_full,rq_empty,rq_pop;
    wire[45:0]rq_data;
    ot_hbm_accel_cdc_fifo #(.W(46),.AW(2))request_cdc(
        .wclk(core_clk),.wrst_n(rst_n),.we(req_issue),.wdata({req_address,row,sector}),.full(rq_full),.rd_freed(),
        .rclk(hbm_clk),.rrst_n(rst_n),.re(rq_pop),.rdata(rq_data),.empty(rq_empty));
    wire[36:0]haddr=rq_data[45:9];wire[1:0]stack;wire[4:0]pc;wire[29:0]sa;wire mapped;
    ot_hbm_loader_kport_address #(.ENABLE(1))mapper(.byte_address(haddr),.stack_bytes(36'd22500000000),
        .stack(stack),.pc(pc),.sector_address(sa),.valid(mapped));
    wire[31:0]kv,krdy,krv,krrdy,kwdone;
    wire[959:0]ka;wire[127:0]kl;wire[543:0]kt,krt;wire[127:0]krb;wire[8191:0]krd;
    wire controller_fault;
    for(genvar p=0;p<32;p=p+1)begin:g_kport
        assign kv[p]=!rq_empty && mapped && stack==3 && pc==p;
        assign ka[p*30+:30]=sa;assign kl[p*4+:4]=1;assign kt[p*17+:17]={8'b0,rq_data[8:0]};
    end
    assign rq_pop=kv[pc] && krdy[pc];
    wire response_full,response_empty;
    reg[264:0]response_word;reg response_any;
    reg hbm_sticky;
    always @*begin
        response_word=0;response_any=0;
        for(integer p=0;p<32;p=p+1)if(krv[p])begin response_word={krt[p*17+:9],krd[p*256+:256]};response_any=1;end
    end
    assign krrdy={32{!response_full}};
    wire response_push=response_any && !response_full;
    wire[264:0]response_core;
    ot_hbm_accel_cdc_fifo #(.W(265),.AW(2))return_cdc(
        .wclk(hbm_clk),.wrst_n(rst_n),.we(response_push),.wdata(response_word),.full(response_full),.rd_freed(),
        .rclk(core_clk),.rrst_n(rst_n),.re(!response_empty),.rdata(response_core),.empty(response_empty));
    wire return_write=!response_empty;
    wire store_fault;
    ot_hbm_native_sector_stack controller(.clk(hbm_clk),.rst_n(rst_n),
        .k_v(kv),.k_rdy(krdy),.k_we(32'b0),.k_addr(ka),.k_len(kl),.k_tag(kt),.k_wdata(8192'b0),.k_wstrb(1024'b0),
        .kr_v(krv),.kr_rdy(krrdy),.kr_tag(krt),.kr_beat(krb),.kr_data(krd),.k_wr_done(kwdone),
        .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
        .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
        .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(controller_fault));
    ot_hbm_engram_row_store_decode #(.DECODE_ENABLE(0))staging(.clk(core_clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
        .write_v(return_write),.write_row(response_core[264:260]),.write_sector(response_core[259:256]),.write_data(response_core[255:0]),
        .read_v(read_v),.read_row(read_row),.read_sector(read_sector),
        .raw_v(raw_v),.raw_row(raw_row),.raw_sector(raw_sector),.raw_data(raw_data),
        .out_v(),.out_row(),.out_block(),.out_data(),.fault(store_fault));
    (* async_reg="true" *)reg hb_bad1,hb_bad2;
    always @(posedge hbm_clk or negedge rst_n)begin
        if(!rst_n)hbm_sticky<=0;
        else begin
            if(controller_fault || (!rq_empty && (!mapped || stack!=3)) || (|(krv & (krv-1'b1))) || (|kwdone))hbm_sticky<=1;
            for(integer p=0;p<32;p=p+1)if(krv[p] && (krb[p*4+:4]!=0 || krt[p*17+9+:8]!=0))hbm_sticky<=1;
        end
    end
    always @(posedge core_clk or negedge rst_n)begin
        if(!rst_n)begin present<=0;active<=0;sticky<=0;age<=0;slot_age<=0;row<=0;sector<=0;pending<=0;done<=0;hb_bad1<=0;hb_bad2<=0;end
        else begin
            hb_bad1<=hbm_sticky;hb_bad2<=hb_bad1;done<=0;
            if(epoch_begin)begin
                if(active || pending!=0 || return_write)sticky<=1;
                present<=0;pending<=0;
            end
            if(descriptor_v && descriptor_rank==HOME_RANK)begin
                if(descriptor_index>=24 || present[descriptor_index])sticky<=1;
                else begin addresses[descriptor_index]<=descriptor_address;present[descriptor_index]<=1;end
            end
            if(fetch_start)begin
                if(active || pending!=0)sticky<=1;
                active<=1;age<=0;slot_age<=0;row<=0;sector<=0;
            end else if(active)begin
                age<=age+1;
                if(age<216*SLOT_EDGES)begin
                    if(slot_age==SLOT_EDGES-1)begin
                        slot_age<=0;
                        if(sector==8)begin sector<=0;if(row!=23)row<=row+1'b1;end
                        else sector<=sector+1'b1;
                    end else slot_age<=slot_age+1'b1;
                end
                if(age==TOTAL-1)begin active<=0;done<=1;if(pending!=0 || return_write)sticky<=1;end
            end
            if(req_issue && rq_full)sticky<=1;
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
