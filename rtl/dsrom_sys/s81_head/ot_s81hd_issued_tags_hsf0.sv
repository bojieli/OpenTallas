`timescale 1ns/1ps
// Exact historical controller tag FIFO. Issue authority and local-final accept
// remain live inputs. This FIFO pop does not retire a head job/token.
module ot_s81hd_issued_tags_hsf0 #(parameter integer MUT_MODE=0)(
 input wire ck,rst_n,accepted_issue,final_accept,
 input wire message_tag_valid,input wire[30:0]message_identity,
 output wire[30:0]head_identity,output wire[20:0]untagged_position,
 output wire[1:0]occupancy,output wire overflow,underflow
);
 reg[30:0]tf0,tf1;
 reg[1:0]tfn;reg tfw,tfr;
 (* keep="true" *)reg tfr_a,tfr_b,tfr_c;
 reg st1;reg[20:0]upos;
 wire[3:0]tfe;
 ot_s81hd_kf u_tfe0(.ck(ck),.d(accepted_issue&&!tfw),.q(tfe[0]));
 ot_s81hd_kf u_tfe1(.ck(ck),.d(accepted_issue&&!tfw),.q(tfe[1]));
 ot_s81hd_kf u_tfe2(.ck(ck),.d(accepted_issue&&tfw),.q(tfe[2]));
 ot_s81hd_kf u_tfe3(.ck(ck),.d(accepted_issue&&tfw),.q(tfe[3]));
 wire[30:0]tag=message_identity^(MUT_MODE==1?(31'd1<<25):31'd0);
 always@(posedge ck)begin
  if(tfe[0])tf0[15:0]<=tag[15:0];if(tfe[1])tf0[30:16]<=tag[30:16];
  if(tfe[2])tf1[15:0]<=tag[15:0];if(tfe[3])tf1[30:16]<=tag[30:16];
 end
 always@(posedge ck or negedge rst_n)
  if(!rst_n)begin tfn<=0;tfw<=0;tfr<=0;tfr_a<=0;tfr_b<=0;tfr_c<=0;upos<=0;st1<=0;end
  else begin
   st1<=accepted_issue;
   if(accepted_issue)tfw<=~tfw;
   if(st1&&(!message_tag_valid||MUT_MODE==2))upos<=upos+21'd1;
   if(final_accept&&tfn!=0)begin tfr<=~tfr;tfr_a<=~tfr_a;tfr_b<=~tfr_b;tfr_c<=~tfr_c;end
   tfn<=tfn+{1'b0,accepted_issue&&tfn!=2'd2}-{1'b0,final_accept&&tfn!=0};
  end
 assign head_identity={tfr_c?tf1[30:21]:tf0[30:21],tfr_b?tf1[20:11]:tf0[20:11],tfr_a?tf1[10:0]:tf0[10:0]};
 assign untagged_position=upos;assign occupancy=tfn;
 assign overflow=accepted_issue&&tfn==2;assign underflow=final_accept&&tfn==0;
endmodule
