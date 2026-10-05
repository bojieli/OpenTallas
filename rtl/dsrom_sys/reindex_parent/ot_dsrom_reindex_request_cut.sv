`timescale 1ns/1ps
// One real request slot per PC in addition to the control's existing output
// slot. No combinational downstream-ready bypass; fields are sealed SECDED61.
module ot_dsrom_reindex_request_cut #(parameter integer PC=0, KIND=0)(
 input wire clk,rst_n,input wire in_valid,output wire in_ready,
 input wire [47:0] in_data,output wire out_valid,input wire out_ready,
 output wire [47:0] out_data,output reg fault
);
 reg valid,valid_n;reg [60:0] word;
 function automatic [60:0] enc(input [53:0] d);
  reg [60:0] w;reg par;integer p,k,j;
  begin w=0;j=0;for(p=1;p<=60;p=p+1)if((p&(p-1))!=0)begin w[p-1]=d[j];j=j+1;end
   for(k=0;k<6;k=k+1)begin par=0;for(p=1;p<=60;p=p+1)if((p&(1<<k))!=0)par=par^w[p-1];w[(1<<k)-1]=par;end
   w[60]=^w[59:0];enc=w;end
 endfunction
 reg [5:0] syndrome;reg [53:0] payload;integer p,k,j;
 always @*begin
  syndrome=0;payload=0;j=0;
  for(p=1;p<=60;p=p+1)begin
   if((p&(p-1))!=0)begin payload[j]=word[p-1];j=j+1;end
   for(k=0;k<6;k=k+1)if((p&(1<<k))!=0)syndrome[k]=syndrome[k]^word[p-1];
  end
 end
 wire state_ok=(valid==~valid_n);
 wire clean=(syndrome==0)&&!(^word)&&(payload[53:48]=={1'(KIND),5'(PC)});
 assign in_ready=state_ok&&!valid&&!fault;
 assign out_valid=state_ok&&valid&&clean&&!fault;
 assign out_data=payload[47:0];
 always @(posedge clk)begin
  if(!rst_n)begin valid<=0;valid_n<=1;fault<=0;end
  else begin
   if(!state_ok||(valid&&!clean))fault<=1;
   if(out_valid&&out_ready)begin valid<=0;valid_n<=1;end
   if(in_valid&&in_ready)begin word<=enc({1'(KIND),5'(PC),in_data});valid<=1;valid_n<=0;end
  end
 end
endmodule
