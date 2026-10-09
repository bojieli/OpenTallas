`timescale 1ns/1ps
// Additive two-seat pipeline: comparison plus byte SECDED, then final64 SECDED.
// Every transient mask byte is protected; golden mask semantics unchanged.
module ot_qwen_r25_causal_mask_pipe #(
 parameter integer ENABLE=0, CAPACITY=8224, OWNER_W=73, CONTEXT_CODE_COPY=0
)(
 input wire clk,rst_n,
 input wire in_v,output wire in_rdy,input wire [1:0] in_checked,
 input wire [OWNER_W-1:0] in_owner,input wire [79:0] in_query_positions,
 input wire [2:0] in_queries,input wire [19:0] in_row0,
 output wire out_v,input wire out_rdy,output wire [OWNER_W-1:0] out_owner,
 output wire [19:0] out_row0,output wire [83:0] out_valid_lengths,
 output wire [127:0] out_live,output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if (!ENABLE) begin:disabled
  assign in_rdy=0;assign out_v=0;assign out_owner=0;assign out_row0=0;
  assign out_valid_lengths=0;assign out_live=0;assign fault=0;
 end else begin:enabled

 function automatic [12:0] enc8(input [7:0] data);
  reg [12:0] c;integer p,k,j;
  begin
   c=0;j=0;
   for(p=1;p<=12;p=p+1)if((p&(p-1))!=0)begin c[p-1]=data[j];j=j+1;end
   for(k=0;k<4;k=k+1)for(p=1;p<=12;p=p+1)
    if((p&(1<<k))!=0&&p!=(1<<k))c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
   c[12]=^c[11:0];enc8=c;
  end
 endfunction
 function automatic [9:0] dec8(input [12:0] code);
  reg [12:0] c;reg [3:0] syndrome;reg overall,ue,ce;reg [7:0] data;
  integer p,k,j;
  begin
   c=code;syndrome=0;data=0;ue=0;ce=0;
   for(k=0;k<4;k=k+1)for(p=1;p<=12;p=p+1)
    if((p&(1<<k))!=0)syndrome[k]=syndrome[k]^c[p-1];
   overall=^c;
   if(overall)begin
    if(syndrome==0)begin c[12]=~c[12];ce=1;end
    else if(syndrome<=12)begin c[syndrome-1]=~c[syndrome-1];ce=1;end
    else ue=1;
   end else if(syndrome!=0)ue=1;
   j=0;for(p=1;p<=12;p=p+1)if((p&(p-1))!=0)begin data[j]=c[p-1];j=j+1;end
   dec8={ue,ce,data};
  end
 endfunction
  localparam integer HI=OWNER_W-64,COUNT_L=20+HI,OCC=COUNT_L+3,FAIL=OCC+1;
  reg [71:0] seat[0:5];
  reg [12:0] pbyte[0:15];reg [71:0] pctx[0:3];
  wire [9:0] pb[0:15];wire [15:0] pue;
  wire [65:0] pd[0:3];wire [3:0] pctxue;
  wire [127:0] plive;
  for(genvar b=0;b<16;b=b+1)begin:byte_decode
   assign pb[b]=dec8(pbyte[b]);assign plive[b*8+:8]=pb[b][7:0];assign pue[b]=pb[b][9];
  end
  for(genvar c=0;c<4;c=c+1)begin:context_decode
   assign pd[c]=decode64(pctx[c]);assign pctxue[c]=pd[c][65];
  end
  wire poccupied=pd[1][OCC],pfailed=pd[1][FAIL];
  wire output_ready=!occupied||out_rdy;
  wire move_frame=poccupied&&output_ready&&!fault;

  wire [65:0] dec[0:5];wire [63:0] d[0:5];wire [5:0] ue;
  for(genvar k=0;k<6;k=k+1)begin:decode
   assign dec[k]=decode64(seat[k]);assign d[k]=dec[k][63:0];assign ue[k]=dec[k][65];
  end
  wire occupied=d[3][OCC],failed=d[3][FAIL];
  wire [2:0] nq=d[3][COUNT_L+:3];
  wire [79:0] qpos={d[5][19:0],d[4][59:0]};
  assign fault=(|ue)||failed||(|pue)||(|pctxue)||pfailed;
  assign in_rdy=!fault&&(!poccupied||output_ready);
  assign out_v=occupied&&!fault;
  assign out_live={d[1],d[0]};
  assign out_owner={d[3][20+:HI],d[2]};assign out_row0=d[3][19:0];
  for(genvar q=0;q<4;q=q+1)begin:lengths
   assign out_valid_lengths[q*21+:21]=(q<nq)?{1'b0,qpos[q*20+:20]}+21'd1:21'd0;
  end
  reg [127:0] live;
  reg shape;
  integer q,r;
  reg [20:0] limit,row;
  always @* begin
   live=0;
   shape=in_checked==2'b11&&(in_queries==1||in_queries==4)&&
         in_row0[4:0]==0&&({1'b0,in_row0}+21'd32<=CAPACITY);
   limit=0;row=0;
   for(q=0;q<4;q=q+1)begin
    limit={1'b0,in_query_positions[q*20+:20]}+21'd1;
    if(q<in_queries&&(limit==0||limit>CAPACITY))shape=0;
    if(q>0&&q<in_queries&&
       {1'b0,in_query_positions[q*20+:20]}!=
       ({1'b0,in_query_positions[19:0]}+q))shape=0;
    for(r=0;r<32;r=r+1)begin
     row={1'b0,in_row0}+r;
     live[q*32+r]=(q<in_queries)&&(row<limit)&&(row<CAPACITY);
    end
   end
  end
  integer i;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
    for(i=0;i<6;i=i+1)seat[i]<=encode64(64'd0);
    for(i=0;i<4;i=i+1)pctx[i]<=encode64(64'd0);
    for(i=0;i<16;i=i+1)pbyte[i]<=enc8(8'd0);
   end else begin
    if(out_v&&out_rdy)seat[3]<=encode64(d[3]&~(64'd1<<OCC));
    if(move_frame)begin
     seat[0]<=encode64(plive[63:0]);seat[1]<=encode64(plive[127:64]);
     // Context is already protected and unchanged; copy the entire codeword.
     // All existing decode/UE fences remain active. A CE is retained and corrected on read.
     seat[2]<=CONTEXT_CODE_COPY ? pctx[0] : encode64(pd[0][63:0]);
     seat[3]<=CONTEXT_CODE_COPY ? pctx[1] : encode64(pd[1][63:0]);
     seat[4]<=CONTEXT_CODE_COPY ? pctx[2] : encode64(pd[2][63:0]);
     seat[5]<=CONTEXT_CODE_COPY ? pctx[3] : encode64(pd[3][63:0]);
     pctx[1]<=encode64(pd[1][63:0]&~(64'd1<<OCC));
    end
    if(in_v&&in_rdy)begin
     if(!shape)pctx[1]<=encode64((64'd1<<FAIL));
     else begin
      for(i=0;i<16;i=i+1)pbyte[i]<=enc8(live[i*8+:8]);
      pctx[0]<=encode64(in_owner[63:0]);
      pctx[1]<=encode64({{(64-HI-25){1'b0}},1'b0,1'b1,in_queries,in_owner[OWNER_W-1:64],in_row0});
      pctx[2]<=encode64({4'd0,in_query_positions[59:0]});
      pctx[3]<=encode64({44'd0,in_query_positions[79:60]});
     end
    end
   end
  end
 end endgenerate
 initial if(OWNER_W!=73&&OWNER_W!=74)$fatal(1,"owner width must preserve legacy73 or native Qwen74");
 initial if(CAPACITY<8195||CAPACITY>1048576||CAPACITY%32!=0)
  $fatal(1,"Qwen p4 mask capacity must include complete final row group");
endmodule
