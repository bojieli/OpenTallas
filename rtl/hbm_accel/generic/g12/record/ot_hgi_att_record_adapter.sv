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
    reg active,setup_pending,rows_pending,setup_sent,rows_sent,att_retired,rows_retired;
    reg [127:0] hdr_q;reg [1023:0] desc_q;
    reg [20:0] pos1_q,bn_q,bm_q,cn_q;reg ring_q;
    wire [255:0] b=rec_desc[256+:256], c=rec_desc[512+:256];
    wire [6:0] opnd=rec_hdr[99:93];
    wire c_present=opnd[2];
    wire [5:0] b_nsel=b[206:201],c_nsel=c[206:201];
    wire bad_header=(rec_hdr[127:124]!=5) || (rec_hdr[123:118]>1) || rec_hdr[92] ||
                    (opnd[4:0] & 5'b11011)!=5'b10011 || (|opnd[6:5]);
    wire bad_range=(rec_pos1>21'h100000) || (rec_b_count>32'h00100000) || (rec_c_count>32'h00100000);
    wire bad_B_count=(b_nsel==0 && rec_b_count!={12'b0,b[67:48]}) ||
                     (b_nsel==2 && rec_b_count!={11'b0,rec_pos1});
    wire bad_C_count=c_present ? ((c_nsel==0 && rec_c_count!={12'b0,c[67:48]}) ||
                                  (c_nsel==2 && rec_c_count!={11'b0,rec_pos1})) : (rec_c_count!=0);
    wire bad_ring=rec_hdr[72] && ((b[87:68]==0) ||
                   ((b[87:68] & (b[87:68]-1'b1))!=0) ||
                   (rec_b_count>{12'b0,b[87:68]}) || (rec_b_count>{11'b0,rec_pos1}));
    assign rec_r=!active;
    assign att_v=active && setup_pending;
    assign att_hdr=hdr_q;
    assign att_desc=desc_q;
    assign rows_cmd_v=active && setup_sent && rows_pending;
    assign rows_ring=ring_q;
    assign rows_pos1=pos1_q;
    assign rows_b_n=bn_q;
    assign rows_b_m=bm_q;
    assign rows_c_n=cn_q;
    assign busy=active;
    always @(posedge clk) begin
        if(!rst_n) begin
            active<=0;setup_pending<=0;rows_pending<=0;setup_sent<=0;rows_sent<=0;
            att_retired<=0;rows_retired<=0;u_done<=0;u_fault<=0;
            hdr_q<=0;desc_q<=0;pos1_q<=0;bn_q<=0;bm_q<=0;cn_q<=0;ring_q<=0;
        end else begin
            u_done<=0;u_fault<=0;
            if(rec_v && rec_r) begin
                if(bad_header || bad_range || bad_B_count || bad_C_count || bad_ring) begin
                    u_done<=1;u_fault<=1;
                end else begin
                    active<=1;setup_pending<=1;rows_pending<=1;setup_sent<=0;rows_sent<=0;
                    att_retired<=0;rows_retired<=0;
                    hdr_q<=MUT_FIELDS ? (rec_hdr ^ (128'b1<<118)) : rec_hdr;
                    desc_q<=rec_desc;pos1_q<=rec_pos1;
                    bn_q<=MUT_COUNTS ? {1'b0,rec_b_count[19:0]} : rec_b_count[20:0];
                    bm_q<={1'b0,b[87:68]};cn_q<=c_present ? rec_c_count[20:0] : 21'b0;
                    ring_q<=MUT_RING ? 1'b0 : rec_hdr[72];
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
