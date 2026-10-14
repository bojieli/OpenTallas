`timescale 1ps/1fs
// Worst case zero-extra-edge VM commit: ACK is asserted directly from VM WWQ
// output. Real VM protected commit can only return later. CDC source64fced1f9.
module tb_hgi_qdq_snapshot_ack_deadline;
 reg cclk=0,vclk=0,rst_n=0;integer phase=61;
 always #416.6665 cclk=~cclk;
 initial begin if($value$plusargs("PHASE=%d",phase))begin end #(phase);forever #555.5555 vclk=~vclk;end
 reg [280:0] cwq=0;wire done,credit,fault;wire [280:0] vwq;wire [16:0] vrq;wire [256:0] crr;wire rc;
 ot_hbm_b2_lane_cdc u(.cclk(cclk),.vclk(vclk),.rst_n(rst_n),.permit(1'b1),.crq(17'd0),.crq_credit(rc),.crr(crr),
 .cwq(cwq),.cwq_credit(credit),.cwq_done(done),.vrq(vrq),.vrq_credit(1'b0),.vrr(257'd0),
 .vwq(vwq),.vwq_credit(vwq[280]),.vwq_done(vwq[280]),.fault(fault));
 integer edge_no=0,launch_edge=0,acks=0,min_edges=1000;real launch_time,dt;
 always @(posedge cclk)begin
  edge_no=edge_no+1;
  #0.001;
  if(rst_n&&fault)$fatal(1,"CDC fault");
  if(rst_n&&done)begin
   acks=acks+1;dt=$realtime-launch_time;
   if(edge_no-launch_edge<min_edges)min_edges=edge_no-launch_edge;
   if(dt<2*833.333)$fatal(1,"ACK before FIN snapshot admission dt%f",dt);
  end
 end
 initial begin
  repeat(10)@(negedge cclk);rst_n=1;repeat(10)@(negedge cclk);
  for(integer k=0;k<64;k=k+1)begin
   @(posedge cclk);#0.002;cwq={1'b1,15'd5,256'(k),8'hff};launch_time=$realtime;launch_edge=edge_no;
   @(posedge cclk);#0.002;cwq=0;
   wait(done);@(negedge cclk);repeat(4)@(negedge cclk);
  end
  repeat(10)@(negedge cclk);
  if(acks!=64)$fatal(1,"ACK count%0d",acks);
  $display("PASS SNAPSHOT_ACK_DEADLINE phase=%0d records=%0d min_engine_edges=%0d admission_edge=2 vm_commit_extra_edges=0",phase,acks,min_edges);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
