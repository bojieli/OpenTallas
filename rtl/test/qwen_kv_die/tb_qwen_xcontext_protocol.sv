`timescale 1ns/1ps
module tb_qwen_xcontext_protocol;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,flush=0,drained=0,rv=0,re=0,ae=0,offer=0,step=0,ready=1;
 reg [3071:0] key=0;reg [378:0] ib=0,offer_ib=0;reg [31:0] version=0;
 reg [20:0] epoch=0;reg [3:0] phase=0;reg [15:0] rt=0,at=0;
 reg [4:0] rr=0,ar=0;reg [127:0] data=0;
 wire reqready,returnready,fire,offerready,go,flushing,fault;
 wire [15:0] token;wire [95:0] fa;wire [378:0] fi,ci;wire [31:0] fv;
 wire [20:0] fe;wire [3:0] fm,fp;wire [127:0] fd;
 reg [378:0] profiles[0:3];reg [15:0] tokens[0:3];
 integer n,r,checks=0,fills=0,accepts=0;
 ot_qwen_xcontext_protocol #(.DEPTH(4),.TOKEN_START(65534),.MUT_CONTEXT(MUT==1),.MUT_DUP(MUT==2),.MUT_GO(MUT==3)) dut(
  .base_clk(clk),.rst_n(rst),.flush(flush),.transport_flushed(drained),
  .req_v(rv),.req_addr(key),.req_ib(ib),.req_version(version),.req_epoch(epoch),.req_mask(4'hf),.req_phase(phase),
  .req_ready(reqready),.req_token(token),.return_event(re),.return_token(rt),.return_root(rr),.return_data(data),
  .return_ready(returnready),.fill_fire(fire),.fill_addr(fa),.fill_ib(fi),.fill_version(fv),.fill_epoch(fe),.fill_mask(fm),.fill_phase(fp),.fill_data(fd),
  .ack_event(ae),.ack_token(at),.ack_root(ar),.ib_offer(offer),.ib_offer_data(offer_ib),.ib_offer_ready(offerready),
  .core_step(step),.core_ready(ready),.core_go(go),.core_ib(ci),.flushing(flushing),.fault(fault));
 function automatic [95:0] keys(input integer tx,input integer root);
  keys={24'(24'hfed123+tx*24'h12345+root*24'hface91+3),24'(24'hfed123+tx*24'h12345+root*24'hface91+2),24'(24'hfed123+tx*24'h12345+root*24'hface91+1),24'(24'hfed123+tx*24'h12345+root*24'hface91)};
 endfunction
 function automatic [20:0] epochs(input integer tx);
  epochs={(tx%2)?18'h30001:18'h10000,3'(tx%2)};
 endfunction
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task allocate(input integer tx,output reg [15:0] saved);
  begin
   if(!reqready)$fatal(1,"unexpected allocation stall");
   for(integer z=0;z<32;z=z+1)key[96*z+:96]=keys(tx,z);
   ib=profiles[tx%4];version=32'(100+tx);epoch=epochs(tx);phase=4'(tx);
   saved=token;rv=1;tick();rv=0;
  end
 endtask
 task retone(input integer tx,input reg [15:0] saved,input integer root);
  begin
   rt=saved;rr=5'(root);data={32'(tx),32'(root),32'h12345678,32'habcdef01};re=1;#1;
   if(!fire || fa!==keys(tx,root) || fi!==profiles[tx%4] || fv!==32'(100+tx) || fe!==epochs(tx) || fp!==4'(tx) || fm!==4'hf || fd!==data)
    $fatal(1,"stale context/full key or return lost tx=%0d root=%0d",tx,root);
   fills=fills+1;checks=checks+1;tick();re=0;
  end
 endtask
 task ackone(input reg [15:0] saved,input integer root);
  begin at=saved;ar=5'(root);ae=1;tick();ae=0;end
 endtask
 initial begin
  $readmemh("native_profiles.hex",profiles);
  tick();tick();rst=1;tick();
  if(reqready || offerready)$fatal(1,"allocation before reset drain");
  // Stale transport data during flushing cannot enter a new context.
  re=1;rt=0;rr=0;#1;if(fire)$fatal(1,"reset stale fire");tick();re=0;
  drained=1;tick();drained=0;
  // Four overlapping descriptors use actual pinned IB words with different xbase/split.
  for(n=0;n<4;n=n+1)allocate(n,tokens[n]);
  if(reqready || token!=2)$fatal(1,"credits overcommitted or token wrap failed");
  // Reverse root and context order; return all roots, but no free until all cache ACKs.
  for(n=3;n>=0;n=n-1)for(r=31;r>=0;r=r-1)retone(n,tokens[n],r);
  if(reqready)$fatal(1,"entry released before downstream ACK");
  // Held source valid with NO output event cannot replay the last fill.
  re=0;repeat(7)begin #1;if(fire)$fatal(1,"held valid duplicated fire");tick();end
  // Deliberately replay same event; must refuse cache write and report protocol fault.
  re=1;rt=tokens[0];rr=0;#1;if(fire)$fatal(1,"duplicate fill accepted");tick();re=0;
  if(!fault)$fatal(1,"duplicate event not reported");
  for(n=0;n<4;n=n+1)for(r=0;r<32;r=r+1)ackone(tokens[n],r);
  if(!reqready)$fatal(1,"all ACKs failed to release credit");
  // Old token never resolves to the next descriptor.
  allocate(4,tokens[0]);re=1;rt=65534;rr=1;#1;if(fire)$fatal(1,"stale token accepted after reuse");tick();re=0;
  // A live loader remains able to allocate while GO is held through core pauses.
  offer_ib=profiles[2];offer=1;tick();offer=0;
  repeat(11)begin if(!go || ci!==profiles[2])$fatal(1,"GO lost during core pause");tick();end
  if(offerready)$fatal(1,"instruction mailbox overwrote held GO");
  allocate(5,tokens[1]); // loader still live while step remains zero
  step=1;#1;if(go && ready)accepts=accepts+1;tick();step=0;
  if(go)$fatal(1,"instruction accepted more than once");
  // Flush blocks even a valid old token until explicit transport drain.
  flush=1;tick();flush=0;re=1;rt=tokens[0];rr=0;
  repeat(5)begin #1;if(fire || reqready)$fatal(1,"flush stale return or premature reuse");tick();end
  re=0;drained=1;tick();drained=0;
  for(n=6;n<22;n=n+1)begin
   allocate(n,tokens[0]);
   for(r=0;r<32;r=r+1)begin retone(n,tokens[0],r);ackone(tokens[0],r);end
  end
  // Reset with a live descriptor forces a distributed flush before token restart.
  allocate(22,tokens[0]);rst=0;tick();rst=1;re=1;rt=tokens[0];rr=0;
  repeat(4)begin #1;if(fire || reqready)$fatal(1,"mid-reset stale return accepted");tick();end
  re=0;drained=1;tick();drained=0;
  if(!reqready)$fatal(1,"mid-reset drain did not unblock");
  if(checks!=640 || accepts!=1)$fatal(1,"coverage checks=%0d accepts=%0d",checks,accepts);
  $display("PASS context protocol fullkey_checks=%0d unique_fills=%0d phases16=1 contexts23=1 repeated_full21_coordinates=1 roots32=1 heldGO_accepts=%0d loader_during_pause=1 reset_drain=1",checks,fills,accepts);$finish;
 end
endmodule
