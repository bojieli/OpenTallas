`timescale 1ps/1ps
module tb_status_endpoint;
 reg clk=0;initial forever begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,load=0,commit=0,start=0,rdone=0;reg[280:0]entry;reg[216:0]jobs[0:1];
 wire jv,done,fault,busy,armed;wire[216:0]job;wire[7:0]wsc;wire[5:0]pk;wire pb;
 integer cc=0,se=0,nj=0,nd=0,done_edge=-1;reg active=0;reg mutate=0;
 ot_hnx_fused_job217_provider #(.DELIVERED_RESET(1)) dut(.clk(clk),.rst_n(rst_n),.load_v(load),.load_addr(8'd0),.load_entry(entry),.cfg_commit(commit),.cfg_calendar_bound(1'b1),.cfg_count(9'd1),.cfg_wsc(8'd24),.cfg_pk5(6'd0),.cfg_pb5(1'b0),.start(start),.job_v(jv),.job(job),.wsc(wsc),.pk5(pk),.pb5(pb),.root_done(rdone),.root_fault(1'b0),.root_busy(1'b0),.done(done),.fault(fault),.busy(busy),.armed(armed));
 always @(posedge clk)begin cc<=cc+1;if(start)se<=cc;end
 always @(negedge clk)if(active)begin
 if(jv)nj=nj+1;if(done)begin nd=nd+1;done_edge=cc-1-se;end
 #1;rdone=(cc-1-se==30);
 end
 task automatic tick;@(negedge clk);#2;endtask
 initial begin
 $readmemh("actual_post_jobs.mem",jobs);mutate=$test$plusargs("MUT_OLD_STATUS1");entry={32'(mutate?31:32),32'd10,jobs[0]};
 repeat(5)tick;rst_n=1;repeat(80)tick;load=1;tick;load=0;commit=1;tick;commit=0;repeat(2)tick;active=1;start=1;tick;start=0;repeat(45)tick;active=0;
 $display("STATUS_ENDPOINT_RESULT root_done_edge=30 pin_capture=31 earliest_check=32 done_edge=%0d jobs=%0d done=%0d fault=%0d MUT_OLD_STATUS1=%0d clock_ps=833",done_edge,nj,nd,fault,mutate);
 if(fault||nj!=1||nd!=1||done_edge!=32)$fatal(1,"STATUS_ENDPOINT FAIL");$display("STATUS_ENDPOINT PASS");$finish;
 end
endmodule
