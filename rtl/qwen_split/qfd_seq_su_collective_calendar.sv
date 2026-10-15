`timescale 1ns/1ps
// Actual sequencer PW/start face: 17 reserved words944..960.
// dh fields are those of qfd_seq_su; no readiness gates the issue cycle.
// This separate source leaf permits a minimal real mechanism bench.
module qfd_seq_su_collective_calendar(
 input wire ck,rsi,input wire[186:0]dh,input wire cmd_free,
 output wire[49:0]cmd,output wire cfg_ready,output wire fault
);
 wire v,mode,active,done,issue_ready,issue_fault;wire[15:0]words;wire[31:0]tag;
 reg[17:0]token_q;reg[7:0]position_q;reg tag_fault;
 always @(posedge ck or negedge rsi)
 if(!rsi)begin token_q<=0;position_q<=0;tag_fault<=0;end
 else begin
  if(dh[42])begin token_q<=dh[35:18];position_q<=dh[7:0];end
  // Tag metadata names a source segment, never a future raw HOST token.
  if(dh[118]&&dh[117:108]>=945&&dh[117:108]<=959&&dh[108])
   if(dh[107:50]!=0||dh[49:44]>=3)tag_fault<=1;
 end
 ot_coll_cmd_issue #(.DEPTH(8),.BASE(944)) u_issue(
 .clk(ck),.rst_n(rsi),.pw_v(dh[118]),.pw_addr(dh[117:108]),.pw_data(dh[107:44]),
 .start(dh[42]),.cmd_free(cmd_free),.cmd_v(v),.cmd_mode(mode),
 .cmd_words(words),.cmd_tag(tag),.active(active),.done(done),.image_ready(issue_ready),.fault(issue_fault));
 assign cmd={v,token_q,position_q,tag[5:0],mode,words};
 assign fault=issue_fault|tag_fault;assign cfg_ready=issue_ready&&!tag_fault;
endmodule
