`timescale 1ps/1ps
module tb_vm_r2048_fields;
 parameter integer MUT=0;
 reg[84:0]lrq;wire[89:0]nrq;reg[561:0]lwq;wire[563:0]nwq;
 reg[280:0]ldq,lkq;wire[281:0]ndq,nkq;reg[275:0]lxq,lx2;wire[276:0]nxq,nx2;
 reg[284:0]lpq;wire[285:0]npq;reg[276:0]neg;wire[275:0]leg;reg[17:0]ns;wire[17:0]ls;
 ot_vms_legacy_r2048_fields #(.MUT(MUT)) dut(.legacy_rq(lrq),.native_rq(nrq),.legacy_wq(lwq),.native_wq(nwq),.legacy_dq(ldq),.native_dq(ndq),.legacy_kq(lkq),.native_kq(nkq),.legacy_xq(lxq),.native_xq(nxq),.legacy_xq2(lx2),.native_xq2(nx2),.legacy_pq(lpq),.native_pq(npq),.native_eg(neg),.legacy_eg(leg),.native_status(ns),.legacy_status(ls));
 function automatic[16:0]lift(input integer n);lift=17'((n&32767)|((n&32768)<<1));endfunction
 function automatic[11:0]local_lift(input integer n);local_lift=12'((n&1023)|((n&1024)<<1));endfunction
 integer checks=0;reg[255:0]d;reg[7:0]m;reg bad;reg[10:0]oldrow;reg[11:0]newrow;
 initial begin
  for(integer n=0;n<65536;n=n+1)begin
   d={8{32'hbead1234^32'(n)}};m=8'(n)^8'h5a;oldrow=11'(n);newrow=12'(n);
   for(integer g=0;g<5;g=g+1)lrq[g*17+:17]={1'b1,16'(n+g)};
   for(integer g=0;g<2;g=g+1)lwq[g*281+:281]={1'b1,16'(n+g),d^256'(g),m};
   ldq={1'b1,16'(n),d,m};lkq={1'b1,16'(n^32768),~d,~m};
   lxq={1'b1,oldrow,d,m};lx2={1'b1,oldrow,~d,~m};lpq={1'b1,1'(n),oldrow,d,m,8'(n)};
   neg={1'(n),newrow,d,m};ns={1'b0,17'(n)};bad=1'(n)&&newrow[10];#1;
   for(integer g=0;g<5;g=g+1)if(nrq[g*18+:18]!=={1'b1,lift((n+g)&65535)})$fatal(1,"sector identity lost n%0d g%0d",n,g);
   for(integer g=0;g<2;g=g+1)if(nwq[g*282+:282]!=={1'b1,lift((n+g)&65535),d^256'(g),m})$fatal(1,"wide payload/mask identity");
   if(ndq!=={1'b1,lift(n),d,m}||nkq!=={1'b1,lift(n^32768),~d,~m})$fatal(1,"DMA/COLL identity");
   if(nxq!=={1'b1,local_lift(n&2047),d,m}||nx2!=={1'b1,local_lift(n&2047),~d,~m})$fatal(1,"ring local identity");
   if(npq!=={1'b1,1'(n),local_lift(n&2047),d,m,8'(n)})$fatal(1,"packet identity");
   if(leg!=={1'(n)&&!bad,newrow[11],newrow[9:0],d,m}||ls!==(ns|{bad,17'd0}))$fatal(1,"unrepresentable reverse valid/fault guard");
   checks=checks+1;
  end
  $display("VM_FIELDS_R2048 PASS exhaustive_sectors=65536 checks=%0d read_groups=5 write_groups=2 carriers=7 reverse_high_guard=1 existing_status_fault_bit=17 added_cycles=0",checks);$finish;
 end
endmodule
