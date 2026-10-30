`timescale 1ns/1ps
`default_nettype none
module tb_static_load_eightleaf;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg begin_v=0,begin_bank=0;reg[15:0]begin_epoch=0;
 reg[15:0]fill_v=0,fill_bank=0;reg[95:0]fill_slot=0;reg[255:0]fill_epoch=0;reg[4095:0]fill_data=0;
 reg[7:0]load_v=0;reg[495:0]load_cmd=0;
 wire[15:0]block_ready;wire[7:0]leaf_fault;wire[280:0]vm_dq;wire route_fault;
 ot_hbm_static_load_quad_vehicle dut(.*);
 reg[31:0]fp8_truth[0:255],i8_truth[0:255],ue8_truth[0:255];
 reg[280:0]expected[0:255];integer sent_cycle[0:255];
 integer cyc=0,sent=0,got=0,latency=-1,word_checks=0,mut_release=0;
 integer phase,b,g,s,w,f,fmt,count,sub,offset,dq,db,slotid,groupid;
 reg[15:0]epoch,sector_id;reg ebank;reg[61:0]cmd;reg[255:0]sec;reg[31:0]raw,val;
 reg[280:0]packet;
 function automatic[31:0] payload_word(input integer p,l,grp,slotno,wordno);
  payload_word=32'h3e800000+32'(p)*32'h01000000+32'(l)*32'h00010000+32'(grp)*32'h00001000+32'(slotno)*32'd8+32'(wordno);
 endfunction
 function automatic integer bytes_per_element(input integer formatno);
  bytes_per_element=(formatno==0||formatno==5)?4:(formatno==1)?2:1;
 endfunction
 task tick;begin @(negedge clk);end endtask
 always @(posedge clk)begin
  cyc=cyc+1;#0.1;
  if(rst_n)begin
   if(|leaf_fault)$fatal(1,"EIGHTLEAF_OWNER_FAILURE cycle=%0d leaf_fault=%h mutant=%0d",cyc,leaf_fault,mut_release);
   if(route_fault)$fatal(1,"EIGHTLEAF_ROUTE_FAILURE cycle=%0d",cyc);
   if(vm_dq[280])begin
    if(got>=sent||vm_dq!==expected[got])$fatal(1,"EIGHTLEAF_DATA_FAILURE got=%0d sent=%0d actual=%h expected=%h",got,sent,vm_dq,expected[got]);
    if(latency<0)latency=cyc-sent_cycle[got];
    if(cyc-sent_cycle[got]!=latency)$fatal(1,"EIGHTLEAF_DATE_FAILURE %0d vs %0d",cyc-sent_cycle[got],latency);
    // Native DQ namespace: mirror0, quad2, row10, bank3. The physical calendar must reserve DQ slot6.
    if(vm_dq[279])$fatal(1,"Unexpected mirror mode");
    word_checks=word_checks+$countones(vm_dq[7:0]);got=got+1;
   end
  end
 end
 initial begin
  $readmemh("fp8_truth.mem",fp8_truth);$readmemh("i8_truth.mem",i8_truth);$readmemh("ue8_truth.mem",ue8_truth);
  if($value$plusargs("MUT_RELEASE=%d",mut_release))begin end
  repeat(32)tick();rst_n=1;repeat(16)tick();
  for(phase=0;phase<3;phase=phase+1)begin
   epoch=16'(7+phase);ebank=phase==2;
   begin_epoch=epoch;begin_bank=ebank;begin_v=1;tick();begin_v=0;repeat(16)tick();
   for(s=0;s<64;s=s+1)begin
    fill_v=16'hffff;
    for(b=0;b<8;b=b+1)for(g=0;g<2;g=g+1)begin
     fill_bank[b*2+g]=ebank;fill_slot[(b*2+g)*6+:6]=6'(s);fill_epoch[(b*2+g)*16+:16]=epoch;
     for(w=0;w<8;w=w+1)fill_data[(b*2+g)*256+w*32+:32]=payload_word(phase,b,g,s,w);
    end
    tick();
   end
   fill_v=0;repeat(16)tick();
   for(b=0;b<8;b=b+1)if(!block_ready[b*2+integer'(ebank)])$fatal(1,"EIGHTLEAF_READY_FAILURE phase=%0d leaf=%0d ready=%h",phase,b,block_ready);
   for(f=0;f<6;f=f+1)begin
    case(f)0:fmt=0;1:fmt=1;2:fmt=2;3:fmt=4;4:fmt=5;default:fmt=6;endcase
    for(b=0;b<8;b=b+1)begin
     count=8-b%3;sub=8-count;offset=bytes_per_element(fmt)*((b+fmt)%(32/bytes_per_element(fmt)-count+1));
     groupid=b%2;slotid=(phase*11+f*7+b)%64;dq=(phase+f+b)%4;db=(b+f)%8;
     sector_id=16'((dq<<13)|((phase*64+f*8+b)<<3)|db);
     cmd=0;cmd[0]=ebank;cmd[16:1]=epoch;cmd[18:17]=2'(groupid);cmd[24:19]=6'(slotid);
     cmd[29:25]=5'(offset);cmd[32:30]=3'(fmt);cmd[48:33]=sector_id;cmd[51:49]=3'(sub);cmd[55:52]=4'(count);
     cmd[59:57]=3'(db);cmd[61:60]=2'(dq);
     for(w=0;w<8;w=w+1)sec[w*32+:32]=payload_word(phase,b,groupid,slotid,w);
     packet=0;packet[280]=1;packet[279:264]=sector_id;
     for(w=0;w<count;w=w+1)begin
      raw=sec>>((offset+w*bytes_per_element(fmt))*8);
      case(fmt)1:val={raw[15:0],16'd0};2:val=fp8_truth[raw[7:0]];4:val=i8_truth[raw[7:0]];6:val=ue8_truth[raw[7:0]];default:val=raw;endcase
      packet[8+(sub+w)*32+:32]=val;packet[sub+w]=1;
     end
     expected[sent]=packet;sent_cycle[sent]=cyc+1;sent=sent+1;
     load_v=8'b1<<b;load_cmd=0;load_cmd[b*62+:62]=cmd;tick();
    end
   end
   load_v=0;repeat(24)tick();
   if(got!=sent)$fatal(1,"EIGHTLEAF_DRAIN_FAILURE got=%0d sent=%0d",got,sent);
   // Release every owner. The mutant releases only the last source leaf.
   load_v=mut_release!=0?8'h80:8'hff;
   cmd=0;cmd[0]=ebank;cmd[16:1]=epoch;cmd[56]=1;
   for(b=0;b<8;b=b+1)load_cmd[b*62+:62]=cmd;
   tick();load_v=0;repeat(24)tick();
  end
  if(mut_release!=0)$fatal(1,"EIGHTLEAF_MUTANT_ESCAPED");
  $display("PASS EIGHTLEAF_LOAD phases=3 commands=%0d writes=%0d checked_words=%0d fixed_latency=%0d cells=8 NPC=2 full-window-bytes=32768 formats=6",sent,got,word_checks,latency);
  $finish;
 end
endmodule
`default_nettype wire
