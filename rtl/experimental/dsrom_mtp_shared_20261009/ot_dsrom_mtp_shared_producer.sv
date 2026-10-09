`timescale 1ns/1ps
// Opt-in primary shared-expert endpoint. Native W2 must publish BF16, as
// golden expert()/linear_q() requires. This endpoint preserves those bits and
// widens them to FP32 for the shared-LAST add. One context owns the SRAM until
// all 80 output flits retire; six draft frames share it serially.
module ot_dsrom_mtp_shared_producer #(
    parameter integer MAXU=866, MAX_CONTEXT=1048576,
    parameter [71:0] READ_INJECT=72'd0
)(
    input wire clk,rst_n,
    input wire cmd_valid,output wire cmd_ready,input wire [73:0] cmd_context,
    input wire in_valid,output wire in_ready,input wire [511:0] in_bf16,
    input wire [73:0] in_context,input wire [5:0] in_word,
    input wire in_last,in_fmt_fp32,in_error,
    output wire out_valid,input wire out_ready,output wire [511:0] out_data,
    output wire [73:0] out_context,output wire [6:0] out_word,
    output wire out_last,out_corrected,output wire busy,output reg fault
);
    localparam [7:0] CMD=8'h01,LOAD=8'h02,STORE=8'h04,WCOMMIT=8'h08,
        RREQ=8'h10,RWAIT=8'h20,RDECODE=8'h40,RHOLD=8'h80;
    reg [7:0] state,state_n;
    reg [73:0] context_q,context_n;
    reg [5:0] write_word,write_n,read_word,read_n;
    reg part,part_n;
    reg [511:0] pack_q,pack_n;
    reg [575:0] held_code;
    reg [255:0] output_q,output_n;
    reg corrected_q;
    wire [575:0] write_code;
    wire [767:0] bank_data;
    wire [511:0] decoded;
    wire [7:0] ce,ue;
    wire guard_bad=(state_n!=~state)||(context_n!=~context_q)||
        (write_n!=~write_word)||(read_n!=~read_word)||(part_n!=~part)||
        (pack_n!=~pack_q)||(output_n!=~output_q);
    genvar k;
    generate for(k=0;k<8;k=k+1)begin:g_ecc
        ot_s81_secded_enc72 enc(.d(pack_q[64*k+:64]),.c(write_code[72*k+:72]));
        ot_s81_secded_dec72 dec(.c(held_code[72*k+:72]^(k==0?READ_INJECT:72'd0)),
            .d(decoded[64*k+:64]),.ce(ce[k]),.ue(ue[k]));
    end
    for(k=0;k<3;k=k+1)begin:g_mem
        wire [767:0] wd={192'd0,write_code};
        ot_sram_1r1w_256x256_m2_r2c2 mem(
            .clk(clk),.r_ce_in(state==RREQ&&!fault&&!guard_bad),
            .r_addr_in({2'd0,read_word}),.rd_out(bank_data[256*k+:256]),
            .w_ce_in(state==STORE&&!fault&&!guard_bad),
            .w_addr_in({2'd0,write_word}),.wd_in(wd[256*k+:256]),
            .w_mask_in({256{1'b1}}),.rr_en(2'd0),.rr_addr(14'd0),
            .cr_en(2'd0),.cr_sel(16'd0));
    end
    for(k=0;k<16;k=k+1)begin:g_widen
        assign out_data[32*k+:32]={output_q[16*k+:16],16'd0};
    end endgenerate
    assign cmd_ready=state==CMD&&!fault&&!guard_bad;
    assign in_ready=state==LOAD&&!fault&&!guard_bad;
    assign out_valid=state==RHOLD&&!fault&&!guard_bad;
    assign out_context=context_q;
    assign out_word={read_word,part};
    assign out_last=read_word==39&&part;
    assign out_corrected=out_valid&&corrected_q;
    assign busy=state!=CMD;
    task automatic transition(input [7:0] next_state);
        state<=next_state;state_n<=~next_state;
    endtask
    integer lane;
    reg input_nonfinite;
    always @*begin
        input_nonfinite=0;
        for(integer j=0;j<32;j=j+1)
            if(in_bf16[16*j+7+:8]==8'hff)input_nonfinite=1;
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            state<=CMD;state_n<=~CMD;fault<=0;
            context_q<=0;context_n<=~74'd0;
            write_word<=0;write_n<=~6'd0;read_word<=0;read_n<=~6'd0;
            part<=0;part_n<=1;pack_q<=0;pack_n<=~512'd0;
            held_code<=0;output_q<=0;output_n<=~256'd0;corrected_q<=0;
        end else if(!fault)begin
            if(guard_bad)fault<=1;
            else case(state)
                CMD:if(cmd_valid)begin
                    if(cmd_context[32+:10]>=MAXU||cmd_context[42+:21]>=MAX_CONTEXT||
                        cmd_context[67+:2]>2||cmd_context[71+:3]>5)fault<=1;
                    else begin
                        context_q<=cmd_context;context_n<=~cmd_context;
                        write_word<=0;write_n<=~6'd0;read_word<=0;read_n<=~6'd0;
                        part<=0;part_n<=1;transition(LOAD);
                    end
                end
                LOAD:if(in_valid)begin
                    if(in_context!=context_q||in_word!=write_word||
                        in_last!=(write_word==39)||in_fmt_fp32||in_error||input_nonfinite)fault<=1;
                    else begin pack_q<=in_bf16;pack_n<=~in_bf16;transition(STORE);end
                end
                STORE:transition(WCOMMIT);
                WCOMMIT:begin
                    if(write_word==39)transition(RREQ);
                    else begin write_word<=write_word+1'b1;write_n<=~(write_word+6'd1);transition(LOAD);end
                end
                RREQ:transition(RWAIT);
                RWAIT:begin held_code<=bank_data[575:0];transition(RDECODE);end
                RDECODE:begin
                    if(|ue)fault<=1;
                    else begin output_q<=decoded[255:0];output_n<=~decoded[255:0];
                        corrected_q<=|ce;transition(RHOLD);end
                end
                RHOLD:if(out_ready)begin
                    if(!part)begin
                        part<=1;part_n<=0;output_q<=decoded[511:256];output_n<=~decoded[511:256];
                    end else begin
                        part<=0;part_n<=1;
                        if(read_word==39)transition(CMD);
                        else begin read_word<=read_word+1'b1;read_n<=~(read_word+6'd1);transition(RREQ);end
                    end
                end
                default:fault<=1;
            endcase
        end
    end
endmodule
