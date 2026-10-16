`timescale 1ns/1ps
module tb_mtp_hrow_hub_local;
 reg ck=0,rst=1;always #5 ck=~ck;
 reg[20:0]ev=0;reg[24:0]vrq=0;reg[10:0]clr=0;
 wire ready0,ready1;wire[1024:0]res0,res1;wire[2:0]flt0,flt1;wire[14:0]rc0[0:2],rc1[0:2];wire[6:0]ack0,ack1;
 dsfd_mtp_hrow_hub old(.ck(ck),.rst(rst),.f_vrq(vrq),.t_vrq(ready0),.t_vrs(res0),.f_clr(clr),.t_flt(flt0),.f_ev0(ev),.f_ev1(ev),.f_ev2(ev),.f_if0(2'b0),.f_if1(2'b0),.f_if2(2'b0),.t_rc0(rc0[0]),.t_rc1(rc0[1]),.t_rc2(rc0[2]),.f_pr0(1025'b0),.f_pr1(1025'b0),.f_pr2(1025'b0),.rst_ack(ack0));
 dsfd_mtp_hrow_hub #(.LOCAL_GROUP_SLOTS(8)) dut(.ck(ck),.rst(rst),.f_vrq(vrq),.t_vrq(ready1),.t_vrs(res1),.f_clr(clr),.t_flt(flt1),.f_ev0(ev),.f_ev1(ev),.f_ev2(ev),.f_if0(2'b0),.f_if1(2'b0),.f_if2(2'b0),.t_rc0(rc1[0]),.t_rc1(rc1[1]),.t_rc2(rc1[2]),.f_pr0(1025'b0),.f_pr1(1025'b0),.f_pr2(1025'b0),.rst_ack(ack1));
 reg gc1=0,run1=0;always #5 if(run1)gc1=~gc1;else gc1=0;
 wire gr0,gr1,ga;
 dsfd_mtp_hrow_group_rst c0(.ck(ck),.rst(rst),.rn(gr0));
 dsfd_mtp_hrow_group_rst c1(.ck(gc1),.rst(rst),.rn(gr1));
`ifdef OT_HROW_LOCAL_MUT_RST_WITNESS
 dsfd_mtp_reset_ack wa(.clk(ck),.request_n(rst),.local_release(gr0),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(ga));
`else
 dsfd_mtp_reset_ack #(.N(2)) wa(.clk(ck),.request_n(rst),.local_release({gr1,gr0}),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(ga));
`endif
 integer cycles=0,issues=0,j;reg check_outputs=0;reg[31:0]trace=0;
 always @(negedge ck)begin
 cycles=cycles+1;if(cycles>3000)$fatal(1,"protocol watchdog");
 if(check_outputs)begin
 if({ready0,flt0,res0[0],ack0} !== {ready1,flt1,res1[0],ack1})begin $display("LOCAL_BAD boundary control cycle%0d",cycles);$fatal(1);end
 for(integer k=0;k<3;k=k+1)begin
 if(rc0[k][0]!==rc1[k][0] || (rc0[k][0] && rc0[k]!==rc1[k]))begin $display("LOCAL_BAD request phase k%0d cycle%0d old%h local%h",k,cycles,rc0[k],rc1[k]);$fatal(1);end
 if(rc1[k][0])begin issues=issues+1;trace=trace*33+rc1[k];end
 end
 end
 end
 task event_row(input integer pos,input integer epoch,input bit first);
 begin @(posedge ck);#1;ev=(first?21'h100000:0)|21'h80000|(pos%16<<12)|(pos<<4)|epoch;@(posedge ck);#1;ev=0;repeat(3)@(posedge ck);end endtask
 task request(input integer pos,input integer epoch,input integer beat);
 begin @(posedge ck);#1;if(!ready0||!ready1)$fatal(1,"protocol grant unavailable");vrq=((((epoch<<19)|(pos<<8)|beat)<<1)|1);@(posedge ck);#1;vrq=0;end endtask
 initial begin
 #1;rst=0;#20;rst=1;repeat(12)@(posedge ck);#1;if(ga)begin $display("LOCAL_BAD stopped regional conditioner acknowledged");$fatal(1);end
 run1=1;repeat(5)@(posedge ck);#1;if(!ga)$fatal(1,"genuine regional reset did not release");check_outputs=1;
 for(j=0;j<8;j=j+1)begin event_row(j,2,1);event_row(j,2,0);end
 for(j=0;j<24;j=j+1)begin request(j%8,2,(j%3)*80+(j%7));repeat(24)@(posedge ck);end
 if(issues!=24)begin $display("LOCAL_BAD expected24 reads got%0d",issues);$fatal(1);end
 // Request a genuinely stale epoch: tag matching must stall until new row events.
 request(3,3,0);repeat(40)@(posedge ck);if(issues!=24)begin $display("LOCAL_BAD stale epoch read");$fatal(1);end
 event_row(3,3,1);event_row(3,3,0);repeat(40)@(posedge ck);
 if(issues!=25)begin $display("LOCAL_BAD reverified epoch read missing count%0d",issues);$fatal(1);end
 @(posedge ck);#1;rst=0;check_outputs=0;#1;if(|ack1)$fatal(1,"raw epoch failed clear");repeat(3)@(posedge ck);#1;rst=1;repeat(12)@(posedge ck);#1;if(!(&ack1))$fatal(1,"second epoch ACK");
 $display("PASS local keys/reset protocol issues%0d trace%h",issues,trace);$finish;
 end
endmodule
