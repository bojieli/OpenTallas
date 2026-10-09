`timescale 1ns/1ps
// HGI-1 normative header; actual sequencer tuple width is unchanged. Its current
// legacy decode/count truncation is NOT reinterpreted here. Caller supplies full
// effective counts/POS1 from the resolved descriptor/DYN path (Claude owner).
module ot_hgi_att_record_adapter #(
    parameter integer MUT_RING=0,MUT_COUNTS=0,MUT_FIELDS=0,MUT_EARLY_DONE=0
)(
    input wire clk,rst_n,
    input wire rec_v,output wire rec_r,
    input wire [127:0] rec_hdr,
    input wire [255:0] rec_sut,
    input wire [1023:0] rec_desc,
    input wire [20:0] rec_pos1,
    input wire [31:0] rec_b_count,rec_c_count,
    output wire att_v,input wire att_r,
    output wire [127:0] att_hdr,
    output wire [1023:0] att_desc,
    input wire att_done,att_fault,
    output wire rows_cmd_v,input wire rows_cmd_r,
    output wire rows_ring,
    output wire [20:0] rows_pos1,rows_b_n,rows_b_m,rows_c_n,
    input wire rows_done,rows_fault,
    output wire busy,output reg u_done,u_fault
);
    reg active,record_pending,setup_pending,rows_pending,setup_sent,rows_sent,att_retired,rows_retired;
    reg [127:0] hdr_q;reg [1023:0] desc_q;
    reg [127:0] att_hdr_q;reg [1023:0] att_desc_q;
    reg [31:0] b_count_q,c_count_q;
    reg [20:0] pos1_q,bn_q,bm_q,cn_q;reg ring_q;
    wire [255:0] b=desc_q[256+:256], c=desc_q[512+:256];
    wire [6:0] opnd=hdr_q[99:93];
    wire c_present=opnd[2];
    wire [5:0] b_nsel=b[206:201],c_nsel=c[206:201];
    wire bad_header=(hdr_q[127:124]!=5) || (hdr_q[123:118]>1) || hdr_q[92] ||
                    (opnd[4:0] & 5'b11011)!=5'b10011 || (|opnd[6:5]);
    wire bad_range=(pos1_q>21'h100000) || (b_count_q>32'h00100000) || (c_count_q>32'h00100000);
    wire bad_B_count=(b_nsel==0 && b_count_q!={12'b0,b[67:48]}) ||
                     (b_nsel==2 && b_count_q!={11'b0,pos1_q});
    wire bad_C_count=c_present ? ((c_nsel==0 && c_count_q!={12'b0,c[67:48]}) ||
                                  (c_nsel==2 && c_count_q!={11'b0,pos1_q})) : (c_count_q!=0);
    wire bad_ring=hdr_q[72] && ((b[87:68]==0) ||
                   ((b[87:68] & (b[87:68]-1'b1))!=0) ||
                   (b_count_q>{12'b0,b[87:68]}) || (b_count_q>{11'b0,pos1_q}));
    assign rec_r=!active && !record_pending;
    assign att_v=active && setup_pending;
    assign att_hdr=att_hdr_q;
    assign att_desc=att_desc_q;
    assign rows_cmd_v=active && setup_sent && rows_pending;
    assign rows_ring=ring_q;
    assign rows_pos1=pos1_q;
    assign rows_b_n=bn_q;
    assign rows_b_m=bm_q;
    assign rows_c_n=cn_q;
    assign busy=active || record_pending;
    always @(posedge clk) begin
        if(!rst_n) begin
            active<=0;record_pending<=0;setup_pending<=0;rows_pending<=0;setup_sent<=0;rows_sent<=0;
            att_retired<=0;rows_retired<=0;u_done<=0;u_fault<=0;
            hdr_q<=0;desc_q<=0;att_hdr_q<=0;att_desc_q<=0;pos1_q<=0;b_count_q<=0;c_count_q<=0;bn_q<=0;bm_q<=0;cn_q<=0;ring_q<=0;
        end else begin
            u_done<=0;u_fault<=0;
            if(rec_v && rec_r) begin
                record_pending<=1;hdr_q<=rec_hdr;desc_q<=rec_desc;pos1_q<=rec_pos1;
                b_count_q<=rec_b_count;c_count_q<=rec_c_count;
            end else if(record_pending) begin
                record_pending<=0;
                if(bad_header || bad_range || bad_B_count || bad_C_count || bad_ring) begin
                    u_done<=1;u_fault<=1;
                end else begin
                    active<=1;setup_pending<=1;rows_pending<=1;setup_sent<=0;rows_sent<=0;
                    att_retired<=0;rows_retired<=0;
                    // Output station uses the existing decode edge, so no extra cycle.
                    att_hdr_q<=MUT_FIELDS ? (hdr_q ^ (128'b1<<118)) : hdr_q;
                    att_desc_q<=desc_q;
                    bn_q<=MUT_COUNTS ? {1'b0,b_count_q[19:0]} : b_count_q[20:0];
                    bm_q<={1'b0,b[87:68]};cn_q<=c_present ? c_count_q[20:0] : 21'b0;
                    ring_q<=MUT_RING ? 1'b0 : hdr_q[72];
                end
            end else if(active) begin
                if(att_v && att_r) begin setup_pending<=0;setup_sent<=1;end
                if(rows_cmd_v && rows_cmd_r) begin rows_pending<=0;rows_sent<=1;end
                if(setup_sent && att_done) att_retired<=1;
                if(rows_sent && rows_done) rows_retired<=1;
                if((setup_sent && att_fault) || (rows_sent && rows_fault)) begin
                    active<=0;setup_pending<=0;rows_pending<=0;u_done<=1;u_fault<=1;
                end else if((rows_retired || (rows_sent && rows_done)) &&
                            (MUT_EARLY_DONE || att_retired || (setup_sent && att_done))) begin
                    active<=0;u_done<=1;
                end
            end
        end
    end
endmodule
