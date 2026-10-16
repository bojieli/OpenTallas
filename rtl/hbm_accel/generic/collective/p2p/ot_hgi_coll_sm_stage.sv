`timescale 1ns/1ps
`default_nettype none
// One common per-SM hardening candidate: two real native 64x512 SRAMs.
// Compiler context names blockslot/beat; the actual SM producer supplies only
// rv/rrow/rdata. All producer and compiler faces are first captured. Faults
// report invalid reservations and never change the fixed issue calendar.
module ot_hgi_coll_sm_stage #(
    parameter integer MUT_BANK=0, MUT_COLUMN=0
)(
    input wire clk_control,
    input wire [1:0] clk_mem,
    input wire rst_n,
    input wire fill_begin, fill_bank,
    input wire pub_slot, pub_block,
    input wire [5:0] pub_beat,
    input wire rv,
    input wire [11:0] rrow,
    input wire [255:0] rdata,
    input wire prefetch_begin, prefetch_bank,
    input wire [1:0] prefetch_head,
    input wire [3:0] prefetch_dimvec,
    input wire release_v, release_bank,
    output reg [511:0] vectors,
    output reg vector_valid, prefetch_done,
    output reg vector_bank,
    output reg [1:0] vector_head,
    output reg [3:0] vector_dimvec,
    output reg [1:0] bank_full,
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
    reg [2:0] issue_idx;
    reg drain_bank;
    reg [2:0] read_col,read_base;
    reg [1:0] read_v;
    reg [5:0] read_row;
    reg [2:0] gather_v;
    reg [2:0] gather_i0,gather_i1,gather_i2;
    wire [63:0] pair_data[0:1];
    wire issue_now=cap_prefetch_begin||issuing;
    wire [2:0] issue_number=cap_prefetch_begin?3'd0:issue_idx;
    wire issue_bank=cap_prefetch_begin?cap_prefetch_bank:drain_bank;
    wire [2:0] issue_base=cap_prefetch_begin?cap_prefetch_dimvec[2:0]:read_base;
    wire [2:0] issue_col=cap_prefetch_begin?{cap_prefetch_head,cap_prefetch_dimvec[3]}:read_col;
    for(genvar b=0;b<2;b=b+1)begin:g_bank
        ot_hgi_coll_sm_stage_bank #(.MUT_COLUMN(MUT_COLUMN)) u_bank(
            .clk(clk_mem[b]),.read_v(read_v[b]),.read_row(read_row),.read_col(read_col),
            .write_v(write_v[b]),.write_row(write_row),.write_data(write_data),.pair_data(pair_data[b]));
    end
    always @(posedge clk_control or negedge rst_n)begin
        if(!rst_n)begin
            fill_active<=0;active_fill_bank<=0;fill_count<=0;pack_v<=0;
            row_valid[0]<=0;row_valid[1]<=0;bank_full<=0;held<=0;
            write_v<=0;write_last<=0;issuing<=0;issue_idx<=0;read_v<=0;
            gather_v<=0;vector_valid<=0;prefetch_done<=0;fault<=0;
            vector_bank<=0;vector_head<=0;vector_dimvec<=0;drain_bank<=0;
        end else begin
            write_v<=0;read_v<=0;prefetch_done<=0;
            gather_v<={gather_v[1:0],issue_now};
            gather_i0<=issue_number;gather_i1<=gather_i0;gather_i2<=gather_i1;
            // This edge is the actual macro write edge, not merely issue.
            if(|write_v)begin
                row_valid[write_logical_bank][write_row]<=1;
                if(write_last)bank_full[write_logical_bank]<=1;
            end
            if(cap_release_v)begin
                if(!held[cap_release_bank] || ((issuing||(|gather_v)) && drain_bank==cap_release_bank))fault<=1;
                held[cap_release_bank]<=0;
            end
            if(cap_fill_begin)begin
                if(fill_active || held[cap_fill_bank] || ((|write_v)&&write_logical_bank==cap_fill_bank) || cap_pub_slot)fault<=1;
                active_fill_bank<=cap_fill_bank;fill_active<=1;fill_count<=0;pack_v<=0;
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
            if(cap_prefetch_begin)begin
                if(issuing || (|gather_v) || !bank_full[cap_prefetch_bank] || !(&row_valid[cap_prefetch_bank]) ||
                   (fill_active&&active_fill_bank==cap_prefetch_bank) ||
                   ((|write_v)&&write_logical_bank==cap_prefetch_bank))fault<=1;
                drain_bank<=cap_prefetch_bank;held[cap_prefetch_bank]<=1;
                vector_valid<=0;vector_bank<=cap_prefetch_bank;
                vector_head<=cap_prefetch_head;vector_dimvec<=cap_prefetch_dimvec;
                issuing<=1;issue_idx<=1;
                read_base<=cap_prefetch_dimvec[2:0];
            end
            if(issue_now)begin
                // Eight fixed reads: slot0 rows0..3, then slot1 rows0..3.
                read_v[issue_bank]<=1;
                read_row<={issue_number[2],issue_base,issue_number[1:0]};
                read_col<=issue_col;
                if(!cap_prefetch_begin)begin
                    issue_idx<=issue_idx+1'b1;
                    if(issue_idx==7)issuing<=0;
                end
            end
            if(gather_v[2])begin
                for(integer j=0;j<8;j=j+1)
                    if(gather_i2==3'(j))vectors[j*64+:64]<=pair_data[drain_bank];
                if(gather_i2==7)begin vector_valid<=1;prefetch_done<=1;end
            end
        end
    end
endmodule

// Actual native macro, followed by only the two required FP32 words. Capturing
// a full unused 512b SRAM output would cost another 896 FF per common master.
module ot_hgi_coll_sm_stage_bank #(parameter integer MUT_COLUMN=0)(
    input wire clk,read_v,write_v,
    input wire [5:0] read_row,write_row,
    input wire [2:0] read_col,
    input wire [511:0] write_data,
    output reg [63:0] pair_data
);
    wire [511:0] rq;
    reg read_v1;
    reg [2:0] col1;
    wire [2:0] actual_col=col1^(MUT_COLUMN!=0?3'd1:3'd0);
    ot_sram_1r1w_64x512_m1_r2c2 u_sram(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_row),.rd_out(rq),
        .w_ce_in(write_v),.w_addr_in(write_row),.wd_in(write_data),.w_mask_in({512{1'b1}}),
        .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
    always @(posedge clk)begin
        read_v1<=read_v;col1<=read_col;
        if(read_v1)pair_data<={rq[256+actual_col*32+:32],rq[actual_col*32+:32]};
    end
endmodule

// Eight identical common SM leaves, with an explicit registered LP selector.
// Four identical wrappers cover the production 32-SM shape. No SM RTL is edited.
module ot_hgi_coll_sm_stage_q #(parameter integer MUT_BANK=0,MUT_COLUMN=0)(
    input wire clk_select,
    input wire [7:0] clk_control,
    input wire [15:0] clk_mem,
    input wire rst_n,
    input wire [7:0] fill_begin,fill_bank,pub_slot,pub_block,
    input wire [47:0] pub_beat,
    input wire [7:0] rv,
    input wire [95:0] rrow,
    input wire [2047:0] rdata,
    input wire prefetch_begin,prefetch_bank,
    input wire [1:0] prefetch_head,
    input wire [3:0] prefetch_dimvec,
    input wire release_v,release_bank,
    input wire lp_issue,
    input wire [3:0] lp_group,
    input wire lp_bank,
    input wire [1:0] lp_head,
    input wire [3:0] lp_dimvec,
    output reg lp_v,
    output reg [255:0] lp_data,
    output reg [3:0] lp_group_o,
    output wire [7:0] vector_valid,prefetch_done,leaf_fault,
    output wire [15:0] bank_full,
    output reg selector_fault
);
    wire [511:0] vectors[0:7];
    wire [7:0] vector_bank;
    wire [1:0] vector_head[0:7];
    wire [3:0] vector_dimvec[0:7];
    for(genvar s=0;s<8;s=s+1)begin:g_sm
        ot_hgi_coll_sm_stage #(.MUT_BANK(MUT_BANK),.MUT_COLUMN(MUT_COLUMN)) u_stage(
            .clk_control(clk_control[s]),.clk_mem(clk_mem[s*2+:2]),.rst_n(rst_n),
            .fill_begin(fill_begin[s]),.fill_bank(fill_bank[s]),.pub_slot(pub_slot[s]),.pub_block(pub_block[s]),
            .pub_beat(pub_beat[s*6+:6]),.rv(rv[s]),.rrow(rrow[s*12+:12]),.rdata(rdata[s*256+:256]),
            .prefetch_begin(prefetch_begin),.prefetch_bank(prefetch_bank),.prefetch_head(prefetch_head),.prefetch_dimvec(prefetch_dimvec),
            .release_v(release_v),.release_bank(release_bank),.vectors(vectors[s]),.vector_valid(vector_valid[s]),
            .prefetch_done(prefetch_done[s]),.vector_bank(vector_bank[s]),.vector_head(vector_head[s]),
            .vector_dimvec(vector_dimvec[s]),.bank_full(bank_full[s*2+:2]),.fault(leaf_fault[s]));
    end
    (* keep=1, dont_touch=1 *) reg cap_lp_issue,cap_lp_bank;
    (* keep=1, dont_touch=1 *) reg [3:0] cap_lp_group,cap_lp_dimvec;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_lp_head;
    always @(posedge clk_select)begin
        cap_lp_issue<=lp_issue;cap_lp_group<=lp_group;cap_lp_bank<=lp_bank;
        cap_lp_head<=lp_head;cap_lp_dimvec<=lp_dimvec;
    end
    always @(posedge clk_select or negedge rst_n)begin
        if(!rst_n)begin lp_v<=0;selector_fault<=0;lp_group_o<=0;end
        else begin
            lp_v<=cap_lp_issue;lp_group_o<=cap_lp_group;
            if(cap_lp_issue)begin
                lp_data<=vectors[cap_lp_group[3:1]][cap_lp_group[0]*256+:256];
                if(!vector_valid[cap_lp_group[3:1]] || vector_bank[cap_lp_group[3:1]]!=cap_lp_bank ||
                   vector_head[cap_lp_group[3:1]]!=cap_lp_head || vector_dimvec[cap_lp_group[3:1]]!=cap_lp_dimvec)selector_fault<=1;
            end
        end
    end
endmodule
`default_nettype wire
