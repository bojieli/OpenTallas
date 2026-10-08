`timescale 1ns/1ps
// Default-off one-outstanding installed result-span reader. No second store.
// Publication and returned owner identity must come from the real protected
// service association, not a constant echo of this descriptor. Model6ca8db61b.
module ot_hbm_su_installed_span #(parameter integer ENABLE=0)(
 input wire clk,por_n,warm_reset,transport_fault,
 input wire bind_v,output wire bind_r,input wire [1:0] installed_checked,
 input wire [72:0] bind_owner,input wire [15:0] bind_record,bind_tag,
 input wire [4:0] bind_source,input wire [23:0] logical_base,
 input wire [12:0] rows,input wire [36:0] byte_base,byte_limit,
 input wire publication_v,output wire publication_r,input wire [72:0] publication_owner,
 input wire [15:0] publication_record,input wire [4:0] publication_source,
 input wire read_v,output wire read_r,input wire [23:0] read_word,input wire [12:0] read_consumer,
 output wire req_v,input wire req_r,output wire [36:0] req_addr,
 output wire [15:0] req_tag,req_record,output wire [72:0] req_owner,output wire [4:0] req_source,
 input wire rsp_v,output wire rsp_r,input wire rsp_we,rsp_error,input wire [1:0] rsp_checked,
 input wire [255:0] rsp_data,input wire [15:0] rsp_tag,rsp_record,
 input wire [72:0] rsp_owner,input wire [4:0] rsp_source,
 output wire result_v,input wire result_r,output wire [31:0] result_data,output wire [12:0] result_consumer,
 input wire release_v,output wire release_r,input wire [72:0] release_owner,
 input wire [15:0] release_record,input wire [4:0] release_source,
 output wire retained,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign bind_r=0;assign publication_r=0;assign read_r=0;assign req_v=0;assign req_addr=0;
  assign req_tag=0;assign req_record=0;assign req_owner=0;assign req_source=0;assign rsp_r=0;
  assign result_v=0;assign result_data=0;assign result_consumer=0;assign release_r=0;assign retained=0;assign fault=0;
 end else begin:on
  localparam [2:0] IDLE=0,BOUND=1,READY=2,REQUEST=3,RESPONSE=4,OUTPUT=5,FAIL=6;
  reg [71:0] code[0:7];wire [65:0] decoded[0:7];wire [63:0] d[0:7];wire [7:0] ue;
  for(genvar g=0;g<8;g=g+1)begin:rows_decode
   assign decoded[g]=decode64(code[g]);assign d[g]=decoded[g][63:0];assign ue[g]=decoded[g][65];
  end
  wire [2:0] state=d[4][2:0];wire [15:0] tag=d[4][18:3];
  wire [72:0] owner={d[1][8:0],d[0]};wire [15:0] record=d[1][24:9];
  wire [4:0] source=d[1][29:25];wire [12:0] held_rows=d[1][42:30];
  wire [36:0] base=d[2][36:0],limit=d[3][36:0];wire [23:0] lbase=d[2][60:37];
  wire [31:0] sent=d[6][31:0],returned=d[6][63:32];
  wire count_bad=(state==RESPONSE)?sent!=returned+1'b1:
     ((state==READY||state==REQUEST||state==OUTPUT||state==BOUND)&&sent!=returned);
  assign fault=(|ue)||state==FAIL||transport_fault||count_bad||state>FAIL;
  wire good=!fault&&!warm_reset;
  wire bind_shape=installed_checked==2'b11&&rows>=1&&rows<=4096&&byte_base[4:0]==0&&
    byte_limit>byte_base&&({1'b0,byte_base}+({25'd0,rows}<<5)<={1'b0,byte_limit})&&
    ({1'b0,logical_base}+({12'd0,rows}<<3)<=25'h1000000);
  wire pub_match=publication_owner==owner&&publication_record==record&&publication_source==source;
  wire rel_match=release_owner==owner&&release_record==record&&release_source==source;
  wire [24:0] offset={1'b0,read_word}-{1'b0,lbase};
  wire read_shape=read_word>=lbase&&offset<({12'd0,held_rows}<<3);
  wire [37:0] address={1'b0,base}+({13'd0,offset}<<2);
  wire read_bounds=read_shape&&address+38'd4<={1'b0,limit}&&!address[37];
  wire rsp_match=!rsp_we&&!rsp_error&&rsp_checked==2'b11&&rsp_tag==tag&&
    rsp_record==record&&rsp_owner==owner&&rsp_source==source;
  assign bind_r=state==IDLE&&good&&bind_shape;
  assign publication_r=state==BOUND&&good&&pub_match;
  assign read_r=state==READY&&good&&read_bounds&&!release_v;
  assign req_v=state==REQUEST&&good;assign req_addr={d[5][36:5],5'd0};
  assign req_tag=tag;assign req_record=record;assign req_owner=owner;assign req_source=source;
  assign rsp_r=state==RESPONSE&&good&&rsp_match;
  assign result_v=state==OUTPUT&&good;assign result_data=d[7][31:0];assign result_consumer=d[7][44:32];
  assign release_r=state==READY&&good&&rel_match&&!read_v;
  assign retained=state!=IDLE;
  integer i;
  always @(posedge clk or negedge por_n)begin
   if(!por_n)for(i=0;i<8;i=i+1)code[i]<=encode64(0);
   else begin
    case(state)
     IDLE:if(bind_v&&bind_r)begin
      code[0]<=encode64(bind_owner[63:0]);
      code[1]<=encode64({21'd0,rows,bind_source,bind_record,bind_owner[72:64]});
      code[2]<=encode64({3'd0,logical_base,byte_base});code[3]<=encode64({27'd0,byte_limit});
      code[4]<=encode64({45'd0,bind_tag,BOUND});code[6]<=encode64(0);
     end
     BOUND:if(publication_v&&publication_r)code[4]<=encode64({45'd0,tag,READY});
     READY:begin
      if(release_v&&release_r)begin code[4]<=encode64(0);code[6]<=encode64(0);end
      else if(read_v&&read_r)begin
       code[5]<=encode64({11'd0,address[4:2],read_consumer,address[36:0]});
       code[4]<=encode64({45'd0,tag,REQUEST});
      end
     end
     REQUEST:if(req_v&&req_r)begin code[6]<=encode64({returned,sent+1'b1});code[4]<=encode64({45'd0,tag,RESPONSE});end
     RESPONSE:if(rsp_v&&rsp_r)begin
      code[7]<=encode64({19'd0,d[5][49:37],rsp_data[d[5][52:50]*32+:32]});
      code[6]<=encode64({returned+1'b1,sent});code[4]<=encode64({45'd0,tag,OUTPUT});
     end
     OUTPUT:if(result_v&&result_r)begin
      if(tag==16'hffff)code[4]<=encode64(64'(FAIL));
      else code[4]<=encode64({45'd0,tag+16'd1,READY});
     end
     default:begin end
    endcase
    if(fault||(warm_reset&&state!=IDLE)||(bind_v&&(state!=IDLE||!bind_shape))||
       (publication_v&&(state!=BOUND||!pub_match))||(read_v&&state==READY&&!read_bounds)||
       (rsp_v&&(state!=RESPONSE||!rsp_match))||(release_v&&state==READY&&!rel_match))
      code[4]<=encode64(64'(FAIL));
   end
  end
 end endgenerate
endmodule
