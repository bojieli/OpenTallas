// Additive default-off literal exp step1 consumer. RF19 is really read before
// FMIN(ex,f32(88)); held numerical acceptance precedes matching W6 consumption.
// No tag minting, golden callback, transient RF release or reset debt discard.
module ot_gpu_pc40_fmin_consumer_r5 #(parameter bit ENABLE=0)(
 input wire clk,por_n,rst_n,parent_fault_stop,
 input wire visible_valid,input wire[54:0]visible_identity,output wire visible_ready,
 output wire rd_valid,input wire rd_ready,output wire[8:0]rd_a,rd_b,
 input wire rsp_valid,input wire[4095:0]rsp_a,output wire rsp_ready,
 output wire result_valid,input wire result_ready,output wire[4095:0]result,
 output wire consumer_valid,input wire consumer_ready,output wire[54:0]consumer_identity,
 output wire busy,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE)begin:enabled
 localparam[2:0]IDLE=0,READ=1,CAPTURE=2,OUTPUT_VALUE=3,ACK=4;
 reg[71:0]control;reg[71:0]data[0:127];
 wire[65:0]decoded=decode64(control);wire[63:0]raw=decoded[63:0];
 wire[2:0]phase=raw[2:0];wire[54:0]identity=raw[57:3];
 wire[127:0]data_bad,nonfinite;wire[4095:0]calculated;
 genvar lane;
 for(lane=0;lane<128;lane=lane+1)begin:word
  wire[65:0]d=decode64(data[lane]);
  assign data_bad[lane]=d[65]||(|d[63:32]);assign result[lane*32+:32]=d[31:0];
  wire[31:0]a=rsp_a[lane*32+:32],b=32'h42b00000;
  wire[30:0]unused;wire mag_ge;
  ot_hdc_ksadd_k #(.W(31))u_cmp(.a(a[30:0]),.b(~b[30:0]),.cin(1'b1),.s(unused),.cout(mag_ge));
  wire both_zero=(a[30:0]==0)&&(b[30:0]==0);
  wire unequal=(a[30:0]!=b[30:0]);
  wire choose_a=!both_zero && ((a[31]!=b[31])?a[31]:(a[31]?(mag_ge&&unequal):!mag_ge));
  wire[31:0]selected=choose_a?a:b;
  assign calculated[lane*32+:32]=selected;
  assign nonfinite[lane]=(a[30:23]==8'hff);
 end
 wire row_bad=decoded[65]||(|raw[63:59])||(phase>ACK)||(|data_bad);
 wire unexpected=(phase!=IDLE && rsp_valid && phase!=CAPTURE);
 wire live=por_n&&rst_n&&!parent_fault_stop&&!row_bad&&!raw[58]&&!unexpected;
 assign visible_ready=live&&phase==IDLE;
 assign rd_valid=live&&phase==READ;assign rd_a=9'd19;assign rd_b=9'd19;
 assign rsp_ready=live&&phase==CAPTURE;
 assign result_valid=live&&phase==OUTPUT_VALUE;
 assign consumer_valid=live&&phase==ACK;assign consumer_identity=identity;
 assign busy=phase!=IDLE;assign fault=row_bad||raw[58]||unexpected;
 reg[63:0]next_raw;
 always @*begin
  next_raw=raw;
  if(live)case(phase)
   IDLE:if(visible_valid)begin next_raw=0;next_raw[2:0]=READ;next_raw[57:3]=visible_identity;end
   READ:if(rd_ready)next_raw[2:0]=CAPTURE;
   CAPTURE:if(rsp_valid)begin if(|nonfinite)next_raw[58]=1;else next_raw[2:0]=OUTPUT_VALUE;end
   OUTPUT_VALUE:if(result_ready)next_raw[2:0]=ACK;
   ACK:if(consumer_ready)next_raw=0;
   default:begin end
  endcase
  if(unexpected)next_raw[58]=1;
  if((!rst_n||parent_fault_stop)&&phase!=IDLE)next_raw[58]=1;
 end
 integer i;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin control<=0;for(i=0;i<128;i=i+1)data[i]<=0;end
  else if(!row_bad)begin
   control<=encode64(next_raw);
   if(live&&phase==CAPTURE&&rsp_valid&&!(|nonfinite))
    for(i=0;i<128;i=i+1)data[i]<=encode64({32'd0,calculated[i*32+:32]});
  end
 end
 end else begin:disabled
 assign visible_ready=0;assign rd_valid=0;assign rd_a=0;assign rd_b=0;assign rsp_ready=0;
 assign result_valid=0;assign result=0;assign consumer_valid=0;assign consumer_identity=0;assign busy=0;assign fault=0;
 end endgenerate
endmodule
