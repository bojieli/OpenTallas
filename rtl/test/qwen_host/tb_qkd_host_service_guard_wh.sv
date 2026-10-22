// KV-RETIRE 10-19: warm-reset history bench for qkd_host_service_guard_wh (the guard itself unchanged).
//  1 raised health, then a warm host reset (producers clear too): the plain guard reopens; the wrapper keeps abort,
//    TK88, status.bad and !service_ready until recovery_certified, then reopens after SETTLE.
//  2 no health but a POR-retained context live at the warm reset: vetoed; a recovery while the context is still
//    retained does not clear; after the context is released, recovery clears.
//  3 clean warm reset with nothing retained: no veto (no false health).  4 POR clears the veto.
//  5 the veto is live from the first warm-reset edge (abort high while host_rst_n is low).
// WH_MUT 1 / 2 / 3 must fail (fail regexes WARM_CERTIFIED_CLEAN / RETAINED_CERTIFIED_CLEAN / RECOVERY_WITH_RETAINED).
module tb_qkd_host_service_guard_wh;
 timeunit 1ns;timeprecision 1ps;
 parameter WH_MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst=0,por=0,ret=0,rec=0;reg[24:0]raw=0;
 wire[92:0]gt,pgt;wire abort,ready,pabort,pready,wl;wire[15:0]epoch;wire[25:0]diag;wire[31:0]status,pstatus;wire[3:0]groups;wire[7:0]pout,tout;
 qkd_host_service_guard_wh #(.WH_MUT(WH_MUT)) dut(.ck_guard(ck),.rst_n(rst),.por_n(por),.raw_faults(raw),.retained_ctx(ret),
  .recovery_certified(rec),.die_id(3'd7),.physical_faults(8'd0),.transport_faults(8'd0),.accepted_ing_v(1'b0),
  .accepted_ing_cls(2'd0),.accepted_ing_header(16'd0),.done_v(1'b0),.done_d(64'd0),.boot_barrier_v(1'b0),
  .boot_barrier_target(32'd0),.begin_v(1'b0),.begin_epoch(16'd0),.pending_advertised(1'b0),.pending_epoch(16'd0),
  .local_tk(93'h0),.guarded_tk(gt),.abort(abort),.service_ready(ready),.service_epoch(epoch),.diag_raw(diag),
  .status(status),.groups(groups),.physical_diag(pout),.transport_diag(tout),.service_protocol_fault(1'b0),.warm_lost(wl));
 // the unchanged guard on the same stimulus (shows the hole)
 qkd_host_service_guard plain(ck,rst,raw,3'd7,8'd0,8'd0,1'b0,2'd0,16'd0,1'b0,64'd0,1'b0,32'd0,1'b0,16'd0,1'b0,16'd0,93'h0,
  pgt,pabort,pready,,,pstatus,,,,1'b0);
 integer checks=0;
 task edges(input integer n);repeat(n)begin @(posedge ck);#0.01;end endtask
 task check(input reg ok,input string why);begin checks=checks+1;if(!ok)$fatal(1,"%s abort=%b ready=%b tk88=%b status=%h wl=%b",why,abort,ready,gt[88],status,wl);end endtask
 task warm;begin @(negedge ck);rst=0;raw=0;edges(1);check(abort||WH_MUT==1||(!ret&&!wl&&!abort),"WARM_VETO_NOT_LIVE_IN_RESET");edges(3);@(negedge ck);rst=1;edges(20);end endtask
 task recover;begin @(negedge ck);rec=1;@(negedge ck);rec=0;edges(12);end endtask
 initial begin
  edges(3);@(negedge ck);por=1;edges(2);@(negedge ck);rst=1;edges(15);check(ready&&!abort&&!wl,"clean start");
  // 1
  @(negedge ck);raw[3]=1;edges(6);check(abort&&!ready&&gt[88],"raised health");
  warm();check(pready&&!pabort,"plain guard reopens after warm reset (the hole)");
  check(abort&&!ready&&gt[88]&&status[2]&&!status[1],"WARM_CERTIFIED_CLEAN after raised health");
  edges(200);check(abort&&!ready,"WARM_CERTIFIED_CLEAN veto must persist");
  recover();check(ready&&!abort&&!gt[88]&&!wl,"recovery reopens");
  // 2
  @(negedge ck);ret=1;edges(4);check(ready&&!abort,"retained context live while healthy");
  warm();check(abort&&!ready,"RETAINED_CERTIFIED_CLEAN after warm reset with live context");
  recover();check(abort&&!ready,"RECOVERY_WITH_RETAINED cleared the veto");
  @(negedge ck);ret=0;recover();check(ready&&!abort&&!wl,"recovery after release reopens");
  // 3
  warm();check(ready&&!abort&&!wl,"false veto on clean warm reset");
  // 4
  @(negedge ck);raw[20]=1;edges(6);warm();check(abort,"WARM_CERTIFIED_CLEAN second");
  @(negedge ck);por=0;rst=0;edges(3);@(negedge ck);por=1;edges(2);@(negedge ck);rst=1;edges(15);check(ready&&!abort&&!wl,"POR clears");
  $display("GUARD_WH_PASS checks=%0d",checks);$finish;
 end
endmodule
