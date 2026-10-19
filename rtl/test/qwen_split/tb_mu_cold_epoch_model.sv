`timescale 1ns/1ps
module tb_mu_cold_epoch_model #(parameter NU=4);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,epoch_abort=0,new_epoch=0,accepted_v=0,accepted_cold_role=0,publish_slot=0,fetch_slot=0,fetch_pending=0,consume_slot=0,release_slot=0,retire_slot=0,init_publication=0;
 reg[1:0] accepted_user=0,accepted_generation=0,fetch_user=0,fetch_generation=0,consume_user=0,init_generation=0;
 reg[15:0] accepted_epoch=0;reg[17:0] accepted_token=0,fetch_token=0,consume_token=0,init_token=0;reg[3:0] publish_mask=0,retire_mask=0;
 wire[15:0] fetch_epoch,expected_epoch,core_epoch;wire fault;
 qfd_mu_embedding_cold_epoch_model #(.ENABLE(1),.NU(NU),.COLD_PENDING(1)) dut(.*);
 wire[15:0] f0,e0,c0,fb,eb,cb;wire fault0,faultb;
 qfd_mu_embedding_cold_epoch_model #(.ENABLE(1),.NU(NU),.COLD_PENDING(0)) off0(.fetch_epoch(f0),.expected_epoch(e0),.core_epoch(c0),.fault(fault0),.*);
 qfd_mu_embedding_epoch_publication #(.ENABLE(1),.NU(NU)) base(.fetch_epoch(fb),.expected_epoch(eb),.core_epoch(cb),.fault(faultb),.*);
 integer checks=0,cyc=0,m,u,k;
 task tick;begin @(posedge ck);#1;cyc=cyc+1;checks=checks+1;if({f0,e0,c0,fault0}!=={fb,eb,cb,faultb})$fatal(1,"COLD_MODEL_FAIL defaultoff equivalence cycle%0d",cyc);end endtask
 task quiet;begin accepted_v=0;publish_slot=0;fetch_slot=0;consume_slot=0;release_slot=0;retire_slot=0;init_publication=0;epoch_abort=0;new_epoch=0;end endtask
 task reset;begin @(negedge ck);quiet();rst_n=0;tick();@(negedge ck);rst_n=1;tick();end endtask
 task ok(input bit good,input string msg);begin checks=checks+1;if(!good)$fatal(1,"COLD_MODEL_FAIL %s cycle%0d",msg,cyc);end endtask
 task accept(input integer usr,input integer ep,input integer tok,input integer gen,input bit role);begin @(negedge ck);accepted_v=1;accepted_user=2'(usr);accepted_epoch=16'(ep);accepted_token=18'(tok);accepted_generation=2'(gen);accepted_cold_role=role;tick();@(negedge ck);accepted_v=0;tick();end endtask
 task fetch(input bit pending_mode,input integer usr,input integer tok,input integer gen);begin @(negedge ck);fetch_slot=1;fetch_pending=pending_mode;fetch_user=2'(usr);fetch_token=18'(tok);fetch_generation=2'(gen);tick();@(negedge ck);fetch_slot=0;tick();end endtask
 task publish(input integer mask,input bit ini,input integer tok,input integer gen);begin @(negedge ck);publish_slot=1;publish_mask=4'(mask);init_publication=ini;init_token=18'(tok);init_generation=2'(gen);tick();@(negedge ck);publish_slot=0;init_publication=0;tick();end endtask
 task consume(input integer usr,input integer tok);begin @(negedge ck);consume_slot=1;consume_user=2'(usr);consume_token=18'(tok);tick();@(negedge ck);consume_slot=0;tick();end endtask
 task release_row;begin @(negedge ck);release_slot=1;tick();@(negedge ck);release_slot=0;tick();end endtask
 task seed;begin reset();accept(0,16'h100,777,2,1);fetch(1,0,777,2);ok(!fault&&expected_epoch==16'h100,"selected cold pending snapshot");end endtask
 initial begin
  for(m=0;m<(1<<NU);m=m+1)begin
   reset();for(u=0;u<NU;u=u+1)if(m&(1<<u))accept(u,16'h100+u,777+u,2,u==0);
   if(m&1)fetch(1,0,777,2);
   publish(m,(m&1)!=0,777,2);ok(!fault,"all four-bank masks preserve legal publication");
   for(u=0;u<NU;u=u+1)if(m&(1<<u))begin
    if(u!=0)fetch(0,u,777+u,2);
    consume(u,777+u);ok(!fault,"all published identities consume");release_row();ok(!fault,"native last-read release boundary");
   end
  end
  // New pending identity while old row remains held cannot retag that row.
  seed();publish(1,1,777,2);accept(0,16'h200,888,3,1);ok(expected_epoch==16'h100&&!fault,"future pending cannot retag old cold row");consume(0,777);ok(!fault,"old row consumes old executing epoch");release_row();fetch(1,0,888,3);publish(1,1,888,3);consume(0,888);ok(!fault&&expected_epoch==16'h200,"next selected cold identity");release_row();
  // Reset, abort and new epoch each invalidate pending/resident/publication.
  for(k=0;k<3;k=k+1)begin seed();@(negedge ck);if(k==0)rst_n=0;else if(k==1)epoch_abort=1;else new_epoch=1;tick();ok(!dut.reserved&&!dut.pending_valid&&!dut.active_valid,"invalidation clears validity and reservation");@(negedge ck);quiet();rst_n=1;tick();accept(0,16'h300,999,1,1);fetch(1,0,999,1);publish(1,1,999,1);consume(0,999);ok(!fault,"fresh identity after invalidation");release_row();end
  // Targeted rejected identity, ordering, role and lifecycle cases.
  for(k=0;k<20;k=k+1)begin
   seed();case(k)
    0:publish(1,1,778,2);
    1:publish(1,1,777,3);
    2:publish(1,0,777,2);
    3:publish(0,1,777,2);
    4:consume(0,777);
    5:begin accept(0,16'h200,888,3,1);publish(1,1,888,3);end
    6:fetch(1,0,777,2);
    7:begin @(negedge ck);retire_slot=1;retire_mask=1;tick();end
    8:release_row();
    9:begin publish(1,1,777,2);consume(0,778);end
    10:begin publish(1,1,777,2);consume(1,777);end
    11:begin @(negedge ck);publish_slot=1;publish_mask=1;init_publication=1;init_token=777;init_generation=2;consume_slot=1;consume_user=0;consume_token=777;tick();end
    12:begin reset();accept(0,16'h100,777,2,0);fetch(1,0,777,2);end
    13:begin reset();accept(0,16'h100,777,2,1);fetch(1,1,777,2);end
    14:begin reset();accept(0,16'h100,777,2,1);fetch(1,0,778,2);end
    15:begin reset();accept(0,16'h100,777,2,1);fetch(1,0,777,3);end
    16:begin reset();accept(0,16'h100,777,2,1);fetch(0,0,777,2);end
    17:begin publish(1,1,777,2);accept(0,16'h200,888,3,1);publish(1,0,888,3);end
    18:begin publish(1,1,777,2);consume(0,777);consume(0,777);end
    19:begin consume(0,777);publish(1,1,777,2);end
   endcase
   ok(fault,"bad identity/order/role must sticky-fault");@(negedge ck);quiet();new_epoch=1;tick();ok(fault,"new epoch cannot mask sticky fault");
  end
  $display("COLD_MODEL_PASS NU%0d checks%0d allmasks/cold/warm/pending/invalidation/20rejects/defaultoff",NU,checks);$finish;
 end
endmodule
