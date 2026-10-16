`timescale 1ns/1ps
`default_nettype none
// Real per-quadrant VM->HBM STORE engine. Distinct successor: historical back untouched.
// Compiler supplies absolute issue/drain cycles. Each move owns <=128 chunks in
// eight real landing SRAMs. Every on-chip request/read/output has a fixed cycle.
// Chunk i lands at issue_at+i+9 and may be read at issue_at+i+10; both ports
// stream concurrently. A whole-move wait would add80 needless production cycles.
// WB reserve/ready is a WHOLE BLOCK checkpoint; ready never changes the calendar.
// Actual HBM posted wa acknowledgements affect fence quiet only. No lane credits.
//
// _vp (HBM-V15-HARDEN 10-15): structural successor of _cursor for its measured timing failure (cursor CTS gate TT
// reg->reg -827 ps: 33-level descriptor validation -- (rows-1)*stride products, rows*ceil(nsec/8), 41-bit end
// sums and ~40 field compares all in the one cv cycle -- plus a 32-bit add+compare per issue/drain slot).
// (1) Descriptor pipeline: the command passes two registered stages before the cursor core sees it (stage A
//     captures, stage B forms the operands-limited products 7x32 / 8x8 / 11x8 and the static field checks); the core's
//     cv cycle only adds and compares.  Products are formed from operands truncated to their VALID range (rows<=128,
//     nsec<=1024): any descriptor outside that range is invalid through its own range term, so the result is unchanged.
// (2) Slot compares against registered next-issue/next-drain cycles (incremented with the index) and registered
//     fill-start / end cycles instead of first_*+index adders.
// Contract: identical to _cursor fed the same command DESC_LAT=2 cycles later (all absolute issue/drain cycles, data
// beats, reservation checkpoints and faults unchanged); the compiler sends each command 2 cycles earlier.  No credit,
// ready or arbitration added; bench tb_dma_back_vp_equiv.sv (cursor reference with the 2-cycle-delayed command).
module ot_hgi_dma_back_static_vp #(
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
    // ---- descriptor pipeline (stage A capture, stage B products + static checks) ----
    reg a_v,b_v; reg [226:0] a_mv,b_mv; reg [31:0] a_ci,a_cd,b_ci,b_cd; reg a_cb,b_cb; reg [15:0] a_ce,b_ce;
    reg [40:0] b_vprod,b_hprod; reg [14:0] b_nchunk; reg [7:0] b_rchunk; reg [17:0] b_total; reg b_static_ok;
    wire [10:0] a_nsec=a_mv[219:209];                     // nsec<=1024 when valid (range term below)
    wire [7:0] a_rchunk=8'((a_mv[219:209]+11'd7)>>3);      // ceil(nsec/8) <= 128 when valid
    wire [6:0] a_rows_m1=7'(a_mv[192:186]-7'd1);           // rows<=128 when valid
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin a_v<=0;b_v<=0; end else begin a_v<=mv_v;b_v<=a_v; end
    always @(posedge clk) begin
        a_mv<=mv;a_ci<=issue_at;a_cd<=drain_at;a_cb<=mv_wb_bank;a_ce<=mv_wb_epoch;
        b_mv<=a_mv;b_ci<=a_ci;b_cd<=a_cd;b_cb<=a_cb;b_ce<=a_ce;
        b_vprod<=41'(a_rows_m1)*41'(a_mv[76:45]);
        b_hprod<=41'(a_rows_m1)*41'(a_mv[169:138]);
        b_rchunk<=(a_mv[226:209]==0)?8'd0:a_rchunk;
        b_nchunk<=15'(a_mv[193:186])*15'(a_rchunk);
        b_total<=18'(a_nsec)*18'(a_mv[193:186]);
        b_static_ok<=a_mv[1:0]==1&&a_mv[94:93]==0&&a_mv[92:77]==1&&a_mv[185:170]==1&&
            (a_mv[4:2]==0||a_mv[4:2]==5)&&(a_mv[97:95]==0||a_mv[97:95]==5)&&a_mv[4:2]==a_mv[97:95]&&
            a_mv[10:5]==0&&a_mv[50:45]==0&&a_mv[208:206]==0&&a_mv[205:186]!=0&&a_mv[205:186]<=128&&
            a_mv[226:209]!=0&&a_mv[226:209]<=1024&&
            a_mv[102:98]==0&&a_mv[142:138]==0&&a_mv[137:135]==0&&a_mv[134:133]==2'(STK)&&
            (a_mv[205:186]==1||a_mv[76:45]>=a_mv[226:206])&&
            (a_mv[205:186]==1||a_mv[169:138]==(32'(a_mv[226:206])<<2))&&
            (a_mv[205:186]==1||a_mv[211:206]==0);
    end
    reg [40:0] c_vprod,c_hprod; reg [14:0] c_nchunk; reg [7:0] c_rchunk; reg [17:0] c_total; reg c_static_ok;
    reg [31:0] next_issue,next_drain,fill_at,end_at;
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
    wire issue_slot=busy&&!cv&&issue_index<chunks&&cycle==next_issue;
    wire drain_slot=busy&&!cv&&drain_index<chunks&&cycle==next_drain;
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
        cm<=b_mv;ci<=b_ci;cd<=b_cd;cb<=b_cb;ce<=b_ce;
        c_vprod<=b_vprod;c_hprod<=b_hprod;c_nchunk<=b_nchunk;c_rchunk<=b_rchunk;c_total<=b_total;c_static_ok<=b_static_ok;
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
            cv<=b_v;mv_src<=0;mv_done<=0;wb_reserve_v<=0;
            wb_fill_start<=busy&&cycle==fill_at;
            if(b_v&&(busy||cv))mv_fault<=1;
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
                issue_index<=issue_index+1'b1;next_issue<=next_issue+1;
                if(column==row_chunks-1)begin
                    column<=0;row_vm<=row_vm+17'(vm_stride);chunk_vm<=row_vm+17'(vm_stride);
                    row_hbm<=row_hbm+37'(hbm_stride);chunk_hbm<=row_hbm+37'(hbm_stride);
                end else begin column<=column+1'b1;chunk_vm<=chunk_vm+17'd64;chunk_hbm<=chunk_hbm+37'd256;end
                if(MUT==2&&issue_index+1==chunks)begin mv_src<=1;src_sent<=1;end
            end
            if(drain_slot)begin
                drain_index<=drain_index+1'b1;next_drain<=next_drain+1;
                if(drain_column==row_chunks-1)begin
                    drain_column<=0;drain_row_hbm<=drain_row_hbm+37'(hbm_stride);
                    drain_chunk_hbm<=drain_row_hbm+37'(hbm_stride);
                end else begin drain_column<=drain_column+1'b1;drain_chunk_hbm<=drain_chunk_hbm+37'd256;end
                if(drain_index==0&&!wb_ready)mv_fault<=1;
            end
            if(busy&&cycle==end_at)busy<=0;
            nland=0;for(integer b=0;b<8;b=b+1)nland=nland+int'(rr_valid[b]);
            landed<=landed+20'(nland);
            if(busy&&!src_sent&&nland!=0&&landed+20'(nland)==total_sectors)begin mv_src<=1;src_sent<=1;end
            pending_sectors<=pending_sectors-32'(wa);
            if(32'(wa)>pending_sectors)mv_fault<=1;
            quiet<=!busy&&!cv&&!b_v&&pending_sectors==0;
            if(dirty&&!busy&&!cv&&!b_v&&pending_sectors==0)begin mv_done<=1;dirty<=0;end
            if(cv)begin
                nsec=int'(cm[226:209]);rchunk=int'(c_rchunk);nchunk=int'(c_nchunk);
                vend={1'b0,cm[44:5]}+c_vprod+41'(cm[226:206]);
                hend={4'b0,cm[134:98]}+c_hprod+41'(cm[226:206])*4;
                valid_move=c_static_ok&&
                    ((cm[44:5]<65536&&vend<=65536)||(cm[44:5]>=65536&&vend<=98304))&&
                    nchunk>0&&nchunk<=128&&
                    hend[40:37]==0&&hend[36:35]==2'(STK)&&{1'b0,hend[34:0]}<=STACK_BYTES&&
                    $signed(ci-cycle)>=1&&$signed(cd-ci)>=10;
                if(!valid_move)mv_fault<=1;
                else begin
                    busy<=1;dirty<=1;src_sent<=0;first_issue<=ci;first_drain<=cd;
                    next_issue<=ci;next_drain<=cd;fill_at<=cd+1;end_at<=cd+32'(nchunk)+1;
                    issue_index<=0;drain_index<=0;column<=0;chunks<=8'(nchunk);row_chunks<=8'(rchunk);
                    row_sectors<=18'(nsec);total_sectors<=20'(c_total);landed<=0;
                    row_vm<=cm[21:5];chunk_vm<=cm[21:5];vm_stride<=cm[76:45];
                    row_hbm<=cm[134:98];chunk_hbm<=cm[134:98];hbm_stride<=cm[169:138];
                    drain_row_hbm<=cm[134:98];drain_chunk_hbm<=cm[134:98];drain_column<=0;
                    pending_sectors<=pending_sectors+32'(c_total)-32'(wa);
                    wb_reserve_bank<=cb;wb_fill_bank<=cb;wb_reserve_epoch<=ce;wb_fill_epoch<=ce;
                    wb_reserve_v<=1;wb_reserve_sectors<=12'(c_total);wb_reserve_base<=cm[134:103];
                end
            end
        end
    end
endmodule
`default_nettype wire
