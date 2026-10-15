`timescale 1ns/1ps
`default_nettype none
// Real per-quadrant VM->HBM STORE engine. Distinct successor: historical back untouched.
// Compiler supplies absolute issue/drain cycles. Each move owns <=128 chunks in
// eight real landing SRAMs. Every on-chip request/read/output has a fixed cycle.
// Chunk i lands at issue_at+i+9 and may be read at issue_at+i+10; both ports
// stream concurrently. A whole-move wait would add80 needless production cycles.
// WB reserve/ready is a WHOLE BLOCK checkpoint; ready never changes the calendar.
// Actual HBM posted wa acknowledgements affect fence quiet only. No lane credits.
module ot_hgi_dma_back_static_cursor #(
    parameter integer STK=0,
    parameter integer QID=STK,
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0 // 1 wrong destination sector; 2 premature source retire
)(
    input wire clk,rst_n,
    input wire [31:0] cycle,
    input wire mv_v,
    input wire [226:0] mv,
    input wire [31:0] issue_at,drain_at,
    input wire mv_wb_bank,
    input wire [15:0] mv_wb_epoch,
    output reg mv_src,mv_done,mv_fault,
    output reg quiet,busy,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output reg wb_reserve_v,wb_reserve_bank,wb_fill_bank,
    output reg [15:0] wb_reserve_epoch,wb_fill_epoch,
    output reg [11:0] wb_reserve_sectors,
    output reg [31:0] wb_reserve_base,
    output reg wb_fill_start,
    input wire wb_ready,
    output wire [8*289-1:0] wd,
    input wire [11:0] wa
);
    reg [7:0] rq_v,wd_v;reg [15:0] rq_payload[0:7];reg [287:0] wd_payload[0:7];
    reg cv,cb;reg [15:0] ce;reg [226:0] cm;reg [31:0] ci,cd;
    reg [31:0] first_issue,first_drain;
    reg [7:0] chunks,issue_index,drain_index,row_chunks,column;
    reg [17:0] row_sectors;
    reg [19:0] total_sectors,landed;
    reg [16:0] row_vm,chunk_vm;
    reg [31:0] vm_stride;
    reg [36:0] row_hbm,chunk_hbm;
    reg [31:0] hbm_stride;
    // The compiler-ordered drain follows exactly the same row/column address recurrence as issue.
    // Keep its own cursor instead of storing 128 x (32 address + 8 mask) FF bits and reading a wide mux.
    // This preserves every valid issue/drain/output edge; adds no cycle, SRAM, arbitration or credit.
    reg [36:0] drain_row_hbm,drain_chunk_hbm;
    reg [7:0] drain_column;
    wire [7:0] drain_mask=(drain_column==row_chunks-1 && row_sectors[2:0]!=0)?
                              ((8'd1<<row_sectors[2:0])-1'b1):8'hff;
    reg [7:0] expect_mask[0:7];reg [6:0] expect_tag[0:7];
    reg [7:0] rr_valid;reg [6:0] rr_tag;reg [255:0] rr_data[0:7];
    wire [255:0] macro_data[0:7];
    reg [255:0] capture[0:7];reg [31:0] capture_addr[0:7];
    reg [7:0] read_mask_q,output_mask_q;
    reg [31:0] read_addr_q;
    reg dirty,src_sent;
    reg [31:0] pending_sectors; // observation only; bounded outstanding, no cumulative wrap
    wire issue_slot=busy&&!cv&&issue_index<chunks&&cycle==first_issue+32'(issue_index);
    wire drain_slot=busy&&!cv&&drain_index<chunks&&cycle==first_drain+32'(drain_index);
    reg [7:0] issue_mask;
    reg [15:0] issue_sec;
    always @* begin
        issue_mask=8'hff;
        if(column==row_chunks-1 && row_sectors[2:0]!=0)
            issue_mask=(8'd1<<row_sectors[2:0])-1'b1;
        if(chunk_vm>=17'd65536) issue_sec=16'h8000|16'((chunk_vm-17'd65536)>>3);
        else issue_sec={1'b0,2'(QID),chunk_vm[15:3]};
    end
    // Whole-block landing storage. One real macro per bank, no memory substitute.
    for(genvar b=0;b<8;b=b+1)begin:L
        assign rq[b*17+:17]={rq_v[b],rq_payload[b]};
        assign wd[b*289+:289]={wd_v[b],wd_payload[b]};
        ot_sram_1r1w_128x256_m1_r2c2 landing(.clk(clk),
            .r_ce_in(drain_slot&&drain_mask[b]),.r_addr_in(drain_index[6:0]),.rd_out(macro_data[b]),
            .w_ce_in(rr_valid[b]),.w_addr_in(rr_tag),.wd_in(rr_data[b]),.w_mask_in({256{1'b1}}),
            .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
        always @(posedge clk) begin
            rr_data[b]<=rr[b*257+:256];
            capture[b]<=macro_data[b];
            capture_addr[b]<=read_addr_q+32'(b)+((MUT==1&&b==1)?32'd1:32'd0);
            wd_payload[b]<={capture_addr[b],capture[b]};
        end
    end
    always @(posedge clk) begin
        cm<=mv;ci<=issue_at;cd<=drain_at;cb<=mv_wb_bank;ce<=mv_wb_epoch;
        rr_tag<=expect_tag[7];
        read_addr_q<=drain_chunk_hbm[36:5];
        for(integer t=1;t<8;t=t+1)expect_tag[t]<=expect_tag[t-1];
        expect_tag[0]<=issue_index[6:0];
        for(integer b=0;b<8;b=b+1) rq_payload[b]<={issue_sec[15:3],3'(b)};
    end
    always @(posedge clk or negedge rst_n) begin:CONTROL
        integer nsec,rchunk,nchunk,nland;
        reg valid_move;reg [40:0] vend;reg [40:0] hend;
        if(!rst_n)begin
            cv<=0;busy<=0;quiet<=1;dirty<=0;src_sent<=0;mv_src<=0;mv_done<=0;mv_fault<=0;
            wb_reserve_v<=0;wb_reserve_sectors<=0;wb_reserve_base<=0;wb_fill_start<=0;wb_reserve_bank<=0;wb_fill_bank<=0;wb_reserve_epoch<=0;wb_fill_epoch<=0;read_mask_q<=0;output_mask_q<=0;rr_valid<=0;
            issue_index<=0;drain_index<=0;chunks<=0;column<=0;landed<=0;
            pending_sectors<=0;
            for(integer t=0;t<8;t=t+1)expect_mask[t]<=0;
            for(integer b=0;b<8;b=b+1)begin rq_v[b]<=0;wd_v[b]<=0;end
        end else begin
            cv<=mv_v;mv_src<=0;mv_done<=0;wb_reserve_v<=0;
            wb_fill_start<=busy&&cycle==first_drain+1;
            if(mv_v&&(busy||cv))mv_fault<=1;
            for(integer t=1;t<8;t=t+1)expect_mask[t]<=expect_mask[t-1];
            expect_mask[0]<=issue_slot?issue_mask:8'd0;
            for(integer b=0;b<8;b=b+1)begin
                rq_v[b]<=issue_slot&&issue_mask[b];
                rr_valid[b]<=rr[b*257+256];
                if(rr[b*257+256]!==expect_mask[7][b])mv_fault<=1;
                wd_v[b]<=output_mask_q[b];
            end
            read_mask_q<=drain_slot?drain_mask:8'd0;
            output_mask_q<=read_mask_q;
            if(issue_slot)begin
                issue_index<=issue_index+1'b1;
                if(column==row_chunks-1)begin
                    column<=0;row_vm<=row_vm+17'(vm_stride);chunk_vm<=row_vm+17'(vm_stride);
                    row_hbm<=row_hbm+37'(hbm_stride);chunk_hbm<=row_hbm+37'(hbm_stride);
                end else begin column<=column+1'b1;chunk_vm<=chunk_vm+17'd64;chunk_hbm<=chunk_hbm+37'd256;end
                if(MUT==2&&issue_index+1==chunks)begin mv_src<=1;src_sent<=1;end
            end
            if(drain_slot)begin
                drain_index<=drain_index+1'b1;
                if(drain_column==row_chunks-1)begin
                    drain_column<=0;drain_row_hbm<=drain_row_hbm+37'(hbm_stride);
                    drain_chunk_hbm<=drain_row_hbm+37'(hbm_stride);
                end else begin drain_column<=drain_column+1'b1;drain_chunk_hbm<=drain_chunk_hbm+37'd256;end
                if(drain_index==0&&!wb_ready)mv_fault<=1;
            end
            if(busy&&cycle==first_drain+32'(chunks)+1)busy<=0;
            nland=0;for(integer b=0;b<8;b=b+1)nland=nland+int'(rr_valid[b]);
            landed<=landed+20'(nland);
            if(busy&&!src_sent&&nland!=0&&landed+20'(nland)==total_sectors)begin mv_src<=1;src_sent<=1;end
            pending_sectors<=pending_sectors-32'(wa);
            if(32'(wa)>pending_sectors)mv_fault<=1;
            quiet<=!busy&&!cv&&!mv_v&&pending_sectors==0;
            if(dirty&&!busy&&!cv&&!mv_v&&pending_sectors==0)begin mv_done<=1;dirty<=0;end
            if(cv)begin
                nsec=int'(cm[226:209]);rchunk=(nsec+7)/8;nchunk=int'(cm[205:186])*rchunk;
                vend={1'b0,cm[44:5]}+41'(cm[205:186]-1)*41'(cm[76:45])+41'(cm[226:206]);
                hend={4'b0,cm[134:98]}+41'(cm[205:186]-1)*41'(cm[169:138])+41'(cm[226:206])*4;
                valid_move=cm[1:0]==1&&cm[94:93]==0&&cm[92:77]==1&&cm[185:170]==1&&
                    (cm[4:2]==0||cm[4:2]==5)&&(cm[97:95]==0||cm[97:95]==5)&&cm[4:2]==cm[97:95]&&
                    cm[10:5]==0&&cm[50:45]==0&&cm[208:206]==0&&cm[205:186]!=0&&cm[205:186]<=128&&nsec>0&&nsec<=1024&&
                    cm[102:98]==0&&cm[142:138]==0&&cm[137:135]==0&&cm[134:133]==2'(STK)&&
                    ((cm[44:5]<65536&&vend<=65536)||(cm[44:5]>=65536&&vend<=98304))&&
                    (cm[205:186]==1||cm[76:45]>=cm[226:206])&&
                    (cm[205:186]==1||cm[169:138]==(32'(cm[226:206])<<2))&&
                    (cm[205:186]==1||cm[211:206]==0)&&nchunk>0&&nchunk<=128&&
                    hend[40:37]==0&&hend[36:35]==2'(STK)&&{1'b0,hend[34:0]}<=STACK_BYTES&&
                    $signed(ci-cycle)>=1&&$signed(cd-ci)>=10;
                if(!valid_move)mv_fault<=1;
                else begin
                    busy<=1;dirty<=1;src_sent<=0;first_issue<=ci;first_drain<=cd;
                    issue_index<=0;drain_index<=0;column<=0;chunks<=8'(nchunk);row_chunks<=8'(rchunk);
                    row_sectors<=18'(nsec);total_sectors<=20'(nsec*int'(cm[205:186]));landed<=0;
                    row_vm<=cm[21:5];chunk_vm<=cm[21:5];vm_stride<=cm[76:45];
                    row_hbm<=cm[134:98];chunk_hbm<=cm[134:98];hbm_stride<=cm[169:138];
                    drain_row_hbm<=cm[134:98];drain_chunk_hbm<=cm[134:98];drain_column<=0;
                    pending_sectors<=pending_sectors+32'(nsec*int'(cm[205:186]))-32'(wa);
                    wb_reserve_bank<=cb;wb_fill_bank<=cb;wb_reserve_epoch<=ce;wb_fill_epoch<=ce;
                    wb_reserve_v<=1;wb_reserve_sectors<=12'(nsec*int'(cm[205:186]));wb_reserve_base<=cm[134:103];
                end
            end
        end
    end
endmodule
`default_nettype wire
