`timescale 1ns/1ps
// FUNCTIONAL_ONLY conditional packet link: true emitted CTRL packets, bounded
// transport queue, credit returned to actual producer only after target rx_cr.
// Deliberately one delivery outstanding per target; no native latency claim.
module native_join_ctrl_link(
 input wire clk,por_n,
 input wire[7:0]tx_v,input wire[4095:0]tx_d,output reg[7:0]tx_cr,
 output reg[7:0]rx_v,output reg[4095:0]rx_d,input wire[7:0]rx_cr,
 output integer emitted,consumed
);
 typedef struct packed {logic[2:0]source;logic[511:0]data;} entry_t;
 entry_t q0[$],q1[$],q2[$],q3[$],q4[$],q5[$],q6[$],q7[$];
 reg[7:0]waiting;
 reg[2:0]owner[0:7];
 integer credit_due[0:7];
 entry_t item;
 integer i,j,target;
 task automatic enqueue(input integer d,input entry_t e);
  case(d)0:q0.push_back(e);1:q1.push_back(e);2:q2.push_back(e);3:q3.push_back(e);4:q4.push_back(e);5:q5.push_back(e);6:q6.push_back(e);7:q7.push_back(e);endcase
  if(q0.size()>32||q1.size()>32||q2.size()>32||q3.size()>32||q4.size()>32||q5.size()>32||q6.size()>32||q7.size()>32)$fatal(1,"CTRL_LINK_CAPACITY");
 endtask
 function automatic integer queued(input integer d);
  case(d)0:queued=q0.size();1:queued=q1.size();2:queued=q2.size();3:queued=q3.size();4:queued=q4.size();5:queued=q5.size();6:queued=q6.size();7:queued=q7.size();endcase
 endfunction
 task automatic dequeue(input integer d,output entry_t e);
  case(d)0:e=q0.pop_front();1:e=q1.pop_front();2:e=q2.pop_front();3:e=q3.pop_front();4:e=q4.pop_front();5:e=q5.pop_front();6:e=q6.pop_front();7:e=q7.pop_front();endcase
 endtask
 initial begin waiting=0;rx_v=0;rx_d=0;tx_cr=0;emitted=0;consumed=0;for(i=0;i<8;i++)begin owner[i]=0;credit_due[i]=0;end end
 always @(negedge clk)begin
  tx_cr=0;rx_v=0;
  if(por_n)begin
   for(i=0;i<8;i=i+1)begin
    if(rx_cr[i])begin
     if(!waiting[i])$fatal(1,"CTRL_LINK_UNOWNED_CREDIT target=%0d",i);
     credit_due[owner[i]]=credit_due[owner[i]]+1;waiting[i]=0;consumed=consumed+1;
    end
    if(tx_v[i])begin
     target=-1;
     for(j=0;j<8;j=j+1)if(tx_d[i*512+24+j])begin if(target!=-1)$fatal(1,"CTRL_LINK_MULTI_TARGET");target=j;end
     if(target<0)$fatal(1,"CTRL_LINK_NO_TARGET");
     item.source=3'(i);item.data=tx_d[i*512+:512];enqueue(target,item);emitted=emitted+1;
    end
   end
   for(i=0;i<8;i=i+1)begin
    if(credit_due[i]!=0)begin tx_cr[i]=1;credit_due[i]=credit_due[i]-1;end
    if(!waiting[i]&&queued(i)!=0)begin dequeue(i,item);rx_v[i]=1;rx_d[i*512+:512]=item.data;owner[i]=item.source;waiting[i]=1;end
   end
  end
 end
endmodule
