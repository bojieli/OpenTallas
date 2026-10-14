`timescale 1ns/1ps
module tb_hbm_b2_packet_mux;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0;reg [1:0] req_v=0;wire [1:0] req_r;
 reg [673:0] req=0;wire [1:0] rsp_v;wire [545:0] rsp;
 wire [337:0] cq;wire fault,drained;
`ifdef ACTUAL_MEMORY
 wire [273:0] cr;wire [547:0] crs;wire [8*285-1:0] pq;wire [7:0] pq_cr;
 wire [8*266-1:0] pr;wire [265:0] pr0;wire pc0;wire [2:0] hs;wire [17:0] bs;
 assign cr=crs[273:0];assign pr={1862'b0,pr0};assign pq_cr={7'b0,pc0};
 ot_vms_hub #(.NC(1)) hub(.clk(clk),.rst_n(rst_n),.sid(2'd0),.cq({338'b0,cq}),.cr(crs),
  .pq(pq),.pq_cr(pq_cr),.pr(pr),.cwi(),.cwi_cr(1'b0),.cci(),.cci_cr(1'b0),.cco0(264'b0),.cco1(264'b0),.status(hs));
 ot_vms_bank bank(.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),
  .rq(34'b0),.rq_cr(),.rr(),.wq(562'b0),.wq_cr(),.wq_done(),.dq(281'b0),.dq_done(),
  .kq(281'b0),.kq_cr(),.kq_done(),.xq(276'b0),.xq_cr(),.xq_done(),.xq2(276'b0),.xq2_cr(),.xq2_done(),
  .eg(),.eg_cr(2'b0),.pq(pq[284:0]),.pq_cr(pc0),.pr(pr0),.status(bs));
`else
 reg [273:0] cr=0;
`endif
`ifdef NATIVE_PEERS
 wire [675:0] c_cq;
 wire [547:0] c_cr;
 for(genvar c=0;c<2;c=c+1)begin:peer
  assign c_cq[c*338+:338]={req_v[c],req[c*337+:337]};
  assign rsp_v[c]=c_cr[c*274+273];assign rsp[c*273+:273]=c_cr[c*274+:273];
  assign req_r[c]=1'b1;
 end
 ot_hbm_b2_packet_share #(.MUT(MUT)) u(.clk(clk),.rst_n(rst_n),.c_cq(c_cq),.c_cr(c_cr),.cq(cq),.cr(cr),.fault(fault),.drained(drained));
`else
 ot_hbm_b2_packet_mux #(.MUT(MUT)) u(.*);
`endif
 reg [273:0] pipe[0:19];reg [15:0] expected[0:1][0:2047];
 integer head[0:1],tail[0:1],sent=0,got=0,t=0,issued=0;
 integer peak=0,outstanding=0,last=0;
 integer active[0:1];
 function automatic [255:0] value(input [15:0] tag);
  for(integer j=0;j<8;j=j+1)value[j*32+:32]={16'h5a73,tag}+j;
 endfunction
 initial begin
  for(integer j=0;j<20;j=j+1)pipe[j]=0;
  for(integer j=0;j<2;j=j+1)begin head[j]=0;tail[j]=0;active[j]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  while(got<4096&&t<30000)begin
   @(negedge clk);t=t+1;
   if(fault)$fatal(1,"unexpected fault");
   for(integer j=0;j<2;j=j+1)begin
    if(rsp_v[j])begin
     if(head[j]>=tail[j])$fatal(1,"unsolicited issuer response");
     if(rsp[j*273+257+:16]!=expected[j][head[j]]||(expected[j][head[j]][0]&&rsp[j*273+:256]!=value(expected[j][head[j]]-1'b1))||rsp[j*273+256]!=!expected[j][head[j]][0])$fatal(1,"issuer/tag/data/echo mismatch");
     head[j]=head[j]+1;got=got+1;active[j]=active[j]-1;
    end
   end
`ifdef ACTUAL_MEMORY
   if(hs!=0||bs!=0)$fatal(1,"actual native VM status");
`else
   cr=pipe[19];
   for(integer j=19;j>0;j=j-1)pipe[j]=pipe[j-1];
   pipe[0]=0;
   if(cq[337])begin
    if(cq[335:304]!=32'(((cq[15:0]/2048)*512+((cq[15:0]%2048)/2)%512)*256)||cq[303:48]!=value(cq[15:0]&16'hfffe)||cq[47:16]!=32'hffffffff)$fatal(1,"packet field mapping");
    pipe[0]={1'b1,cq[15:0],cq[336],value(cq[15:0]&16'hfffe)};issued=issued+1;
   end
`endif
   outstanding=sent-got;if(outstanding>peak)peak=outstanding;
   `ifndef NATIVE_PEERS
   if(outstanding>4)$fatal(1,"four-credit overrun");
`endif
   for(integer j=0;j<2;j=j+1)begin
    `ifdef NATIVE_PEERS
    req_v[j]=tail[j]<2048&&active[j]<4;
`else
    req_v[j]=tail[j]<2048;
`endif
    req[j*337+:337]={1'(1-tail[j]%2),32'((j*512+(tail[j]/2)%512)*256),value(16'(j*2048+(tail[j]/2)*2)),32'hffffffff,16'(j*2048+tail[j])};
   end
   @(posedge clk);
   for(integer j=0;j<2;j=j+1)if(req_v[j]&&req_r[j])begin expected[j][tail[j]]=16'(j*2048+tail[j]);tail[j]=tail[j]+1;sent=sent+1;active[j]=active[j]+1;end
  end
  @(negedge clk);req_v=0;
`ifndef ACTUAL_MEMORY
 cr=0;
`endif
  if(got!=4096||sent!=4096||peak!=
`ifdef NATIVE_PEERS
8
`else
4
`endif
)$fatal(1,"traffic/credits timeout");
  repeat(3)@(negedge clk);
  if(!drained)$fatal(1,"not drained");
`ifdef NATIVE_PEERS
  // Pulse-only peers have exactly FOUR retained permissions, even when queued.
  req_v=2'b11;
  repeat(5)@(negedge clk);
  req_v=0;
  if(!fault)$fatal(1,"fifth native peer request not refused");
`endif
`ifndef ACTUAL_MEMORY
  // A hub has no spontaneous return permission; refuse an unmatched response.
  cr={1'b1,16'hbeef,1'b0,256'b0};@(negedge clk);cr=0;
  if(!fault)$fatal(1,"unsolicited response accepted");
`endif
`ifdef ACTUAL_MEMORY
`ifdef NATIVE_PEERS
  $display("PASS_PACKET_NATIVE_PEERS_ACTUAL_MEMORY words_per_bank=8192 rows=1024 sectors=4096 cycles=%0d peak=%0d price_qualification=OPEN",t,peak);
`else
  $display("PASS_PACKET_ACTUAL_MEMORY words_per_bank=8192 rows=1024 sectors=4096 cycles=%0d peak=%0d price_qualification=OPEN",t,peak);
`endif
`else
  $display("PASS_PACKET boundary sectors=4096 cycles=%0d peak=%0d production_memory_gate=OPEN",t,peak);
`endif
$finish;
 end
endmodule
