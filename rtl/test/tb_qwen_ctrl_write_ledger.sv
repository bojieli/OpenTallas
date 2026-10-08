`timescale 1ns/1ps
module tb_qwen_ctrl_write_ledger;
 parameter integer PC=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0,w_v=0,sched_take=0,row_v=0,col_v=0,col_we=0,done_v=0;
 reg ctrl_fault=0,refresh_ack=0,upstream_quiescent=0,epoch_advance=0;
 reg [23:0] w_sec=0;reg[255:0] w_data=0;reg[8:0]w_tag=0,done_tag=0;
 reg[2:0]row_op=0;reg[4:0]row_bank=0,col_bank=0,col_col=0;reg[18:0]row_row=0;
 wire w_room,sched_v,phy_row_v,phy_col_v,phy_col_we,wd_v,stop,quarantine,refresh_req,epoch_ready;
 wire[4:0]sched_bank,sched_col,phy_row_bank,phy_col_bank,phy_col_col,cancel_count;
 wire[2:0]phy_row_op;wire[18:0]phy_row_row;wire[23:0]phy_w_sec;
 wire[255:0]phy_w_data;wire[8:0]phy_w_tag,wd_tag;wire[6:0]committed_count;
 ot_qwen_ctrl_write_ledger #(.ENABLE(1),.PC(PC)) dut(.*);
 integer accepted=0,finished=0,checked=0,k,t;
 reg block_expected=0;
 reg [23:0] expected_sec;reg[255:0]expected_data;reg[8:0]expected_tag;
 // Actual receiver samples before producer NBA updates, like stream_ack.
 always @(posedge clk) if(rst_n) begin
  if(block_expected && (phy_row_v||phy_col_v||wd_v||sched_v||w_room))
   $fatal(1,"unexpected receiving-edge publication after quarantine");
  if(phy_col_we) begin
   if(phy_w_sec!==expected_sec || phy_w_data!==expected_data || phy_w_tag!==expected_tag)
    $fatal(1,"native receiving-edge payload/tag/sector mismatch");
   accepted=accepted+1;
  end
  if(wd_v) begin
   if(wd_tag!==done_tag) $fatal(1,"wrong real completion tag");
   finished=finished+1;
  end
 end
 task edge_step;begin @(posedge clk);#0.001;@(negedge clk);end endtask
 task idle;begin w_v=0;sched_take=0;row_v=0;col_v=0;col_we=0;done_v=0;#0.001;end endtask
 task reset_all;begin
  @(negedge clk);rst_n=0;idle();ctrl_fault=0;refresh_ack=0;upstream_quiescent=0;epoch_advance=0;block_expected=0;
  edge_step();rst_n=1;edge_step();if(!w_room)$fatal(1,"no room after cold reset");
 end endtask
 function automatic[23:0] sector(input integer bank,col,rw);
  reg[14:0]s;begin s={3'(bank>>2),5'(col),5'(PC),2'(bank&3)};
   sector={7'(rw),s[7],s[6],2'b00,s[14:8],s[5:0]};end
 endfunction
 task enqueue(input integer bank,col,rw,tag);
 begin
  w_sec=sector(bank,col,rw);w_data={8{32'h12345678^32'(tag)}};w_tag=9'(tag);w_v=1;
  edge_step();w_v=0;#0.001;
 end endtask
 task handoff(input integer bank,col);
 begin
  if(!sched_v || sched_bank!=bank || sched_col!=col)$fatal(1,"wrong handoff");
  sched_take=1;edge_step();sched_take=0;#0.001;
 end endtask
 task activate(input integer bank,rw);
 begin row_v=1;row_op=1;row_bank=5'(bank);row_row=19'(rw);edge_step();row_v=0;#0.001;end
 endtask
 task write_command(input integer bank,col,rw,tag);
 begin
  col_v=1;col_we=1;col_bank=5'(bank);col_col=5'(col);
  expected_sec=sector(bank,col,rw);expected_data={8{32'h12345678^32'(tag)}};expected_tag=9'(tag);
  edge_step();col_v=0;col_we=0;#0.001;
 end endtask
 task complete(input integer tag);
 begin done_v=1;done_tag=9'(tag);edge_step();done_v=0;#0.001;end endtask
 task inject(input integer which);
 begin
  case(which)
   0: dut.g_copy[0].u.ingress[1][9]=~dut.g_copy[0].u.ingress[1][9];
   1: dut.g_copy[0].u.ingress[1][0]=~dut.g_copy[0].u.ingress[1][0];
   2: dut.g_copy[0].u.completion[0][0]=~dut.g_copy[0].u.completion[0][0];
   3: dut.g_copy[0].u.completion[0][9]=~dut.g_copy[0].u.completion[0][9];
   4: dut.g_copy[0].u.rows[0][0]=~dut.g_copy[0].u.rows[0][0];
   5: dut.g_copy[0].u.open_bank[0]=~dut.g_copy[0].u.open_bank[0];
   6: dut.g_copy[0].u.wp[0]=~dut.g_copy[0].u.wp[0];
   7: dut.g_copy[0].u.hp[0]=~dut.g_copy[0].u.hp[0];
   8: dut.g_copy[0].u.cp[0]=~dut.g_copy[0].u.cp[0];
   9: dut.g_copy[0].u.awp[0]=~dut.g_copy[0].u.awp[0];
   10: dut.g_copy[0].u.arp[0]=~dut.g_copy[0].u.arp[0];
   11: dut.g_copy[0].u.occupied[0]=~dut.g_copy[0].u.occupied[0];
   12: dut.g_copy[0].u.handed[0]=~dut.g_copy[0].u.handed[0];
   13: dut.g_copy[0].u.committed[0]=~dut.g_copy[0].u.committed[0];
   14: dut.g_copy[0].u.aborted=~dut.g_copy[0].u.aborted;
   15: dut.g_copy[0].u.acknowledged=~dut.g_copy[0].u.acknowledged;
   16: dut.g_copy[1].u.ingress[1][9]=~dut.g_copy[1].u.ingress[1][9];
   17: dut.g_copy[1].u.ingress[1][0]=~dut.g_copy[1].u.ingress[1][0];
   18: dut.g_copy[1].u.completion[0][0]=~dut.g_copy[1].u.completion[0][0];
   19: dut.g_copy[1].u.completion[0][9]=~dut.g_copy[1].u.completion[0][9];
   20: dut.g_copy[1].u.rows[0][0]=~dut.g_copy[1].u.rows[0][0];
   21: dut.g_copy[1].u.open_bank[0]=~dut.g_copy[1].u.open_bank[0];
   22: dut.g_copy[1].u.wp[0]=~dut.g_copy[1].u.wp[0];
   23: dut.g_copy[1].u.hp[0]=~dut.g_copy[1].u.hp[0];
   24: dut.g_copy[1].u.cp[0]=~dut.g_copy[1].u.cp[0];
   25: dut.g_copy[1].u.awp[0]=~dut.g_copy[1].u.awp[0];
   26: dut.g_copy[1].u.arp[0]=~dut.g_copy[1].u.arp[0];
   27: dut.g_copy[1].u.occupied[0]=~dut.g_copy[1].u.occupied[0];
   28: dut.g_copy[1].u.handed[0]=~dut.g_copy[1].u.handed[0];
   29: dut.g_copy[1].u.committed[0]=~dut.g_copy[1].u.committed[0];
   30: dut.g_copy[1].u.aborted=~dut.g_copy[1].u.aborted;
   31: dut.g_copy[1].u.acknowledged=~dut.g_copy[1].u.acknowledged;
   32: dut.trip_seen=1;
   33: dut.permit_state=0;
  endcase
 end endtask
 initial begin
  reset_all();
  // All 32 bank maps, two columns per bank, both ring pointers wrap.
  for(k=0;k<128;k=k+1) begin
   if(k<32) activate(k,2);
   enqueue(k%32,k/32,2,256+k);
   handoff(k%32,k/32);
   write_command(k%32,k/32,2,256+k);
   complete(256+k);
   if(quarantine || committed_count!=0)$fatal(1,"healthy failed k=%0d",k);
  end
  checked=checked+1;
  // Commit, ingress push, and real completion on one accepting edge.
  reset_all();activate(0,2);
  enqueue(0,0,2,256);handoff(0,0);write_command(0,0,2,256);
  enqueue(0,1,2,257);handoff(0,1);
  w_v=1;w_sec=sector(0,2,2);w_tag=258;w_data={8{32'h12345678^32'd258}};
  done_v=1;done_tag=256;write_command(0,1,2,257);idle();
  if(committed_count!=1 || dut.occupied[0]!=1 || dut.handed[0]!=0 || quarantine)
   $fatal(1,"simultaneous ownership transfer failed");
  complete(257);handoff(0,2);write_command(0,2,2,258);complete(258);checked=checked+1;
  // Completion capacity is reserved before scheduler handoff, never discovered
  // after an unbackpressurable physical WR has already been emitted.
  reset_all();activate(0,2);
  for(k=0;k<64;k=k+1) begin
   enqueue(0,k%32,2,256+k);handoff(0,k%32);write_command(0,k%32,2,256+k);
  end
  enqueue(0,0,2,320);
  if(sched_v || committed_count!=64 || quarantine)$fatal(1,"completion reserve missing");
  complete(256);handoff(0,0);write_command(0,0,2,320);
  if(committed_count!=64)$fatal(1,"completion ring wrap lost record");
  for(k=257;k<=320;k=k+1) complete(k);
  if(committed_count!=0 || quarantine)$fatal(1,"completion saturation drain failed");checked=checked+1;
  // Abort on attempted second WR; the first committed write still owns data
  // in the PHY. Two unissued + one late advertised native record cancel.
  reset_all();activate(0,2);
  enqueue(0,0,2,256);enqueue(0,1,2,257);enqueue(0,2,2,258);
  handoff(0,0);handoff(0,1);write_command(0,0,2,256);
  ctrl_fault=1;col_v=1;col_we=1;col_bank=0;col_col=1;
  edge_step();col_v=0;col_we=0;#0.001;
  if(!refresh_req || committed_count!=1 || cancel_count!=2)$fatal(1,"abort lost ownership");
  enqueue(0,3,2,259);
  if(cancel_count!=3)$fatal(1,"late advertised pulse not canceled");
  refresh_ack=1;epoch_advance=1;upstream_quiescent=1;edge_step();
  if(epoch_ready || committed_count!=1)$fatal(1,"premature epoch");
  complete(256);ctrl_fault=0;epoch_advance=0;edge_step();
  if(!epoch_ready || quarantine)$fatal(1,"real drain not ready");
  epoch_advance=1;edge_step();epoch_advance=0;refresh_ack=0;
  if(!w_room || stop || committed_count!=0)$fatal(1,"safe epoch failed");
  checked=checked+1;
  // Address disagreement must suppress the command on its first edge.
  reset_all();activate(0,2);enqueue(0,0,2,256);handoff(0,0);
  col_v=1;col_we=1;col_bank=0;col_col=1;block_expected=1;
  edge_step();idle();if(!quarantine)$fatal(1,"bad physical sector accepted");checked=checked+1;
  // Unknown completion cannot fabricate service retirement.
  reset_all();activate(0,2);enqueue(0,0,2,256);handoff(0,0);write_command(0,0,2,256);
  done_v=1;done_tag=257;block_expected=1;edge_step();idle();
  if(!quarantine)$fatal(1,"bad completion accepted");checked=checked+1;
  // Three-free-slot advertisement, followed by two delayed native emissions.
  reset_all();for(k=0;k<14;k=k+1) enqueue(0,k,2,256+k);
  if(w_room)$fatal(1,"room did not reserve delayed emissions");
  enqueue(0,14,2,270);enqueue(0,15,2,271);
  if(quarantine || dut.occupied[0]!=16)$fatal(1,"reservation bound failed");
  checked=checked+1;
  for(t=0;t<34;t=t+1) begin
   reset_all();activate(0,2);enqueue(0,0,2,256);handoff(0,0);write_command(0,0,2,256);
   enqueue(0,1,2,257);handoff(0,1);
   inject(t);block_expected=1;
   col_v=1;col_we=1;col_bank=0;col_col=1;done_v=1;done_tag=256;
   edge_step();idle();
   if(!quarantine || !refresh_req)$fatal(1,"upset not quarantined %0d",t);
   // Neither an external ACK nor an epoch pulse can release ambiguity.
   refresh_ack=1;upstream_quiescent=1;epoch_advance=1;
   repeat(3)edge_step();
   if(epoch_ready || !quarantine)$fatal(1,"quarantine incorrectly recovered %0d",t);
   // Restore the original upset: quarantine must remain after equality returns.
   if(t<32) inject(t);
   #0.001;
   if(!quarantine)$fatal(1,"restoring damaged bit incorrectly released quarantine");
   // Corrupt either sticky rail back toward release: the other holds.
   dut.trip_seen=0;edge_step();dut.permit_state=1;edge_step();
   if(!quarantine)$fatal(1,"halt rail not independent");checked=checked+1;
  end
  $display("PASS PC=%0d scenarios=%0d accepted=%0d real_completions=%0d upset_cases=34",PC,checked,accepted,finished);
  $finish;
 end
endmodule
