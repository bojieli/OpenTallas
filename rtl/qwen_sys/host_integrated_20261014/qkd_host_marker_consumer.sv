`timescale 1ns/1ps
// Storage-backed visibility certificate. The producer owns one marker credit;
// credit returns only after the verified complete prefix has been committed to
// these registers. No marker_v -> marker_cr combinational acknowledgement.
module qkd_host_marker_consumer #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire marker_v,input wire[65:0]marker,
 input wire[31:0]issued,landed,input wire[12:0]est,input wire source_fault,
 output reg marker_cr,output reg certificate_v,output reg[65:0]certificate,
 output reg[31:0]certificate_prefix,output reg fault);
 reg pending;reg[65:0]word;reg[31:0]target,completed;reg ready_image,bad;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin marker_cr<=0;certificate_v<=0;certificate<=0;certificate_prefix<=0;fault<=0;pending<=0;word<=0;target<=0;completed<=0;ready_image<=0;bad<=0;end
  else begin
   marker_cr<=0;certificate_v<=0;
   if(marker_v)begin
    if(pending)fault<=1;
    else begin pending<=1;word<=marker;target<=issued;completed<=landed;ready_image<=est[0]&&!est[1];bad<=source_fault;end
   end
   if(pending)begin
    pending<=0;
    if(!bad&&ready_image&&(target==completed||MUT==1)&&!fault)begin
     certificate<=word;certificate_prefix<=target;certificate_v<=1;marker_cr<=1;
    end else fault<=1;
   end
  end
 end
endmodule
