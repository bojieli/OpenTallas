`timescale 1ns/1ps
// Dedicated HC seed message: MT5, distinct from HIDDEN1/SIDE3/DRAFT4.
// 512-bit header: existing dest0/src12/type24/len28/user40/position52,
// capture[209:208], epoch[213:210]. All other fields/reserved bits are zero.
// Followed by exactly40 protected512-bit mean frames. Reliable native553
// transport keeps its existing {last,40zero,512flit} contract and CRC/replay.
module ot_s81_seed_packet_tx #(
 parameter integer ENABLE=0,MY_ID=4095,DEST_ID=4095,CAPTURE=0
)(
 input wire clk,rst_n,
 input wire in_valid,output wire in_ready,input wire[511:0] in_data,
 input wire[9:0] in_user,input wire[20:0] in_position,input wire[3:0] in_epoch,
 input wire[1:0] in_capture,input wire[5:0] in_frame,input wire in_last,
 output wire out_valid,input wire out_ready,output wire[511:0] out_data,
 output wire out_last,output reg fault
);
 localparam [1:0] IDLE=0,HEADER=1,BODY=2;
 reg[1:0] state;
 reg[511:0] header;
 reg[9:0] user_q;reg[20:0] pos_q;reg[3:0] epoch_q;reg[5:0] frame;
 wire enabled=ENABLE&&(MY_ID<4095)&&(MY_ID>=0)&&(DEST_ID<4095)&&(DEST_ID>=0)&&(CAPTURE>=0)&&(CAPTURE<3);
 wire identity=(in_user==user_q)&&(in_position==pos_q)&&(in_epoch==epoch_q)&&(in_capture==CAPTURE);
 wire legal=identity&&(in_frame==frame)&&(in_last==(frame==39));
 wire queue_ready;
 wire queue_valid=!fault&&((state==HEADER)||((state==BODY)&&in_valid&&legal));
 wire[512:0] queue_data=(state==HEADER)?{1'b0,header}:{frame==39,in_data};
 assign in_ready=!fault&&(state==BODY)&&legal&&queue_ready;
 ot_s81_ctrl_skid2 #(.W(513)) u_queue(.clk(clk),.rst_n(rst_n),
  .in_valid(queue_valid),.in_ready(queue_ready),.in_data(queue_data),
  .out_valid(out_valid),.out_ready(out_ready),.out_data({out_last,out_data}));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;header<=0;user_q<=0;pos_q<=0;epoch_q<=0;frame<=0;fault<=0;end
  else if(!fault)begin
   if(state==IDLE&&in_valid)begin
    if(!enabled||in_capture!=CAPTURE||in_frame!=0||in_last)fault<=1;
    else begin
     header<=0;header[11:0]<=DEST_ID;header[23:12]<=MY_ID;
     header[27:24]<=4'd5;header[39:28]<=12'd40;header[51:40]<={2'd0,in_user};
     header[72:52]<=in_position;header[209:208]<=in_capture;header[213:210]<=in_epoch;
     user_q<=in_user;pos_q<=in_position;epoch_q<=in_epoch;frame<=0;state<=HEADER;
    end
   end
   if(state==HEADER&&queue_ready)state<=BODY;
   if(state==BODY&&in_valid)begin
    if(!legal)fault<=1;
    else if(queue_ready)begin
     if(frame==39)begin state<=IDLE;frame<=0;end else frame<=frame+1'b1;
    end
   end
  end
 end
endmodule

// Place before the historical controller/WFC header parser. Only MT5 enters
// the seed join; all other whole packets remain bit-identical on normal_*.
// Source IDs are specialized from actual stage_join perTP rank, not layer #.
module ot_s81_seed_packet_rx #(
 parameter integer ENABLE=0,MY_ID=4095,SRC0=4095,SRC1=4095,SRC2=4095
)(
 input wire clk,rst_n,input wire in_valid,output wire in_ready,
 input wire[511:0] in_data,input wire in_last,
 output wire normal_valid,input wire normal_ready,output wire[511:0] normal_data,output wire normal_last,
 output wire seed_valid,input wire seed_ready,output wire[511:0] seed_data,
 output wire[9:0] seed_user,output wire[20:0] seed_position,output wire[3:0] seed_epoch,
 output wire[1:0] seed_capture,output wire[5:0] seed_frame,output wire seed_last,
 output reg fault
);
 localparam [1:0] HEADER=0,NORMAL=1,SEED=2;
 reg[1:0] state;
 reg[9:0] user_q;reg[20:0] pos_q;reg[3:0] epoch_q;reg[1:0] capture_q;reg[5:0] frame;
 wire seed_header=ENABLE&&(state==HEADER)&&(in_data[27:24]==5);
 wire[1:0] cap=in_data[209:208];
 wire[11:0] expected_src=(cap==0)?SRC0:(cap==1)?SRC1:SRC2;
 wire legal_header=(MY_ID>=0)&&(MY_ID<4095)&&(cap<3)&&(expected_src<4095)&&
  (in_data[11:0]==MY_ID)&&(in_data[23:12]==expected_src)&&(in_data[39:28]==40)&&
  (in_data[51:50]==0)&&(in_data[207:73]==0)&&(in_data[511:214]==0)&&!in_last;
 wire legal_body=(in_last==(frame==39));
 assign in_ready=!fault&&(seed_header?1'b1:(state==SEED)?(legal_body&&seed_ready):normal_ready);
 assign normal_valid=in_valid&&!fault&&!seed_header&&(state!=SEED);
 assign normal_data=in_data;assign normal_last=in_last;
 assign seed_valid=in_valid&&!fault&&(state==SEED)&&legal_body;
 assign seed_data=in_data;assign seed_user=user_q;assign seed_position=pos_q;assign seed_epoch=epoch_q;
 assign seed_capture=capture_q;assign seed_frame=frame;assign seed_last=frame==39;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=HEADER;user_q<=0;pos_q<=0;epoch_q<=0;capture_q<=0;frame<=0;fault<=0;end
  else if(!fault)begin
   if(in_valid&&seed_header)begin
    if(!legal_header)fault<=1;
    else begin state<=SEED;user_q<=in_data[49:40];pos_q<=in_data[72:52];
     epoch_q<=in_data[213:210];capture_q<=cap;frame<=0;end
   end else if(in_valid&&state==SEED&&!legal_body)fault<=1;
   else if(in_valid&&in_ready)begin
    if(state==SEED)begin if(frame==39)begin state<=HEADER;frame<=0;end else frame<=frame+1'b1;end
    else if(in_last)state<=HEADER;else state<=NORMAL;
   end
  end
 end
endmodule
