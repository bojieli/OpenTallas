`timescale 1ns/1ps
`default_nettype none
module tb_vm_provider;
 reg clk=0,rst_n=0;always begin #0.416 clk=1;#0.417 clk=0;end
 // Fixturestrap106 exercises existing native target ports; not an additional
 // productiontarget allocation or overlap with the realSTOREtarget.
 reg[7:0]tgt=106,cfg_target=106;reg cfg_v=0,desc_v=0,launch_v=0;
 reg[11:0]cfg_addr=0,desc_base=0;reg[12:0]desc_limit=14;reg[15:0]desc_loops=1;reg[255:0]cfg_data=0;
 reg begin_v=0,begin_bank=0;reg[15:0]begin_epoch=0;reg[14:0]begin_row=20752;reg[3:0]begin_col=0;
 reg[15:0]fill_v=0,fill_bank=0;reg[95:0]fill_slot=0;reg[255:0]fill_epoch=0;reg[4095:0]fill_data=0;
 reg release_v_i=0,release_buffer_i=0;reg[15:0]release_epoch_i=0;
 wire configured,cp_active,busy_o,fault_o,load_done_o;wire[31:0]cycle;wire[280:0]vm_dq;wire[15:0]block_ready;wire[7:0]leaf_fault;
 ot_hbm_static_load_cp_provider_quad #(.SOURCE_QUAD(2))dut(.*);
 reg[226:0]descs[0:13];reg[31:0]steps[0:13];reg[280:0]expected[0:2687];
 integer cyc=0,sent=0,got=0,latency=-1,phase,b,g,s,w,di,wordno,mut_epoch=0,mut_deadline=0,mut_slot=0,mut_bank=0,mut_late=0;
 integer sent_cycle[0:2687];integer first_step=-1,last_step=-1,first_packet=-1,last_packet=-1,cmds=0;
 integer at_date,issue_date,drain_date,final_drain;
 integer vm_latency=-1,read_latency=-1,vm_acks=0,load_dones=0,read_sent=0,read_got=0,first_fault=-1,first_dq_capture=-1,first_bank_ack=-1;
 integer dq_sent[0:31],dq_got[0:31],dq_cycle[0:31][0:1023];
 integer read_cycle[0:2687];integer read_j,read_bank,k,resp;
 wire[8991:0]bank_dq;
 wire demux_fault;
 wire[31:0]native_done;
 // Actual native geography: SID0=SW(flat0..7),SID1=SE(flat8..15),
 // SID2=NW(flat16..23),SID3=NE(flat24..31). These are not NW-first qids.
 wire geo_SW_bank0_done=native_done[0];
 wire geo_SE_bank0_done=native_done[8];
 wire geo_NW_bank0_done=native_done[16];
 wire geo_NE_bank0_done=native_done[24];
 wire[17:0]vm_status[0:31];
 wire[31:0]vm_dq_done_i,vm_fault_i;
 reg[31:0]ack_delay[0:23];
 reg[16:0]rq0_bank[0:31];wire[256:0]rr0_bank[0:31];
 ot_hbm_static_load_vm_dq_demux demux(.packet_i(vm_dq),.bank_dq_o(bank_dq),.fault_o(demux_fault));
 assign vm_dq_done_i=mut_late!=0?ack_delay[23]:native_done;
 for(genvar bankidx=0;bankidx<32;bankidx=bankidx+1)begin:VM
  wire[280:0]incoming=bank_dq[bankidx*281+:281]^((mut_bank!=0&&bank_dq[bankidx*281+280])?(281'd1<<264):281'd0);
  assign vm_fault_i[bankidx]=vm_status[bankidx][17]|vm_status[bankidx][16];
  hfd_vms_bank_native_q0_faces bank(
   .rq0(rq0_bank[bankidx]),.rr0(rr0_bank[bankidx]),.rq1(17'd0),.rr1(),.rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
   .wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.bid(3'(bankidx%8)),.sid(2'(bankidx/8)),
   .clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),
   .rslot_v(rq0_bank[bankidx][16]),.rslot(3'd0),.wslot_v(bank_dq[bankidx*281+280]),.wslot(mut_slot!=0?3'd5:3'd6),
   .dq(incoming),.dq_done(native_done[bankidx]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(vm_status[bankidx]));
 end
 always @(posedge clk)begin
  if(!rst_n)begin for(integer delayidx=0;delayidx<24;delayidx=delayidx+1)ack_delay[delayidx]<=0;end
  else begin ack_delay[0]<=native_done;for(integer delayidx=1;delayidx<24;delayidx=delayidx+1)ack_delay[delayidx]<=ack_delay[delayidx-1];end
 end
 reg[307:0]command;reg[339:0]entry;reg[15:0]epoch;reg ebank;
 function automatic[31:0]payload(input integer ph,l,grp,slotno,wordidx);
 payload=32'h3e800000+32'(ph)*32'h01000000+32'(l)*32'h10000+32'(grp)*32'h1000+32'(slotno)*8+32'(wordidx);
 endfunction
 task tick;begin @(negedge clk);end endtask
 task write_word(input[11:0]address,input[255:0]data);
 begin cfg_addr=address;cfg_data=data;cfg_v=1;tick();cfg_v=0;tick();end endtask
 always @(posedge clk)begin
 cyc=cyc+1;
 if(rst_n)for(integer nb=0;nb<32;nb=nb+1)if(bank_dq[nb*281+280])begin
  if(first_dq_capture<0)first_dq_capture=cyc;
  dq_cycle[nb][dq_sent[nb]]=cyc;dq_sent[nb]=dq_sent[nb]+1;
 end
 if(rst_n&&dut.dated_step)begin
 if(first_step<0)first_step=cyc;last_step=cyc;sent_cycle[sent]=cyc;sent=sent+1;
 end
 if(rst_n&&dut.admit)begin cmds=cmds+1;
 $display("CP_CMD index=%0d edge=%0d nativecycle=%0d issue_at=%0d drain_at=%0d n=%0d",cmds,cyc,cycle,dut.cmd[31:0],dut.cmd[63:32],dut.move[226:206]);end
 #0.1;
 if(rst_n)begin
 if(fault_o||(|leaf_fault)||demux_fault)begin
  if(mut_slot==0&&mut_bank==0&&mut_late==0)$fatal(1,"VM_PROVIDER_UNEXPECTED_FAULT edge=%0d phase=%0d nativecycle=%0d fault=%b vm_fault=%h leaf=%h",cyc,phase,cycle,fault_o,vm_fault_i,leaf_fault);
  if(first_fault<0)first_fault=cyc;
  if(cyc>=first_fault+8)$fatal(1,"VM_PROVIDER_FAULT first=%0d edge=%0d slot=%0d bank=%0d late=%0d actual_native_acks=%0d load_done=%0d vm_fault=%h",first_fault,cyc,mut_slot,mut_bank,mut_late,vm_acks,load_dones,vm_fault_i);
 end
 if(load_done_o)begin
  if(mut_slot!=0||mut_bank!=0||mut_late!=0)$fatal(1,"VM_MUTANT_COMPLETED");
  load_dones=load_dones+1;
  $display("VM_LOAD_DONE index=%0d edge=%0d cycle_post=%0d drain_at=%0d",load_dones,cyc,cycle,dut.drain_at);
 end
 for(integer nb=0;nb<32;nb=nb+1)if(native_done[nb])begin
  if(first_bank_ack<0)first_bank_ack=cyc;
  if(dq_got[nb]>=dq_sent[nb])$fatal(1,"VM_UNSOLICITED_NATIVE_ACK bank=%0d",nb);
  if(vm_latency<0)vm_latency=cyc-dq_cycle[nb][dq_got[nb]];
  if(cyc-dq_cycle[nb][dq_got[nb]]!=vm_latency)$fatal(1,"VM_ACK_DATE bank=%0d actual=%0d expected=%0d",nb,cyc-dq_cycle[nb][dq_got[nb]],vm_latency);
  dq_got[nb]=dq_got[nb]+1;vm_acks=vm_acks+1;
 end
 resp=0;
 for(integer nb=0;nb<32;nb=nb+1)if(rr0_bank[nb][256])begin
  resp=resp+1;
  if(nb!=integer'({expected[read_got][278:277],expected[read_got][266:264]}))$fatal(1,"VM_READBACK_GEOGRAPHY actualflat=%0d expectedSID=%0d expectedbank=%0d",nb,expected[read_got][278:277],expected[read_got][266:264]);
  if(read_got>=read_sent||rr0_bank[nb][255:0]!==expected[read_got][263:8])$fatal(1,"VM_READBACK_DATA bank=%0d got=%0d sent=%0d actual=%h expected=%h",nb,read_got,read_sent,rr0_bank[nb],expected[read_got][263:8]);
  if(read_latency<0)read_latency=cyc-read_cycle[read_got];
  if(cyc-read_cycle[read_got]!=read_latency)$fatal(1,"VM_READBACK_DATE");
  read_got=read_got+1;
 end
 if(resp>1)$fatal(1,"VM_READBACK_COLLISION");
 if(vm_dq[280])begin
 if(got>=sent||vm_dq!==expected[got])$fatal(1,"CP_PROVIDER_DATA got=%0d sent=%0d actual=%h expected=%h",got,sent,vm_dq,expected[got]);
 if(latency<0)latency=cyc-sent_cycle[got];
 if(cyc-sent_cycle[got]!=latency)$fatal(1,"CP_PROVIDER_DATE actual=%0d expect=%0d",cyc-sent_cycle[got],latency);
 if(first_packet<0)first_packet=cyc;last_packet=cyc;got=got+1;
 end end end
 initial begin
 for(k=0;k<32;k=k+1)begin rq0_bank[k]=0;dq_sent[k]=0;dq_got[k]=0;end
 $readmemh("fixture_desc.mem",descs);$readmemh("fixture_steps.mem",steps);$readmemh("fixture_expected.mem",expected);
 if($value$plusargs("MUT_SLOT=%d",mut_slot))begin end
 if($value$plusargs("MUT_BANK=%d",mut_bank))begin end
 if($value$plusargs("MUT_LATE=%d",mut_late))begin end
 if($value$plusargs("MUT_EPOCH=%d",mut_epoch))begin end
 if($value$plusargs("MUT_DEADLINE=%d",mut_deadline))begin end
 repeat(32)tick();rst_n=1;repeat(16)tick();
 for(phase=0;phase<3;phase=phase+1)begin
 epoch=16'(7+phase);ebank=phase==2;
 begin_epoch=epoch;begin_bank=ebank;begin_v=1;tick();begin_v=0;repeat(16)tick();
 for(s=0;s<64;s=s+1)begin
 fill_v=16'hffff;
 for(b=0;b<8;b=b+1)for(g=0;g<2;g=g+1)begin
 fill_bank[b*2+g]=ebank;fill_slot[(b*2+g)*6+:6]=6'(s);fill_epoch[(b*2+g)*16+:16]=epoch;
 for(w=0;w<8;w=w+1)fill_data[(b*2+g)*256+w*32+:32]=payload(phase,b,g,s,w);
 end tick();end
 fill_v=0;repeat(16)tick();
 for(b=0;b<8;b=b+1)if(!block_ready[b*2+integer'(ebank)])$fatal(1,"CP_PROVIDER_FILL_READY");
 at_date=32;
 for(di=0;di<14;di=di+1)begin
 issue_date=at_date+8;drain_date=issue_date+integer'(steps[di])+20;
 if(mut_deadline!=0&&phase==0&&di==0)drain_date=issue_date+integer'(steps[di])-1;
 command=0;command[31:0]=32'(issue_date);command[63:32]=32'(drain_date);command[290:64]=descs[di];command[291]=ebank;command[307:292]=epoch;
 if(mut_epoch!=0&&phase==0&&di==0)command[307:292]=epoch+1;
 entry={command,32'(at_date)};
 write_word(12'h800+12'(di*2),entry[255:0]);write_word(12'h801+12'(di*2),{172'd0,entry[339:256]});
 at_date=drain_date+8;
 end
 final_drain=drain_date;
 repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(16)tick();
 if(!configured)$fatal(1,"CP_PROVIDER_CONFIGURED");
 launch_v=1;tick();launch_v=0;
 repeat(final_drain+64)tick();
 if(got!=sent||got!=(phase+1)*896||busy_o||cp_active)$fatal(1,"CP_PROVIDER_DRAIN got=%0d sent=%0d busy=%b cpactive=%b",got,sent,busy_o,cp_active);
 if(load_dones!=(phase+1)*14||vm_acks!=got)$fatal(1,"VM_COMPLETION_CONSERVATION done=%0d acks=%0d packets=%0d",load_dones,vm_acks,got);
 // Read actual native SRAM through ordinary rq0/rr0 after real bankdone and
 // clean status. Requests use real calendar rslot0; no memory-model peeks.
 for(read_j=phase*896;read_j<(phase+1)*896;read_j=read_j+1)begin
  for(k=0;k<32;k=k+1)rq0_bank[k]=0;
  // The header SID chooses geographicSW0/SE1/NW2/NE3, then localbank.
  read_bank=integer'({expected[read_j][278:277],expected[read_j][266:264]});
  rq0_bank[read_bank]={1'b1,expected[read_j][279:264]};read_cycle[read_sent]=cyc+1;read_sent=read_sent+1;tick();
 end
 for(k=0;k<32;k=k+1)rq0_bank[k]=0;
 repeat(16)tick();
 if(read_got!=read_sent)$fatal(1,"VM_READBACK_DRAIN got=%0d sent=%0d",read_got,read_sent);
 release_buffer_i=ebank;release_epoch_i=epoch;release_v_i=1;tick();release_v_i=0;repeat(24)tick();
 end
 if(mut_epoch!=0||mut_deadline!=0)$fatal(1,"CP_PROVIDER_MUTANT_ESCAPED");
 $display("PASS NATIVE_VM_CP_PROVIDER exact833ps descriptors=%0d packets=%0d words=%0d epochs=3 latency=%0d first_step=%0d last_step=%0d first_packet=%0d last_packet=%0d native_dq_done=%0d load_done=%0d SRAMreadback=%0d dqcap_to_ack=%0d read_latency=%0d first_dq_capture=%0d first_native_ack=%0d",cmds,got,got*8,latency,first_step,last_step,first_packet,last_packet,vm_acks,load_dones,read_got,vm_latency,read_latency,first_dq_capture,first_bank_ack);$finish;
 end
endmodule
`default_nettype wire
