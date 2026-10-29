`timescale 1ns/1ps
module dut(input ck,rst_top,head_prepare_v,input[1:0]head_prepare_user,input[17:0]head_prepare_token,head_prepare_position,
 input p_hev,p_hfc,input[15:0]p_he,input[58:0]p_ht,input[1:0]p_hg,
 output reg head_descriptor_v,output reg[58:0]head_descriptor_tag,output reg[1:0]head_descriptor_generation);
 localparam integer HEAD_PREP=1,MU=1,NU=4,MU_SEQ0=0;
 wire native_context=0,c_l0=0,begin_slot=0;wire[1:0]c_user_w=0,c_user=0;wire[13:0]c_seq=0;wire[58:0]begin_tag=0;
 reg[1:0]hp_v;reg[1:0]hp_u0,hp_u1;reg[17:0]hp_t0,hp_t1,hp_p0,hp_p1;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin hp_v<=0;hp_u0<=0;hp_u1<=0;hp_t0<=0;hp_t1<=0;hp_p0<=0;hp_p1<=0;end
  else begin
   hp_v<={hp_v[0],head_prepare_v};hp_u0<=head_prepare_user;hp_u1<=hp_u0;
   hp_t0<=head_prepare_token;hp_t1<=hp_t0;hp_p0<=head_prepare_position;hp_p1<=hp_p0;
  end
 reg[13:0]fseq[0:3];reg[3:0]fstart;reg mu_fault;
 wire hp_fill=HEAD_PREP!=0&&MU!=0&&hp_v[1]&&hp_u1!=2'd0;
 wire hp_host=HEAD_PREP!=0&&hp_v[1]&&hp_u1==2'd0;
 reg hp_host_pending,hp_host_fault;reg[17:0]hp_host_token,hp_host_position;
 wire hp_host_match=hp_host_pending&&p_hev&&p_hfc&&p_ht[58:43]==p_he&&
    1'b1&&p_ht[18:6]==hp_host_position[12:0]&&p_ht[42:37]==0&&p_ht[5:0]==0;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin hp_host_pending<=0;hp_host_fault<=0;hp_host_token<=0;hp_host_position<=0;end
  else begin
   if(hp_host)begin
    if(hp_host_pending||hp_t1>=151936||hp_p1>=8192)hp_host_fault<=1;
    hp_host_pending<=1;hp_host_token<=hp_t1;hp_host_position<=hp_p1;
   end else if(hp_host_match&&!hp_fill)hp_host_pending<=0;
  end
 wire[13:0]hp_seq=fstart[hp_u1]?fseq[hp_u1]+14'd1:fseq[hp_u1];
 integer fu;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin for(fu=0;fu<4;fu=fu+1)fseq[fu]<=MU_SEQ0;fstart<=0;mu_fault<=0;end
  else begin
   if(hp_fill)begin
    fseq[hp_u1]<=hp_seq;fstart[hp_u1]<=1'b1;
    if({1'b0,hp_u1}>=3'(NU)||hp_t1>=18'd151936||hp_p1>=18'd8192)mu_fault<=1'b1;
   end
   if(MU!=0&&native_context&&c_user_w!=2'd0)begin   // R3h: c_user_w == c_user
    if(HEAD_PREP==0)begin fseq[c_user_w]<=c_seq;if(c_l0)fstart[c_user_w]<=1'b1;end
    if({1'b0,c_user}>=3'(NU)||(!fstart[c_user]&&(HEAD_PREP!=0||!c_l0)))mu_fault<=1'b1;
   end
  end
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin head_descriptor_v<=0;head_descriptor_tag<=0;head_descriptor_generation<=0;end
  else begin
   head_descriptor_v<=HEAD_PREP!=0?(hp_fill||hp_host_match):(begin_slot&&(begin_tag[42:37]==6'd1));
   if(hp_fill)begin
    head_descriptor_tag<={hp_seq,hp_u1,6'd0,hp_t1,hp_p1[12:0],6'd0};
    head_descriptor_generation<=p_hg;
   end else if(HEAD_PREP!=0&&hp_host_match)begin
    head_descriptor_tag<={p_ht[58:43],6'd0,p_ht[36:0]};
    head_descriptor_generation<=p_hg;
   end else if(HEAD_PREP==0&&begin_slot&&(begin_tag[42:37]==6'd1))begin
    head_descriptor_tag<={begin_tag[58:43],6'd0,begin_tag[36:0]};
    head_descriptor_generation<=p_hg;
   end
  end

endmodule
