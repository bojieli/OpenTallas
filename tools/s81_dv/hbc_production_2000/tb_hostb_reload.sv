`timescale 1ns/1ps
module tb_hostb_reload;
 reg ck=0,rn=0;always #0.5 ck=~ck;
 reg[1103:0]ring=0;reg[559:0]rec[0:2047];integer mode=0,nrec=0,idx=0,writes=0,activations=0;reg oldctx=0;
 wire[47:0]boot,epoch;wire ctx;wire[514:0]fh;wire[11:0]fault;wire[7:0]hbc_fault;
 wire[1103:0]ordinary,forwarded;wire[52:0]ks;wire[2:0]slot;wire[5:0]mask;wire arm;
 wire busy=mode==4&&boot>=799&&boot<=811;
 dsdv_hostb_stage_hbc #(.ENABLE(1),.LOCAL_STAGE(1),.LOCAL_RANK(0),.PHASE_BOUND(1),.VARIABLE_WORDS(1),.ALLOW_RELOAD(1),
 .CLOCK_RESET_ID(64'h5381C7C0DE1021),.BOOT_HEADER_EDGE(48'd20),.BOOT_COMMIT_EDGE(48'd30)) dut(
 .ck(ck),.rst_n(rn),.job_active(busy),.starter_armed(1'b0),.from_prev(ring),.local_ro(1104'd0),.return_ro(1104'd0),
 .status_t_host(77'd0),.status_t_kd(54'd0),.to_local(ordinary),.next_ro(forwarded),
 .f_host(fh),.ks_descriptor(ks),.ks_slot(slot),.fault(flt));
 // S81/PORTFIX-FLT 10-25: the unit's ports are one 1-bit sticky fault (flt); the former status ports are tapped
 wire flt;assign mask=dut.arm_mask;assign arm=dut.arm_commit;assign fault=dut.stage_fault;
 assign ctx=dut.context_valid;assign epoch=dut.receiver_edge;assign boot=dut.boot_edge;assign hbc_fault=dut.hbc_fault;
 always @(posedge ck)if(flt&&!(|fault)&&!(|hbc_fault)&&!(|dut.return_fault))$fatal(1,"FAIL 1-bit fault set with no unit fault");
 string vec;integer wi;reg[31:0]want;
 initial begin
  if(!$value$plusargs("MODE=%d",mode)||!$value$plusargs("VEC=%s",vec))$fatal(1,"MODE/VEC required");
  $readmemh({vec,"/r",$sformatf("%0d",mode),".memh"},rec);
  for(nrec=0;nrec<2048&&rec[nrec]!==560'bx;nrec++);
  repeat(3)@(posedge ck);rn=1;
 end
 always @(negedge ck)begin
  ring=0;if(rn&&idx<nrec&&boot==rec[idx][559:512])begin ring[0]=1;ring[3:1]=6;ring[532:21]=rec[idx][511:0];idx++;end
 end
 always @(posedge ck)if(rn)begin
  #0.01;if(ctx&&!oldctx)activations++;oldctx=ctx;
  if(fh[0])begin
   wi=writes<33?writes:writes-33;want=32'hf0000000|(writes<33?32'd0:32'h01000000)|32'(wi);
   if(fh[512:1]!=={16{want}})$fatal(1,"reload wrong payload/identity word%0d",writes);writes++;
  end
  if((mode==0&&boot==9500)||(mode!=0&&boot==1000))begin
   if(mode==0)begin
    if(writes!=548||activations!=2||fault||hbc_fault||flt||dut.g_hbc.tid!=38||dut.g_hbc.epoch_id!=32'h2021)$fatal(1,"reloadpositive writes%0d activations%0d fault%h/%h",writes,activations,fault,hbc_fault);
    $display("HBC_RELOAD PASS 33then515 HOSTwords; newTID/user/token/programme; explicit boot/receiver clocks separate");
   end else begin
    if(hbc_fault==0||!flt||writes!=33)$fatal(1,"reloadnegative not caught mode%0d writes%0d fault%h",mode,writes,hbc_fault);
    $display("HBC_RELOAD NEGATIVE CAUGHT mode%0d hbc_fault%h",mode,hbc_fault);
   end
   $finish;
  end
 end
 initial begin #20000;$fatal(1,"reloadtimeout mode%0d writes%0d hbc%h",mode,writes,hbc_fault);end
endmodule
