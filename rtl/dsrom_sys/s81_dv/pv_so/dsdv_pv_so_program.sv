`timescale 1ns/1ps
`default_nettype none
// Compiler-owned private type15 frames on the EXISTING entry q path. They are
// removed before the service job gate; the seventeen generated SMJ frames are
// counted in its job descriptor instead. No new die configuration sideband.
// subtype spec[447:444]:0 CFG len0,1 PARAM len5,2 LAUNCH len0.
// CFG spec:owner[19:0],SEjid[27:20],SOjid[35:28],local_first[51:36],peer_first[67:52].
// PARAM/LAUNCH carry the same owner; position is always the real outer header.
// S81/PORTFIX-DEAD (10-25): TF = 1 the q port carries the transport fault bit q[514] (checked below); TF = 0 (the S81
// die entry dsdv_svc_rs_pvso_entry: its q lane is the 513-b frame {d 512, v}, there is no q[514]) builds no reader of
// q[514:513] (q_pass[514:513] = 0, no transport-fault check).
module dsdv_pv_so_program #(parameter integer ENABLE=0, parameter integer TF=1)(
 input wire clk,rst_n,input wire[514:0]q,output wire[514:0]q_pass,
 output reg cfg_v,output reg[19:0]owner,output reg[20:0]position,output reg[7:0]se_jid,so_jid,
 output reg[15:0]local_first,peer_first,
 output reg param_v,output reg[2:0]param_row,output reg[19:0]param_owner,output reg[20:0]param_position,output reg[511:0]param_d,
 output reg launch,output reg fault
);
 wire v=q[0];wire[511:0]d=q[512:1];
 reg in_frame,private_frame;reg[11:0]left;reg[2:0]row_;reg[19:0]powner;reg[20:0]ppos;
 wire ph=ENABLE!=0 && v && !in_frame && d[511:508]==15;
 wire drop_q=ENABLE!=0 && ((v&&in_frame&&private_frame)||ph);
 assign q_pass[512:0]=drop_q?513'd0:q[512:0];
 generate if(TF!=0)begin:g_tf assign q_pass[514:513]=drop_q?2'd0:q[514:513];
 end else begin:g_ntf assign q_pass[514:513]=2'd0; end endgenerate   // TF 0: q[514:513] not read
 wire context_ok=d[17:0]=={d[458:449],d[502:495]} && d[506:503]==1;
 always @(posedge clk)begin
  if(v && in_frame && private_frame)begin param_d<=d;param_row<=row_;param_owner<=powner;param_position<=ppos;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin in_frame<=0;private_frame<=0;left<=0;row_<=0;powner<=0;ppos<=0;cfg_v<=0;param_v<=0;launch<=0;fault<=0;owner<=0;position<=0;se_jid<=0;so_jid<=0;local_first<=0;peer_first<=0;end
  else begin
   cfg_v<=0;param_v<=0;launch<=0;
   if(ENABLE!=0 && v)begin
    if(TF!=0 && q[514])fault<=1; // private frames must preserve transport fault visibility
    if(!in_frame)begin
     in_frame<=d[491:480]!=0;left<=d[491:480];private_frame<=d[511:508]==15;row_<=0;
     if(ph)begin
      if(!context_ok)fault<=1;
      else case(d[447:444])
       0:if(d[491:480]!=0)fault<=1;else begin cfg_v<=1;owner<=d[19:0];position<=d[479:459];se_jid<=d[27:20];so_jid<=d[35:28];local_first<=d[51:36];peer_first<=d[67:52];end
       1:if(d[491:480]!=5)fault<=1;else begin powner<=d[19:0];ppos<=d[479:459];end
       2:if(d[491:480]!=0 || d[19:0]!=owner || d[479:459]!=position)fault<=1;else launch<=1;
       default:fault<=1;
      endcase
     end
    end else begin
     left<=left-1;if(left==1)in_frame<=0;
     if(private_frame)begin param_v<=row_<5;row_<=row_+1;if(row_>=5)fault<=1;end
    end
   end
  end
 end
endmodule
`default_nettype wire
