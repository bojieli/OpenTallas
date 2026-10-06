`timescale 1ps/1fs
// Static group-slot FP4 byte unpacker. One 260-byte elastic seat, no numeric
// operations. A source task has 255 data lines and one required zero pad line.
// Each accepted native line advances the unchanged wave,t,slot issue order.
module ot_hbm_accel_wg_gearbox #(parameter integer ENABLE=0)(
 input wire clk,rst_n,start,input wire in_valid,output wire in_ready,
 input wire [1023:0] in_data,output wire out_valid,input wire out_ready,
 output wire [1087:0] out_data,output wire done,output wire fault
);
 generate if(!ENABLE) begin : off
 // All lengths are multiples4. A residual132 needs4 more bytes for the
 // next136-byte word. 132+128=260 is the minimum whole-input elastic seat;
 // the original256-byte seat deadlocked at accepted26/issued27/count132.
 assign in_ready=0;assign out_valid=0;assign out_data=0;assign done=0;assign fault=0;
 end else begin : on
 reg [2079:0] bytes_q,bytes_n;
 reg [8:0] count,count_n,issued;
 reg [8:0] accepted;
 reg [2:0] wave,t,slot;
 reg done_q,fault_q;
 wire tail=((int'(wave)*8+int'(slot))%3)==2;
 wire [8:0] need=tail?9'd68:9'd136;
 wire take=out_valid&&out_ready;
 assign out_valid=!done_q&&!fault_q&&issued<288&&count>=need;
 assign out_data=tail?{32'b0,bytes_q[543:512],512'b0,bytes_q[511:0]}:bytes_q[1087:0];
 // All lengths are multiples4. A residual132 needs4 more bytes for the
 // next136-byte word. 132+128=260 is the minimum whole-input elastic seat;
 // the original256-byte seat deadlocked at accepted26/issued27/count132.
 assign in_ready=!done_q&&!fault_q&&accepted<256&&
                 (int'(count)-(take?int'(need):0)<=132);
 assign done=done_q;assign fault=fault_q;
 always @* begin
  bytes_n=bytes_q;count_n=count;
  if(take) begin bytes_n=bytes_n>>(int'(need)*8);count_n=count_n-need;end
  if(in_valid&&in_ready) begin
   bytes_n=bytes_n|({1056'b0,in_data}<<(int'(count_n)*8));count_n=count_n+9'd128;
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin bytes_q<=0;count<=0;issued<=0;accepted<=0;wave<=0;t<=0;slot<=0;done_q<=0;fault_q<=0;end
  else if(start) begin
   if(!done_q&&(accepted!=0||issued!=0)) fault_q<=1;
   else begin bytes_q<=0;count<=0;issued<=0;accepted<=0;wave<=0;t<=0;slot<=0;done_q<=0;fault_q<=0;end
  end else begin
   bytes_q<=bytes_n;count<=count_n;
   if(in_valid&&in_ready) accepted<=accepted+1'b1;
   if(take) begin
    issued<=issued+1'b1;
    if(slot==(wave==4?3:7)) begin slot<=0;
     if(t==7) begin t<=0;wave<=wave+1'b1;end else t<=t+1'b1;
    end else slot<=slot+1'b1;
   end
   if(issued==288&&accepted==256&&!done_q) begin
    if(count!=128||bytes_q[1023:0]!=0) fault_q<=1;
    else begin done_q<=1;count<=0;bytes_q<=0;end
   end
  end
 end
 end endgenerate
endmodule
