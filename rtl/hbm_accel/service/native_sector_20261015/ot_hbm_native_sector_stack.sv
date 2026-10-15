`timescale 1ns/1ps
// Arbitrary single-sector native K-port owner. Actual existing R/W bank/refresh
// sequencers drive physical row/column commands. No behavioral DRAM scheduler
// exists inside this module. One outstanding request per PC; len=1 only.
// R/W state protection and physical admission remain separate requirements.
module ot_hbm_native_sector_stack #(
    parameter integer PHASE=0
)(
    input wire clk,rst_n,
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
        localparam[2:0]IDLE=0,DESC=1,ENQUEUE=2,COMMAND=3,RETURN=4,REPLY=5,DRAIN=6;
        reg[2:0]state;
        reg sticky,we;
        reg[29:0]sector;
        reg[16:0]tag;
        reg[255:0]data,reply;
        reg[31:0]mask;
        reg[31:0]observed_open;
        wire[18:0]physical_row=sector[29:15];
        wire[4:0]physical_bank={((sector[14:12]^physical_row[4:2])),(sector[1:0]^physical_row[1:0])};
        wire[4:0]physical_column=sector[11:7];
        wire[29:0]incoming=k_addr[p*30+:30];
        wire[4:0]incoming_pc=incoming[6:2]^incoming[11:7]^incoming[16:12];
        wire legal=k_len[p*4+:4]==1 && incoming_pc==5'(p) && incoming<30'd703125000;
        wire dr,wr,cv,cwe,caq;
        wire[4:0]cb,cc;
        wire[2:0]credit_return=3'(dram_rvalid[p] && state==RETURN);
        assign k_rdy[p]=state==IDLE && !sticky && !pc_fault[p] && legal;
        assign kr_v[p]=state==REPLY && !sticky && !pc_fault[p];
        assign kr_tag[p*17+:17]=tag;assign kr_beat[p*4+:4]=0;assign kr_data[p*256+:256]=reply;
        assign col_v[p]=cv;assign col_we[p]=cwe;
        assign col_bank[p*5+:5]=cb;assign col_col[p*5+:5]=cc;
        assign col_data[p*256+:256]=data;assign col_strb[p*32+:32]=mask;
        assign owner_fault[p]=sticky;
        // The current row is loaded without inventing a streaming read. The
        // access queue carries the exact target bank/column and read/write bit.
        ot_hbm_r14_stream_pc #(.ENABLE(1),.PC(p),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(4),
            .REF_PHASE((PHASE+p*118/32)%118)) controller(
            .clk(clk),.rst_n(rst_n),.desc_v(state==DESC),.desc_r(dr),.desc_row(physical_row),.desc_n(11'd0),
            .go(1'b1),.next_posted(1'b0),.row_v(row_v[p]),.row_prio(),.row_gnt(1'b1),
            .row_op(row_op[p*3+:3]),.row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
            .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(credit_return),.busy(),.ref_fault(pc_fault[p]),
            .wr_v(state==ENQUEUE),.wr_bank(physical_bank),.wr_col(physical_column),.wr_r(wr),
            .col_we(cwe),.wr_rd(!we),.col_aq(caq));
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin state<=IDLE;sticky<=0;we<=0;sector<=0;tag<=0;data<=0;reply<=0;mask<=0;observed_open<=0;k_wr_done[p]<=0;end
            else begin
                k_wr_done[p]<=0;
                if(k_v[p] && state==IDLE && !legal)sticky<=1;
                if(k_v[p] && k_rdy[p])begin
                    sector<=incoming;we<=k_we[p];tag<=k_tag[p*17+:17];data<=k_wdata[p*256+:256];mask<=k_wstrb[p*32+:32];state<=DESC;
                end
                if(row_v[p])begin
                    case(row_op[p*3+:3])
                        0:observed_open[row_bank[p*5+:5]]<=0;
                        1:observed_open[row_bank[p*5+:5]]<=1;
                        5:observed_open<=0;
                        default:;
                    endcase
                end
                if(state==DESC && dr)state<=DRAIN;
                // Drain stale physical rows before queueing an access: the
                // existing access queue deliberately protects its target bank
                // from PRE, so enqueueing first would deadlock a row change.
                if(state==DRAIN && observed_open==0)state<=ENQUEUE;
                if(state==ENQUEUE && wr)state<=COMMAND;
                if(cv)begin
                    if(state!=COMMAND || cwe!=we || cb!=physical_bank || cc!=physical_column || (!we && !caq))sticky<=1;
                    if(we)begin k_wr_done[p]<=1;state<=IDLE;end
                    else state<=RETURN;
                end
                if(dram_rvalid[p])begin
                    if(state!=RETURN)sticky<=1;
                    else begin reply<=dram_rdata[p*256+:256];state<=REPLY;end
                end
                if(kr_v[p] && kr_rdy[p])state<=IDLE;
            end
        end
    end
endmodule
