`timescale 1ns/1ps
// Bench: real static ingress -> ot_hbm_static_cfg_collar (SU/SFU variant A, IDX/TOPK/ARGMAX variant B,
// spare A for negatives) -> ot_hbm_status_join -> ingress block_ready/program_active/program_fault.
// Host stimulus = AXI-lite writes only; client busy/done are bench models of the engines' status pins.
// CMUT -> collar MUT, JMUT -> join MUT. Every mutant must produce FAIL.
module tb_hbm_static_cfg_collar;
parameter integer CMUT=0, JMUT=0;
parameter integer NA0=2100, NA1=5, NB0=10;
reg clk=0, sclk=0, rst_n=0; always #3 clk=~clk; always #4 sclk=~sclk;   // stream:serial = 4:3 frequency, common epoch
integer errors=0, checks=0; integer mon_err=0;
task chk(input c, input [8*64-1:0] what); begin checks=checks+1; if(!c) begin errors=errors+1; $display("FAIL %0s t=%0t", what, $time); end end endtask
// ---------------- ingress
reg s_awvalid=0,s_wvalid=0,s_bready=0,s_arvalid=0,s_rready=0; reg [11:0] s_awaddr=0,s_araddr=0; reg [31:0] s_wdata=0; reg [3:0] s_wstrb=4'hf;
wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid; wire [1:0] s_bresp; wire [31:0] s_rdata;
wire block_ready,program_active,program_fault,die_fault,irq;
wire cfg_v,desc_v,launch_v,ifault; wire [7:0] cfg_target; wire [11:0] cfg_addr,desc_base; wire [255:0] cfg_data; wire [12:0] desc_limit; wire [15:0] desc_loops;
localparam [255:0] MASK=(256'd1<<112)|(256'd1<<113)|(256'd1<<114)|(256'd1<<120);
ot_hbm_host_static_ingress #(.TARGET_MASK(MASK)) ing(.clk(clk),.rst_n(rst_n),
 .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
 .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.block_ready(block_ready),.program_active(program_active),.program_fault(program_fault),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
 .desc_loops(desc_loops),.launch_v(launch_v),.fault(ifault));
// ---------------- collars
wire [1:0] a_we; wire [22:0] a_addr; wire [255:0] a_data; wire [255:0] a_prm; wire a_start; wire [0:0] a_go; wire [220:0] a_rec; wire a_ready,a_active,a_fault;
reg [1:0] a_busy=0; reg a_done=0; reg a_cf=0;
ot_hbm_static_cfg_collar #(.PAGE_W(12),.NS(2),.NPR(1),.NREC(0),.NGO(1),.NB(2),.NF(1),.MUT(CMUT)) ca(.clk(clk),.rst_n(rst_n),.tgt(8'd112),.clk_in(clk),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),
 .c_busy(a_busy),.c_done(a_done),.c_fault(a_cf),.pw_we(a_we),.pw_addr(a_addr),.pw_data(a_data),.prm(a_prm),.start_v(a_start),
 .go(a_go),.rec(a_rec),.ready(a_ready),.active(a_active),.fault(a_fault));
wire [0:0] b_we; wire [11:0] b_addr; wire [255:0] b_data; wire [6*256-1:0] b_prm; wire b_start; wire [1:0] b_go; wire [220:0] b_rec; wire b_ready,b_active,b_fault;
reg [1:0] b_busy=0; reg b_done=0; reg [3:0] b_cf=0;
ot_hbm_static_cfg_collar #(.PAGE_W(1),.NS(1),.NPR(6),.NREC(8),.NGO(2),.NB(2),.NF(4),.MUT(CMUT)) cb(.clk(clk),.rst_n(rst_n),.tgt(8'd120),.clk_in(clk),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),
 .c_busy(b_busy),.c_done(b_done),.c_fault(b_cf),.pw_we(b_we),.pw_addr(b_addr),.pw_data(b_data),.prm(b_prm),.start_v(b_start),
 .go(b_go),.rec(b_rec),.ready(b_ready),.active(b_active),.fault(b_fault));
wire [1:0] c_we; wire [22:0] c_addr; wire [255:0] c_data,c_prm; wire c_start; wire [0:0] c_go; wire [220:0] c_rec; wire c_ready,c_active,c_fault;
ot_hbm_static_cfg_collar #(.PAGE_W(12),.NS(2),.NPR(1),.NREC(0),.NGO(1),.NB(2),.NF(1),.MUT(CMUT)) cc(.clk(clk),.rst_n(rst_n),.tgt(8'd114),.clk_in(clk),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),
 .c_busy(2'b00),.c_done(1'b0),.c_fault(1'b0),.pw_we(c_we),.pw_addr(c_addr),.pw_data(c_data),.prm(c_prm),.start_v(c_start),
 .go(c_go),.rec(c_rec),.ready(c_ready),.active(c_active),.fault(c_fault));
// D: SU-style collar in the serial (3:4) domain, broadcast pins in stream
wire [0:0] d_we; wire [22:0] d_addr; wire [255:0] d_data,d_prm; wire d_start; wire [0:0] d_go; wire [220:0] d_rec; wire d_ready,d_active,d_fault;
reg [1:0] d_busy=0; reg d_done=0;
ot_hbm_static_cfg_collar #(.PAGE_W(12),.NS(1),.NPR(1),.NREC(0),.NGO(1),.NB(2),.NF(1),.XSER(1),.MUT(CMUT)) cd_(.clk(sclk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd113),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),
 .c_busy(d_busy),.c_done(d_done),.c_fault(1'b0),.pw_we(d_we),.pw_addr(d_addr),.pw_data(d_data),.prm(d_prm),.start_v(d_start),
 .go(d_go),.rec(d_rec),.ready(d_ready),.active(d_active),.fault(d_fault));
integer d_seen=0, d_starts=0, dbusy=0;
always @(posedge sclk) begin
 if(d_we[0]) begin if(d_addr!=d_seen || d_data!=row_data(8'd113,d_seen)) mon_err=mon_err+1; d_seen=d_seen+1; end
 if(d_start) d_starts=d_starts+1;
 d_done<=0; if(d_start) dbusy<=10; else if(dbusy>0) begin dbusy<=dbusy-1; if(dbusy==1) d_done<=1; end
 d_busy<={1'b0,dbusy>0};
end
// E: serial collar driven directly with back-to-back broadcast events (faster than any ingress) -> must fault
reg e_cv=0; wire e_fault;
ot_hbm_static_cfg_collar #(.PAGE_W(12),.NS(1),.NPR(1),.NREC(0),.NGO(1),.NB(2),.NF(1),.XSER(1),.MUT(CMUT)) ce_(.clk(sclk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd99),
 .cfg_v(e_cv),.cfg_target(8'd99),.cfg_addr(12'h800),.cfg_data(256'd1),.desc_v(1'b0),.launch_v(1'b0),
 .c_busy(2'b00),.c_done(1'b0),.c_fault(1'b0),.pw_we(),.pw_addr(),.pw_data(),.prm(),.start_v(),
 .go(),.rec(),.ready(),.active(),.fault(e_fault));
ot_hbm_status_join #(.NT(4),.NF(4),.NH(1),.TGTS({8'd113,8'd114,8'd120,8'd112}),.MUT(JMUT)) sj(.clk(clk),.rst_n(rst_n),
 .cfg_v(cfg_v),.desc_v(desc_v),.launch_v(launch_v),.cfg_target(cfg_target),
 .t_ready({d_ready,c_ready,b_ready,a_ready}),.t_active({d_active,c_active,b_active,a_active}),.t_fault({d_fault,c_fault,b_fault,a_fault}),.h_fault(ifault),
 .block_ready(block_ready),.program_active(program_active),.program_fault(program_fault),.die_fault(die_fault),.irq(irq));
// ---------------- AXI host driver
reg [1:0] last_resp;
task axw(input [11:0] a, input [31:0] d); reg aw_done,w_done; begin
 @(negedge clk); s_awvalid=1; s_awaddr=a; s_wvalid=1; s_wdata=d; s_wstrb=4'hf; aw_done=0; w_done=0;
 while(!(aw_done&&w_done)) begin @(posedge clk); if(s_awvalid&&s_awready) aw_done=1; if(s_wvalid&&s_wready) w_done=1;
  @(negedge clk); if(aw_done) s_awvalid=0; if(w_done) s_wvalid=0; end
 s_bready=1; @(posedge clk); while(!s_bvalid) @(posedge clk); last_resp=s_bresp; @(negedge clk); s_bready=0;
end endtask
reg [31:0] last_rd;
task axr(input [11:0] a); begin
 @(negedge clk); s_arvalid=1; s_araddr=a; @(posedge clk); while(!s_arready) @(posedge clk); @(negedge clk); s_arvalid=0; s_rready=1;
 @(posedge clk); while(!s_rvalid) @(posedge clk); last_rd=s_rdata; @(negedge clk); s_rready=0;
end endtask
function [255:0] row_data(input [7:0] t, input [31:0] r); row_data={t,r,216'h5a5a_1234_5678_9abc_def0_0f0f_f0f0_3c3c_c3c3_a5a5_5a5a_0102_0304_0506 ^ {184'd0,r}}; endfunction
task frame(input [255:0] d); integer p; begin for(p=0;p<8;p=p+1) axw(12'hf24,d[p*32+:32]); end endtask
task sel(input [7:0] t, input [11:0] row); axw(12'hf20,{12'd0,row,t}); endtask
task desc(input [7:0] t); begin sel(t,12'd0); axw(12'hf28,{7'd0,13'd1,12'd0}); axw(12'hf2c,32'd1); end endtask
// ---------------- write monitors
integer a_seen0=0,a_seen1=0,b_seen=0;
always @(posedge clk) begin
 if(a_we[0]) begin if(a_addr!=a_seen0 || a_data!=row_data(8'd112,a_seen0)) mon_err=mon_err+1; a_seen0=a_seen0+1; end
 if(a_we[1]) begin if(a_addr!=a_seen1 || a_data!=row_data(8'd113,a_seen1)) mon_err=mon_err+1; a_seen1=a_seen1+1; end
 if(b_we[0]) begin if(b_addr!=b_seen || b_data!=row_data(8'd120,b_seen)) mon_err=mon_err+1; b_seen=b_seen+1; end
end
// go timing monitor
integer t_bstart=-1, ngo=0; integer go_t[0:7]; reg [1:0] go_m[0:7]; reg [220:0] go_p[0:7];
integer cyc=0; always @(posedge clk) cyc<=cyc+1;
always @(posedge clk) begin if(b_start) t_bstart=cyc; if(b_go!=0) begin go_t[ngo]=cyc-t_bstart; go_m[ngo]=b_go; go_p[ngo]=b_rec; ngo=ngo+1; end end
// guard property: block_ready never within 8 edges of a cfg/desc frame (stale target readiness)
integer since=100, guard_err=0;
always @(posedge clk) begin if(cfg_v||desc_v) since<=0; else if(since<100) since<=since+1; if(block_ready && since<8) guard_err=guard_err+1; end
// client models: busy for 12 edges after start, done pulse at the end
integer abusy=0,bbusy=0;
always @(posedge clk) begin
 a_done<=0; if(a_start) abusy<=12; else if(abusy>0) begin abusy<=abusy-1; if(abusy==1) a_done<=1; end
 a_busy<={1'b0,abusy>0};
 b_done<=0; if(b_go[1]) bbusy<=6; else if(bbusy>0) begin bbusy<=bbusy-1; end
 b_busy<={bbusy>0,1'b0};
end
integer i,p; reg [255:0] d;
initial begin
 repeat(5) @(posedge clk); rst_n=1; repeat(5) @(posedge clk);
 // ===== A: space 0 rows 0..NA0-1 (two pages), space 1 rows 0..NA1-1, operand row, need
 sel(8'd112,12'he00); frame(256'd0);                 // select space0 page0
 sel(8'd112,12'h000); for(i=0;i<NA0 && i<2048;i=i+1) frame(row_data(8'd112,i));
 if(NA0>2048) begin sel(8'd112,12'he00); frame({247'd0,1'b0,8'd0}|(256'd1<<8)); sel(8'd112,12'h000);
  for(i=2048;i<NA0;i=i+1) frame(row_data(8'd112,i)); end
 sel(8'd112,12'he00); frame(256'd1);                 // space1 page0
 sel(8'd112,12'h000); for(i=0;i<NA1;i=i+1) frame(row_data(8'd113,i));
 sel(8'd112,12'h800); frame(256'hfeed_0000_0000_1bc7);
 // need set to one more row than installed -> ready must stay low even when armed
 sel(8'd112,12'he01); frame((256'd1<<128)|(256'(NA1)<<32)|256'(NA0+1));
 desc(8'd112); repeat(20) @(posedge clk);
 chk(!a_ready,"A ready with an uninstalled row"); chk(!block_ready,"block_ready with an uninstalled row");
 sel(8'd112,12'he01); frame((256'd1<<128)|(256'(NA1)<<32)|256'(NA0));
 chk(!a_ready,"A ready without descriptor after reconfig");
 desc(8'd112); repeat(20) @(posedge clk);
 chk(a_seen0==NA0 && a_seen1==NA1 && mon_err==0,"A programme rows sequential/data exact");
 chk(a_prm[63:0]==64'hfeed_0000_0000_1bc7,"A operand row");
 chk(a_ready,"A ready after install+desc"); chk(block_ready,"join block_ready (A participates)");
 axr(12'hf30); chk(last_rd[1]==1,"ingress sees block_ready");
 axw(12'hf30,32'd1); chk(last_resp==0,"A launch accepted");
 repeat(6) @(posedge clk); chk(a_active && program_active,"A active after launch");
 repeat(40) @(posedge clk); chk(!a_active && !program_active,"A inactive after busy+done");
 chk(irq,"irq after programme complete");
 // ===== B: programme rows, operands, records; A must not participate (not armed)
 sel(8'd120,12'h000); for(i=0;i<NB0;i=i+1) frame(row_data(8'd120,i));
 sel(8'd120,12'h800); for(i=0;i<6;i=i+1) frame({8'(i),248'h77});
 sel(8'd120,12'hc00);
 frame({221'h1_0000_0000_aaaa,2'b01,1'b1,32'd5});
 frame({221'h2_0000_0000_bbbb,2'b10,1'b1,32'd9});
 frame({221'h3_0000_0000_cccc,2'b01,1'b1,32'd30});
 frame({221'd0,2'b00,1'b0,32'd0});
 sel(8'd120,12'he01); frame(256'(NB0));
 desc(8'd120); repeat(20) @(posedge clk);
 chk(b_ready && !a_ready && block_ready,"B ready, A not participating");
 axw(12'hf30,32'd1); chk(last_resp==0,"B launch accepted");
 repeat(60) @(posedge clk);
 chk(b_seen==NB0 && mon_err==0,"B programme rows");
 chk(b_prm[5*256+248+:8]==8'd5 && b_prm[248+:8]==8'd0,"B operand rows");
 chk(ngo==3,"three records issued");
 chk(go_t[0]==6 && go_t[1]==10 && go_t[2]==31,"record go at offset+1 edges after start_v");
 chk(go_m[0]==2'b01 && go_m[1]==2'b10 && go_m[2]==2'b01,"record go masks");
 chk(go_p[0][15:0]==16'haaaa && go_p[1][15:0]==16'hbbbb && go_p[2][15:0]==16'hcccc,"record payloads");
 chk(!b_active && !program_active && !program_fault,"B complete, no fault");
 // ===== D: serial-domain collar via the 3:4 crossing
 sel(8'd113,12'h000); for(i=0;i<300;i=i+1) frame(row_data(8'd113,i));
 sel(8'd113,12'h800); frame(256'd7116);
 sel(8'd113,12'he01); frame(256'd300);
 desc(8'd113); repeat(30) @(posedge clk);
 chk(d_seen==300 && mon_err==0 && !d_fault,"serial collar rows exactly once, in order");
 chk(d_ready && block_ready,"serial collar ready through join");
 axw(12'hf30,32'd1); chk(last_resp==0,"serial launch accepted");
 repeat(60) @(posedge clk);
 chk(d_starts==1 && !d_active && !program_active && irq,"serial start exactly once, completes");
 chk(d_prm[15:0]==16'd7116,"serial operand row (SU length)");
 // lost-event detection on the crossing
 @(negedge clk); e_cv=1; repeat(4) @(negedge clk); e_cv=0; repeat(10) @(posedge clk);
 chk(e_fault,"crossing faults on events closer than a serial edge");
 // ===== negatives (end: target faults are sticky)
 sel(8'd114,12'h000); frame(row_data(8'd114,0)); frame(row_data(8'd114,1));
 sel(8'd114,12'h005); frame(row_data(8'd114,5));     // skips rows 2..4
 repeat(10) @(posedge clk); chk(c_fault,"out-of-sequence row faults");
 chk(program_fault,"join program_fault from target");
 axw(12'hf30,32'd1); chk(last_resp==2,"launch refused after fault");
 chk(guard_err==0,"block_ready held low after configuration frames");
 if(errors==0) $display("PASS collar+join+ingress checks=%0d A0=%0d A1=%0d B=%0d go=%0d/%0d/%0d", checks,a_seen0,a_seen1,b_seen,go_t[0],go_t[1],go_t[2]);
 else $display("FAIL errors=%0d checks=%0d", errors, checks);
 $finish;
end
initial begin #4000000; $display("FAIL timeout"); $finish; end
endmodule
