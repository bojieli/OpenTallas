module tb;
reg[135:0]rq;reg[1:0]sid;wire[135:0]out;integer s,q,b,n;reg[16:0]want;
ot_hbm_static_dma_vm_rq_context dut(rq,sid,out);
initial begin n=0;
for(q=0;q<4;q=q+1)begin sid=q;
 for(s=0;s<65536;s=s+1)begin
  for(b=0;b<8;b=b+1)rq[b*17+:17]={1'b1,s[15:0]};
  #1;
  want={1'b1,s[15],s[15]?s[14:13]:sid,s[12:0]};
  for(b=0;b<8;b=b+1)begin
   if(out[b*17+:17]!==want)$fatal(1,"context mismatch");
   if(s[15]&&out[b*17+:17]!==rq[b*17+:17])$fatal(1,"mirror changed");
   if(!s[15]&&q==2&&s[14:13]==2&&out[b*17+:17]!==rq[b*17+:17])$fatal(1,"NW baseline changed");
  end
  n=n+8;
 end
end
$display("PASS RQ_CONTEXT all_sid/all_sector checks=%0d zero-cycle mirror-bitexact NW-context-bitexact",n);
$finish;
end
endmodule
