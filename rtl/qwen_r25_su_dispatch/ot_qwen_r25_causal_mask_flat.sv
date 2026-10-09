// Package functions inlined verbatim for native Yosys package parser.
`timescale 1ns/1ps
// Full p4 causal consumer frame, model d46b7384b. Immutable ROM has no ECC;
// these mutable masks/context seats do. One resident frame, held until consumed.
module ot_qwen_r25_causal_mask #(
 parameter integer ENABLE=0, CAPACITY=8224
)(
 input wire clk,rst_n,
 input wire in_v,output wire in_rdy,input wire [1:0] in_checked,
 input wire [72:0] in_owner,input wire [79:0] in_query_positions,
 input wire [2:0] in_queries,input wire [19:0] in_row0,
 output wire out_v,input wire out_rdy,output wire [72:0] out_owner,
 output wire [19:0] out_row0,output wire [83:0] out_valid_lengths,
 output wire [127:0] out_live,output wire fault
);

  function automatic logic [71:0] encode64(input logic [63:0] data);
    logic [71:0] c; integer p, k, j;
    begin
      c='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin c[p-1]=data[j]; j=j+1; end
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0 && p!=(1<<k)) c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
      c[71]=^c[70:0]; encode64=c;
    end
  endfunction
  // {uncorrectable, corrected, data64}; overall parity is bit71.
  function automatic logic [65:0] decode64(input logic [71:0] code);
    logic [71:0] c; logic [6:0] syndrome; logic overall, ue, corrected;
    logic [63:0] data; integer p,k,j;
    begin
      c=code; syndrome='0; overall=^code; ue=0; corrected=0;
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0) syndrome[k]=syndrome[k]^code[p-1];
      if (syndrome!=0) begin
        if (overall && syndrome<=71) begin c[syndrome-1]=~c[syndrome-1]; corrected=1; end
        else ue=1;
      end else if (overall) begin c[71]=~c[71]; corrected=1; end
      data='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin data[j]=c[p-1]; j=j+1; end
      decode64={ue,corrected,data};
    end
  endfunction
  function automatic logic [143:0] encode_row(input logic [70:0] raw);
    encode_row={encode64({57'b0,raw[70:64]}),encode64(raw[63:0])};
  endfunction

 generate if (!ENABLE) begin:disabled
  assign in_rdy=0;assign out_v=0;assign out_owner=0;assign out_row0=0;
  assign out_valid_lengths=0;assign out_live=0;assign fault=0;
 end else begin:enabled
  reg [71:0] seat[0:5];
  wire [65:0] dec[0:5];wire [63:0] d[0:5];wire [5:0] ue;
  for(genvar k=0;k<6;k=k+1)begin:decode
   assign dec[k]=decode64(seat[k]);assign d[k]=dec[k][63:0];assign ue[k]=dec[k][65];
  end
  wire occupied=d[3][32],failed=d[3][33];
  wire [2:0] nq=d[3][31:29];
  wire [79:0] qpos={d[5][19:0],d[4][59:0]};
  assign fault=(|ue)||failed;
  assign in_rdy=!fault&&(!occupied||out_rdy);
  assign out_v=occupied&&!fault;
  assign out_live={d[1],d[0]};
  assign out_owner={d[3][28:20],d[2]};assign out_row0=d[3][19:0];
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
   if(!rst_n)for(i=0;i<6;i=i+1)seat[i]<=encode64(64'd0);
   else begin
    if(out_v&&out_rdy)seat[3]<=encode64(d[3]&~64'h100000000);
    if(in_v&&in_rdy)begin
     if(!shape)seat[3]<=encode64(64'h200000000);
     else begin
      seat[0]<=encode64(live[63:0]);seat[1]<=encode64(live[127:64]);
      seat[2]<=encode64(in_owner[63:0]);
      seat[3]<=encode64({30'd0,1'b0,1'b1,in_queries,in_owner[72:64],in_row0});
      seat[4]<=encode64({4'd0,in_query_positions[59:0]});
      seat[5]<=encode64({44'd0,in_query_positions[79:60]});
     end
    end
   end
  end
 end endgenerate
 initial if(CAPACITY<8195||CAPACITY>1048576||CAPACITY%32!=0)
  $fatal(1,"Qwen p4 mask capacity must include complete final row group");
endmodule
