`timescale 1ps/1fs
`default_nettype none
// Scoped main-bank proof. Explicit held group1 grant does not allocate an SFU
// source in shared arbitration. SRAM pin models retain actual masked words;
// real B2 ECC, queues, arbitration, protected CDC, credits and ACKs are active.
module tb_hgi_sfu_bank_native;
 parameter integer PHASE=61;
 reg clk=0,vclk=0;always #416.6665 clk=~clk;initial begin #(PHASE);forever #555.5555 vclk=~vclk;end
 reg rst_n=0,bo=0,fence=0,quiet=1,rd_v=0,wr_v=0;reg [15:0] sec=0,tag=0;reg [255:0] data=0;
 wire owner,rready,wready,idle,fault,rv,cv;wire [16:0] rq,vrq;wire [280:0] wq,vwq;
 wire rc,wc,done,vrc,vwc,vdone,cf;wire [256:0] rr,vrr;
 wire [15:0] rs,rt,cs,ct;wire [255:0] result;wire [1:0] brc,bwc,bdone;wire [513:0] brr;wire [17:0] status;
 integer n,checks=0,words=0;reg seen;
 ot_hgi_sfu_bank_lifetime client(.clk(clk),.rst_n(rst_n),.begin_owner(bo),.fence(fence),.grant(1'b1),.path_quiet(quiet),.bank_id(3'd0),.slice_id(2'd2),.owner_req(owner),.rd_ready(rready),.wr_ready(wready),.idle(idle),.fault(fault),.rd_v(rd_v),.rd_sec(sec),.rd_tag(tag),.wr_v(wr_v),.wr_sec(sec),.wr_tag(tag),.wr_data(data),.wr_mask(8'hff),.rq(rq),.wq(wq),.rq_credit(rc),.wq_credit(wc),.wq_done(done),.rr(rr),.result_v(rv),.result_sec(rs),.result_tag(rt),.result_data(result),.commit_v(cv),.commit_sec(cs),.commit_tag(ct));
 ot_hbm_b2_lane_cdc cdc(.cclk(clk),.vclk(vclk),.rst_n(rst_n),.permit(owner),.crq(rq),.crq_credit(rc),.crr(rr),.cwq(wq),.cwq_credit(wc),.cwq_done(done),.vrq(vrq),.vrq_credit(vrc),.vrr(vrr),.vwq(vwq),.vwq_credit(vwc),.vwq_done(vdone),.fault(cf));
 assign vrc=brc[1];assign vwc=bwc[1];assign vdone=bdone[1];assign vrr=brr[257+:257];
 ot_vms_bank bank(.clk(vclk),.rst_n(rst_n),.bid(3'd0),.sid(2'd2),.rq({vrq,17'd0}),.rq_cr(brc),.rr(brr),.wq({vwq,281'd0}),.wq_cr(bwc),.wq_done(bdone),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_cr(),.kq_done(),.xq(276'd0),.xq_cr(),.xq_done(),.xq2(276'd0),.xq2_cr(),.xq2_done(),.eg(),.eg_cr(2'd0),.pq(285'd0),.pq_cr(),.pr(),.status(status));
 task tick;begin @(posedge clk);#1;checks++;if(rst_n&&(fault||cf||status!=0))$fatal(1,"NATIVE_FAULT client=%b cdc=%b bank=%h",fault,cf,status);end endtask
 task lease;begin @(negedge clk);bo=1;tick();@(negedge clk);bo=0;repeat(5)tick();end endtask
 task reset;begin @(negedge clk);rst_n=0;repeat(8)tick();@(negedge clk);rst_n=1;repeat(8)tick();lease();end endtask
 initial begin
  reset();
  for(n=0;n<67;n++)begin
   while(!wready)tick();@(negedge clk);sec=16'h4000+8*n;tag=n;data={8{32'(32'h3f000000+n)}};wr_v=1;tick();@(negedge clk);wr_v=0;
   seen=0;while(!seen)begin tick();if(cv)begin seen=1;if(ct!=n||cs!=sec)$fatal(1,"COMMIT_ID");end end
   while(!rready)tick();@(negedge clk);rd_v=1;tick();@(negedge clk);rd_v=0;
   seen=0;while(!seen)begin tick();if(rv)begin seen=1;if(rt!=n||rs!=sec||result!=data)$fatal(1,"NATIVE_WORD n=%0d",n);words+=8;end end
   if(n==32)begin repeat(20)tick();reset();end
  end
  @(negedge clk);quiet=0;fence=1;tick();@(negedge clk);fence=0;repeat(12)begin tick();if(!owner)$fatal(1,"PATH_DRAIN");end
  @(negedge clk);quiet=1;repeat(12)tick();if(owner||!idle)$fatal(1,"NOT_IDLE");
  $display("PASS SFU native bank PHASE=%0d checks=%0d writes=67 reads=67 exact_words=%0d engine833.333_VM1111.111 warm_reset=1 scoped_held_group1_grant=1",PHASE,checks,words);$finish;
 end
 initial begin #10000000;$fatal(1,"TIMEOUT");end
endmodule
`default_nettype wire
