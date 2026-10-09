`timescale 1ns/1ps
// Full32-PC completion identity ledger. Same-PC completions must follow issue
// order; cross-PC completions may reorder freely. Admission reserves a source
// slot on actual PHY acceptance. Same-cycle completion of a new request to an
// emptyPC is outside the registered PHY contract and faults.
module ot_hbm_write_source_pc #(parameter integer DEPTH=8)(
 input wire ck,rst_n,
 input wire [31:0] issue_v,input wire[1:0] issue_source,
 output wire[31:0] issue_rdy,
 input wire[31:0] done_v,
 output reg[17:0] ack_n,output reg fault
);
 localparam integer PW=$clog2(DEPTH);
 reg[1:0] ids[0:31][0:DEPTH-1];
 reg[PW-1:0] wp[0:31],rp[0:31];reg[PW:0] count[0:31];
 reg[5:0] a0,a1,a2;reg bad;
 genvar p;
 generate for(p=0;p<32;p=p+1)begin:g_ready
  assign issue_rdy[p]=(count[p]<DEPTH)&&!fault;
 end endgenerate
 always @(*)begin
  a0=0;a1=0;a2=0;bad=0;
  for(integer j=0;j<32;j=j+1)begin
   if(issue_v[j] && (!issue_rdy[j] || issue_source==3))bad=1;
   if(done_v[j])begin
    if(count[j]==0)bad=1;
    else case(ids[j][rp[j]])
     0:a0=a0+1'b1;1:a1=a1+1'b1;2:a2=a2+1'b1;default:bad=1;
    endcase
   end
  end
 end
 integer i;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;ack_n<=0;
   for(i=0;i<32;i=i+1)begin wp[i]<=0;rp[i]<=0;count[i]<=0;end
  end else begin
   ack_n<=0;
   if(bad)fault<=1;
   if(!fault&&!bad)begin
    ack_n<={a2,a1,a0};
    for(i=0;i<32;i=i+1)begin
     count[i]<=count[i]+(issue_v[i]?1'b1:1'b0)-(done_v[i]?1'b1:1'b0);
     if(issue_v[i])begin ids[i][wp[i]]<=issue_source;wp[i]<=wp[i]+1'b1;end
     if(done_v[i])rp[i]<=rp[i]+1'b1;
    end
   end
  end
 end
`ifndef SYNTHESIS
 initial if(DEPTH<2 || (1<<PW)!=DEPTH)$fatal(1,"ledger depth must poweroftwo>=2");
`endif
endmodule
