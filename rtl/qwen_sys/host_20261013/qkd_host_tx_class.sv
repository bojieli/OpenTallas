`timescale 1ns/1ps
// TX half of W528 transport. Four local source queue credits per HOST/CTRL/
// completion. Peer application credits are independent of adapter IBUF4.
// Returned class-credit packet7 has priority, then IRQ level6, then fair RR.
module qkd_host_tx_class #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire host_v,input wire[511:0]host_d,output reg host_cr,
 input wire ctrl_v,input wire[511:0]ctrl_d,output reg ctrl_cr,
 input wire ing_v,input wire[63:0]ing_d,output reg ing_cr,
 input wire[23:0]credit_return,peer_credit,input wire irq,
 output reg tx_v,output reg[527:0]tx_d,input wire tx_cr,
 output reg fault
);
 reg[511:0]hq[0:3],cq[0:3];reg[63:0]iq[0:3];reg[1:0]wp[0:2],rp[0:2];reg[2:0]count[0:2];
 reg hv,cv,iv,tc,irq_q,irq_sent;reg[511:0]hd,cd;reg[63:0]id;
 reg[23:0]rc,pc;reg[7:0]acc[0:2];reg[3:0]peer[0:2],physical;reg[1:0]rr;
 integer chosen;
 always @*begin
  chosen=-1;
  for(integer j=2;j>=0;j--)begin
   if(count[(int'(rr)+j)%3]!=0&&peer[(int'(rr)+j)%3]!=0)chosen=(int'(rr)+j)%3;
  end
 end
 wire free_credit=acc[0]!=0||acc[1]!=0||acc[2]!=0;
 wire send=!fault&&physical!=0;
 wire appsend=send&&!free_credit&&(irq_q==irq_sent)&&chosen>=0;
 always @(posedge ck)begin
  hd<=host_d;cd<=ctrl_d;id<=ing_d;
  if(hv&&count[0]<4)hq[wp[0]]<=hd;
  if(cv&&count[1]<4)cq[wp[1]]<=cd;
  if(iv&&count[2]<4)iq[wp[2]]<=id;
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin hv<=0;cv<=0;iv<=0;tc<=0;irq_q<=0;irq_sent<=0;rc<=0;pc<=0;physical<=4;rr<=0;
   tx_v<=0;tx_d<=0;host_cr<=0;ctrl_cr<=0;ing_cr<=0;fault<=0;
   for(integer k=0;k<3;k++)begin wp[k]<=0;rp[k]<=0;count[k]<=0;peer[k]<=4;acc[k]<=0;end
  end else begin
   hv<=host_v;cv<=ctrl_v;iv<=ing_v;tc<=tx_cr;irq_q<=irq;rc<=credit_return;pc<=peer_credit;
   tx_v<=0;host_cr<=0;ctrl_cr<=0;ing_cr<=0;
   physical<=physical+4'(tc)-4'(send&&(free_credit||irq_q!=irq_sent||appsend));
   if(tc&&physical==4&&!(send&&(free_credit||irq_q!=irq_sent||appsend)))fault<=1;
   for(integer k=0;k<3;k++)begin
    reg push,pop;
    push=(k==0)?hv:(k==1)?cv:iv;pop=appsend&&chosen==k;
    if(push)begin if(count[k]==4)fault<=1;else wp[k]<=wp[k]+1'b1;end
    if(pop)rp[k]<=rp[k]+1'b1;
    case({push&&count[k]<4,pop})2'b10:count[k]<=count[k]+1'b1;2'b01:count[k]<=count[k]-1'b1;default:;endcase
    if(9'(peer[k])+9'(pc[k*8+:8])-9'(pop)>4)fault<=1;
    else peer[k]<=peer[k]+4'(pc[k*8+:8])-4'(pop);
    if(send&&free_credit)acc[k]<=rc[k*8+:8];
    else begin
     if(9'(acc[k])+9'(rc[k*8+:8])>255)fault<=1;
     else acc[k]<=acc[k]+rc[k*8+:8];
    end
   end
   if(send)begin
    if(free_credit)begin tx_v<=1;tx_d<={4'd7,12'd0,488'd0,acc[2],acc[1],acc[0]};end
    else if(irq_q!=irq_sent)begin tx_v<=1;tx_d<={4'd6,12'd0,511'd0,irq_q};irq_sent<=irq_q;end
    else if(appsend)begin
     tx_v<=1;rr<=2'((chosen+1)%3);
     case(chosen)
      0:begin tx_d<={4'd0,12'd0,(MUT==1)?hq[rp[0]]^512'd1:hq[rp[0]]};host_cr<=1;end
      1:begin tx_d<={4'd1,12'd0,cq[rp[1]]};ctrl_cr<=1;end
      2:begin tx_d<={4'd5,12'd0,448'd0,iq[rp[2]]};ing_cr<=1;end
     endcase
    end
   end
  end
 end
endmodule
