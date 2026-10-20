module tb_query;
reg ck=0;always #5 ck=~ck;
reg[511:0]d=0;reg[11:0]pw=0;reg ev=0,od=0;reg[31:0]rn=0;
wire vb,va;wire[7:0]hb,ha;wire[511:0]cb,ca;wire[31:0]sb,sa;wire[15:0]wb,wa;
query_before b(ck,d,pw,1'b0,ev,od,rn,vb,hb,cb,sb,wb);
query_after a(ck,d,pw,1'b0,ev,od,rn,va,ha,ca,sa,wa);
integer j,n,nb=0,na=0,mb=0,ma=0;reg[511:0]codes[0:31];reg[31:0]sc[0:31];reg[15:0]wt[0:31];
always @(posedge ck) begin
 #1;
 if(vb) begin if(hb!==8'(nb)||cb!==codes[nb]||sb!==sc[nb]||wb!==wt[nb])mb=mb+1;nb=nb+1;end
 if(va) begin if(ha!==8'(na)||ca!==codes[na]||sa!==sc[na]||wa!==wt[na])ma=ma+1;na=na+1;end
end
initial begin
 for(n=0;n<32;n=n+1)begin codes[n]={16{32'(32'h12560000+n)}};sc[n]=32'h88776600+n;wt[n]=16'h3f80+n;end
 repeat(8)@(negedge ck);rn='1;
 for(j=0;j<64;j=j+1) begin
  @(negedge ck);pw=12'(j);ev=!j[0];od=j[0];d=j[0]?{464'd0,wt[j/2],sc[j/2]}:codes[j/2];
 end
 @(negedge ck);ev=0;od=0;d=0;
 repeat(5)@(negedge ck);
 $display("QUERY_ALIGNMENT before_valid=%0d before_mismatch=%0d after_valid=%0d after_mismatch=%0d",nb,mb,na,ma);
 if(nb!=32||mb==0||na!=32||ma!=0)$fatal(1,"QUERY FAIL");
 $display("QUERY PASS source-sliced actual g_stb32heads; original mismatch detected; repaired same-data valid");$finish;
end
endmodule
