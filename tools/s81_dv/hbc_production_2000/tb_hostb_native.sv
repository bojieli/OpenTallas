`timescale 1ns/1ps
module tb_hostb_native #(parameter integer STAGE=0);
 reg ck=0,rn=0;always #0.5 ck=~ck;
 reg[1103:0]ring=0;reg[559:0]rec[0:2047];reg[563:0]expected_host[0:1023];reg[55:0]meta[0:3];
 integer nrec=0,idx=0,writes=0,ks_seen=0;wire[47:0]boot,epoch;wire ctx;
 wire[514:0]fh,issued_host;wire[52:0]ks,issued_ks,egks;wire[2:0]slot,sfault;
 wire[11:0]fault;wire[7:0]hbc_fault;wire[1103:0]ordinary,forwarded;wire[5:0]mask;wire arm,armed;
 dsdv_hostb_stage_hbc #(.ENABLE(1),.LOCAL_STAGE(STAGE),.LOCAL_RANK(0),.PHASE_BOUND(1),.VARIABLE_WORDS(1),
 .CLOCK_RESET_ID(64'h1021),.BOOT_HEADER_EDGE(48'd20),.BOOT_COMMIT_EDGE(48'd30)) dut(
 .ck(ck),.rst_n(rn),.job_active(1'b0),.starter_armed(armed),.from_prev(ring),.local_ro(1104'd0),.return_ro(1104'd0),
 .status_t_host(77'd0),.status_t_kd(54'd0),.to_local(ordinary),.next_ro(forwarded),
 .f_host(fh),.ks_descriptor(ks),.ks_slot(slot),.fault(flt));
 // S81/PORTFIX-FLT 10-25: the unit's ports are one 1-bit sticky fault (flt); the former status ports are tapped
 wire flt;assign mask=dut.arm_mask;assign arm=dut.arm_commit;assign fault=dut.stage_fault;
 assign ctx=dut.context_valid;assign epoch=dut.receiver_edge;assign boot=dut.boot_edge;assign hbc_fault=dut.hbc_fault;
 always @(posedge ck)if(flt&&!(|fault)&&!(|hbc_fault)&&!(|dut.return_fault))$fatal(1,"FAIL 1-bit fault set with no unit fault");
 dsdv_hostb_source #(.HOSTB_ENABLE(1),.STATIC_KS6(0)) consumer(.ck(ck),.rst_n(rn),.select_hbe(1'b1),.upstream_fault(1'b0),
 .f_host(515'd0),.f_ks(53'd0),.hbe_f_host(fh),.starter_f_ks(ks),.hbe_ks_slot(slot),
 .issue_host(issued_host),.issue_ks(issued_ks),.engram_f_ks(egks),.hostb_fault(sfault),.hb_starter_armed(armed));
 string vec,case_name;integer dump;
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"VEC required");
  case_name=STAGE==0?"A":"B";
  $readmemh({vec,"/",case_name,".ring.memh"},rec);
  $readmemh({vec,"/",case_name,".host.memh"},expected_host);
  $readmemh({vec,"/",case_name,".meta.memh"},meta);
  for(nrec=0;nrec<2048&&rec[nrec]!==560'bx;nrec++);
  dump=$fopen({vec,"/",case_name,".consumer_dump.log"},"w");
  repeat(3)@(posedge ck);rn=1;
 end
 always @(negedge ck)begin
  ring=0;if(rn&&idx<nrec&&boot==rec[idx][559:512])begin ring[0]=1;ring[3:1]=6;ring[532:21]=rec[idx][511:0];idx++;end
 end
 // Active region observes the values sampled by the real downstream sequencer.
 always @(posedge ck)if(rn&&ctx)begin
  if(issued_host[0])begin
   if(writes>=meta[0]||issued_host!==expected_host[writes][514:0]||epoch!==expected_host[writes][562:515])
    $fatal(1,"native HOST mismatch stage%0d word%0d receiveredge%0d expected%0d",STAGE,writes,epoch,expected_host[writes][562:515]);
   $fdisplay(dump,"HOST %0d %0130h",epoch,issued_host);writes++;
  end
  if(issued_ks[52])begin
   if(issued_ks!==meta[2][52:0]||epoch!==meta[1][47:0]||issued_ks!==egks)$fatal(1,"native KS payload or capture edge mismatch");
   $fdisplay(dump,"KS %0d %014h",epoch,issued_ks);ks_seen++;
  end
  if(epoch==meta[3])begin
   if(writes!=meta[0]||ks_seen!=1||fault||hbc_fault||flt||sfault||armed)$fatal(1,"native stage%0d counts%0d/%0d fault%h/%h/%h",STAGE,writes,ks_seen,fault,hbc_fault,sfault);
   $display("HBC_NATIVE PASS stage%0d realHOST%0d realKS1 exact sourcepayload +4HOSTbody/+2KSheader",STAGE,writes);$fclose(dump);$finish;
  end
 end
 initial begin #100000;$fatal(1,"native receiver timeout stage%0d writes%0d fault%h",STAGE,writes,hbc_fault);end
endmodule
