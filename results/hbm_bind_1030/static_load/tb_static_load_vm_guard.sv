`timescale 1ns/1ps
module tb_static_load_vm_guard;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,start=0,deadline=0,releasev=0,beginv=0;reg[20:0]n=8;reg[280:0]packet=0;reg[31:0]acks=0,statusbad=0;
 wire active,done,fault,rs,bs;integer testno;
 ot_hbm_static_load_vm_commit_guard u(clk,rst,start,n,1'b0,packet,acks,statusbad,deadline,releasev,1'b0,beginv,1'b0,active,done,fault,rs,bs);
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task prepare;begin
 rst=0;start=0;deadline=0;releasev=0;beginv=0;packet=0;acks=0;statusbad=0;tick();tick();rst=1;start=1;tick();start=0;
 packet=0;packet[280]=1;packet[278:277]=2;packet[266:264]=3;packet[7:0]=8'hff;tick();packet=0;
 end endtask
 initial begin
 // Unit-audit test only: ack inputs are stimuli, not a substitute native VM proof.
 for(testno=0;testno<5;testno=testno+1)begin
 prepare();repeat(4)tick();
 if(testno==1)acks=32'b1<<18;
 else if(testno!=3)acks=32'b1<<19;
 if(testno==2)statusbad=32'b1<<19;
 if(testno==4)begin releasev=1;if(rs)$fatal(1,"EARLY_RELEASE_ACCEPTED");end
 tick();acks=0;releasev=0;tick();deadline=1;tick();deadline=0;
 if(testno==0)begin if(!done||fault)$fatal(1,"GOOD_NATIVE_ACK_REJECTED");end
 else if(done||!fault)$fatal(1,"BAD_NATIVE_ACK_ESCAPED test=%0d",testno);
 end
 $display("PASS VM_COMMIT_GUARD native_ack/sticky_status_gate/deadline/wrong_bank/early_release unit_controls=5 (nativeVMfixture separate)");$finish;
 end
endmodule
