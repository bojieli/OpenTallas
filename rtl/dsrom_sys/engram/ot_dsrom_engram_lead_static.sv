`timescale 1ns/1ps
// Compiler-slotted successor of historical lead_producer. Token slot R samples
// real token-map ROM; registered history output captured at R+3. No flow control.
// Commands may be consecutive; rollback and an arriving history write for the
// same user is illegal and faults (compiler reserves separate history edges).
module ot_dsrom_engram_lead_static #(parameter [16:0] PAD=17'd2)(
 input wire clk,rst_n,t_v,input wire [11:0] t_user,
 input wire [20:0] t_pos,t_tok,input wire t_first,t_dead,t_slot,
 input wire rb_v,input wire [11:0] rb_user,input wire [2:0] rb_n,
 output reg out_v,output reg [67:0] out_ids,output reg out_dead,out_slot,
 output reg [11:0] out_user,output reg [20:0] out_pos,out_tok,
 output wire fault
);
 reg bad;
 reg [21:0] count[0:63];
 wire legal=t_user<64 && t_tok<129280 &&
  ((t_first&&t_pos==0)||(!t_first&&t_user<64&&{1'b0,t_pos}==count[t_user[5:0]]));
 wire rb_legal=rb_user<64&&rb_n>=1&&rb_n<=5&&{19'b0,rb_n}<=count[rb_user[5:0]];
 reg [1:0] pv;
 reg [11:0] usr[0:2];reg [20:0] pos[0:2],tok[0:2];reg [2:0] first,dead,slot;
 wire map_v,map_fault,win_v,win_dead;wire [16:0] cid;wire[67:0]ids;
 wire collide=rb_v&&((t_v&&rb_user==t_user)||(pv[0]&&rb_user==usr[0])||(pv[1]&&rb_user==usr[1]));
 assign fault=bad|map_fault;
 ot_dsrom_engram_token_map map(.clk(clk),.rst_n(rst_n),.in_v(t_v&&legal),.in_tok(t_tok),.out_v(map_v),.out_cid(cid),.fault(map_fault));
 ot_dsrom_engram_idwin #(.PAD(PAD)) history(.clk(clk),.rst_n(rst_n),
 .t_valid(map_v),.t_user(usr[1][5:0]),.t_cid(cid),.t_first(first[1]),.t_dead(dead[1]),
 .rb_valid(rb_v&&rb_legal&&!collide),.rb_user(rb_user[5:0]),.rb_n(rb_n),
 .win_valid(win_v),.win_ids(ids),.win_dead(win_dead));
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   bad<=0;pv<=0;first<=0;dead<=0;slot<=0;out_v<=0;out_ids<=0;out_dead<=0;out_slot<=0;out_user<=0;out_pos<=0;out_tok<=0;
   for(i=0;i<64;i=i+1)count[i]<=0;
   for(i=0;i<3;i=i+1)begin usr[i]<=0;pos[i]<=0;tok[i]<=0;end
  end else begin
   pv<={pv[0],t_v&&legal};first<={first[1:0],t_first};dead<={dead[1:0],t_dead};slot<={slot[1:0],t_slot};
   usr[0]<=t_user;pos[0]<=t_pos;tok[0]<=t_tok;
   for(i=1;i<3;i=i+1)begin usr[i]<=usr[i-1];pos[i]<=pos[i-1];tok[i]<=tok[i-1];end
   if(t_v)begin if(!legal)bad<=1;else count[t_user[5:0]]<={1'b0,t_pos}+22'd1;end
   if(rb_v)begin if(!rb_legal||collide)bad<=1;else count[rb_user[5:0]]<=count[rb_user[5:0]]-{19'b0,rb_n};end
   out_v<=win_v;
   if(win_v)begin out_ids<=ids;out_dead<=win_dead;out_slot<=slot[2];out_user<=usr[2];out_pos<=pos[2];out_tok<=tok[2];end
  end
 end
endmodule
