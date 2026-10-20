module tb_stage;
reg ck=0;always #5 ck=~ck;reg[511:0]d=0;reg[11:0]pw=0;reg hdr=0,ev=0,od=0;reg[31:0]rn=0;
wire va,vb;wire[7:0]ha,hb;wire[511:0]ca,cb,ma,mb;wire[31:0]sa,sb;wire[15:0]wa,wb;
stage_a a(ck,d,pw,hdr,ev,od,rn,va,ha,ca,sa,wa,ma);
stage_b b(ck,d,pw,hdr,ev,od,rn,vb,hb,cb,sb,wb,mb);
integer i,k;integer checks=0;
initial begin
 repeat(8)@(negedge ck);rn='1;
 for(i=0;i<4096;i=i+1) begin
  @(negedge ck);pw=12'(i%64);hdr=(i%89==0);ev=!pw[0];od=pw[0];
  for(k=0;k<16;k=k+1)d[32*k+:32]=$urandom;
  @(posedge ck);#1;
  if(va!==vb || ha!==hb || ca!==cb || sa!==sb || wa!==wb || ma!==mb)begin
   $display("STAGE FAIL cycle%0d query%0b meta%0b",i, {va,ha,ca,sa,wa}==={vb,hb,cb,sb,wb},ma===mb);$fatal(1);
  end
  checks=checks+1;
 end
 $display("STAGE PASS actualsourceg_stb query+allheaderfields random%0d",checks);$finish;
end
endmodule
