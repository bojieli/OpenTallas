`timescale 1ns/1ps
// Review53 successor: plain finite control, SECDED only on mutable SRAM payload.
// Native W2 contribution is BF16 rounded then widened FP32,80 full512b flits.
module ot_s81_shared_publisher_plain #(
 parameter integer ENABLE=0,MAXU=866,MAX_CONTEXT=1048576,
 parameter [71:0] READ_INJECT=72'd0
)(
 input wire clk,rst_n,cmd_valid,output wire cmd_ready,input wire[73:0] cmd_context,
 input wire in_valid,output wire in_ready,input wire[511:0] in_data,
 input wire[73:0] in_context,input wire[6:0] in_word,
 input wire in_last,in_fmt_fp32,in_error,
 output wire out_valid,input wire out_ready,output wire[511:0] out_data,
 output wire[73:0] out_context,output wire[6:0] out_word,
 output wire out_last,out_corrected,busy,fault
);
 generate if(!ENABLE)begin:disabled
 assign cmd_ready=0;assign in_ready=0;assign out_valid=0;assign out_data=0;
 assign out_context=0;assign out_word=0;assign out_last=0;
 assign out_corrected=0;assign busy=0;assign fault=0;
 end else begin:enabled
 localparam [7:0] CMD=1,LOAD=2,STORE=4,WCOMMIT=8,RREQ=16,RWAIT=32,RDECODE=64,RHOLD=128;
 reg[7:0] state;reg[73:0] context_q;reg[6:0] write_word,read_word;
 reg[511:0] pack_q,output_q;reg corrected_q,fault_q;
 wire[575:0] write_code;wire[767:0] bank_data;wire[511:0] decoded;
 wire[7:0] ce,ue,dvalid;
 assign fault=fault_q;assign cmd_ready=state==CMD&&!fault_q;
 assign in_ready=state==LOAD&&!fault_q;assign out_valid=state==RHOLD&&!fault_q;
 assign out_data=output_q;assign out_context=context_q;
 assign out_word=read_word;assign out_last=read_word==79;
 assign out_corrected=out_valid&&corrected_q;assign busy=state!=CMD;
 genvar k;
 for(k=0;k<8;k=k+1)begin:ecc
 ot_s81_secded_enc72 enc(.d(pack_q[64*k+:64]),.c(write_code[72*k+:72]));
 ot_dsrom_mtp_shared_secded_pipe dec(.clk(clk),.rst_n(rst_n),
  .valid_in(state==RWAIT&&!fault_q),
  .c(bank_data[72*k+:72]^(k==0?READ_INJECT:72'd0)),
  .valid_out(dvalid[k]),.d(decoded[64*k+:64]),.ce(ce[k]),.ue(ue[k]));
 end
 for(k=0;k<3;k=k+1)begin:mem
 wire[767:0] wd={192'd0,write_code};
 ot_sram_1r1w_256x256_m2_r2c2 m(.clk(clk),
  .r_ce_in(state==RREQ&&!fault_q),.r_addr_in({1'b0,read_word}),
  .rd_out(bank_data[256*k+:256]),.w_ce_in(state==STORE&&!fault_q),
  .w_addr_in({1'b0,write_word}),.wd_in(wd[256*k+:256]),
  .w_mask_in({256{1'b1}}),.rr_en(2'd0),.rr_addr(14'd0),
  .cr_en(2'd0),.cr_sel(16'd0));
 end
 reg input_nonfinite;
 always @*begin
 input_nonfinite=0;
 for(integer j=0;j<16;j=j+1)
  if(in_data[32*j+23+:8]==8'hff||in_data[32*j+:16]!=0)input_nonfinite=1;
 end
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
 state<=CMD;fault_q<=0;context_q<=0;write_word<=0;read_word<=0;
 pack_q<=0;output_q<=0;corrected_q<=0;
 end else if(!fault_q)case(state)
 CMD:if(cmd_valid)begin
  if(cmd_context[32+:10]>=MAXU||cmd_context[42+:21]>=MAX_CONTEXT||
     cmd_context[67+:2]>2||cmd_context[71+:3]>5)fault_q<=1;
  else begin context_q<=cmd_context;write_word<=0;read_word<=0;state<=LOAD;end
 end
 LOAD:if(in_valid)begin
  if(in_context!=context_q||in_word!=write_word||in_last!=(write_word==79)||
     in_fmt_fp32||in_error||input_nonfinite)fault_q<=1;
  else begin pack_q<=in_data;state<=STORE;end
 end
 STORE:state<=WCOMMIT;
 WCOMMIT:if(write_word==79)state<=RREQ;
  else begin write_word<=write_word+1'b1;state<=LOAD;end
 RREQ:state<=RWAIT;
 RWAIT:state<=RDECODE;
 RDECODE:if(&dvalid)begin
  if(|ue)fault_q<=1;
  else begin output_q<=decoded;corrected_q<=|ce;state<=RHOLD;end
 end
 RHOLD:if(out_ready)begin
  if(read_word==79)state<=CMD;
  else begin read_word<=read_word+1'b1;state<=RREQ;end
 end
 default:fault_q<=1;
 endcase
 end
 end endgenerate
endmodule
