`timescale 1ns/1ps
// FUNCTIONAL_ONLY host-memory/CSR packet environment. Gold is descriptor data,
// never DUT mirror, current grant, binding output or internal scheduler state.
module native_join_host_memory(
 input wire clk,por_n,
 input wire tx_v,input wire[511:0]tx_d,output reg tx_cr,
 output reg rx_v,output reg[511:0]rx_d,input wire rx_cr,
 input wire hold_dma_b,
 output integer csr_acks,read_beats,write_beats,cq_entries,cq_successes,cq_errors,
 output reg[63:0]last_cq_w0,last_cq_w1
);
 reg[63:0]memory[0:2047];
 reg[511:0]reply_queue[$];
 reg[511:0]manual_queue[$];
 reg[511:0]packet;
 integer csr_issued=0;
 integer edge_count=0;
 integer cq_word1_pending=0;
 integer seen_reads[0:2047];
 integer i;
 initial begin
  tx_cr=0;rx_v=0;rx_d=0;csr_acks=0;read_beats=0;write_beats=0;cq_entries=0;cq_successes=0;cq_errors=0;last_cq_w0=0;last_cq_w1=0;
  for(i=0;i<2048;i=i+1)begin memory[i]=0;seen_reads[i]=0;end
 end
 task automatic descriptor(input integer index,input[15:0]client,input[7:0]op,input[7:0]flags,input[7:0]slot,input[15:0]plen,max_new,input[63:0]prompt_ptr);
  integer a;
  a=('h1000+index*32)/8;
  memory[a]={max_new,plen,client,flags,op};memory[a+1]=prompt_ptr;memory[a+2]={56'd0,slot};memory[a+3]=64'h0003ffff0003ffff;
 endtask
 task automatic prompt_word(input integer index,input[17:0]lo,hi);
  memory[('h3000/8)+index]={14'd0,hi,14'd0,lo};
 endtask
 task automatic csr_write(input[12:0]address,input[31:0]data);
  reg[511:0]p;integer expected;
  @(negedge clk);expected=csr_issued+1;csr_issued=expected;
  p=0;p[7:0]=1;p[15:8]=1;p[31:16]=16'(expected);p[44:32]=address;p[127:96]=data;p[131:128]=15;
  manual_queue.push_back(p);
  wait(csr_acks>=expected);
  repeat(2)@(negedge clk);
 endtask
 // bridge owns packet credits. Memory supplies exactly one response per actual
 // read/write request. Delayed B does not suppress already accepted work.
 always @(negedge clk)begin
  rx_v=0;tx_cr=0;edge_count=edge_count+1;
  if(por_n)begin
   if(tx_v)begin
    tx_cr=1;packet=0;packet[15:8]=1;
    case(tx_d[7:0])
     8'h81:begin
      if(tx_d[33:32]!=0)$fatal(1,"CSR_BRESP edge=%0d resp=%h",edge_count,tx_d[33:32]);
      if(tx_d[31:16]!=16'(csr_acks+1))$fatal(1,"CSR_PACKET_ID_OR_DUPLICATE got=%h expected=%0d",tx_d[31:16],csr_acks+1);
      csr_acks=csr_acks+1;
     end
     8'h82:begin if(tx_d[33:32]!=0)$fatal(1,"CSR_RRESP");end
     8'h12:begin
      if(tx_d[34:32]!=0 || tx_d[95:32] >= 16384)$fatal(1,"DMA_READ_ADDRESS %h",tx_d[95:32]);
      packet[7:0]=8'h13;packet[34]=1;packet[159:96]=memory[tx_d[95:35]];
      seen_reads[tx_d[95:35]]=seen_reads[tx_d[95:35]]+1;
      read_beats=read_beats+1;reply_queue.push_back(packet);
     end
     8'h14:begin
      if(tx_d[34:32]!=0 || tx_d[95:32] >=16384)$fatal(1,"DMA_WRITE_ADDRESS %h",tx_d[95:32]);
      for(integer b=0;b<8;b=b+1)if(tx_d[160+b])memory[tx_d[95:35]][b*8+:8]=tx_d[96+b*8+:8];
      write_beats=write_beats+1;
      if(tx_d[95:32]>=64'h2000 && tx_d[95:32]<64'h2100)begin
       if(tx_d[35])begin
        if(cq_word1_pending)$fatal(1,"CQ_WORD1_DUPLICATE");
        cq_word1_pending=1;last_cq_w1=tx_d[159:96];
       end else begin
        if(!cq_word1_pending)$fatal(1,"CQ_WORD0_BEFORE_WORD1");
        cq_word1_pending=0;last_cq_w0=tx_d[159:96];cq_entries=cq_entries+1;
        if(tx_d[98:97]==2'd3)cq_errors=cq_errors+1;else cq_successes=cq_successes+1;
        if(tx_d[127:112]!=16'h91e3)$fatal(1,"CQ_CLIENT_TAG_GOLD got=%h",tx_d[127:112]);
        $display("CQ_PACKET time=%0t edge=%0d entry=%0d w0=%h w1=%h",$time,edge_count,cq_entries,last_cq_w0,last_cq_w1);
       end
      end
      packet[7:0]=8'h15;reply_queue.push_back(packet);
     end
     default:$fatal(1,"HOST_UNEXPECTED_PACKET op=%h",tx_d[7:0]);
    endcase
   end
   if(manual_queue.size()!=0)begin rx_v=1;rx_d=manual_queue.pop_front();end
   else if(reply_queue.size()!=0 && !(hold_dma_b && reply_queue[0][7:0]==8'h15))begin rx_v=1;rx_d=reply_queue.pop_front();end
  end
 end
endmodule
