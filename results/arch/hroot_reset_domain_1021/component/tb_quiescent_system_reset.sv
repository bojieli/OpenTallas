`timescale 1ps/1fs
module tb;
reg [0:0] ck_core=0;
reg [0:0] ck_host=0;
reg [0:0] ck_ingest=0;
reg [0:0] host_rst_n=0;
wire [0:0] service_faults;
reg [511:0] u_rank__qm_d=0;
reg [1:0] u_rank__qm_cls=0;
reg [0:0] u_rank__qm_v=0;
wire [4:0] u_rank__qm_crn;
wire [0:0] u_rank__ov;
wire [0:0] u_rank__owe;
wire [31:0] u_rank__oa;
wire [255:0] u_rank__od;
reg [0:0] u_rank__ocr=0;
reg [0:0] u_rank__qm_t_cr=0;
wire [63:0] u_rank__qm_t_d;
wire [0:0] u_rank__qm_t_v;
wire [0:0] host_upstream_quiet_core;
wire [0:0] host_upstream_quiet_host;
wire [0:0] host_upstream_quiet_ingest;
wire [1:0] eng_rst_n;
wire [0:0] eng_dv;
wire [255:0] eng_ddata;
wire [0:0] eng_inv_a;
wire [0:0] eng_inv_b;
wire [511:0] eng_indata;
wire [0:0] eng_wrdy;
reg [0:0] eng_drdy=0;
reg [0:0] eng_inrdy=0;
reg [0:0] eng_wv=0;
reg [19:0] eng_wv_c=0;
reg [31:0] eng_waddr=0;
reg [255:0] eng_wdata=0;
reg [0:0] eng_rv=0;
reg [31:0] eng_raddr=0;
reg [0:0] eng_done=0;
reg [0:0] eng_done_a=0;
reg [0:0] eng_done_b=0;
reg [0:0] eng_done_c=0;
reg [7:0] eng_tag=0;
reg [0:0] eng_busy=0;
reg [31:0] eng_nsec=0;
qkd_hr_ingest_shell dut(.ck_core(ck_core),.ck_host(ck_host),.ck_ingest(ck_ingest),.host_rst_n(host_rst_n),.service_faults(service_faults),.u_rank__qm_d(u_rank__qm_d),.u_rank__qm_cls(u_rank__qm_cls),.u_rank__qm_v(u_rank__qm_v),.u_rank__qm_crn(u_rank__qm_crn),.u_rank__ov(u_rank__ov),.u_rank__owe(u_rank__owe),.u_rank__oa(u_rank__oa),.u_rank__od(u_rank__od),.u_rank__ocr(u_rank__ocr),.u_rank__qm_t_cr(u_rank__qm_t_cr),.u_rank__qm_t_d(u_rank__qm_t_d),.u_rank__qm_t_v(u_rank__qm_t_v),.host_upstream_quiet_core(host_upstream_quiet_core),.host_upstream_quiet_host(host_upstream_quiet_host),.host_upstream_quiet_ingest(host_upstream_quiet_ingest),.eng_rst_n(eng_rst_n),.eng_dv(eng_dv),.eng_ddata(eng_ddata),.eng_inv_a(eng_inv_a),.eng_inv_b(eng_inv_b),.eng_indata(eng_indata),.eng_wrdy(eng_wrdy),.eng_drdy(eng_drdy),.eng_inrdy(eng_inrdy),.eng_wv(eng_wv),.eng_wv_c(eng_wv_c),.eng_waddr(eng_waddr),.eng_wdata(eng_wdata),.eng_rv(eng_rv),.eng_raddr(eng_raddr),.eng_done(eng_done),.eng_done_a(eng_done_a),.eng_done_b(eng_done_b),.eng_done_c(eng_done_c),.eng_tag(eng_tag),.eng_busy(eng_busy),.eng_nsec(eng_nsec));
`define Q dut.u_ot_pr_core.u_rank__u_qm
integer mode=0,writes=0,completions=0,c_old=0;
reg armed=0;
always #416.6665 ck_core=~ck_core;
initial begin #127.111;forever #500 ck_host=~ck_host;end
initial begin #311.777;forever #833.3335 ck_ingest=~ck_ingest;end
always @(posedge ck_core)begin #0.01;if(armed && u_rank__ov)begin
 if(!u_rank__owe || u_rank__oa!==((writes==0)?32'h1234:32'h5678) || u_rank__od!==256'd55)$fatal(1,"write payload writes=%0d addr=%h",writes,u_rank__oa);
 writes=writes+1;
end end
always @(posedge ck_host)begin #0.01;if(armed && u_rank__qm_t_v)begin
 if(u_rank__qm_t_d!==64'h01005a0000000001)$fatal(1,"completion payload=%h",u_rank__qm_t_d);
 completions=completions+1;
end end
task check_release;begin
 fork
 begin:hc integer j;for(j=1;j<=4;j=j+1)begin @(posedge ck_host);#0.01;if(`Q.rn_h!==(j==4))$fatal(1,"hostreleaseedge%0d rn=%b",j,`Q.rn_h);end end
 begin:ic integer j;for(j=1;j<=4;j=j+1)begin @(posedge ck_ingest);#0.01;if(`Q.rn_i!==(j==4))$fatal(1,"ingestreleasedge%0d rn=%b",j,`Q.rn_i);end end
 begin:cc integer j;for(j=1;j<=4;j=j+1)begin @(posedge ck_core);#0.01;if(`Q.rn_c!==(j==4))$fatal(1,"corereleaseedge%0d rn=%b",j,`Q.rn_c);end end
 join
end endtask
task reset_idle;begin
 armed=0;u_rank__ocr=0;u_rank__qm_t_cr=0;eng_wv=0;eng_wv_c=0;eng_done=0;eng_done_a=0;eng_done_b=0;eng_done_c=0;u_rank__qm_v=0;
 host_rst_n=0;#0.01;
 if({`Q.rn_h,`Q.rn_i,`Q.rn_c}!==3'b000)$fatal(1,"not asyncasserted");
 // Only an edge STRICTLY AFTER asynchronous-clear settling qualifies.
 @(posedge ck_core);#0.01;
 if(u_rank__ov!==0 || service_faults!==0)$fatal(1,"heldedge didnotclearpins");
 @(negedge ck_core);host_rst_n=1;
 check_release;
 wait(host_upstream_quiet_core && host_upstream_quiet_host && host_upstream_quiet_ingest);#0.01;
 if(`Q.ocr!==8 || `Q.tcr!==4)$fatal(1,"resetcredits");
 armed=1;
end endtask
task write_and_complete(input[31:0] addr);begin
 @(negedge ck_ingest);wait(eng_wrdy);eng_waddr=addr;eng_wdata=55;eng_wv=1;eng_wv_c='1;
 eng_done=1;eng_done_a=1;eng_done_b=1;eng_done_c=1;eng_tag=8'h5a;eng_nsec=1;
 @(negedge ck_ingest);eng_wv=0;eng_wv_c=0;eng_done=0;eng_done_a=0;eng_done_b=0;eng_done_c=0;
end endtask
initial begin
 if($value$plusargs("MODE=%d",mode))begin end
 host_rst_n=1;#1;reset_idle;
 if(mode==1)begin
 @(negedge ck_core);u_rank__ocr=1;@(negedge ck_core);u_rank__ocr=0;repeat(4)@(posedge ck_core);#0.01;
 if(`Q.ocr!==9)$fatal(1,"lateOCR witnessmissing ocr=%0d",`Q.ocr);
 $fatal(1,"EXPECTED_CONTRACT_VIOLATION lateOLDcredit OCR8to9");
 end
 if(mode==2)begin
 @(negedge ck_host);u_rank__qm_t_cr=1;@(negedge ck_host);u_rank__qm_t_cr=0;repeat(3)@(posedge ck_host);#0.01;
 if(`Q.tcr!==5)$fatal(1,"lateTCRED witnessmissing tcr=%0d",`Q.tcr);
 $fatal(1,"EXPECTED_CONTRACT_VIOLATION lateOLDcredit TCRED4to5");
 end
 write_and_complete(32'h1234);
 if(mode==3)begin
 wait(`Q.o_v);#0.01;
 // Reset assertion in NBA at the same edge: pin FF captures old internal o_v.
 armed=0;@(posedge ck_core);host_rst_n<=0;#0.01;
 $display("COINCIDENT_ASSERT internal=%b pin=%b",`Q.o_v,u_rank__ov);
 if(`Q.o_v!==0 || u_rank__ov!==1)$fatal(1,"coincident stale-pin witness missing");
 $fatal(1,"EXPECTED_CONTRACT_VIOLATION assertionedge not guaranteed cleared pin");
 end
 wait(u_rank__ov);#0.01;
 c_old=completions;
 // Peer deliberately flushes the old request/completion and all old returns;
 // no credit from this pre-reset transaction is returned after rearm.
 #1;reset_idle;
 write_and_complete(32'h5678);
 wait(writes==2);wait(completions==c_old+1);
 @(negedge ck_core);u_rank__ocr=1;@(negedge ck_core);u_rank__ocr=0;
 @(negedge ck_host);u_rank__qm_t_cr=1;@(negedge ck_host);u_rank__qm_t_cr=0;
 wait(host_upstream_quiet_core && host_upstream_quiet_host && host_upstream_quiet_ingest);#0.01;
 if(service_faults!==0 || `Q.ocr!==8 || `Q.tcr!==4)$fatal(1,"postflush rearmfailed");
 $display("QUIESCENT_SYSTEM_RESET_COMPONENT_PASS writes=%0d completions=%0d release4local no globalphase",writes,completions);$finish;
end
initial begin repeat(2000) @(posedge ck_core);$fatal(1,"COMPONENT_FIXTURE_EVENT_LIMIT noquiescence within2000coreedges");end
endmodule
