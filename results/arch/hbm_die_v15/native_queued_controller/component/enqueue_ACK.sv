`timescale 1ns/1ps
// Arbitrary single-sector native K-port owner. Actual existing R/W bank/refresh
// sequencers drive physical row/column commands. No behavioral DRAM scheduler
// exists inside this module. Same-row FIFO32 per PC; len=1 only.
// Explicit pc_clk roots must match clk frequency/phase with synchronous SDC.
// R/W state protection and physical admission remain separate requirements.
module ot_hbm_svc_native_sector_queued_stack #(
    parameter integer PHASE=0
)(
    input wire clk,rst_n,input wire[31:0]pc_clk,
    input wire[31:0]k_v,output wire[31:0]k_rdy,input wire[31:0]k_we,
    input wire[959:0]k_addr,input wire[127:0]k_len,input wire[543:0]k_tag,
    input wire[8191:0]k_wdata,input wire[1023:0]k_wstrb,
    output wire[31:0]kr_v,input wire[31:0]kr_rdy,
    output wire[543:0]kr_tag,output wire[127:0]kr_beat,output wire[8191:0]kr_data,
    output reg[31:0]k_wr_done,
    output wire[31:0]row_v,output wire[95:0]row_op,output wire[159:0]row_bank,
    output wire[607:0]row_row,
    output wire[31:0]col_v,col_we,output wire[159:0]col_bank,col_col,
    output wire[8191:0]col_data,output wire[1023:0]col_strb,
    input wire[31:0]dram_rvalid,input wire[8191:0]dram_rdata,
    output wire fault
);
    wire[31:0]pc_fault,owner_fault;
    reg ca_fault;
    assign fault=ca_fault || (|pc_fault) || (|owner_fault);
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)ca_fault<=0;
        else for(integer c=0;c<16;c=c+1)
            if(row_v[2*c] && row_v[2*c+1])ca_fault<=1;
    end
    for(genvar p=0;p<32;p=p+1)begin:g_pc
        localparam[1:0]IDLE=0,DESC=1,DRAIN=2,RUN=3;
        reg[1:0]state;reg sticky;reg[18:0]active_row;
        reg[31:0]observed_open;
        reg[4:0]wp,rp,ep;reg[5:0]count,unposted;
        reg[315:0]queue[0:31];
        reg read_busy,read_wait,reply_valid;reg[16:0]read_tag;reg[255:0]reply;
        wire[29:0]incoming=k_addr[p*30+:30];
        wire[18:0]incoming_row={4'b0,incoming[29:15]};
        wire[4:0]incoming_pc=incoming[6:2]^incoming[11:7]^incoming[16:12];
        wire[4:0]incoming_bank={incoming[14:12]^incoming[19:17],incoming[1:0]^incoming[16:15]};
        wire legal=k_len[p*4+:4]==1 && incoming_pc==5'(p) && incoming<30'd703125000;
        wire same_row=incoming_row==active_row;
        wire dr,wr,cv,cwe,caq;wire[4:0]cb,cc;
        wire[315:0]head=queue[rp],push=queue[ep];
        wire push_read=!push[315];
        wire enqueue=state==RUN && unposted!=0 && (!push_read || !read_busy) && !sticky;
        wire accepted=k_v[p]&&k_rdy[p];wire posted=enqueue&&wr;
        wire row_idle=count==0&&!read_busy;
        assign k_rdy[p]=!sticky&&!pc_fault[p]&&legal&&count<32&&
            (state==IDLE || (state==RUN && (same_row || row_idle)));
        assign kr_v[p]=reply_valid&&!sticky&&!pc_fault[p];
        assign kr_tag[p*17+:17]=read_tag;assign kr_beat[p*4+:4]=0;assign kr_data[p*256+:256]=reply;
        assign col_v[p]=cv;assign col_we[p]=cwe;
        assign col_bank[p*5+:5]=cb;assign col_col[p*5+:5]=cc;
        assign col_data[p*256+:256]=head[255:0];assign col_strb[p*32+:32]=head[287:256];
        assign owner_fault[p]=sticky;
        ot_hbm_r14_stream_pc #(.ENABLE(1),.PC(p),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),
            .REF_PHASE((PHASE+p*118/32)%118)) controller(
            .clk(pc_clk[p]),.rst_n(rst_n),.desc_v(state==DESC),.desc_r(dr),.desc_row(active_row),.desc_n(11'd0),
            .go(1'b1),.next_posted(1'b0),.row_v(row_v[p]),.row_prio(),.row_gnt(1'b1),
            .row_op(row_op[p*3+:3]),.row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
            .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(3'(dram_rvalid[p]&&read_wait)),.busy(),.ref_fault(pc_fault[p]),
            .wr_v(enqueue),.wr_bank(push[314:310]),.wr_col(push[309:305]),.wr_r(wr),
            .col_we(cwe),.wr_rd(push_read),.col_aq(caq));
        always @(posedge pc_clk[p] or negedge rst_n)begin
            if(!rst_n)begin
                state<=IDLE;sticky<=0;active_row<=0;observed_open<=0;wp<=0;rp<=0;ep<=0;count<=0;unposted<=0;
                read_busy<=0;read_wait<=0;reply_valid<=0;read_tag<=0;reply<=0;k_wr_done[p]<=0;
            end else begin
                k_wr_done[p]<=0;
                if(k_v[p]&&!legal)sticky<=1;
                if(accepted)begin k_wr_done[p]<=k_we[p];
                    queue[wp]<={k_we[p],incoming_bank,incoming[11:7],k_tag[p*17+:17],k_wstrb[p*32+:32],k_wdata[p*256+:256]};wp<=wp+1'b1;
                    if(state==IDLE || !same_row)begin active_row<=incoming_row;state<=DESC;end
                end
                case({accepted,cv})
                    2'b10:count<=count+1'b1;
                    2'b01:count<=count-1'b1;
                    default:;
                endcase
                case({accepted,posted})
                    2'b10:unposted<=unposted+1'b1;
                    2'b01:unposted<=unposted-1'b1;
                    default:;
                endcase
                if(posted)begin ep<=ep+1'b1;if(push_read)read_busy<=1;end
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
                    if(state!=RUN || count==0 || cwe!=head[315] || cb!=head[314:310] || cc!=head[309:305] || (!cwe&&!caq))sticky<=1;
                    rp<=rp+1'b1;
                    if(cwe)k_wr_done[p]<=1;
                    else begin read_tag<=head[304:288];read_wait<=1;end
                end
                if(dram_rvalid[p])begin
                    if(!read_wait)sticky<=1;
                    else begin reply<=dram_rdata[p*256+:256];read_wait<=0;reply_valid<=1;end
                end
                if(kr_v[p]&&kr_rdy[p])begin reply_valid<=0;read_busy<=0;end
            end
        end
    end
endmodule
