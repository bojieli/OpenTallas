`timescale 1ns/1ps
// Functional source/ordinal FIFO at actual PC write acceptance. Physical
// completions may reorder across PCs. ACKs retire each source's accepted prefix,
// so later writes cannot satisfy an earlier cumulative visibility fence.
// Plain flop state: no ECC/parity/mirrors, leases, epochs or aperture state.
// One stack service accepts at most one write/cycle, same-PC WD is issue ordered.
module ot_hbm_write_source_ordered #(
 parameter integer ENABLE=0,DEPTH=8
)(input wire ck,rst_n,input wire[31:0]issue_v,input wire[1:0]issue_source,
 output wire[31:0]issue_rdy,busy_pc,input wire[31:0]done_v,
 output reg[17:0]ack_n,output reg fault);
 localparam integer PW=$clog2(DEPTH),N=32*DEPTH,OW=$clog2(N);
 generate if(!ENABLE)begin:g_off
  assign issue_rdy=0;assign busy_pc=0;
  always @*begin ack_n=0;fault=0;end
 end else begin:g_on
  reg[1:0]id[0:31][0:DEPTH-1];reg[OW-1:0]ord[0:31][0:DEPTH-1];
  reg[PW-1:0]wp[0:31],rp[0:31];reg[PW:0]count[0:31];
  reg[N-1:0]completed[0:2];reg[OW-1:0]head[0:2],tail[0:2];reg[OW:0]pending[0:2];
  reg[N-1:0]next_completed[0:2];reg[2:0]retire;reg bad;integer p,s;
  genvar g;
  for(g=0;g<32;g=g+1)begin:gr
   assign issue_rdy[g]=!fault&&issue_source<3&&count[g]<DEPTH&&pending[issue_source]<N;
   assign busy_pc[g]=count[g]!=0;
  end
  always @*begin
   bad=0;retire=0;
   for(integer j=0;j<3;j=j+1)next_completed[j]=completed[j];
   if((issue_v&(issue_v-1'b1))!=0)bad=1;
   for(integer j=0;j<32;j=j+1)begin
    if(issue_v[j]&&!issue_rdy[j])bad=1;
    if(done_v[j])begin
     if(count[j]==0||id[j][rp[j]]>=3)bad=1;
     else if(next_completed[id[j][rp[j]]][ord[j][rp[j]]])bad=1;
     else next_completed[id[j][rp[j]]][ord[j][rp[j]]]=1;
    end
   end
   // One ACK/source/cycle matches the one-write stack admission rate and
   // leaves the existing6-bit count ABI unchanged. A backlog is explicit.
   for(integer j=0;j<3;j=j+1)
    if(pending[j]!=0&&next_completed[j][head[j]])begin
     retire[j]=1;next_completed[j][head[j]]=0;
    end
  end
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin
    ack_n<=0;fault<=0;
    for(p=0;p<32;p=p+1)begin wp[p]<=0;rp[p]<=0;count[p]<=0;end
    for(s=0;s<3;s=s+1)begin completed[s]<=0;head[s]<=0;tail[s]<=0;pending[s]<=0;end
   end else begin
    ack_n<=0;if(bad)fault<=1;
    if(!fault&&!bad)begin
     ack_n<={5'b0,retire[2],5'b0,retire[1],5'b0,retire[0]};
     for(p=0;p<32;p=p+1)begin
      count[p]<=count[p]+issue_v[p]-done_v[p];
      if(issue_v[p])begin id[p][wp[p]]<=issue_source;ord[p][wp[p]]<=tail[issue_source];wp[p]<=wp[p]+1'b1;end
      if(done_v[p])rp[p]<=rp[p]+1'b1;
     end
     for(s=0;s<3;s=s+1)begin
      completed[s]<=next_completed[s];
      pending[s]<=pending[s]+((|issue_v)&&issue_source==s)-retire[s];
      if((|issue_v)&&issue_source==s)tail[s]<=tail[s]+1'b1;
      if(retire[s])head[s]<=head[s]+1'b1;
     end
    end
   end
  end
 end endgenerate
`ifndef SYNTHESIS
 initial if(DEPTH<2||(1<<PW)!=DEPTH)$fatal(1,"source FIFOdepth must poweroftwo>=2");
`endif
endmodule
