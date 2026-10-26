`timescale 1ns/1ps
`default_nettype none
// One common per-SM hardening candidate: two real native 64x512 SRAMs.
// Compiler context names blockslot/beat; the actual SM producer supplies only
// rv/rrow/rdata. All producer and compiler faces are first captured. Faults
// report invalid reservations and never change the fixed issue calendar.
module ot_hgi_coll_sm_stage_profiles #(
    parameter integer MUT_BANK=0, MUT_COLUMN=0, MUT_EPOCH=0, MUT_READ_DROP=0
)(
    input wire clk_control,
    input wire [1:0] clk_mem,
    input wire rst_n,
    input wire fill_begin, fill_bank,
    input wire [7:0] fill_epoch,
    input wire pub_slot, pub_block,
    input wire [5:0] pub_beat,
    input wire rv,
    input wire [11:0] rrow,
    input wire [255:0] rdata,
    input wire prefetch_begin, prefetch_bank,
    input wire [7:0] prefetch_epoch,
    input wire raw_begin,raw_bank,
    input wire [7:0] raw_epoch,
    input wire [1:0] prefetch_head,
    input wire [3:0] prefetch_dimvec,
    input wire release_v, release_bank,
    output reg [511:0] vectors,
    output reg vector_valid, prefetch_done,
    output reg vector_bank,
    output reg [1:0] vector_head,
    output reg [3:0] vector_dimvec,
    output reg [1:0] bank_full,
    output reg [7:0] vector_epoch,
    output reg raw_v,raw_done,raw_bank_o,
    output reg [5:0] raw_seq,
    output reg [7:0] raw_epoch_o,
    output reg fault
);
    // No data/control path bypasses this unconditional first face capture.
    (* keep=1, dont_touch=1 *) reg cap_fill_begin,cap_fill_bank;
    (* keep=1, dont_touch=1 *) reg cap_pub_slot,cap_pub_block,cap_rv;
    (* keep=1, dont_touch=1 *) reg [5:0] cap_pub_beat;
    (* keep=1, dont_touch=1 *) reg [11:0] cap_rrow;
    (* keep=1, dont_touch=1 *) reg [255:0] cap_rdata;
    (* keep=1, dont_touch=1 *) reg cap_prefetch_begin,cap_prefetch_bank;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_prefetch_head;
    (* keep=1, dont_touch=1 *) reg [3:0] cap_prefetch_dimvec;
    (* keep=1, dont_touch=1 *) reg cap_release_v,cap_release_bank;
    always @(posedge clk_control)begin
        cap_fill_begin<=fill_begin;cap_fill_bank<=fill_bank;
        cap_pub_slot<=pub_slot;cap_pub_block<=pub_block;cap_pub_beat<=pub_beat;
        cap_rv<=rv;cap_rrow<=rrow;cap_rdata<=rdata;
        cap_prefetch_begin<=prefetch_begin;cap_prefetch_bank<=prefetch_bank;
        cap_prefetch_head<=prefetch_head;cap_prefetch_dimvec<=prefetch_dimvec;
        cap_release_v<=release_v;cap_release_bank<=release_bank;
    end
    (* keep=1,dont_touch=1 *) reg [7:0] cap_fill_epoch,cap_prefetch_epoch,cap_raw_epoch;
    (* keep=1,dont_touch=1 *) reg cap_raw_begin,cap_raw_bank;
    always @(posedge clk_control)begin
        cap_fill_epoch<=fill_epoch;cap_prefetch_epoch<=prefetch_epoch;
        cap_raw_begin<=raw_begin;cap_raw_bank<=raw_bank;cap_raw_epoch<=raw_epoch;
    end
    reg [7:0] bank_epoch[0:1];
    reg [7:0] drain_epoch;
    reg engine_raw;
    reg fill_active,active_fill_bank;
    reg [7:0] fill_count;
    reg pack_v,pack_block;
    reg [5:0] pack_beat;
    reg [255:0] even_beat;
    reg [63:0] row_valid[0:1];
    reg [1:0] held;
    reg [1:0] write_v;
    reg [5:0] write_row;
    reg [511:0] write_data;
    reg write_logical_bank,write_last;
    reg issuing;
    reg [5:0] issue_idx;
    reg drain_bank;
    reg [2:0] read_col,read_base;
    reg [1:0] read_v;
    reg [5:0] read_row;
    reg [2:0] gather_v;
    reg [5:0] gather_i0,gather_i1,gather_i2;
    reg [2:0] gather_raw,gather_bank;
    reg [7:0] gather_e0,gather_e1,gather_e2;
    reg [2:0] gather_c0,gather_c1,gather_c2;
    wire [511:0] bank_data[0:1];
    wire start_any=cap_prefetch_begin||cap_raw_begin;
    wire issue_now=start_any||issuing;
    wire issue_raw=start_any?cap_raw_begin:engine_raw;
    wire [5:0] issue_number=start_any?6'd0:issue_idx;
    wire issue_bank=cap_raw_begin?cap_raw_bank:(cap_prefetch_begin?cap_prefetch_bank:drain_bank);
    wire [7:0] issue_epoch=start_any?bank_epoch[issue_bank]:drain_epoch;
    wire [2:0] issue_base=cap_prefetch_begin?cap_prefetch_dimvec[2:0]:read_base;
    wire [2:0] issue_col=cap_prefetch_begin?{cap_prefetch_head,cap_prefetch_dimvec[3]}:read_col;
    for(genvar b=0;b<2;b=b+1)begin:g_bank
        ot_hgi_coll_sm_stage_profiles_bank #(.MUT_COLUMN(MUT_COLUMN)) u_bank(
            .clk(clk_mem[b]),.read_v(read_v[b]),.read_row(read_row),
            .write_v(write_v[b]),.write_row(write_row),.write_data(write_data),.data(bank_data[b]));
    end
    always @(posedge clk_control or negedge rst_n)begin
        if(!rst_n)begin
            fill_active<=0;active_fill_bank<=0;fill_count<=0;pack_v<=0;
            row_valid[0]<=0;row_valid[1]<=0;bank_full<=0;held<=0;
            write_v<=0;write_last<=0;issuing<=0;issue_idx<=0;read_v<=0;
            gather_v<=0;vector_valid<=0;prefetch_done<=0;fault<=0;
            vector_bank<=0;vector_head<=0;vector_dimvec<=0;drain_bank<=0;
            bank_epoch[0]<=0;bank_epoch[1]<=0;drain_epoch<=0;engine_raw<=0;
            gather_raw<=0;gather_bank<=0;raw_v<=0;raw_done<=0;raw_seq<=0;
            raw_bank_o<=0;raw_epoch_o<=0;vector_epoch<=0;
        end else begin
            write_v<=0;read_v<=0;prefetch_done<=0;raw_v<=0;raw_done<=0;
            gather_v<={gather_v[1:0],issue_now};
            gather_i0<=issue_number;gather_i1<=gather_i0;gather_i2<=gather_i1;
            gather_raw<={gather_raw[1:0],issue_raw};gather_bank<={gather_bank[1:0],issue_bank};
            gather_e0<=issue_epoch;gather_e1<=gather_e0;gather_e2<=gather_e1;
            gather_c0<=issue_col;gather_c1<=gather_c0;gather_c2<=gather_c1;
            // This edge is the actual macro write edge, not merely issue.
            if(|write_v)begin
                row_valid[write_logical_bank][write_row]<=1;
                if(write_last)bank_full[write_logical_bank]<=1;
            end
            if(cap_release_v)begin
                if(!held[cap_release_bank] || (issuing&&drain_bank==cap_release_bank) ||
                   (gather_v[0]&&gather_bank[0]==cap_release_bank) ||
                   (gather_v[1]&&gather_bank[1]==cap_release_bank))fault<=1;
                held[cap_release_bank]<=0;
            end
            if(cap_fill_begin)begin
                if(fill_active || held[cap_fill_bank] || ((|write_v)&&write_logical_bank==cap_fill_bank) || cap_pub_slot)fault<=1;
                active_fill_bank<=cap_fill_bank;fill_active<=1;fill_count<=0;pack_v<=0;bank_epoch[cap_fill_bank]<=cap_fill_epoch;
                row_valid[cap_fill_bank]<=0;bank_full[cap_fill_bank]<=0;
                if(vector_bank==cap_fill_bank)vector_valid<=0;
            end
            if(cap_rv!=cap_pub_slot)fault<=1;
            if(cap_pub_slot)begin
                if(!fill_active || fill_count>=128 || {cap_pub_block,cap_pub_beat}!=fill_count[6:0] ||
                   cap_rrow!={6'b0,cap_pub_beat} || held[active_fill_bank])fault<=1;
                fill_count<=fill_count+1'b1;
                if(!cap_pub_beat[0])begin
                    if(pack_v)fault<=1;
                    even_beat<=cap_rdata;pack_v<=1;pack_block<=cap_pub_block;pack_beat<=cap_pub_beat;
                end else begin
                    if(!pack_v || pack_block!=cap_pub_block || cap_pub_beat!=pack_beat+1'b1)fault<=1;
                    // Address is compiler context, never guessed from an SM
                    // head/block identifier absent from the actual producer.
                    write_v[active_fill_bank^(MUT_BANK!=0)]<=1;
                    write_row<={cap_pub_block,cap_pub_beat[5:1]};
                    write_data<={cap_rdata,even_beat};
                    write_logical_bank<=active_fill_bank;
                    write_last<=cap_pub_block&&(&cap_pub_beat);
                    pack_v<=0;
                    if(cap_pub_block&&(&cap_pub_beat))fill_active<=0;
                end
            end
            if(start_any)begin
                if(issuing || (cap_prefetch_begin&&(|gather_v)) ||
                   (cap_raw_begin&&(|(gather_v&~gather_raw))) ||
                   (cap_prefetch_begin&&cap_raw_begin) || !bank_full[issue_bank] || !(&row_valid[issue_bank]) ||
                   bank_epoch[issue_bank]!=(cap_raw_begin?cap_raw_epoch:cap_prefetch_epoch) ||
                   (fill_active&&active_fill_bank==issue_bank) ||
                   ((|write_v)&&write_logical_bank==issue_bank))fault<=1;
                drain_bank<=issue_bank;drain_epoch<=bank_epoch[issue_bank];held[issue_bank]<=1;
                engine_raw<=cap_raw_begin;vector_valid<=0;vector_bank<=issue_bank;
                vector_head<=cap_prefetch_head;vector_dimvec<=cap_prefetch_dimvec;
                vector_epoch<=bank_epoch[issue_bank];issuing<=1;issue_idx<=1;
                read_base<=cap_prefetch_dimvec[2:0];
            end
            if(issue_now)begin
                // Raw mode interleaves blockslot0/1 for each packed rowpair.
                if(!(MUT_READ_DROP!=0 && issue_raw && issue_number==5))read_v[issue_bank]<=1;
                read_row<=issue_raw?{issue_number[0],issue_number[5:1]}:
                                      {issue_number[2],issue_base,issue_number[1:0]};
                read_col<=issue_col;
                if(!start_any)begin
                    issue_idx<=issue_idx+1'b1;
                    if((engine_raw&&issue_idx==63)||(!engine_raw&&issue_idx==7))issuing<=0;
                end
            end
            if(gather_v[2])begin
                if(gather_raw[2])begin
                    vectors<=bank_data[gather_bank[2]];
                    raw_v<=1;raw_seq<=gather_i2;raw_bank_o<=gather_bank[2];
                    raw_epoch_o<=gather_e2^(MUT_EPOCH!=0?8'd1:8'd0);
                    if(gather_i2==63)raw_done<=1;
                end else begin
                    for(integer j=0;j<8;j=j+1)
                        if(gather_i2==6'(j))vectors[j*64+:64]<=
                            {bank_data[gather_bank[2]][256+gather_c2*32+:32],bank_data[gather_bank[2]][gather_c2*32+:32]};
                    if(gather_i2==7)begin vector_valid<=1;prefetch_done<=1;end
                end
            end
        end
    end
endmodule

// Same two real SRAMs. The registered macro row is shared by both profiles;
// vector mode selects two FP32 words downstream, raw mode publishes all512bits.
module ot_hgi_coll_sm_stage_profiles_bank #(parameter integer MUT_COLUMN=0)(
    input wire clk,read_v,write_v,
    input wire [5:0] read_row,write_row,
    input wire [511:0] write_data,
    output reg [511:0] data
);
    wire [511:0] rq,actual_row;
    reg read_v1;
    ot_sram_1r1w_64x512_m1_r2c2 u_sram(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq),
        .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data),.w_mask_in({512{1'b1}}),
        .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
    for(genvar w=0;w<16;w=w+1)begin:g_col
        assign actual_row[w*32+:32]=rq[(w^(MUT_COLUMN!=0?1:0))*32+:32];
    end
    always @(posedge clk)begin
        read_v1<=read_v;
        if(read_v1)data<=actual_row;
    end
endmodule
`default_nettype wire
