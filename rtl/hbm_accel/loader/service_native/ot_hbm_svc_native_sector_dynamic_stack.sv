`timescale 1ns/1ps
// Arbitrary single-sector native K-port owner. Actual existing R/W bank/refresh
// sequencers drive physical row/column commands. No behavioral DRAM scheduler
// exists inside this module. Same-row FIFO32 per PC; reads len1..4, writes len1.
// Each PC reserves32 physical read responses, with actual SRAM payload storage.
// Explicit pc_clk roots must match clk frequency/phase with synchronous SDC.
// R/W state protection and physical admission remain separate requirements.
module ot_hbm_svc_native_sector_dynamic_stack #(
    parameter integer DYNAMIC_CA=0,
    parameter integer INTENT_PREVIEW=0,REGISTERED_HEAD_BYPASS=0,
    parameter integer FAST_IDLE_DESC=0,
    parameter integer AQ_ROW_LEASE=0,
    parameter integer COLUMN_CLOSE_GUARD=1,
    parameter integer PHASE=0
)(
    input wire clk,rst_n,input wire[31:0]pc_clk,
    input wire[31:0]k_v,output wire[31:0]k_rdy,input wire[31:0]k_we,
    input wire[959:0]k_addr,input wire[127:0]k_len,input wire[543:0]k_tag,
    input wire[8191:0]k_wdata,input wire[1023:0]k_wstrb,
    output wire[31:0]kr_v,input wire[31:0]kr_rdy,
    output wire[543:0]kr_tag,output wire[127:0]kr_beat,output wire[8191:0]kr_data,
    output wire[31:0]k_wr_done,
    output wire[31:0]row_v,output wire[95:0]row_op,output wire[159:0]row_bank,
    output wire[607:0]row_row,
    output wire[31:0]col_v,col_we,output wire[159:0]col_bank,col_col,
    output wire[8191:0]col_data,output wire[1023:0]col_strb,
    input wire[31:0]dram_rvalid,input wire[8191:0]dram_rdata,
    output wire fault
);
    wire[31:0]pc_fault,owner_fault;
    wire[31:0]pc_row_request,pc_row_grant,pc_row_priority;
    assign row_v=pc_row_request & pc_row_grant;
    reg ca_fault;
    assign fault=ca_fault || (|pc_fault) || (|owner_fault);
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)ca_fault<=0;
        else for(integer c=0;c<16;c=c+1)
            if(row_v[2*c] && row_v[2*c+1])ca_fault<=1;
    end
    if(DYNAMIC_CA)begin:g_dynamic_ca
        for(genvar channel=0;channel<16;channel=channel+1)begin:g_pair
            reg prefer_odd;
            wire even_req=pc_row_request[2*channel],odd_req=pc_row_request[2*channel+1];
            wire even_ref=even_req&&(row_op[6*channel+:3]==6||row_op[6*channel+:3]==4);
            wire odd_ref=odd_req&&(row_op[6*channel+3+:3]==6||row_op[6*channel+3+:3]==4);
            wire choose_odd=odd_req&&(!even_req||(!even_ref&&(odd_ref||prefer_odd)));
            assign pc_row_grant[2*channel]=even_req&&!choose_odd;
            assign pc_row_grant[2*channel+1]=choose_odd;
            always @(posedge clk or negedge rst_n)begin
                if(!rst_n)prefer_odd<=0;
                else if(pc_row_grant[2*channel])prefer_odd<=1;
                else if(pc_row_grant[2*channel+1])prefer_odd<=0;
            end
        end
    end else begin assign pc_row_grant=32'hffffffff;end
    for(genvar p=0;p<32;p=p+1)begin:g_pc
        localparam[1:0]IDLE=0,DESC=1,DRAIN=2,RUN=3;
        reg pc_write_done;
        assign k_wr_done[p]=pc_write_done;
        reg[1:0]state;reg sticky;reg[18:0]active_row;reg[31:0]observed_open;
        reg[4:0]wp,rp,ep;reg[5:0]count,unposted;
        reg[319:0]queue[0:31];
        reg[5:0]read_reserved,pending_count,response_count;
        reg[4:0]pending_wp,pending_rp,response_wp,response_rp;
        reg[20:0]pending_identity[0:31],response_identity[0:31];
        reg[20:0]head_identity;reg head_valid;
        wire[255:0]response_data;
        reg [255:0] head_payload;reg head_bypass;
        wire[31:0]bank_intent;wire intent_fault;
        wire[29:0]incoming=k_addr[p*30+:30];
        wire[18:0]incoming_row={4'b0,incoming[29:15]};
        wire[4:0]incoming_pc=incoming[6:2]^incoming[11:7]^incoming[16:12];
        wire[3:0]length=k_len[p*4+:4];
        wire legal=length>=1 && length<=4 && (!k_we[p] || length==1) &&
            {1'b0,incoming[1:0]}+length<=4 && incoming_pc==5'(p) && {1'b0,incoming}+length<=31'd703125000;
        wire same_row=incoming_row==active_row;
        wire dr,wr,cv,cwe,caq;wire[4:0]cb,cc;
        wire[319:0]head=queue[rp],push=queue[ep];
        wire push_read=!push[319];
        wire enqueue=state==RUN && unposted!=0 && (!push_read || read_reserved<32) && !sticky;
        wire accepted=k_v[p]&&k_rdy[p];wire posted=enqueue&&wr;
        wire posted_read=posted&&push_read;
        wire column_read=cv&&!cwe;
        wire response_take=kr_v[p]&&kr_rdy[p];
        wire initial_descriptor=FAST_IDLE_DESC && state==IDLE && accepted;
        wire row_idle=count==0&&read_reserved==0;
        assign k_rdy[p]=!sticky&&!intent_fault&&!pc_fault[p]&&legal&&count+length<=32&&
            (state==IDLE || (state==RUN && (same_row || row_idle)));
        assign kr_v[p]=head_valid&&!sticky&&!intent_fault&&!pc_fault[p];
        assign kr_tag[p*17+:17]=head_identity[20:4];assign kr_beat[p*4+:4]=head_identity[3:0];assign kr_data[p*256+:256]=(REGISTERED_HEAD_BYPASS&&head_bypass)?head_payload:response_data;
        assign col_v[p]=cv;assign col_we[p]=cwe;
        assign col_bank[p*5+:5]=cb;assign col_col[p*5+:5]=cc;
        assign col_data[p*256+:256]=head[255:0];assign col_strb[p*32+:32]=head[287:256];
        assign owner_fault[p]=sticky||intent_fault;
        wire response_read=!sticky&&((!head_valid&&response_count!=0)||(response_take&&response_count>1));
        wire[4:0]response_read_address=response_take?response_rp+5'd1:response_rp;
        wire response_write=dram_rvalid[p]&&pending_count!=0&&!sticky;
        ot_sram_1r1w_128x256_m1_r2c2 u_response_payload(
            .clk(pc_clk[p]),.r_ce_in(response_read),.r_addr_in({2'b0,response_read_address}),.rd_out(response_data),
            .w_ce_in(response_write),.w_addr_in({2'b0,response_wp}),.wd_in(dram_rdata[p*256+:256]),.w_mask_in({256{1'b1}}),
            .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
        reg[31:0] incoming_banks;
        always @*begin
            incoming_banks=0;
            for(integer beat=0;beat<4;beat=beat+1)if(beat<length)
                incoming_banks[{incoming[14:12]^incoming[19:17],2'(incoming[1:0]+beat)^incoming[16:15]}]=1;
        end
        if(INTENT_PREVIEW)begin:g_intent_debt
            reg[5:0]debt[0:31];reg bad;
            assign intent_fault=bad;
            for(genvar bank=0;bank<32;bank=bank+1)assign bank_intent[bank]=state==RUN && debt[bank]!=0;
            always @(posedge pc_clk[p] or negedge rst_n)begin
                if(!rst_n)begin bad<=0;for(integer bank=0;bank<32;bank=bank+1)debt[bank]<=0;end
                else begin
                    if(cv && debt[cb]==0)bad<=1;
                    for(integer bank=0;bank<32;bank=bank+1)begin
                        if(accepted && (state==IDLE||!same_row))debt[bank]<=incoming_banks[bank]?6'd1:6'd0;
                        else case({accepted&&incoming_banks[bank],cv&&cb==5'(bank)})
                            2'b10:begin if(debt[bank]>=32)bad<=1;debt[bank]<=debt[bank]+1'b1;end
                            2'b01:debt[bank]<=debt[bank]-1'b1;
                            default:;
                        endcase
                    end
                end
            end
        end else begin assign bank_intent=0;assign intent_fault=0;end
        ot_hbm_svc_native_stream_pc_dynamic #(.DYNAMIC_CA(DYNAMIC_CA),.INTENT_PREVIEW(INTENT_PREVIEW),.AQ_ROW_LEASE(AQ_ROW_LEASE),.COLUMN_CLOSE_GUARD(COLUMN_CLOSE_GUARD),.ENABLE(1),.PC(p),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),
            .REF_PHASE((PHASE+p*118/32)%118)) controller(
            .clk(pc_clk[p]),.rst_n(rst_n),.aq_bank_intent(bank_intent),.desc_v(state==DESC || initial_descriptor),.desc_r(dr),.desc_row(initial_descriptor?incoming_row:active_row),.desc_n(11'd0),
            .go(1'b1),.next_posted(1'b0),.row_v(pc_row_request[p]),.row_prio(pc_row_priority[p]),.row_gnt(pc_row_grant[p]),
            .row_op(row_op[p*3+:3]),.row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
            // desc_n=0 uses the actual access queue only. AQ reads never
            // consume the separate streaming-reader credit counter.
            .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(3'b0),.busy(),.ref_fault(pc_fault[p]),
            .wr_v(enqueue),.wr_bank(push[318:314]),.wr_col(push[313:309]),.wr_r(wr),
            .col_we(cwe),.wr_rd(push_read),.col_aq(caq));
        always @(posedge pc_clk[p] or negedge rst_n)begin
            if(!rst_n)begin
                state<=IDLE;sticky<=0;active_row<=0;observed_open<=0;wp<=0;rp<=0;ep<=0;count<=0;unposted<=0;
                read_reserved<=0;pending_count<=0;response_count<=0;pending_wp<=0;pending_rp<=0;response_wp<=0;response_rp<=0;
                head_identity<=0;head_valid<=0;head_payload<=0;head_bypass<=0;pc_write_done<=0;
            end else begin
                pc_write_done<=0;
                if(k_v[p]&&!legal)sticky<=1;
                if(accepted)begin
                    for(integer b=0;b<4;b=b+1)if(b<length)
                        queue[5'(wp+b)]<={k_we[p],incoming[14:12]^incoming[19:17],(2'(incoming[1:0]+b)^incoming[16:15]),incoming[11:7],k_tag[p*17+:17],4'(b),k_wstrb[p*32+:32],k_wdata[p*256+:256]};
                    wp<=wp+5'(length);
                    if(state==IDLE || !same_row)begin
                        active_row<=incoming_row;
                        state<=(initial_descriptor && dr)?RUN:DESC;
                    end
                end
                count<=count+(accepted?6'(length):6'd0)-(cv?6'd1:6'd0);
                unposted<=unposted+(accepted?6'(length):6'd0)-(posted?6'd1:6'd0);
                read_reserved<=read_reserved+(posted_read?6'd1:6'd0)-(response_take?6'd1:6'd0);
                pending_count<=pending_count+(column_read?6'd1:6'd0)-(dram_rvalid[p]?6'd1:6'd0);
                response_count<=response_count+(dram_rvalid[p]?6'd1:6'd0)-(response_take?6'd1:6'd0);
                if(posted)ep<=ep+1'b1;
                if(row_v[p])begin
                    case(row_op[p*3+:3])
                        0:observed_open[row_bank[p*5+:5]]<=0;
                        1:observed_open[row_bank[p*5+:5]]<=1;
                        5:observed_open<=0;
                        default:;
                    endcase
                end
                if(state==DESC && dr)state<=DRAIN;
                if(state==DRAIN && observed_open==0)state<=RUN;
                if(cv)begin
                    if(state!=RUN || count==0 || cwe!=head[319] || cb!=head[318:314] || cc!=head[313:309] || (!cwe&&!caq))sticky<=1;
                    rp<=rp+1'b1;
                    if(cwe)pc_write_done<=1;
                    else begin
                        if(pending_count>=32)sticky<=1;
                        pending_identity[pending_wp]<=head[308:288];pending_wp<=pending_wp+1'b1;
                    end
                end
                if(dram_rvalid[p])begin
                    if(pending_count==0 || (response_count>=32&&!response_take))sticky<=1;
                    else begin response_identity[response_wp]<=pending_identity[pending_rp];pending_rp<=pending_rp+1'b1;response_wp<=response_wp+1'b1;end
                end
                if(response_read)begin head_identity<=response_identity[response_read_address];head_valid<=1;head_bypass<=0;end
                else if(response_take)head_valid<=0;
                if(REGISTERED_HEAD_BYPASS && response_write &&
                   ((!head_valid&&response_count==0)||(response_take&&response_count==1)))begin
                    head_identity<=pending_identity[pending_rp];head_payload<=dram_rdata[p*256+:256];
                    head_valid<=1;head_bypass<=1;
                end
                if(response_take)begin
                    if(read_reserved==0||response_count==0)sticky<=1;
                    response_rp<=response_rp+1'b1;
                end
                if(read_reserved>32||pending_count>32||response_count>32)sticky<=1;
            end
        end
    end
endmodule
