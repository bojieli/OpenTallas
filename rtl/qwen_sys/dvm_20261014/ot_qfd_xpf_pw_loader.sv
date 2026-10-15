`timescale 1ns/1ps
// XPF1 compiled image extension on the ACTUAL pw10x64 program-write port.
// Instruction words0..60; rows61..63 are typed metadata. Nothing
// here generates ready, credits, producer permits or runtime arbitration.
// Header address1023: upper32=58504631 ('XPF1'), lower32={zero20,stage6,count4,op2}.
// op1 clears before loading; data addresses1004..1015 carry4 records of188
// bits,3 consecutive64-bit beats each; high4bits of the third beat are0.
// Time header address1022: upper32=58504654 ('XPFT'), lower32=stage stop cycle.
// op2 seals ONLY after exactly count records and the time header arrived.
module ot_qfd_xpf_pw_loader (
 input wire clk,rst_n,stage_active,
 input wire pw_v,input wire [9:0] pw_addr,input wire [63:0] pw_data,
 output reg cfg_clear,cfg_v,cfg_seal,output reg [2:0] cfg_index,
 output reg [187:0] cfg_data,output reg [3:0] cfg_count,
 output reg [5:0] stage,output reg [31:0] stop_cycle,
 output reg fault
);
 reg loading,time_loaded;reg [4:0] beats;reg [1:0] part;reg [2:0] index_r;
 reg [127:0] payload;
 wire metadata=(pw_addr>=10'd1004&&pw_addr<=10'd1015)||pw_addr>=10'd1022;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cfg_clear<=0;cfg_v<=0;cfg_seal<=0;cfg_index<=0;cfg_data<=0;cfg_count<=0;stage<=0;stop_cycle<=0;
   fault<=0;loading<=0;time_loaded<=0;beats<=0;part<=0;index_r<=0;payload<=0;end
  else begin
   cfg_clear<=0;cfg_v<=0;cfg_seal<=0;
   if(pw_v&&metadata)begin
    if(stage_active)fault<=1;
    else if(pw_addr==1023)begin
     if(pw_data[63:32]!=32'h58504631||pw_data[31:12]!=0||pw_data[5:2]==0||pw_data[5:2]>4)fault<=1;
     else if(pw_data[1:0]==1)begin
      cfg_clear<=1;loading<=1;time_loaded<=0;beats<=0;part<=0;index_r<=0;
      cfg_count<=pw_data[5:2];stage<=pw_data[11:6];
     end else if(pw_data[1:0]==2)begin
      if(!loading||!time_loaded||part!=0||beats!=3*cfg_count||
         pw_data[5:2]!=cfg_count||pw_data[11:6]!=stage)fault<=1;
      else begin cfg_seal<=1;loading<=0;end
     end else fault<=1;
    end else if(pw_addr==1022)begin
     if(!loading||time_loaded||pw_data[63:32]!=32'h58504654||pw_data[31:0]==0)fault<=1;
     else begin time_loaded<=1;stop_cycle<=pw_data[31:0];end
    end else if(pw_addr>=1004&&pw_addr<=1015)begin
     if(!loading||pw_addr!=10'd1004+beats||beats>=3*cfg_count)fault<=1;
     else begin
      beats<=beats+1'b1;
      if(part==0)begin payload[63:0]<=pw_data;part<=1;end
      else if(part==1)begin payload[127:64]<=pw_data;part<=2;end
      else begin
       if(pw_data[63:60]!=0||payload[91:86]!=stage)fault<=1;
       else begin cfg_data<={pw_data[59:0],payload};cfg_index<=index_r;cfg_v<=1;end
       part<=0;index_r<=index_r+1'b1;
      end
     end
    end else fault<=1;
   end
  end
 end
endmodule
