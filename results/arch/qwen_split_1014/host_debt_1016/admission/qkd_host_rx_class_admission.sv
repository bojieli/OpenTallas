`timescale 1ns/1ps
// Exceptional HOST admission only. The actual class receiver retains its
// original HOST4/ING16 board promises. Already credited arrivals can be held
// here during a native reservation without entering the downstream HOST path.
// CTRL and peer-credit traffic continue. No native operation uses these queues.
module qkd_host_rx_class_admission #(parameter integer MUT=0,STRAPPED=0)(
 input wire ck,rst_n,input wire[2:0]die_id,input wire rx_v,input wire[527:0]rx_d,output wire rx_cr,
 input wire native_reserved,ownership_valid,
 output reg host_v,output reg[511:0]host_d,input wire host_cr,
 output wire ctrl_v,output wire[511:0]ctrl_d,input wire ctrl_cr,
 output reg ing_v,output reg[1:0]ing_cls,output reg[511:0]ing_d,input wire[4:0]ing_crn,
 output wire[23:0]credit_return,peer_credit,output wire fault,
 output reg admission_open,launch_quiet,output wire deferred
);
 wire hv,iv,base_fault;wire[511:0]hd,id;wire[1:0]ic;
 reg reserved_q,valid_q;reg[511:0]hq[0:3];reg[513:0]iq[0:15];
 reg[1:0]hw,hr;reg[3:0]iw,ir;reg[2:0]hn,hcredits;reg[4:0]in_count,icredits;
 reg hcq;reg[4:0]icq;reg queue_fault;
 wire permit=(MUT==1)||(!reserved_q&&valid_q);
 wire hp=permit&&!fault&&hn!=0&&hcredits!=0;
 wire ip=permit&&!fault&&in_count!=0&&icredits!=0;
 assign fault=base_fault|queue_fault;
 assign deferred=hn!=0||in_count!=0;
 qkd_host_rx_class #(.MUT(0),.STRAPPED(STRAPPED))u_rx(
  .ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),
  .host_v(hv),.host_d(hd),.host_cr(host_cr),.ctrl_v(ctrl_v),.ctrl_d(ctrl_d),.ctrl_cr(ctrl_cr),
  .ing_v(iv),.ing_cls(ic),.ing_d(id),.ing_crn(ing_crn),
  .credit_return(credit_return),.peer_credit(peer_credit),.fault(base_fault));
 always @(posedge ck)begin
  if(hv&&hn<4)hq[hw]<=hd;
  if(iv&&in_count<16)iq[iw]<={ic,id};
  if(hp)host_d<=hq[hr];
  if(ip){ing_cls,ing_d}<=iq[ir];
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin reserved_q<=1;valid_q<=0;admission_open<=0;launch_quiet<=0;
   hw<=0;hr<=0;iw<=0;ir<=0;hn<=0;in_count<=0;hcredits<=4;icredits<=16;
   hcq<=0;icq<=0;host_v<=0;ing_v<=0;queue_fault<=0;
  end else begin
   reserved_q<=native_reserved;valid_q<=ownership_valid;hcq<=host_cr;icq<=ing_crn;
   admission_open<=permit&&!fault;host_v<=hp;ing_v<=ip;
   // Deferred words have not entered the downstream HOST path. This signal
   // observes launches, not a claim that all downstream work has drained.
   launch_quiet<=!hp&&!ip&&!host_v&&!ing_v&&!fault;
   if(hv&&hn==4&&!hp)queue_fault<=1;
   if(iv&&in_count==16&&!ip)queue_fault<=1;
   if(hv)hw<=hw+1'b1;if(hp)hr<=hr+1'b1;
   if(iv)iw<=iw+1'b1;if(ip)ir<=ir+1'b1;
   case({hv,hp})2'b10:hn<=hn+1'b1;2'b01:hn<=hn-1'b1;default:;endcase
   case({iv,ip})2'b10:in_count<=in_count+1'b1;2'b01:in_count<=in_count-1'b1;default:;endcase
   if({1'b0,hcredits}+4'(hcq)-4'(hp)>4)queue_fault<=1;
   else hcredits<=hcredits+3'(hcq)-3'(hp);
   if({1'b0,icredits}+6'(icq)-6'(ip)>16)queue_fault<=1;
   else icredits<=icredits+icq-5'(ip);
  end
 end
endmodule
