`timescale 1ns/1ps
// H-DIE 2026-10-15: ot_hbm_svc_native_sector_pipeline_stack with each PC as an ot_hbm_svc_pc_ctrl_leaf instance (same
// ports, same behaviour; the original module stays byte-identical).
// Arbitrary single-sector native K-port owner. Actual existing R/W bank/refresh
// sequencers drive physical row/column commands. No behavioral DRAM scheduler
// exists inside this module. Same-row FIFO32 per PC; reads len1..4, writes len1.
// Each PC reserves32 physical read responses, with actual SRAM payload storage.
// Explicit pc_clk roots must match clk frequency/phase with synchronous SDC.
// R/W state protection and physical admission remain separate requirements.
module ot_hbm_svc_native_sector_pipeline_leaves #(
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
    reg ca_fault;
    assign fault=ca_fault || (|pc_fault) || (|owner_fault);
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)ca_fault<=0;
        else for(integer c=0;c<16;c=c+1)
            if(row_v[2*c] && row_v[2*c+1])ca_fault<=1;
    end
    for(genvar p=0;p<32;p=p+1)begin:g_pc
        ot_hbm_svc_pc_ctrl_leaf #(.PHASE(PHASE),.P(p)) u_ctrl(
            .clk(pc_clk[p]),.rst_n(rst_n),
            .k_v(k_v[p]),.k_rdy(k_rdy[p]),.k_we(k_we[p]),.k_addr(k_addr[p*30+:30]),.k_len(k_len[p*4+:4]),.k_tag(k_tag[p*17+:17]),
            .k_wdata(k_wdata[p*256+:256]),.k_wstrb(k_wstrb[p*32+:32]),
            .kr_v(kr_v[p]),.kr_rdy(kr_rdy[p]),.kr_tag(kr_tag[p*17+:17]),.kr_beat(kr_beat[p*4+:4]),.kr_data(kr_data[p*256+:256]),
            .k_wr_done(k_wr_done[p]),
            .row_v(row_v[p]),.row_op(row_op[p*3+:3]),.row_bank(row_bank[p*5+:5]),.row_row(row_row[p*19+:19]),
            .col_v(col_v[p]),.col_we(col_we[p]),.col_bank(col_bank[p*5+:5]),.col_col(col_col[p*5+:5]),
            .col_data(col_data[p*256+:256]),.col_strb(col_strb[p*32+:32]),
            .dram_rvalid(dram_rvalid[p]),.dram_rdata(dram_rdata[p*256+:256]),
            .pc_fault(pc_fault[p]),.owner_fault(owner_fault[p]));
    end
endmodule
