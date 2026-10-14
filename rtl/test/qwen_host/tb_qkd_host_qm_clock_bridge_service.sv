`timescale 1ns/1ps
module tb_qkd_host_qm_clock_bridge_service;
 parameter integer MUT=0;
 reg c=0,h=0;always #0.416 c=~c;
 initial begin #0.197;forever #0.5 h=~h;end
 reg permit=0;reg rst_n=0,iv=0,dv=0,dc=0;reg[1:0]ic=0;reg[511:0]id=0;reg[63:0]dd=0;reg[4:0]hc=0;
 wire[4:0]icr;wire hv,dcr,pv;wire[1:0]hcls;wire[511:0]hd;wire[63:0]pd;wire[5:0]faults;
 qkd_host_qm_clock_bridge_service #(.ENABLE_SERVICE(1),.MUT(MUT))dut(.cq(c),.qw(c),.qr(h),.qp(h),.ccw(h),.ccr(c),.rst_n(rst_n),
 .ing_v(iv),.ingest_permission(permit),.ing_cls(ic),.ing_d(id),.ing_crn(icr),.qm_v(hv),.qm_cls(hcls),.qm_d(hd),.qm_crn(hc),
 .done_v(dv),.done_d(dd),.done_cr(dcr),.packet_done_v(pv),.packet_done_d(pd),.packet_done_cr(dc),.faults(faults));
 integer sent=0,received=0,dsent=0,dreceived=0,sourcecredits=16,donecredits=4;
 integer hpending=0,dpending=0,csteps=0,hsteps=0,batches=0;reg begun=0;
 function[511:0]word(input integer n);word={{15{32'hfa659ac3}},n[31:0]};endfunction
 function[63:0]completion(input integer n);completion={32'hc19a57af,n[31:0]};endfunction
 always @(posedge c)if(begun)begin
  sourcecredits=sourcecredits+icr;
  if(sourcecredits>16)$fatal(1,"extra upstream capacity credit %0d",sourcecredits);
  if(pv)begin if(pd!==completion(dreceived))$fatal(1,"completion exact/order %0d",dreceived);dreceived=dreceived+1;dpending=dpending+1;end
  if(faults)$fatal(1,"bridge fault %b sent%0d received%0d",faults,sent,received);
 end
 always @(posedge h)if(begun)begin
  if(dcr)donecredits=donecredits+1;
  if(donecredits>4)$fatal(1,"extra completion credit");
  if(hv)begin
   if(hd!==word(received)||hcls!==2'(received%3))$fatal(1,"QM exact514/order %0d",received);
   received=received+1;hpending=hpending+1;
  end
  if(hpending>4)$fatal(1,"unreserved QM output %0d",hpending);
 end
 always @(negedge c)if(begun)begin
  csteps=csteps+1;iv=0;dc=0;permit=csteps>250 && !(csteps>=900 && csteps<1100);
  if(csteps==240&&(sent!=16||received!=0||sourcecredits!=0))$fatal(1,"ING16 beforeepochpermission sent%0d received%0d capacity%0d",sent,received,sourcecredits);
  if(sent<192&&sourcecredits>0)begin iv=1;ic=2'(sent%3);id=word(sent);sent=sent+1;sourcecredits=sourcecredits-1;end
  if(csteps>700&&dpending>0&&csteps%7!=0)begin dc=1;dpending=dpending-1;end
 end
 always @(negedge h)if(begun)begin
  hsteps=hsteps+1;hc=0;dv=0;
  if(hsteps>500&&hpending>0&&hsteps%17==0&&(hpending==4||received==192))begin
   hc=5'(hpending);if(hpending==4)batches=batches+1;hpending=0;
  end
  if(dsent<96&&donecredits>0&&hsteps%3!=0)begin dv=1;dd=completion(dsent);dsent=dsent+1;donecredits=donecredits-1;end
 end
 initial begin repeat(12)@(negedge c);rst_n=1;repeat(24)@(negedge c);begun=1;
  wait(received==192&&dreceived==96);repeat(100)@(negedge c);
  if(sourcecredits!=16||donecredits!=4||hpending!=0||dpending!=0||batches<20||faults)$fatal(1,"capacity drain src%0d done%0d hp%0d dp%0d batches%0d faults%b",sourcecredits,donecredits,hpending,dpending,batches,faults);
  $display("PASS QM_EPOCH_GATED_CLOCK_BRIDGE ING192 DONE96 batches4=%0d packet832ps QM1000ps phase197ps stallQM500 stallpacket700 source16 CDC4",batches);$finish;
 end
 initial begin #100000;$fatal(1,"bridge timeout sent%0d received%0d done%0d/%0d credit%0d/%0d faults%b",sent,received,dsent,dreceived,sourcecredits,donecredits,faults);end
endmodule
