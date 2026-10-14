`timescale 1ps/1fs
module tb_hbm_b2_peer_lease #(parameter integer MUT=0);
 reg vclk=0;always #555.5555 vclk=~vclk;
 reg [2:0] cclk=0;for(genvar s=0;s<3;s=s+1)initial begin #(61+s*17);forever #416.666625 cclk[s]=~cclk[s];end
 reg rst_n=0;reg [2:0] req=0,sd=7,vd=7;wire [2:0] cg,ack,vg;wire fault;integer checks=0;
 ot_hbm_b2_peer_lease #(.MUT(MUT)) dut(.cclk(cclk),.vclk(vclk),.rst_n(rst_n),.src_req(req),.src_drained(sd),.vm_drained(vd),.src_grant(cg),.src_drain_ack(ack),.vm_grant(vg),.fault(fault));
 task automatic tick(input integer n);repeat(n)@(negedge vclk);endtask
 task automatic expected(input[2:0] g);begin tick(12);if(vg!==g||cg!==g)$fatal(1,"lease owner mismatch VM%h client%h expected%h",vg,cg,g);checks++;end endtask
 initial begin tick(6);rst_n=1;tick(8);req=3'b101;expected(1);
  vd[0]=0;req[0]=0;tick(20);if(vg!==1)$fatal(1,"released before actual VM drain");checks++;
  vd[0]=1;expected(4);if(!ack[0])$fatal(1,"missing held drain acknowledgment");checks++;
  sd[2]=0;req[2]=0;req[1]=1;tick(20);if(vg!==4)$fatal(1,"released before source queues/tickets drain");checks++;
  sd[2]=1;expected(2);req[0]=1;tick(20);if(vg!==2)$fatal(1,"preempted held owner");checks++;
  req[1]=0;expected(1);req[0]=0;expected(0);if(ack!==7)$fatal(1,"missing final drain acknowledgments");checks++;
  if(fault)$fatal(1,"protected ownership rail fault");$display("NATIVE_PEER_LEASE PASS checks=%0d source_classes=3 engine_edges=4 VM_edges=3",checks);$finish;
 end
 always @(posedge vclk)if(rst_n)begin if($countones(vg)>1||$countones(cg)>1)$fatal(1,"nonexclusive producer grants");checks++;end
 initial begin #2000000;$fatal(1,"ownership timeout");end
endmodule
