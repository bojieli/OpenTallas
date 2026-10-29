`timescale 1ns/1ps
module tb_publish;
parameter MUT=0;
reg clk=0;always #5 clk=~clk;reg rst_n=0,cv=0,active=0,finish=0;reg[11:0]addr=0;reg[255:0]data=0;
reg[31:0]legacy=0;wire consume,collision,fault,pending;wire[281:0]pub;wire[4:0]dest;
wire[281:0]wq=(dest==0)?pub:282'd0;reg[17:0]rq=0;wire[256:0]rr;wire done;wire[17:0]status;
wire rv=1'b1,wv=1'b1;wire[2:0]rs=0,ws=1;
ot_vms_f20_boot_publish_r2048 #(.MUT(MUT)) publisher(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_target(8'h78),.cfg_addr(addr),.cfg_data(data),.index_active(active),.finish(finish),.legacy_write_valid(legacy),.consume_cfg(consume),.native_wq(pub),.destination(dest),.collision(collision),.fault(fault),.pending(pending));
hfd_vms_bank_native_q0_faces_r2048_oneclk #() newer(.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),.rslot_v(rv),.rslot(rs),.wslot_v(wv),.wslot(ws),.rq0(rq),.rr0(rr),.rq1(18'd0),.rr1(),.rq2(18'd0),.rr2(),.rq3(18'd0),.rr3(),.rq4(18'd0),.rr4(),.wq0(282'd0),.wq_done0(),.wq1(wq),.wq_done1(done),.dq(282'd0),.dq_done(),.kq(282'd0),.kq_done(),.xq(277'd0),.xq_done(),.xq2(277'd0),.xq2_done(),.eg(),.pq(286'd0),.pr(),.status(status));

task tick;begin @(posedge clk);#1;end endtask
task reset;begin @(negedge clk);rst_n=0;cv=0;legacy=0;active=0;finish=0;rq=0;repeat(6)tick();@(negedge clk);rst_n=1;repeat(14)tick();end endtask
task frame(input[11:0]a,input[255:0]d);begin @(negedge clk);addr=a;data=d;cv=1;tick();@(negedge clk);cv=0;tick();end endtask
task header(input[18:0]a,input[16:0]count);begin frame(12'hF00,{212'd0,8'hff,count,a});repeat(2)tick();end endtask
task payload(input[255:0]d);begin frame(12'hF01,d);if(!pub[281])$fatal(1,"publisher launch date");repeat(8)tick();if(status!=0)$fatal(1,"bank status");end endtask
task readback(input[16:0]sec,input[255:0]d);begin @(negedge clk);rq={1'b1,sec};tick();@(negedge clk);rq=0;repeat(7)tick();if(!rr[256]||rr[255:0]!==d)$fatal(1,"real SRAM publication readback sec%h got%h",sec,rr);repeat(4)tick();end endtask
initial begin
 reset();header(19'd0,1);payload(256'h11223344);header(19'd262144,1);payload(256'h55667788);
 readback(17'h00000,256'h11223344);readback(17'h08000,256'h55667788);
 reset();header(19'd262144,1);legacy=1;frame(12'hF01,256'habcd);if(!collision||pub[281])$fatal(1,"oldwriter collision failedopen");repeat(3)tick();if(!fault)$fatal(1,"collision diag missing");
 reset();header(19'd524280,2);repeat(3)tick();if(!fault)$fatal(1,"capacity overflow accepted");
 reset();header(19'd1,1);repeat(3)tick();if(!fault)$fatal(1,"unaligned wordaddr accepted");
 reset();active=1;header(19'd262144,1);repeat(3)tick();if(!fault||pub[281])$fatal(1,"runtime boot write accepted");
 reset();header(19'd262144,1);frame(12'hF01,256'h42);finish=1;tick();finish=0;if(!fault)$fatal(1,"finish before commit fence accepted");
 reset();header(19'd524280,17'd131071);repeat(3)tick();if(!fault)$fatal(1,"wide sum overflow accepted");
 reset();frame(12'hF01,256'h1);repeat(3)tick();if(!fault)$fatal(1,"unconfigured payload accepted");
 $display("VM_F20_PUBLISH PASS actual19bitwordaddr low/highrealSRAMreadback collision bounds active unconfigured");$finish;
end
endmodule
