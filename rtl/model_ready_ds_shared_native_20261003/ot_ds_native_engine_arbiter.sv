`timescale 1ns/1ps
`default_nettype none
// Source-selected shared VX read and native ME-write port. No extra VM ports.
// Cold reset initialises ownership; warm reset freezes debt, never retires it.
module ot_ds_native_engine_arbiter #(parameter integer ENABLE=0)(
 input wire clk,cold_n,rst_n,
 input wire [2:0] read_v,output reg [2:0] read_ready,
 input wire [11:0] read_enable,input wire [359:0] read_addr,
 input wire [494:0] read_context,
 output wire vm_read_v,input wire vm_read_ready,
 output wire [3:0] vm_read_enable,output wire [119:0] vm_read_addr,
 output wire [164:0] vm_read_context,
 input wire vm_reply_v,output wire vm_reply_ready,
 input wire [127:0] vm_reply_data,input wire [227:0] vm_reply_owner,
 output reg [2:0] reply_v,input wire [2:0] reply_ready,
 output wire [383:0] reply_data,output wire [95:0] reply_cookie,
 input wire [3:0] write_v,output reg [3:0] write_accept,write_visible,write_pending,
 input wire [15:0] write_enable,input wire [479:0] write_addr,
 input wire [255:0] write_mask,input wire [8191:0] write_data,
 input wire [659:0] write_context,
 output wire [3:0] vm_write_enable,output wire [119:0] vm_write_addr,
 output wire [63:0] vm_write_mask,output wire [2047:0] vm_write_data,
 output wire [164:0] vm_write_context,
 input wire vm_write_ready,vm_write_visible,vm_write_pending,
 output reg fault,output wire outstanding
);
 reg [1:0] rstate,wstate,rowner,wowner,rr,wr;
 integer i,k,rs,ws;
 always @* begin
  rs=rowner;ws=wowner;
  if(rstate==0) begin
   rs=-1;
   for(i=0;i<3;i=i+1)begin k=(rr+i)%3;if(rs<0 && read_v[k])rs=k;end
  end
  if(wstate==0) begin
   ws=-1;
   for(i=0;i<4;i=i+1)begin k=(wr+i)%4;if(ws<0 && write_v[k])ws=k;end
  end
 end
 wire run=ENABLE && cold_n && rst_n && !fault;
 wire roffer=run && rstate!=2 && rs>=0;
 wire woffer=run && wstate!=2 && ws>=0;
 assign vm_read_v=roffer;
 assign vm_read_enable=roffer ? read_enable[rs*4+:4] : 4'b0;
 assign vm_read_addr=roffer ? read_addr[rs*120+:120] : 120'b0;
 assign vm_read_context=roffer ? read_context[rs*165+:165] : 165'b0;
 assign vm_reply_ready=run && rstate==2 && reply_ready[rowner];
 assign reply_data={3{vm_reply_data}};
 // Context low32 is the actual issuer cookie, embedded in owner bits59..90.
 assign reply_cookie={3{vm_reply_owner[59+:32]}};
 assign vm_write_enable=woffer ? write_enable[ws*4+:4] : 4'b0;
 assign vm_write_addr=woffer ? write_addr[ws*120+:120] : 120'b0;
 assign vm_write_mask=woffer ? write_mask[ws*64+:64] : 64'b0;
 assign vm_write_data=woffer ? write_data[ws*2048+:2048] : 2048'b0;
 assign vm_write_context=woffer ? write_context[ws*165+:165] : 165'b0;
 assign outstanding=(rstate!=0)||(wstate!=0);
 always @* begin
  read_ready=0;reply_v=0;write_accept=0;write_visible=0;write_pending=0;
  if(roffer)read_ready[rs]=vm_read_ready;
  if(run && rstate==2)reply_v[rowner]=vm_reply_v;
  if(woffer)write_accept[ws]=vm_write_ready;
  if(wstate!=0)write_pending[wowner]=1;
  if(run && wstate==2)write_visible[wowner]=vm_write_visible;
 end
 always @(posedge clk)begin
  if(!cold_n)begin rstate<=0;wstate<=0;rowner<=0;wowner<=0;rr<=0;wr<=0;fault<=0;end
  else if(!rst_n && outstanding)fault<=1;
  else if(run)begin
   if(roffer)begin rowner<=2'(rs);rstate<=vm_read_ready ? 2 : 1;end
   if(rstate==1 && !read_v[rowner])fault<=1;
   if(rstate==2 && vm_reply_v && vm_reply_ready)begin rstate<=0;rr<=(rowner==2)?0:rowner+1'b1;end
   if(woffer)begin
    wowner<=2'(ws);wstate<=vm_write_ready ? 2 : 1;
    if(!( |write_enable[ws*4+:4]))fault<=1;
   end
   if(wstate==1 && !write_v[wowner])fault<=1;
   if(vm_write_visible)begin
    if(wstate!=2)fault<=1;
    else begin wstate<=0;wr<=wowner+1'b1;end
   end
  end
 end
endmodule
`default_nettype wire
