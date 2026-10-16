`timescale 1ns/1ps
// H-DIE 2026-10-15: ONE pseudo-channel of ot_hbm_svc_native_sector_pipeline_stack as a hardenable die leaf (the stack's
// g_pc[P] body verbatim, per-PC slices renamed to scalar ports; the stack's ca_fault channel-pair check and fault OR stay
// in the parent ot_hbm_svc_native_sector_pipeline_leaves).  Real controller: actual ot_hbm_r14_stream_pc sequencer +
// same-row FIFO32 + 32 reserved responses in an actual 128x256 SRAM.  K side faces the SM service group; row/column/data
// side faces the PHY-only abstract (the only modelled boundary).  clk = this PC's pc_clk root.
// OREG=1 (H-DIE 2026-10-15, die default): every PHY-side command output (row_*, col_*, write data/strobe) leaves from a
// flop -- one uniform extra cycle on the command path to the PHY (relative DRAM command timing unchanged); the read
// return path is unchanged.  OREG=0 is the stack body exactly.
// KREG=1 (die default): the K request enters a 2-entry pin-registered skid; k_rdy = skid not full (a register), so no
// K input reaches k_rdy or the queue combinationally; one extra hbm cycle on the request, full rate.  KREG=0: as the stack.
module ot_hbm_svc_pc_ctrl_leaf #(
    parameter integer PHASE=0,
    parameter integer P=0,
    parameter integer OREG=1,
    parameter integer KREG=1
)(
    input wire clk,rst_n,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output reg k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output wire pc_fault,owner_fault
);
    localparam[1:0]IDLE=0,DESC=1,DRAIN=2,RUN=3;
    wire i_v,i_we;wire[29:0]i_addr;wire[3:0]i_len;wire[16:0]i_tag;wire[255:0]i_wdata;wire[31:0]i_wstrb;
    wire i_rdy;
    reg[1:0]state;reg sticky;reg[18:0]active_row;reg[31:0]observed_open;
    reg[4:0]wp,rp,ep;reg[5:0]count,unposted;
    reg[319:0]queue[0:31];
    reg[5:0]read_reserved,pending_count,response_count;
    reg[4:0]pending_wp,pending_rp,response_wp,response_rp;
    reg[20:0]pending_identity[0:31],response_identity[0:31];
    reg[20:0]head_identity;reg head_valid;
    wire[255:0]response_data;
    wire[29:0]incoming=i_addr;
    wire[18:0]incoming_row={4'b0,incoming[29:15]};
    wire[4:0]incoming_pc=incoming[6:2]^incoming[11:7]^incoming[16:12];
    wire[3:0]length=i_len;
    wire legal=length>=1 && length<=4 && (!i_we || length==1) &&
        {1'b0,incoming[1:0]}+length<=4 && incoming_pc==5'(P) && {1'b0,incoming}+length<=31'd703125000;
    wire same_row=incoming_row==active_row;
    wire dr,wr,cv,cwe,caq;wire[4:0]cb,cc;
    wire[319:0]head=queue[rp],push=queue[ep];
    wire push_read=!push[319];
    wire enqueue=state==RUN && unposted!=0 && (!push_read || read_reserved<32) && !sticky;
    wire accepted=i_v&&i_rdy;wire posted=enqueue&&wr;
    wire posted_read=posted&&push_read;
    wire column_read=cv&&!cwe;
    wire response_take=kr_v&&kr_rdy;
    wire row_idle=count==0&&read_reserved==0;
    assign i_rdy=!sticky&&!pc_fault&&legal&&count+length<=32&&
        (state==IDLE || (state==RUN && (same_row || row_idle)));
    generate if(KREG!=0)begin:g_kreg
        reg[339:0]sk[0:1];reg[1:0]sn;reg sw,sr;
        wire push_k=k_v&&k_rdy,pop_k=i_v&&i_rdy;
        assign k_rdy=sn!=2'd2;
        assign i_v=sn!=0;
        assign {i_we,i_addr,i_len,i_tag,i_wstrb,i_wdata}=sk[sr];
        always @(posedge clk)if(push_k)sk[sw]<={k_we,k_addr,k_len,k_tag,k_wstrb,k_wdata};
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin sn<=0;sw<=0;sr<=0;end
            else begin
                if(push_k)sw<=~sw;
                if(pop_k)sr<=~sr;
                sn<=sn+(push_k?2'd1:2'd0)-(pop_k?2'd1:2'd0);
            end
    end else begin:g_kdirect
        assign i_v=k_v;assign i_we=k_we;assign i_addr=k_addr;assign i_len=k_len;assign i_tag=k_tag;
        assign i_wdata=k_wdata;assign i_wstrb=k_wstrb;assign k_rdy=i_rdy;
    end endgenerate

    assign kr_v=head_valid&&!sticky&&!pc_fault;
    assign kr_tag=head_identity[20:4];assign kr_beat=head_identity[3:0];assign kr_data=response_data;
    wire r_v;wire[2:0]r_op;wire[4:0]r_bank;wire[18:0]r_row;
    generate if(OREG!=0)begin:g_oreg
        reg q_rv,q_cv,q_cwe;reg[2:0]q_rop;reg[4:0]q_rbank,q_cb,q_cc;reg[18:0]q_rrow;reg[255:0]q_cd;reg[31:0]q_cs;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin q_rv<=0;q_cv<=0;q_cwe<=0;end else begin q_rv<=r_v;q_cv<=cv;q_cwe<=cwe;end
        always @(posedge clk)begin q_rop<=r_op;q_rbank<=r_bank;q_rrow<=r_row;q_cb<=cb;q_cc<=cc;q_cd<=head[255:0];q_cs<=head[287:256];end
        assign row_v=q_rv;assign row_op=q_rop;assign row_bank=q_rbank;assign row_row=q_rrow;
        assign col_v=q_cv;assign col_we=q_cwe;assign col_bank=q_cb;assign col_col=q_cc;assign col_data=q_cd;assign col_strb=q_cs;
    end else begin:g_comb
        assign row_v=r_v;assign row_op=r_op;assign row_bank=r_bank;assign row_row=r_row;
        assign col_v=cv;assign col_we=cwe;assign col_bank=cb;assign col_col=cc;
        assign col_data=head[255:0];assign col_strb=head[287:256];
    end endgenerate
    assign owner_fault=sticky;
    wire response_read=!sticky&&((!head_valid&&response_count!=0)||(response_take&&response_count>1));
    wire[4:0]response_read_address=response_take?response_rp+5'd1:response_rp;
    wire response_write=dram_rvalid&&pending_count!=0&&!sticky;
    ot_sram_1r1w_128x256_m1_r2c2 u_response_payload(
        .clk(clk),.r_ce_in(response_read),.r_addr_in({2'b0,response_read_address}),.rd_out(response_data),
        .w_ce_in(response_write),.w_addr_in({2'b0,response_wp}),.wd_in(dram_rdata),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    ot_hbm_r14_stream_pc #(.ENABLE(1),.PC(P),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),
        .REF_PHASE((PHASE+P*118/32)%118)) controller(
        .clk(clk),.rst_n(rst_n),.desc_v(state==DESC),.desc_r(dr),.desc_row(active_row),.desc_n(11'd0),
        .go(1'b1),.next_posted(1'b0),.row_v(r_v),.row_prio(),.row_gnt(1'b1),
        .row_op(r_op),.row_bank(r_bank),.row_row(r_row),
        // desc_n=0 uses the actual access queue only. AQ reads never
        // consume the separate streaming-reader credit counter.
        .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(3'b0),.busy(),.ref_fault(pc_fault),
        .wr_v(enqueue),.wr_bank(push[318:314]),.wr_col(push[313:309]),.wr_r(wr),
        .col_we(cwe),.wr_rd(push_read),.col_aq(caq));
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            state<=IDLE;sticky<=0;active_row<=0;observed_open<=0;wp<=0;rp<=0;ep<=0;count<=0;unposted<=0;
            read_reserved<=0;pending_count<=0;response_count<=0;pending_wp<=0;pending_rp<=0;response_wp<=0;response_rp<=0;
            head_identity<=0;head_valid<=0;k_wr_done<=0;
        end else begin
            k_wr_done<=0;
            if(i_v&&!legal)sticky<=1;
            if(accepted)begin
                for(integer b=0;b<4;b=b+1)if(b<length)
                    queue[5'(wp+b)]<={i_we,incoming[14:12]^incoming[19:17],(2'(incoming[1:0]+b)^incoming[16:15]),incoming[11:7],i_tag,4'(b),i_wstrb,i_wdata};
                wp<=wp+5'(length);
                if(state==IDLE || !same_row)begin active_row<=incoming_row;state<=DESC;end
            end
            count<=count+(accepted?6'(length):6'd0)-(cv?6'd1:6'd0);
            unposted<=unposted+(accepted?6'(length):6'd0)-(posted?6'd1:6'd0);
            read_reserved<=read_reserved+(posted_read?6'd1:6'd0)-(response_take?6'd1:6'd0);
            pending_count<=pending_count+(column_read?6'd1:6'd0)-(dram_rvalid?6'd1:6'd0);
            response_count<=response_count+(dram_rvalid?6'd1:6'd0)-(response_take?6'd1:6'd0);
            if(posted)ep<=ep+1'b1;
            if(r_v)begin
                case(r_op)
                    0:observed_open[r_bank]<=0;
                    1:observed_open[r_bank]<=1;
                    5:observed_open<=0;
                    default:;
                endcase
            end
            if(state==DESC && dr)state<=DRAIN;
            if(state==DRAIN && observed_open==0)state<=RUN;
            if(cv)begin
                if(state!=RUN || count==0 || cwe!=head[319] || cb!=head[318:314] || cc!=head[313:309] || (!cwe&&!caq))sticky<=1;
                rp<=rp+1'b1;
                if(cwe)k_wr_done<=1;
                else begin
                    if(pending_count>=32)sticky<=1;
                    pending_identity[pending_wp]<=head[308:288];pending_wp<=pending_wp+1'b1;
                end
            end
            if(dram_rvalid)begin
                if(pending_count==0 || (response_count>=32&&!response_take))sticky<=1;
                else begin response_identity[response_wp]<=pending_identity[pending_rp];pending_rp<=pending_rp+1'b1;response_wp<=response_wp+1'b1;end
            end
            if(response_read)begin head_identity<=response_identity[response_read_address];head_valid<=1;end
            else if(response_take)head_valid<=0;
            if(response_take)begin
                if(read_reserved==0||response_count==0)sticky<=1;
                response_rp<=response_rp+1'b1;
            end
            if(read_reserved>32||pending_count>32||response_count>32)sticky<=1;
        end
    end
endmodule
