`timescale 1ns/1ps
// Actual cmd32 adapter. DESC/GO pulse storage and native FIFO reservations
// precede command launch. A retired read window is insufficient alone: old
// writes and transport must also be quiet before replacing its descriptor.
module ot_qfd_native_cmd_plain #(parameter integer ENABLE=0, MUT_SKIP_DRAIN=0)(
 input wire clk,rst_n,
 input wire desc_v,input wire [18:0] desc_row,input wire [10:0] desc_n,
 input wire go_v,input wire wr_v,input wire [4:0] wr_bank,wr_col,
 input wire window_retired,write_quiet,transport_quiet,
 input wire cmd_credit_return,input wire [2:0] read_release,
 output wire desc_take,go_take,wr_take,
 output wire cmd_v,output wire [31:0] cmd,output wire [2:0] read_credit,
 output reg fault
);
 reg [29:0] dp;
 reg dv,gp;
 reg [3:0] credits;
 // {go issued, window retired, context live}
 reg [2:0] phase;
 reg [31:0] cq;
 reg cv;
 reg [2:0] rc;
 wire context_room=!phase[0]||(phase[1]&&(MUT_SKIP_DRAIN!=0 || (write_quiet&&transport_quiet&&!wr_v)));
 wire desc_bad=desc_v&&(desc_n==0||desc_n>1024);
 wire retire_bad=window_retired&&(!phase[0]||!phase[2]);
 reg choose;reg [31:0] packet;reg [1:0] kind;
 always @*begin
  choose=0;packet=0;kind=0;
  if(credits!=0)begin
   if(dv)begin choose=1;packet={2'd0,dp};kind=0;end
   else if(gp)begin choose=1;packet=32'h40000000;kind=1;end
   else if(wr_v&&phase[0]&&phase[2])begin choose=1;packet={2'd2,20'd0,wr_col,wr_bank};kind=2;end
  end
 end
 wire credit_bad=cmd_credit_return&&credits==8&&!choose;
 wire pre_safe=ENABLE&&!fault&&!desc_bad&&!retire_bad&&!credit_bad;
 wire take_desc=pre_safe&&desc_v&&!dv&&!gp&&context_room;
 wire go_bad=go_v&&(gp||phase[2]||(!phase[0]&&!take_desc));
 wire safe=pre_safe&&!go_bad;
 assign desc_take=safe&&take_desc;
 assign go_take=safe&&go_v;
 assign wr_take=safe&&choose&&kind==2;
 assign cmd_v=safe&&cv;
 assign cmd=cq;
 assign read_credit=safe?rc:3'd0;
 reg [2:0] next_phase;reg next_dv,next_gp;
 always @*begin
  next_phase=phase;next_dv=dv;next_gp=gp;
  if(window_retired)next_phase[1]=1;
  if(choose&&kind==0)next_dv=0;
  if(choose&&kind==1)begin next_gp=0;next_phase[2]=1;end
  if(desc_take)begin next_dv=1;next_phase=3'b001;end
  if(go_take)next_gp=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;
   begin dp<=0;dv<=0;gp<=0;credits<=8;phase<=0;cq<=0;cv<=0;rc<=0;end
  end else begin
   fault<=fault||(ENABLE&&(desc_bad||retire_bad||credit_bad||go_bad));
   begin
    cv<=safe&&choose;rc<=safe?read_release:3'd0;
    if(safe)begin
     if(desc_take)dp<={desc_n,desc_row};
     dv<=next_dv;gp<=next_gp;phase<=next_phase;
     if(choose)cq<=packet;
     case({cmd_credit_return,choose})
      2'b01:credits<=credits-1'b1;
      2'b10:credits<=credits+1'b1;
      default:credits<=credits;
     endcase
    end
   end
  end
 end
endmodule
