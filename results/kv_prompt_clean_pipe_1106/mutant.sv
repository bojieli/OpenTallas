`timescale 1ns/1ps
// Real W528 physical HOST ingress. Class8 is the program service; other classes
// retain their complete existing frame. This is not a RAW HBM-sector encoding.
// Target ABI v1: BEGIN[42:39], AUTH[91:88], IDs0ISA,1roots,2writer,
// 3ownership,4landing,5front,6..9controllerWS/WN/ES/EN.
// KVJ-G2b 10-17: + the static KV die's dispatcher targets 10 die cfg (pre-boot), 11 link calendar,
// 12 PC chain players, 13 join4 beat calendar (qkd_static_kv_boot_dispatch DIECFG/LINKCFG/ESCFG).
// Payload op1 BEGIN:epoch[23:8],pw_count[34:24],dw_count[38:35].
// op2 WORD:desc8,addr[18:9],data[82:19]. op3 SEAL. op4 AUTH:
// epoch[23:8],digest[87:24]. Remaining payload/header-reserved bits must be0.
// AUTH is supplied by the trusted physical HOST service, not looped from digest.
module qkd_host_program_rx_target_cp #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire rx_v,input wire[527:0]rx_d,output reg rx_cr,
 output reg normal_v,output reg[527:0]normal_d,input wire normal_cr,
 output reg begin_image,output reg[15:0]image_epoch,output reg[3:0]image_target,auth_target,
 output reg[10:0]pw_count,output reg[3:0]dw_count,
 output reg word_v,word_desc,output reg[9:0]word_addr,output reg[63:0]word_data,
 output reg seal,auth_v,output reg[15:0]auth_epoch,output reg[63:0]auth_digest,
 output reg fault);
 reg rv,ncq;reg[527:0]rd;reg[6:0]returns;
 wire is_program=rd[527:524]==8;wire pop=rv&&is_program;
 wire[7:0]op=rd[7:0];
 wire emit=returns!=0;wire[7:0]next_returns={1'b0,returns}+8'(ncq)+8'(pop)-8'(emit);
 // DIE-KV-70 prompt form: program decode one edge after the frame register (rd -> p1 -> outputs), all ops alike, so the
 // order is kept; the credit return and the normal path keep their timing.
 // Opt-in clean-decode pipeline: complete program op/data/valid bundle gains one edge.
 // Normal frames and credit return retain their existing latency. Invalid-program
 // fault observation gains the same edge as the program command bundle.
 reg p1_v;reg[7:0]clean_pipe_op;reg[91:8]p1_d;
 reg[15:1]p1_zero;reg[3:0]p1_boundary;reg[1:0]p1_target;reg p1_header;
 reg p2_v,clean_pipe_result;reg[7:0]p2_op;reg[91:8]p2_d;
 wire clean_stage2=p1_header&&((clean_pipe_op==1&&(&p1_zero[15:2])&&p1_boundary[0]&&p1_target[0])||(clean_pipe_op==2&&(&p1_zero[15:3])&&p1_boundary[1])||(clean_pipe_op==3&&(&p1_zero[15:1])&&p1_boundary[2])||(clean_pipe_op==4&&(&p1_zero[15:3])&&p1_boundary[3]&&p1_target[1]));
 genvar ci;generate for(ci=1;ci<16;ci=ci+1)begin:chunk_zero
  always @(posedge ck)p1_zero[ci]<=(ci==2 ? 1 : rd[32*ci+:32]==0);
 end endgenerate
 always @(posedge ck)begin
  p1_header<=rd[523:512]==0;
  p1_boundary<={rd[95:92]==0,rd[31:8]==0,rd[95:83]==0,rd[63:43]==0};
  p1_target<={rd[91:88]<=13,rd[42:39]<=13};
  p2_op<=clean_pipe_op;p2_d<=p1_d;
 end
 always @(posedge ck)begin rd<=rx_d;normal_d<=rd;clean_pipe_op<=op;p1_d<=rd[91:8];end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin p1_v<=0;p2_v<=0;clean_pipe_result<=0;rv<=0;ncq<=0;returns<=0;rx_cr<=0;normal_v<=0;begin_image<=0;image_epoch<=0;image_target<=0;auth_target<=0;pw_count<=0;dw_count<=0;word_v<=0;word_desc<=0;word_addr<=0;word_data<=0;seal<=0;auth_v<=0;auth_epoch<=0;auth_digest<=0;fault<=0;end
  else begin
   rv<=rx_v;ncq<=normal_cr;rx_cr<=emit;returns<=next_returns[6:0];if(next_returns[7])fault<=1;
   normal_v<=rv&&!is_program&&!fault;begin_image<=0;word_v<=0;seal<=0;auth_v<=0;
   p1_v<=pop;p2_v<=p1_v;clean_pipe_result<=clean_stage2;
   if(p2_v&&!fault)begin
    if(!clean_pipe_result)fault<=1;
    else case(p2_op)
     1:begin begin_image<=1;image_target<=p2_d[42:39];image_epoch<=p2_d[23:8];pw_count<=p2_d[34:24];dw_count<=p2_d[38:35];end
     2:begin word_v<=1;word_desc<=p2_d[8];word_addr<=p2_d[18:9];word_data<=p2_d[82:19]^64'(MUT==1);end
     3:seal<=1;
     4:begin auth_v<=1;auth_target<=p2_d[91:88];auth_epoch<=p2_d[23:8];auth_digest<=p2_d[87:24];end
     default:fault<=1;
    endcase
   end
  end
 end
endmodule
