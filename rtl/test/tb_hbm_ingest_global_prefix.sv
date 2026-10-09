`timescale 1ns/1ps
module tb_hbm_ingest_global_prefix;
 parameter integer MUT_SUM_ACK=0;
 reg ck=0;always #0.416667 ck=~ck;
 reg rst_n=0,iv=0;reg[1:0]istack=0;wire ir,pending,fault;reg[23:0]a=0;wire[5:0]ack;
 integer accepted=0,retired=0,i,cycles=0;reg slow_done=0;
 ot_hbm_ingest_global_prefix #(.ENABLE(1),.DEPTH(1024),.MUT_SUM_ACK(MUT_SUM_ACK)) dut(
 .ck(ck),.rst_n(rst_n),.issue_v(iv),.issue_stack(istack),.issue_rdy(ir),
 .stack_ack_n(a),.ack_n(ack),.pending(pending),.fault(fault));
 always @(posedge ck)begin
 cycles=cycles+1;if(fault)$fatal(1,"GLOBALPREFIX fault");
 if(iv&&ir)accepted=accepted+1;
 if(ack)begin if(!slow_done)$fatal(1,"GLOBALPREFIX EARLY_FENCE laterstack falsely retires earlierstack0");
 retired=retired+ack;if(retired>accepted)$fatal(1,"GLOBALPREFIX retire exceeds accepted");end
 end
 initial begin
 repeat(3)@(negedge ck);rst_n=1;
 for(i=0;i<1024;i=i+1)begin @(negedge ck);iv=1;istack=i%4;
 @(posedge ck);if(!ir)$fatal(1,"GLOBALPREFIX acceptance capacity");end
 @(negedge ck);iv=0;if(ir)$fatal(1,"GLOBALPREFIX full admission not blocked");
 for(i=0;i<256;i=i+1)begin @(negedge ck);a={6'd1,6'd1,6'd1,6'd0};end
 @(negedge ck);a=0;repeat(5)@(negedge ck);
 if(retired!=0||!pending)$fatal(1,"GLOBALPREFIX earlier fence released");
 slow_done=1;
 for(i=0;i<256;i=i+1)begin @(negedge ck);a=24'd1;end
 @(negedge ck);a=0;wait(retired==1024);repeat(2)@(negedge ck);
 if(pending||!ir)$fatal(1,"GLOBALPREFIX drain");
 for(i=0;i<512;i=i+1)begin @(negedge ck);iv=1;istack=(i+1)%4;a=24'd1<<(6*((i+1)%4));end
 @(negedge ck);iv=0;a=0;wait(retired==1536);repeat(3)@(negedge ck);
 if(pending)$fatal(1,"GLOBALPREFIX wrap drain");
 $display("GLOBALPREFIX PASS1536actualacceptedordinals full1024depth crossstack reorder/wrap, cycles%0d",cycles);$finish;
 end
endmodule
