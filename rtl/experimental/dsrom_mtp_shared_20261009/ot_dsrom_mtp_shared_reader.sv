`timescale 1ns/1ps
// Default-off existing read1 client facade. req_ready is the arbiter's real
// grant, not a native VM ready pin. rsp_valid/owner must come from the actual
// outstanding-read router. No numeric E3 base or free native port is assumed.
module ot_dsrom_mtp_shared_reader #(parameter integer ENABLE=0)(
    input wire clk,rst_n,
    input wire cmd_valid,output wire cmd_ready,input wire [73:0] cmd_context,
    input wire [13:0] cmd_base,input wire [14:0] cmd_region_rows,
    input wire cmd_native_write_retired,
    input wire lease_valid,input wire [73:0] lease_context,
    output reg lease_release,output wire [73:0] release_context,
    output wire pub_cmd_valid,input wire pub_cmd_ready,
    output wire [73:0] pub_cmd_context,
    output wire req_valid,input wire req_ready,output wire [13:0] req_row,
    output wire [73:0] req_context,output wire [6:0] req_word,
    input wire rsp_valid,input wire [511:0] rsp_data,input wire rsp_fault,
    input wire [73:0] rsp_context,input wire [6:0] rsp_word,
    output wire pub_valid,input wire pub_ready,output wire [511:0] pub_data,
    output wire [73:0] pub_context,output wire [6:0] pub_word,
    output wire pub_last,pub_fmt_fp32,pub_error,
    input wire pub_retired,input wire [73:0] pub_retired_context,
    output wire busy,output reg fault
);
    localparam [5:0] IDLE=1,PCMD=2,REQ=4,WAIT=8,SEND=16,DRAIN=32;
    reg [5:0] state,state_n;
    reg [73:0] context_q,context_n;
    reg [13:0] base_q,base_n;
    reg [14:0] limit_q,limit_n;
    reg [6:0] word_q,word_n;
    reg [511:0] data_q,data_n;
    wire guard_bad=(state_n!=~state)||(context_n!=~context_q)||
        (base_n!=~base_q)||(limit_n!=~limit_q)||(word_n!=~word_q)||
        (data_n!=~data_q);
    wire [14:0] address={1'b0,base_q}+{8'd0,word_q};
    reg bad_payload;
    always @*begin
        bad_payload=0;
        for(integer j=0;j<16;j=j+1)
            if(rsp_data[32*j+:16]!=0||rsp_data[32*j+23+:8]==8'hff)bad_payload=1;
    end
    assign cmd_ready=ENABLE&&state==IDLE&&!fault&&!guard_bad;
    assign pub_cmd_valid=ENABLE&&state==PCMD&&!fault&&!guard_bad;
    assign pub_cmd_context=context_q;
    assign req_valid=ENABLE&&state==REQ&&!fault&&!guard_bad;
    assign req_row=address[13:0];assign req_context=context_q;assign req_word=word_q;
    assign pub_valid=ENABLE&&state==SEND&&!fault&&!guard_bad;
    assign pub_data=data_q;assign pub_context=context_q;assign pub_word=word_q;
    assign pub_last=word_q==79;assign pub_fmt_fp32=0;assign pub_error=0;
    assign busy=state!=IDLE;assign release_context=context_q;
    task automatic transition(input [5:0] ns);state<=ns;state_n<=~ns;endtask
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            state<=IDLE;state_n<=~IDLE;fault<=0;lease_release<=0;
            context_q<=0;context_n<=~74'd0;base_q<=0;base_n<=~14'd0;
            limit_q<=0;limit_n<=~15'd0;word_q<=0;word_n<=~7'd0;
            data_q<=0;data_n<=~512'd0;
        end else if(ENABLE&&!fault)begin
            lease_release<=0;
            if(guard_bad||(state!=IDLE&&(!lease_valid||lease_context!=context_q))||
                (rsp_valid&&state!=WAIT)||(pub_retired&&state!=DRAIN))fault<=1;
            else case(state)
                IDLE:if(cmd_valid)begin
                    if(!lease_valid||lease_context!=cmd_context||!cmd_native_write_retired||
                        {1'b0,cmd_base}+15'd80>cmd_region_rows||cmd_region_rows>16384)fault<=1;
                    else begin
                        context_q<=cmd_context;context_n<=~cmd_context;
                        base_q<=cmd_base;base_n<=~cmd_base;limit_q<=cmd_region_rows;limit_n<=~cmd_region_rows;
                        word_q<=0;word_n<=~7'd0;transition(PCMD);
                    end
                end
                PCMD:if(pub_cmd_ready)transition(REQ);
                REQ:begin
                    if(address>=limit_q||address[14])fault<=1;
                    else if(req_ready)transition(WAIT);
                end
                WAIT:if(rsp_valid)begin
                    if(rsp_fault||rsp_context!=context_q||rsp_word!=word_q||bad_payload)fault<=1;
                    else begin data_q<=rsp_data;data_n<=~rsp_data;transition(SEND);end
                end
                SEND:if(pub_ready)begin
                    if(word_q==79)transition(DRAIN);
                    else begin word_q<=word_q+1'b1;word_n<=~(word_q+7'd1);transition(REQ);end
                end
                DRAIN:if(pub_retired)begin
                    if(pub_retired_context!=context_q)fault<=1;
                    else begin lease_release<=1;transition(IDLE);end
                end
                default:fault<=1;
            endcase
        end
    end
endmodule
