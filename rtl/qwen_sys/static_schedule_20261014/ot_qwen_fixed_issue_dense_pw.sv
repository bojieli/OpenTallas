`timescale 1ns/1ps
// Actual synthesizable 47-bit calendar storage on the existing PW10x64 face.
// ME8 records [976..983], SU20 [984..1003], four XPF188 [1004..1015].
// PW0 clears. CAL1/CAL2 carry per-owner stop32; CALS carries counts/stage.
// PW1023 validated dense footer seals after all records and CP payloads.
// All storage here is real FF state; physical parent must census/map it.
module ot_qwen_fixed_issue_dense_pw #(
 parameter integer OWN=1,
 parameter integer DEPTH=(OWN==1)?8:20,
 parameter integer BASE=(OWN==1)?976:984
)(
 input wire clk,input wire rst_n,
 input wire pw_v,input wire [9:0]pw_addr,input wire[63:0]pw_data,
 input wire start,input wire[5:0]stage,
 input wire candidate_v,input wire[11:0]candidate_pc,input wire[1:0]candidate_unit,
 input wire available,input wire end_ok,input wire cp_available,
 output wire issue_v,output wire end_v,output wire[55:0]cp_cmd,output wire cp_v,output wire[11:0]issue_pc,output wire[1:0]issue_unit,
 output wire active,output wire done,output wire[31:0]cycle,output wire image_ready,output wire fault
);
 // Dense profile: PW0 clears; ascending full1024 image, footer1023 seals.
 localparam integer RAW=(DEPTH>1)?$clog2(DEPTH):1;
 reg[46:0]rows[0:DEPTH-1];reg[DEPTH-1:0]valid;
 reg[55:0]cp_rows[0:2];reg[2:0]cp_valid;wire[1:0]cp_index;
 reg[46:0]q;reg[31:0]stop_q;reg[63:0]meta_q;
 reg loading,sealed,stop_seen,meta_seen,cfg_fault,read_fault;
 wire read_en;wire[RAW-1:0]read_addr;wire core_fault;
 wire own_row=pw_addr>=BASE&&pw_addr<BASE+DEPTH;
 wire cp_row=OWN==1&&pw_addr>=1019&&pw_addr<=1021;
 wire[5:0]count=(OWN==1)?meta_q[5:0]:meta_q[11:6];
 integer k,copies;reg seal_bad;
 always @*begin
  seal_bad=!loading||!stop_seen||!meta_seen||meta_q[63:32]!=32'h43414c53||meta_q[31:28]!=0||
           meta_q[27:18]==0||meta_q[27:18]>=61||count==0||count>DEPTH||
           pw_data[63:32]!=32'h58504631||pw_data[31:13]!=0||pw_data[1:0]!=2||
           pw_data[11:6]!=meta_q[17:12]||pw_data[5:2]==0||pw_data[5:2]>4;
  copies=0;
  for(k=0;k<DEPTH;k=k+1)begin
   if(!valid[k])seal_bad=1;
   if(k<count)begin
    if(rows[k][45:44]==3)copies=copies+1;
    if(rows[k][46]!=(k==count-1))seal_bad=1;
   end else if(rows[k]!=0)seal_bad=1;
  end
  if(copies>3||(OWN!=1&&copies!=0))seal_bad=1;
  if(OWN==1)for(k=0;k<3;k=k+1)begin
   if(!cp_valid[k])seal_bad=1;
   if(k<copies)begin
    if(!cp_rows[k][0]||cp_rows[k][55:49]==0||cp_rows[k][55:49]>64)seal_bad=1;
   end else if(cp_rows[k]!=0)seal_bad=1;
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin valid<=0;cp_valid<=0;q<=0;stop_q<=0;meta_q<=0;loading<=0;sealed<=0;stop_seen<=0;meta_seen<=0;cfg_fault<=0;read_fault<=0;end
  else begin
   if(read_en)begin
    if(read_addr<DEPTH&&valid[read_addr])q<=rows[read_addr];else begin q<=0;read_fault<=1;end
   end
   if(pw_v)begin
    if(active)cfg_fault<=1;
    else if(pw_addr==0)begin
     if(loading)cfg_fault<=1;
     else begin valid<=0;cp_valid<=0;loading<=1;sealed<=0;stop_seen<=0;meta_seen<=0;cfg_fault<=0;read_fault<=0;end
    end else if(own_row)begin
     if(!loading||valid[pw_addr-BASE]||pw_data[63:47]!=0)cfg_fault<=1;
     rows[pw_addr-BASE]<=pw_data[46:0];valid[pw_addr-BASE]<=1;
    end else if(pw_addr==((OWN==1)?1016:1018))begin
     if(!loading||stop_seen||pw_data[63:32]!=((OWN==1)?32'h43414c31:32'h43414c32)||pw_data[31:0]==0)cfg_fault<=1;
     stop_q<=pw_data[31:0];stop_seen<=1;
    end else if(pw_addr==1017)begin
     if(!loading||meta_seen)cfg_fault<=1;meta_q<=pw_data;meta_seen<=1;
    end else if(cp_row)begin
     if(!loading||cp_valid[pw_addr-1019]||pw_data[63:56]!=0)cfg_fault<=1;
     cp_rows[pw_addr-1019]<=pw_data[55:0];cp_valid[pw_addr-1019]<=1;
    end else if(pw_addr==1023)begin
     if(seal_bad||cfg_fault)cfg_fault<=1;
     else begin sealed<=1;loading<=0;end
    end
   end
   if(cp_v&&(cp_index>=3||!cp_valid[cp_index]))cfg_fault<=1;
   if(start&&(!sealed||meta_q[17:12]!=stage))cfg_fault<=1;
  end
 end
 ot_qwen_fixed_issue #(.ROW_AW(RAW),.OWN(OWN))u_issue(
 .clk(clk),.rst_n(rst_n),.start(start),.stop_cycle(stop_q),.slot_re(read_en),.slot_addr(read_addr),.slot_q(q),
 .candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),.available(available),.end_ok(end_ok),.cp_available(cp_available),
 .issue_v(issue_v),.end_v(end_v),.cp_v(cp_v),.cp_index(cp_index),.issue_pc(issue_pc),.issue_unit(issue_unit),.active(active),.done(done),.cycle(cycle),.fault(core_fault));
 assign cp_cmd=OWN==1?{(cp_index<3?cp_rows[cp_index][55:1]:55'd0),cp_v}:56'd0;
 assign image_ready=sealed&&!cfg_fault&&!read_fault;
 assign fault=cfg_fault||read_fault||core_fault;
endmodule
