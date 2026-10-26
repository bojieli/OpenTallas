`timescale 1ns/1ps
module tb_qkd_host_ctrl_token_legacy;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 wire[2:0]die_id=0;
 reg rst_n=0,rx_v=0,tx_cr=0,cmd_v=0;reg[511:0]rx_d=0;reg[181:0]cmd_hc=0;
 reg[92:0]local_tk=0;reg[9:0]local_kst=0;reg[1:0]local_boot=0;
 wire rx_cr,tx_v,cmd_cr,fault;wire[511:0]tx_d;wire[181:0]hc;wire[743:0]tk8;wire[79:0]kst8;wire[15:0]boot8;wire[7:0]seen;
 reg startup_allowed=0;reg local_service_ready=0,begin_v=0;reg[15:0]local_service_epoch=0,begin_epoch=0;
 wire begin_cr,begin_available,service_begin_v,pending_advertised,ingest_permission;wire[15:0]service_begin_epoch,pending_epoch;wire[7:0]service_ready8,pending_ack8;wire[127:0]service_epoch8;
 qkd_host_ctrl_token_service_packet #(.DIE(0),.MUT(MUT),.STRAPPED(1))dut(.por_n(rst_n),.token_wrap_fence_valid('0),.token_wrap_drained('0),.token_wrap_link_reset_seen('0),.token_wrap_retraining_done('0),.token_allocator_fault(1'b0),.package_abort('0),.abort_drained('0),.token_request_ready('0),.token_grant_valid('0),.token_grant_epoch('0),.token_grant_token('0),.token_grant_position('0),.token_grant_generation('0),.token_grant_tag('0),.allocated_valid('0),.allocated_delivered('0),.allocated_epoch('0),.allocated_token('0),.allocated_position('0),.allocated_generation('0),.terminal_accepted('0),.token_request_valid(),.token_request_token(),.token_request_position(),.token_request_generation(),.token_grant_ready(),.token_epoch_valid(),.token_epoch(),.cancel_valid(),.cancel_tag(),.cancel_generation(),.cancel_done(),.cancel_fault(),.cancel_drained(),.*);
 // Peer7 also tests addressed command decode and status encoding independently.
 reg[2:0]peer_id=3'd7;
 reg prx_v=0,ptx_cr=0;reg[511:0]prx_d=0;reg[92:0]ptk=0;reg[9:0]pb=0;
 wire ptx_v,prx_cr,pfault;wire[511:0]ptx_d;wire[181:0]phc;
 qkd_host_ctrl_token_service_packet #(.DIE(7),.STRAPPED(1))peer(.die_id(peer_id),.ck(ck),.rst_n(rst_n),.rx_v(prx_v),.rx_d(prx_d),.rx_cr(prx_cr),
 .tx_v(ptx_v),.tx_d(ptx_d),.tx_cr(ptx_cr),.local_tk(ptk),.local_kst(pb),.local_boot(2'd3),.cmd_v(1'b0),.cmd_hc(182'd0),.cmd_cr(),
 .hc(phc),.tk8(),.kst8(),.boot8(),.seen(),.fault(pfault));
 integer peerstarts=0;
 always @(posedge ck)if(rst_n&&phc[38])begin peerstarts++;if(phc!=cmd_hc)$fatal(1,"peer command exact");end
 integer checks=0,n=0;reg[6:0]destseen=0;reg[511:0]p;
 task tick;begin @(posedge ck);#1;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 task status(input integer d,input[92:0]tk,input[15:0]seq);begin
  p=512'h01000121|(512'(d)<<16)|(512'(seq)<<32)|(512'(tk)<<48)|(512'(d+10)<<141)|(512'd3<<151);
  @(negedge ck);rx_v=1;rx_d=p;@(negedge ck);rx_v=0;
 end endtask
 initial begin
  repeat(4)tick();rst_n=1;repeat(5)tick();
  // First peer packet is version1, opcode21, src7,targetdie0,seq0.
  check(ptx_d[7:0]==8'h21&&ptx_d[18:16]==7&&ptx_d[31:24]==1,"peer status header");
  local_tk=93'h12345678901234567890123;local_kst=10'h2ab;local_boot=3;
  for(integer d=1;d<8;d++)status(d,93'(d)*93'h123456789abcd,0);
  repeat(10)tick();check(seen==8'hff,"all8 sources seen");check(tk8[92:0]==local_tk&&kst8[9:0]==local_kst&&boot8[1:0]==local_boot,"local snapshot");
  for(integer d=1;d<8;d++)begin check(tk8[d*93+:93]==93'(d)*93'h123456789abcd,"peer exact tk93");check(kst8[d*10+:10]==d+10&&boot8[d*2+:2]==3,"peer boot10");end
  // Partial command broadcasts consume exactly one upstream credit after7 copies.
  cmd_hc=182'h123456789abcdef123456789abcdef123456789abcdef;
  cmd_hc[38]=1;cmd_hc[113]=1;cmd_hc[181]=1;
  @(negedge ck);cmd_v=1;@(negedge ck);cmd_v=0;
  for(integer k=0;k<45;k++)begin
   tick();
   if(tx_v)begin
    check(tx_d[7:0]==8'h22&&tx_d[229:48]==cmd_hc&&tx_d[47:32]==0,"command exact");
    check(tx_d[31:24]==(8'd1<<(n+1)),"command routing");n++;destseen[n-1]=1;
    if(n==7)begin @(negedge ck);prx_v=1;prx_d=tx_d;@(negedge ck);prx_v=0;end
    @(negedge ck);tx_cr=1;@(negedge ck);tx_cr=0;
   end
   if(phc[38])check(phc==cmd_hc,"peer command exact");
  end
  check(n==7&&destseen==7'h7f&&peerstarts==1&&!fault&&!pfault,"all remote copies");
  // Sequence replay fails closed instead of overwriting generation-qualified state.
  status(7,0,0);repeat(10)tick();check(fault,"replayed peer status rejected");
  peer_id=6;repeat(5)tick();check(pfault,"identity change rejected within epoch");
  $display("PASS CTRL8_PACKET checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
