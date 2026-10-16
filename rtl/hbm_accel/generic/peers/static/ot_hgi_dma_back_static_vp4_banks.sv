`timescale 1ns/1ps
`default_nettype none
// Four-stage descriptor successor. Seven-by-32 products use registered 7x8
// partial products and pair sums. Register aperture end sums before validation.
// Command lead is DESC_LAT4; absolute issue/drain/data edges remain compiled.
// Eight unchanged bank leaves retain their own related clock roots. Functional
// and physical qualification is separate; no producer or compiler adoption.
module ot_hgi_dma_back_static_vp4_banks #(
    parameter integer STK=0,
    parameter integer QID=STK,
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0 // 1 wrong destination sector; 2 premature source retire
)(
    input wire clk,rst_n,
    input wire [7:0] clk_bank, // eight real related bank clock entries; clk is controller root
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
    // Wires-only physical parent: nine compensated related clock entries.
    // Banks use identical source and parameters; address constants are resolved in controller registers.
    wire [7:0] rr_valid_i,bank_read_en,bank_output_en;
    wire [6:0] bank_read_slot,bank_write_slot;
    wire [255:0] bank_read_addr;
    ot_hgi_dma_back_static_vp4_controller #(.STK(STK),.QID(QID),.STACK_BYTES(STACK_BYTES),.MUT(MUT)) u_control(
        .clk(clk),
        .rst_n(rst_n),
        .cycle_in(cycle),
        .mv_v(mv_v),
        .mv(mv),
        .issue_at(issue_at),
        .drain_at(drain_at),
        .mv_wb_bank(mv_wb_bank),
        .mv_wb_epoch(mv_wb_epoch),
        .mv_src(mv_src),
        .mv_done(mv_done),
        .mv_fault(mv_fault),
        .quiet(quiet),
        .busy(busy),
        .rq(rq),
        .wb_reserve_v(wb_reserve_v),
        .wb_reserve_bank(wb_reserve_bank),
        .wb_fill_bank(wb_fill_bank),
        .wb_reserve_epoch(wb_reserve_epoch),
        .wb_fill_epoch(wb_fill_epoch),
        .wb_reserve_sectors(wb_reserve_sectors),
        .wb_reserve_base(wb_reserve_base),
        .wb_fill_start(wb_fill_start),
        .wb_ready(wb_ready),
        .wa(wa),
        .rr_valid_i(rr_valid_i),
        .bank_read_en(bank_read_en),
        .bank_read_slot(bank_read_slot),
        .bank_write_slot(bank_write_slot),
        .bank_output_en(bank_output_en),
        .bank_read_addr(bank_read_addr));
    for(genvar b=0;b<8;b=b+1)begin:L
        assign rr_valid_i[b]=rr[b*257+256];
        ot_hgi_dma_back_landing_bank u_bank(
            .clk(clk_bank[b]),.rst_n(rst_n),
            .read_en(bank_read_en[b]),.read_slot(bank_read_slot),
            .write_en(rr_valid_i[b]),.write_slot(bank_write_slot),.rr_data(rr[b*257+:256]),
            .read_addr(bank_read_addr[b*32+:32]),.output_en(bank_output_en[b]),.wd(wd[b*289+:289]));
    end
endmodule
module ot_hgi_dma_back_static_vp4_controller #(
    parameter integer STK=0,
    parameter integer QID=STK,
    parameter [35:0] STACK_BYTES=36'd22500000000,
    parameter integer MUT=0 // 1 wrong destination sector; 2 premature source retire
)(
    input wire clk,rst_n,
    input wire [31:0] cycle_in,
    input wire mv_v,
    input wire [226:0] mv,
    input wire [31:0] issue_at,drain_at,
    input wire mv_wb_bank,
    input wire [15:0] mv_wb_epoch,
    output reg mv_src,mv_done,mv_fault,
    output reg quiet,busy,
    output wire [8*17-1:0] rq,
    input wire [7:0] rr_valid_i,
    output reg wb_reserve_v,wb_reserve_bank,wb_fill_bank,
    output reg [15:0] wb_reserve_epoch,wb_fill_epoch,
    output reg [11:0] wb_reserve_sectors,
    output reg [31:0] wb_reserve_base,
    output reg wb_fill_start,
    input wire wb_ready,
    output reg [7:0] bank_read_en,
    output wire [6:0] bank_read_slot,bank_write_slot,
    output wire [7:0] bank_output_en,
    output reg [255:0] bank_read_addr,
    input wire [11:0] wa
);
    // Reset is exceptional initialization: async assertion, two fixed release
    // edges, then normal compiler-scheduled commands. Only this two-flop leaf
    // touches the external reset pin; no normal command or data cycle is added.
    (* async_reg = "true" *) reg reset_meta,reset_ready;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;reset_ready<=0;end
        else begin reset_meta<=1;reset_ready<=reset_meta;end
    wire local_rst_n=reset_ready;
    // A response-valid pin capture already supplies the landing write enables.
    // Compare its captured value with the equally delayed expected mask; only
    // malformed response fault reporting gains one edge, never execution stalls.
    reg [7:0] expect_response_q;
    reg response_check_q;
    always @(posedge clk or negedge local_rst_n)
        if(!local_rst_n)begin expect_response_q<=0;response_check_q<=0;end
        else begin expect_response_q<=expect_mask[7];response_check_q<=1;end
    // Pin captures. Normal execution advances the absolute input cycle once per
    // related clock edge; this is checked, never used to reschedule execution.
    function automatic [31:0] inc32(input [31:0] x);
        inc32={x[31:24]+8'(&x[23:0]),x[23:16]+8'(&x[15:0]),
               x[15:8]+8'(&x[7:0]),x[7:0]+8'd1};
    endfunction
    reg [31:0] cycle_q;
    wire [31:0] cycle=inc32(cycle_q);
    reg cycle_valid_q,wa_valid_q;reg [11:0] wa_q;
    always @(posedge clk)cycle_q<=cycle_in;
    always @(posedge clk or negedge local_rst_n)
        if(!local_rst_n)begin cycle_valid_q<=0;wa_valid_q<=0;wa_q<=0;end
        else begin cycle_valid_q<=1;wa_valid_q<=1;wa_q<=wa;end
`ifndef SYNTHESIS
    always @(posedge clk)if(local_rst_n&&cycle_valid_q&&cycle_in!==cycle)
        $fatal(1,"DMA absolute cycle did not advance by one");
`endif
    // ---- descriptor pipeline (stage A capture, stage B products + static checks) ----
    reg a_v,p_valid,q_valid,b_v; reg [226:0] a_mv,b_mv; reg [31:0] a_ci,a_cd,b_ci,b_cd; reg a_cb,b_cb; reg [15:0] a_ce,b_ce;
    reg [40:0] b_vprod,b_hprod; reg [14:0] b_nchunk; reg [7:0] b_rchunk; reg [17:0] b_total; reg b_static_ok;
    wire [10:0] a_nsec=a_mv[219:209];                     // nsec<=1024 when valid (range term below)
    wire [7:0] a_rchunk=8'((a_mv[219:209]+11'd7)>>3);      // ceil(nsec/8) <= 128 when valid
    wire [6:0] a_rows_m1=7'(a_mv[192:186]-7'd1);           // rows<=128 when valid
    reg [226:0] p_mv,q_mv;reg [31:0] p_ci,p_cd,q_ci,q_cd;reg p_cb,q_cb;reg [15:0] p_ce,q_ce;
    reg [14:0] p_vpart[0:3],p_hpart[0:3];
    reg [22:0] q_vlo,q_vhi,q_hlo,q_hhi;
    reg [14:0] p_nchunk,q_nchunk;reg [7:0] p_rchunk,q_rchunk;
    reg [17:0] p_total,q_total;reg p_static_ok,q_static_ok;
    reg [18:0] b_vbase_end;reg [40:0] b_hbase_end;
    reg [31:0] b_ci_m2,b_ci_m3,b_cd_m1,b_cd_m2,b_cd_m3,b_cd_m4,b_end_m2,b_end_m3;
    always @(posedge clk or negedge local_rst_n)
        if(!local_rst_n) begin a_v<=0;p_valid<=0;q_valid<=0;b_v<=0;end
        else begin a_v<=mv_v;p_valid<=a_v;q_valid<=p_valid;b_v<=q_valid;end
    always @(posedge clk) begin
        a_mv<=mv;a_ci<=issue_at;a_cd<=drain_at;a_cb<=mv_wb_bank;a_ce<=mv_wb_epoch;
        p_mv<=a_mv;p_ci<=a_ci;p_cd<=a_cd;p_cb<=a_cb;p_ce<=a_ce;
        for(integer i=0;i<4;i=i+1)begin
            p_vpart[i]<=15'(a_rows_m1)*15'(a_mv[45+8*i+:8]);
            p_hpart[i]<=15'(a_rows_m1)*15'(a_mv[138+8*i+:8]);
        end
        p_rchunk<=(a_mv[226:209]==0)?8'd0:a_rchunk;
        p_nchunk<=15'(a_mv[193:186])*15'(a_rchunk);
        p_total<=18'(a_nsec)*18'(a_mv[193:186]);
        p_static_ok<=a_mv[1:0]==1&&a_mv[94:93]==0&&a_mv[92:77]==1&&a_mv[185:170]==1&&
            (a_mv[4:2]==0||a_mv[4:2]==5)&&(a_mv[97:95]==0||a_mv[97:95]==5)&&a_mv[4:2]==a_mv[97:95]&&
            a_mv[10:5]==0&&a_mv[50:45]==0&&a_mv[208:206]==0&&a_mv[205:186]!=0&&a_mv[205:186]<=128&&
            a_mv[226:209]!=0&&a_mv[226:209]<=1024&&
            a_mv[102:98]==0&&a_mv[142:138]==0&&a_mv[137:135]==0&&a_mv[134:133]==2'(STK)&&
            (a_mv[205:186]==1||a_mv[76:45]>=a_mv[226:206])&&
            (a_mv[205:186]==1||a_mv[169:138]==(32'(a_mv[226:206])<<2))&&
            (a_mv[205:186]==1||a_mv[211:206]==0);
        q_mv<=p_mv;q_ci<=p_ci;q_cd<=p_cd;q_cb<=p_cb;q_ce<=p_ce;
        q_vlo<=23'(p_vpart[0])+(23'(p_vpart[1])<<8);
        q_vhi<=23'(p_vpart[2])+(23'(p_vpart[3])<<8);
        q_hlo<=23'(p_hpart[0])+(23'(p_hpart[1])<<8);
        q_hhi<=23'(p_hpart[2])+(23'(p_hpart[3])<<8);
        q_rchunk<=p_rchunk;q_nchunk<=p_nchunk;q_total<=p_total;q_static_ok<=p_static_ok;
        b_mv<=q_mv;b_ci<=q_ci;b_cd<=q_cd;b_cb<=q_cb;b_ce<=q_ce;
        b_vprod<=41'(q_vlo)+(41'(q_vhi)<<16);
        b_hprod<=41'(q_hlo)+(41'(q_hhi)<<16);
        b_rchunk<=q_rchunk;b_nchunk<=q_nchunk;b_total<=q_total;b_static_ok<=q_static_ok;
        b_vbase_end<=19'(q_mv[21:5])+19'(q_mv[219:206]);
        b_hbase_end<={4'b0,q_mv[134:98]}+(41'(q_mv[219:206])<<2);
        b_ci_m2<=q_ci-32'd2;b_ci_m3<=q_ci-32'd3;
        b_cd_m1<=q_cd-32'd1;b_cd_m2<=q_cd-32'd2;b_cd_m3<=q_cd-32'd3;b_cd_m4<=q_cd-32'd4;
        b_end_m2<=q_cd+32'(q_nchunk)-32'd1;b_end_m3<=q_cd+32'(q_nchunk)-32'd2;   // end_at = cd+nchunk+1
    end
    // ---- registered schedule matches (H-HARDEN 10-15 r4) ----
    // Every absolute-cycle event (issue, drain, pre-drain read, fill start, end) is a 1-bit register
    // computed one edge ahead from the captured cycle and a pre-offset copy of its target, so no
    // 32-bit cycle increment/compare sits in front of the wide enables. Exact under the input contract
    // cycle_in(k)=cycle_in(k-1)+1 (checked above); identical issue/drain/fill/end/fault edges.
    reg [31:0] c_ci_m2,c_cd_m1,c_cd_m2,c_cd_m3,c_end_m2;
    reg c_ihit,c_dhit,c_phit,c_fhit,c_ehit,c_ilead_ok,c_lag_ok,c_vok,c_hok,c_nchunk_ok;
    reg [40:0] c_hend_d;
    reg [18:0] c_vend_d;
    reg [14:0] c_nchunk; reg [7:0] c_rchunk; reg [17:0] c_total; reg c_static_ok;
    reg [31:0] ni_m2,nd_m2,nd_m3,fa_m2,ea_m2;
    reg m_issue,m_drain,m_pre,m_fill,m_end;
    reg [7:0] rq_v;reg [15:0] rq_payload[0:7];
    reg cv,cb;reg [15:0] ce;reg [226:0] cm;
    reg [7:0] chunks,issue_index,drain_index,row_chunks,column;
    reg [17:0] row_sectors;
    reg [19:0] land_left;
    reg [16:0] row_vm,chunk_vm;
    reg [31:0] vm_stride;
    reg [36:0] row_hbm,chunk_hbm;
    reg [31:0] hbm_stride;
    // The compiler-ordered drain follows exactly the same row/column address recurrence as issue.
    reg [36:0] drain_row_hbm,drain_chunk_hbm;
    reg [7:0] drain_column;
    wire [7:0] drain_mask=(drain_column==row_chunks-1 && row_sectors[2:0]!=0)?
                              ((8'd1<<row_sectors[2:0])-1'b1):8'hff;
    reg [7:0] expect_mask[0:7];reg [6:0] expect_tag[0:7];
    reg [7:0] rr_valid;
    reg [7:0] read_mask_q,output_mask_q;
    reg dirty,src_sent;
    // wb_ready is pin-captured; a not-ready landing at the first drain is an exceptional fault
    // reported one edge later (normal execution unchanged).
    reg wb_ready_q,first_drain_q;
    // Counter consumes registered acknowledgements (exact modulo-2^32 carry-save + prefix add).
    function automatic [31:0] add_total_sub_ack(
        input [31:0] a, input [31:0] b, input [31:0] subtrahend);
        reg [31:0] inv_c, sum_bits, carry_bits, prop_bits, pref_p, pref_g;
        reg [31:0] next_p, next_g, carry_in;
        integer step, bit_index;
        begin
            inv_c = ~subtrahend;
            sum_bits = a ^ b ^ inv_c;
            carry_bits = ((a & b) | (a & inv_c) | (b & inv_c)) << 1;
            prop_bits = sum_bits ^ carry_bits;
            pref_p = prop_bits;
            pref_g = sum_bits & carry_bits;
            for (step=1; step<32; step=step*2) begin
                next_p = pref_p; next_g = pref_g;
                for (bit_index=step; bit_index<32; bit_index=bit_index+1) begin
                    next_g[bit_index] = pref_g[bit_index] |
                        (pref_p[bit_index] & pref_g[bit_index-step]);
                    next_p[bit_index] = pref_p[bit_index] & pref_p[bit_index-step];
                end
                pref_p=next_p; pref_g=next_g;
            end
            carry_in = ((pref_g | pref_p) << 1) | 32'd1;
            add_total_sub_ack = prop_bits ^ carry_in;
        end
    endfunction
    reg [31:0] pending_sectors;
    reg [31:0] ack_base_q;
    wire observed_pending_zero=pending_sectors==32'(wa_q);
    wire issue_slot=busy&&!cv&&issue_index<chunks&&m_issue;
    wire drain_slot=busy&&!cv&&drain_index<chunks&&m_drain;
    wire valid_move=c_static_ok&&c_vok&&c_nchunk_ok&&c_hok&&c_ilead_ok&&c_lag_ok;
    wire reload=cv&&valid_move;
    reg [7:0] issue_mask;
    reg [15:0] issue_sec;
    always @* begin
        issue_mask=8'hff;
        if(column==row_chunks-1 && row_sectors[2:0]!=0)
            issue_mask=(8'd1<<row_sectors[2:0])-1'b1;
        if(chunk_vm>=17'd65536) issue_sec=16'h8000|16'((chunk_vm-17'd65536)>>3);
        else issue_sec={1'b0,2'(QID),chunk_vm[15:3]};
    end
    assign bank_read_slot=drain_index[6:0];
    // Each landing bank pin-captures the raw response valid itself; its slot is this
    // register one edge ahead, so the bank's write is on the same edge as before.
    assign bank_write_slot=expect_tag[7];
    assign bank_output_en=output_mask_q;
    for(genvar b=0;b<8;b=b+1)begin:RQ
        assign rq[b*17+:17]={rq_v[b],rq_payload[b]};
    end
    always @(posedge clk) ack_base_q<=pending_sectors-32'(wa_q);
    always @(posedge clk) begin
        cm<=b_mv;cb<=b_cb;ce<=b_ce;
        c_nchunk<=b_nchunk;c_rchunk<=b_rchunk;c_total<=b_total;
        c_static_ok<=b_static_ok&&b_mv[44:22]==0&&b_vprod[40:17]==0;
        // acceptance range terms evaluated one edge early from the same operands
        c_vend_d=b_vbase_end+19'(b_vprod[16:0]);
        c_hend_d=b_hbase_end+b_hprod;
        c_vok<=(b_mv[44:5]<65536&&41'(c_vend_d)<=65536)||(b_mv[44:5]>=65536&&41'(c_vend_d)<=98304);
        c_hok<=c_hend_d[40:37]==0&&c_hend_d[36:35]==2'(STK)&&{1'b0,c_hend_d[34:0]}<=STACK_BYTES;
        c_nchunk_ok<=b_nchunk>0&&b_nchunk<=128;
        c_ilead_ok<=$signed(b_ci_m2-cycle_q)>=1;            // ci-cycle(k)>=1, cycle(k)=cycle_q(k-1)+2
        c_lag_ok<=$signed(b_cd-b_ci)>=10;
        c_ihit<=cycle_q==b_ci_m3;                            // cycle(k)+1==ci
        c_dhit<=cycle_q==b_cd_m3;                            // cycle(k)+1==cd
        c_phit<=cycle_q==b_cd_m4;                            // cycle(k)+2==cd
        c_fhit<=cycle_q==b_cd_m2;                            // cycle(k)+1==cd+1
        c_ehit<=cycle_q==b_end_m3;                           // cycle(k)+1==cd+nchunk+1
        c_ci_m2<=b_ci_m2;c_cd_m1<=b_cd_m1;c_cd_m2<=b_cd_m2;c_cd_m3<=b_cd_m3;c_end_m2<=b_end_m2;
        for(integer b=0;b<8;b=b+1)bank_read_addr[b*32+:32]<=drain_chunk_hbm[36:5]+32'(b)+((MUT==1&&b==1)?32'd1:32'd0);
        for(integer t=1;t<8;t=t+1)expect_tag[t]<=expect_tag[t-1];
        expect_tag[0]<=issue_index[6:0];
        for(integer b=0;b<8;b=b+1) rq_payload[b]<={issue_sec[15:3],3'(b)};
        wb_ready_q<=wb_ready;
        // match registers: value of each absolute-cycle comparison at the next edge
        m_issue<=issue_slot?1'b1:reload?c_ihit:(cycle_q==ni_m2);
        m_drain<=drain_slot?1'b1:reload?c_dhit:(cycle_q==nd_m2);
        m_pre<=drain_slot?1'b0:reload?c_phit:(cycle_q==nd_m3);
        m_fill<=reload?c_fhit:(cycle_q==fa_m2);
        m_end<=reload?c_ehit:(cycle_q==ea_m2);
        if(reload)begin ni_m2<=c_ci_m2;nd_m2<=c_cd_m2;nd_m3<=c_cd_m3;fa_m2<=c_cd_m1;ea_m2<=c_end_m2;end
        else begin
            if(issue_slot)ni_m2<=inc32(ni_m2);
            if(drain_slot)begin nd_m2<=inc32(nd_m2);nd_m3<=inc32(nd_m3);end
        end
    end
    always @(posedge clk or negedge local_rst_n) begin:CONTROL
        integer nland;
        if(!local_rst_n)begin
            cv<=0;busy<=0;quiet<=1;dirty<=0;src_sent<=0;mv_src<=0;mv_done<=0;mv_fault<=0;
            wb_reserve_v<=0;wb_reserve_sectors<=0;wb_reserve_base<=0;wb_fill_start<=0;wb_reserve_bank<=0;wb_fill_bank<=0;wb_reserve_epoch<=0;wb_fill_epoch<=0;bank_read_en<=0;read_mask_q<=0;output_mask_q<=0;rr_valid<=0;
            issue_index<=0;drain_index<=0;chunks<=0;column<=0;land_left<=0;first_drain_q<=0;
            pending_sectors<=0;
            for(integer t=0;t<8;t=t+1)expect_mask[t]<=0;
            for(integer b=0;b<8;b=b+1)begin rq_v[b]<=0;end
        end else begin
            cv<=b_v;mv_src<=0;mv_done<=0;wb_reserve_v<=0;
            bank_read_en<=0;
            if(busy&&!cv&&drain_index<chunks)begin
                if(drain_slot)begin
                    if(drain_index+1'b1<chunks)begin
                        if((drain_column==row_chunks-1?8'd0:drain_column+1'b1)==row_chunks-1&&row_sectors[2:0]!=0)
                            bank_read_en<=(8'd1<<row_sectors[2:0])-1'b1;
                        else bank_read_en<=8'hff;
                    end
                end else if(m_pre)bank_read_en<=drain_mask;
            end
            wb_fill_start<=busy&&m_fill;
            if(b_v&&(busy||cv))mv_fault<=1;
            for(integer t=1;t<8;t=t+1)expect_mask[t]<=expect_mask[t-1];
            expect_mask[0]<=issue_slot?issue_mask:8'd0;
            for(integer b=0;b<8;b=b+1)begin
                rq_v[b]<=issue_slot&&issue_mask[b];
                rr_valid[b]<=rr_valid_i[b];
                if(response_check_q && rr_valid[b]!==expect_response_q[b])mv_fault<=1;
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
            first_drain_q<=drain_slot&&drain_index==0;
            if(first_drain_q&&!wb_ready_q)mv_fault<=1;
            if(drain_slot)begin
                drain_index<=drain_index+1'b1;
                if(drain_column==row_chunks-1)begin
                    drain_column<=0;drain_row_hbm<=drain_row_hbm+37'(hbm_stride);
                    drain_chunk_hbm<=drain_row_hbm+37'(hbm_stride);
                end else begin drain_column<=drain_column+1'b1;drain_chunk_hbm<=drain_chunk_hbm+37'd256;end
            end
            if(busy&&m_end)busy<=0;
            // land_left = total_sectors - landed (mod 2^20): last landing when this edge's count equals it
            nland=0;for(integer b=0;b<8;b=b+1)nland=nland+int'(rr_valid[b]);
            land_left<=land_left-20'(nland);
            if(busy&&!src_sent&&nland!=0&&land_left==20'(nland))begin mv_src<=1;src_sent<=1;end
            pending_sectors<=pending_sectors-32'(wa_q);
            if(wa_valid_q&&32'(wa_q)>ack_base_q)mv_fault<=1;
            quiet<=!busy&&!cv&&!b_v&&observed_pending_zero;
            if(dirty&&!busy&&!cv&&!b_v&&observed_pending_zero)begin mv_done<=1;dirty<=0;end
            if(cv)begin
                if(!valid_move)mv_fault<=1;
                else begin
                    busy<=1;dirty<=1;src_sent<=0;
                    issue_index<=0;drain_index<=0;column<=0;chunks<=8'(c_nchunk);row_chunks<=c_rchunk;
                    row_sectors<=18'(cm[226:209]);land_left<=20'(c_total);
                    row_vm<=cm[21:5];chunk_vm<=cm[21:5];vm_stride<=cm[76:45];
                    row_hbm<=cm[134:98];chunk_hbm<=cm[134:98];hbm_stride<=cm[169:138];
                    drain_row_hbm<=cm[134:98];drain_chunk_hbm<=cm[134:98];drain_column<=0;
                    pending_sectors<=add_total_sub_ack(pending_sectors,32'(c_total),32'(wa_q));
                    wb_reserve_bank<=cb;wb_fill_bank<=cb;wb_reserve_epoch<=ce;wb_fill_epoch<=ce;
                    wb_reserve_v<=1;wb_reserve_sectors<=12'(c_total);wb_reserve_base<=cm[134:103];
                end
            end
        end
    end
endmodule
`default_nettype wire
