`timescale 1ns/1ps
module tb_s81_host_dispatch;
 reg ck=0;always #0.416667 ck=~ck;reg rn=0;
 reg iv=0,iwe=1;reg[31:0] ia=0;reg[255:0] id=0;wire ic;wire[2:0] bv;wire bw;wire[31:0] ba;wire[255:0] bd;
 reg[2:0] cr=0;wire fault;
 ot_s81_host_dispatch #(.ENABLE(1)) dut(ck,rn,iv,iwe,ia,id,ic,bv,bw,ba,bd,cr,fault);
 integer credits=8,offered=0,seen=0,returned=0,pending[0:2],i,c,simultaneous=0;
 integer qaddr[0:63],qclass[0:63];reg[255:0] qdata[0:63];
 initial begin
  pending[0]=0;pending[1]=0;pending[2]=0;
  repeat(5)@(negedge ck);rn=1;
  for(c=0;c<240;c=c+1)begin
   iv=0;cr=0;
   if(offered<48&&credits>0)begin
    iv=1;iwe=1;ia=(offered%3==0)?32'(offered):(offered%3==1)?32'h80000000|offered:32'hc0000000|offered;
    id=offered;
    if(offered%8==7)begin ia=32'hffffffff;id[65:64]=(offered%16==7)?2:3;end
    qaddr[offered]=ia;qdata[offered]=id;qclass[offered]=(ia==32'hffffffff)?(id[65:64]==3?2:1):(ia[31]? (ia[30]?2:1):0);
    credits=credits-1;offered=offered+1;
   end
   if(c>=20)for(i=0;i<3;i=i+1)if(pending[i]>0)begin cr[i]=1;pending[i]=pending[i]-1;end
   if(cr==7)simultaneous=simultaneous+1;
   @(posedge ck);#0.05;
   if(fault)$fatal(1,"dispatch fault cycle%0d",c);
   if(bv!=0)begin
    if(bv!=(3'b001<<qclass[seen])||ba!=qaddr[seen]||bd!=qdata[seen]||!bw)$fatal(1,"wrong branch/payload");
    pending[qclass[seen]]=pending[qclass[seen]]+1;seen=seen+1;
   end
   if(ic)begin credits=credits+1;returned=returned+1;end
   @(negedge ck);
  end
  if(offered!=48||seen!=48||returned!=48||credits!=8||simultaneous==0)$fatal(1,"sharedseat gate notdrained");
  // A phantom branchcredit must fault; upstream seats cannot multiply.
  iv=0;cr=1;@(posedge ck);#0.05;if(!fault)$fatal(1,"unowned branchcredit accepted");
  $display("S81_HOST_DISPATCH PASS sectors=%0d credit_returns=%0d simultaneous=%0d",seen,returned,simultaneous);$finish;
 end
endmodule
