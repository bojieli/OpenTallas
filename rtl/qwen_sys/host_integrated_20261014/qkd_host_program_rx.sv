`timescale 1ns/1ps
// Real W528 physical HOST ingress. Class8 is the program service; other classes
// retain their complete existing frame. This is not a RAW HBM-sector encoding.
// Payload op1 BEGIN:epoch[23:8],pw_count[34:24],dw_count[38:35].
// op2 WORD:desc8,addr[18:9],data[82:19]. op3 SEAL. op4 AUTH:
// epoch[23:8],digest[87:24]. Remaining payload/header-reserved bits must be0.
// AUTH is supplied by the trusted physical HOST service, not looped from digest.
module qkd_host_program_rx #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire rx_v,input wire[527:0]rx_d,output reg rx_cr,
 output reg normal_v,output reg[527:0]normal_d,input wire normal_cr,
 output reg begin_image,output reg[15:0]image_epoch,
 output reg[10:0]pw_count,output reg[3:0]dw_count,
 output reg word_v,word_desc,output reg[9:0]word_addr,output reg[63:0]word_data,
 output reg seal,auth_v,output reg[15:0]auth_epoch,output reg[63:0]auth_digest,
 output reg fault);
 reg rv,ncq;reg[527:0]rd;reg[6:0]returns;
 wire is_program=rd[527:524]==8;wire pop=rv&&is_program;
 wire[7:0]op=rd[7:0];
 wire clean=rd[523:512]==0&&((op==1&&rd[511:39]==0)||(op==2&&rd[511:83]==0)||(op==3&&rd[511:8]==0)||(op==4&&rd[511:88]==0));
 wire emit=returns!=0;wire[7:0]next_returns={1'b0,returns}+8'(ncq)+8'(pop)-8'(emit);
 always @(posedge ck)begin rd<=rx_d;normal_d<=rd;end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin rv<=0;ncq<=0;returns<=0;rx_cr<=0;normal_v<=0;begin_image<=0;image_epoch<=0;pw_count<=0;dw_count<=0;word_v<=0;word_desc<=0;word_addr<=0;word_data<=0;seal<=0;auth_v<=0;auth_epoch<=0;auth_digest<=0;fault<=0;end
  else begin
   rv<=rx_v;ncq<=normal_cr;rx_cr<=emit;returns<=next_returns[6:0];if(next_returns[7])fault<=1;
   normal_v<=rv&&!is_program&&!fault;begin_image<=0;word_v<=0;seal<=0;auth_v<=0;
   if(pop&&!fault)begin
    if(!clean)fault<=1;
    else case(op)
     1:begin begin_image<=1;image_epoch<=rd[23:8];pw_count<=rd[34:24];dw_count<=rd[38:35];end
     2:begin word_v<=1;word_desc<=rd[8];word_addr<=rd[18:9];word_data<=rd[82:19]^64'(MUT==1);end
     3:seal<=1;
     4:begin auth_v<=1;auth_epoch<=rd[23:8];auth_digest<=rd[87:24];end
     default:fault<=1;
    endcase
   end
  end
 end
endmodule
