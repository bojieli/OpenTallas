`timescale 1ps/1fs
module tb_sram_cdc;
 parameter integer W=280,AW=4,PHASE=61,REVERSE=0,MUT=0,MODE=0;
 localparam integer D=1<<AW,TOTAL=192;
 reg wclk=0,rclk=0,wrst_n=0,rrst_n=0,we=0,re=0;
 reg [W-1:0] wdata=0;reg [31:0] wepoch=1,repoch=1;
 wire full,empty,w_fault,r_fault;wire [W-1:0] rdata;wire[2:0] rd_freed;
 ot_hbm_native_sram_cdc #(.W(W),.AW(AW),.MUT(MUT)) dut(.*);
 initial forever #(REVERSE?555.5555:416.666625) wclk=~wclk;
 initial begin #(PHASE);forever #(REVERSE?416.666625:555.5555) rclk=~rclk;end
 integer sent=0,received=0,wcycles=0,rcycles=0,first_accept=-1,first_read=-1,first_publish=-1,first_visible=-1;
 integer full_stalls=0,empty_stalls=0,freed_total=0,held_checks=0,issues=0,landings=0,ce_checks=0;
 integer phase_round=0;reg inj_done=0,credit_pause=0;reg held_valid=0;reg [W-1:0] held_data;
 realtime accepted_at,visible_at;
 function automatic [W-1:0] payload(input integer n,input integer ep);
  reg [W-1:0] d;integer i;
  begin for(i=0;i<W;i=i+1)d[i]=((n*37+i*11+ep*29)>>(i%11))&1;
   for(i=0;i<W&&i<16;i=i+1)d[i]=(n>>i)&1;payload=d;end
 endfunction
 initial begin
  repeat(5)@(negedge wclk);wrst_n=1;rrst_n=1;
  if(MODE==4)begin
   wait(sent>=8);@(negedge wclk);wepoch=3;@(posedge wclk);#1;
   if(!w_fault||!full)$fatal(1,"EARLY_EPOCH discarded pending payload");
   $display("SRAM_CDC_BOUNDARY PASS early epoch refuses pending obligations");$finish;
  end
  if(MODE==5)begin
   wait(!empty);@(negedge rclk);dut.out_data[0]=~dut.out_data[0];#1;
   if(!r_fault||!empty)$fatal(1,"HELD_OUTPUT_PAYLOAD corruption escaped");
   $display("SRAM_CDC_BOUNDARY PASS protected held output payload");$finish;
  end
  wait(received==TOTAL);
  repeat(8)@(negedge wclk);
  if(freed_total!=TOTAL)$fatal(1,"CREDIT_TOTAL got=%0d expected=%0d",freed_total,TOTAL);
  // Matched new epoch after a drained transaction set; source changes first.
  wepoch=2;repeat(7)@(negedge wclk);
  if(!full)$fatal(1,"EPOCH_DISAGREEMENT accepted old destination epoch");
  repoch=2;repeat(7)@(negedge rclk);
  if(w_fault||r_fault)$fatal(1,"unexpected epoch fault");
  phase_round=1;sent=0;received=0;freed_total=0;inj_done=0;
  wait(received==TOTAL);repeat(8)@(negedge wclk);
  if(freed_total!=TOTAL)$fatal(1,"second epoch credit total");
  if(MODE==1&&ce_checks!=2)$fatal(1,"single error correction was not observed twice: %0d",ce_checks);
  if(MODE==3)begin
   @(negedge wclk);dut.fetch_n[0]=~dut.fetch_n[0];#1;
   if(!w_fault||!full)$fatal(1,"SOURCE_CONTROL_RAIL not fail closed");
   $display("SRAM_CDC_BOUNDARY PASS source control rail fail closed");
  end
  $display("SRAM_CDC PASS W=%0d AW=%0d phase=%0d reverse=%0d mode=%0d words=%0d full_stalls=%0d empty_stalls=%0d held=%0d issues=%0d landings=%0d first_accept=%0d first_sram_read=%0d first_publish=%0d first_visible_r=%0d first_access_ps=%0.3f ce_checks=%0d",W,AW,PHASE,REVERSE,MODE,2*TOTAL,full_stalls,empty_stalls,held_checks,issues,landings,first_accept,first_read,first_publish,first_visible,visible_at-accepted_at,ce_checks);
  $finish;
 end
 always @(negedge wclk)begin
  if(wrst_n)begin
   we=(sent<TOTAL)&&(wepoch==repoch)&&!full;wdata=payload(sent,wepoch);
   if((MODE==1||MODE==2)&&!inj_done&&dut.issue&&dut.fetch_seq==1)begin
    // Mutate the actual catalog SRAM array after its synchronous write and
    // before its source-clock read. Repairs are tied off, mux=1, bit column=bit.
    dut.u_sram.arr[1][2]=~dut.u_sram.arr[1][2];
    if(MODE==2)dut.u_sram.arr[1][4]=~dut.u_sram.arr[1][4];
    inj_done=1;
   end
  end
 end
 always @(posedge wclk)if(wrst_n)begin
  wcycles=wcycles+1;
  if(we&&!full)begin
   if(first_accept<0)begin first_accept=wcycles;accepted_at=$realtime;end
   sent=sent+1;
   if(sent-received>D)$fatal(1,"LOGICAL_CAPACITY accepted=%0d consumed=%0d D=%0d",sent,received,D);
  end
  if(full&&sent<TOTAL)full_stalls=full_stalls+1;
  if(dut.issue)begin issues=issues+1;if(first_read<0)first_read=wcycles;end
  if(dut.read_v&&dut.source_safe)begin landings=landings+1;if(first_publish<0)first_publish=wcycles;end
  freed_total=freed_total+rd_freed;
  if(freed_total>received)$fatal(1,"PREMATURE_SOURCE_CREDIT %0d > %0d",freed_total,received);
  if(w_fault)$fatal(1,"unexpected source fault before boundary injection");
 end
 // Long initial and recurring stalls fill all eight source-held slots.
 always @(negedge rclk)begin
  if(rrst_n)begin
   re=(rcycles>45)&&((rcycles%41)<24);

  end
 end
 always @(posedge rclk)if(rrst_n)begin
  rcycles=rcycles+1;
  if(dut.rx_v&&(|dut.decode_ce))ce_checks=ce_checks+1;
  if(!empty)begin
   if(first_visible<0)begin first_visible=rcycles;visible_at=$realtime;end
   if(rdata!==payload(received,repoch))$fatal(1,"PAYLOAD_MISMATCH W=%0d got=%h want=%h seq=%0d",W,rdata,payload(received,repoch),received);
   if(held_valid&&rdata!==held_data)$fatal(1,"HELD_SLOT_CHANGED");
   held_checks=held_checks+1;held_data=rdata;held_valid=!re;
   if(re)received=received+1;
  end else begin empty_stalls=empty_stalls+1;held_valid=0;end
  if(r_fault)begin
   if(MODE==2)begin
    if(!empty)$fatal(1,"UE_POISON leaked valid output");
    $display("SRAM_CDC_BOUNDARY PASS uncorrectable payload poisoned W=%0d accepted=%0d received=%0d",W,sent,received);$finish;
   end
   $fatal(1,"unexpected consumer fault W=%0d seq=%0d",W,received);
  end
 end
 initial begin #3000000;$fatal(1,"WATCHDOG sent=%0d received=%0d wf=%0d rf=%0d full=%0d empty=%0d fetch=%0d pub=%0d wb=%0d commit=%0d rb=%0d",sent,received,w_fault,r_fault,full,empty,dut.fetch_seq,dut.publish_seq,dut.wb,dut.commit_seq,dut.rb);end
endmodule
