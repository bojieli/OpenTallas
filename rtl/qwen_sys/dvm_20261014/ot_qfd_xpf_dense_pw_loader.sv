`timescale 1ns/1ps
// Full1024-word ascending image: realPW0 clears, unused188b records zero,
// footer1023 {XPF1,zero19,fusedcap1,stage6,count4,op2} seals AFTERallrecords.
module ot_qfd_xpf_dense_pw_loader(
 input wire clk,rst_n,stage_active,
 input wire pw_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,
 output reg cfg_clear,cfg_v,cfg_seal,output reg[2:0]cfg_index,
 output reg[187:0]cfg_data,output reg[3:0]cfg_count,
 output reg[5:0]stage,output reg[31:0]stop_cycle,
 output wire image_ready,output reg fault
);
 reg loading,sealed,time_loaded,padding;reg[4:0]beats;reg[1:0]part;reg[2:0]index_r;reg[127:0]payload;
 wire[187:0]record_word={pw_data[59:0],payload};
 assign image_ready=sealed&&!fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cfg_clear<=0;cfg_v<=0;cfg_seal<=0;cfg_index<=0;cfg_data<=0;cfg_count<=0;stage<=0;stop_cycle<=0;fault<=0;loading<=0;sealed<=0;time_loaded<=0;padding<=0;beats<=0;part<=0;index_r<=0;payload<=0;end
  else begin
   cfg_clear<=0;cfg_v<=0;cfg_seal<=0;
   if(pw_v)begin
    if(stage_active)fault<=1;
    else if(pw_addr==0)begin
     if(loading)fault<=1;
     else begin cfg_clear<=1;loading<=1;sealed<=0;time_loaded<=0;padding<=0;beats<=0;part<=0;index_r<=0;cfg_count<=0;fault<=0;end
    end else if(pw_addr>=1004&&pw_addr<=1015)begin
     if(!loading||pw_addr!=1004+beats||beats>=12)fault<=1;
     else begin
      beats<=beats+1'b1;
      if(part==0)begin payload[63:0]<=pw_data;part<=1;end
      else if(part==1)begin payload[127:64]<=pw_data;part<=2;end
      else begin
       if(pw_data[63:60]!=0)fault<=1;
       else if(record_word==0)padding<=1;
       else if(padding||!record_word[0]||(cfg_count!=0&&payload[91:86]!=stage))fault<=1;
       else begin cfg_data<=record_word;cfg_index<=index_r;cfg_v<=1;cfg_count<=cfg_count+1'b1;stage<=payload[91:86];end
       part<=0;index_r<=index_r+1'b1;
      end
     end
    end else if(pw_addr==1022)begin
     if(!loading||time_loaded||pw_data[63:32]!=32'h58504654||pw_data[31:0]==0)fault<=1;
     else begin time_loaded<=1;stop_cycle<=pw_data[31:0];end
    end else if(pw_addr==1023)begin
     if(!loading||fault||!time_loaded||part!=0||beats!=12||cfg_count==0||cfg_count>4||pw_data[63:32]!=32'h58504631||pw_data[31:13]!=0||pw_data[1:0]!=2||pw_data[5:2]!=cfg_count||pw_data[11:6]!=stage)fault<=1;
     else begin cfg_seal<=1;loading<=0;sealed<=1;end
    end
   end
  end
 end
endmodule
