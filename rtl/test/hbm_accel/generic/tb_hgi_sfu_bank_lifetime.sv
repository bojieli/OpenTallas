`timescale 1ps/1fs
`default_nettype none
module tb_hgi_sfu_bank_lifetime;
 parameter integer MUT=0;
 reg clk=0;always #416.6665 clk=~clk;
 reg rst_n=0,begin_owner=0,fence=0,grant=1,path_quiet=1,rd_v=0,wr_v=0,rc=0,wc=0,done=0;
 reg [15:0] rd_sec=0,rd_tag=0,wr_sec=0,wr_tag=0;reg [255:0] data=0;reg [256:0] rr=0;
 wire owner,ready_r,ready_w,idle,fault,rv,cv;wire [16:0] rq;wire [280:0] wq;
 wire [15:0] rs,rt,cs,ct;wire [255:0] rdata;
 integer n,checks=0,commits=0,returns=0;
 ot_hgi_sfu_bank_lifetime #(.MUT_EARLY_RELEASE(MUT)) dut(.clk(clk),.rst_n(rst_n),.begin_owner(begin_owner),.fence(fence),.grant(grant),.path_quiet(path_quiet),.bank_id(3'd0),.slice_id(2'd2),.owner_req(owner),.rd_ready(ready_r),.wr_ready(ready_w),.idle(idle),.fault(fault),.rd_v(rd_v),.rd_sec(rd_sec),.rd_tag(rd_tag),.wr_v(wr_v),.wr_sec(wr_sec),.wr_tag(wr_tag),.wr_data(data),.wr_mask(8'hff),.rq(rq),.wq(wq),.rq_credit(rc),.wq_credit(wc),.wq_done(done),.rr(rr),.result_v(rv),.result_sec(rs),.result_tag(rt),.result_data(rdata),.commit_v(cv),.commit_sec(cs),.commit_tag(ct));
 task tick;begin @(posedge clk);#1;checks=checks+1;end endtask
 task lease;begin @(negedge clk);begin_owner=1;tick();@(negedge clk);begin_owner=0;repeat(4)tick();if(!owner||!ready_r||!ready_w)$fatal(1,"LEASE");end endtask
 task reset;begin @(negedge clk);rst_n=0;repeat(3)tick();@(negedge clk);rst_n=1;repeat(4)tick();end endtask
 initial begin
  reset();lease();
  // More than six wraps of the actual ten-entry identity queues.
  for(n=0;n<67;n=n+1)begin
   @(negedge clk);rd_v=1;wr_v=1;rd_sec=16'h4000+8*n;wr_sec=16'h4000+8*n;rd_tag=n;wr_tag=n;data={8{32'(n)}};
   tick();if(!rq[16]||!wq[280])$fatal(1,"ACCEPT %0d",n);
   @(negedge clk);rd_v=0;wr_v=0;rc=1;wc=1;tick();
   @(negedge clk);rc=0;wc=0;rr={1'b1,{8{32'(n)}}};done=1;tick();
   @(negedge clk);rr=0;done=0;tick();
   if(!rv||!cv||rt!=n||ct!=n||rs!=16'h4000+8*n||cs!=16'h4000+8*n||rdata!={8{32'(n)}})$fatal(1,"IDENTITY %0d",n);
   returns++;commits++;repeat(2)tick();
  end
  // Queue credit is returned while committed ACK and real path drain lag.
  @(negedge clk);wr_v=1;wr_tag=16'hface;wr_sec=16'h4800;path_quiet=0;tick();
  @(negedge clk);wr_v=0;wc=1;fence=1;tick();
  @(negedge clk);wc=0;fence=0;
  repeat(12)begin tick();if(!owner)$fatal(1,"EARLY_OWNER_RELEASE before committed ACK");end
  @(negedge clk);done=1;tick();@(negedge clk);done=0;tick();if(!cv||ct!=16'hface)$fatal(1,"LAST_COMMIT");
  repeat(8)begin tick();if(!owner)$fatal(1,"EARLY_OWNER_RELEASE before external path drain");end
  @(negedge clk);path_quiet=1;repeat(8)tick();if(owner||!idle||fault)$fatal(1,"FINAL_DRAIN");
  lease();@(negedge clk);rd_v=1;rd_sec=16'h4001;tick();if(rq[16])$fatal(1,"BAD_BANK_SENT");@(negedge clk);rd_v=0;repeat(8)tick();if(!fault)$fatal(1,"BAD_BANK_NOT_FAULTED");
  reset();lease();@(negedge clk);fence=1;tick();@(negedge clk);fence=0;repeat(8)tick();if(owner||!idle||fault)$fatal(1,"WARM_RESET");
  $display("PASS SFU bank lifetime checks=%0d returns=%0d commits=%0d LQ10 wraps=6 earlycredit_delayedACK_externaldrain=1 warm_reset=1 invalid_bank=1",checks,returns,commits+1);$finish;
 end
 initial begin #2000000;$fatal(1,"TIMEOUT");end
endmodule
`default_nettype wire
