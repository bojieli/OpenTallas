`timescale 1ns/1ps
module tb;
reg ck=0;always #1 ck=~ck;
reg rn=0;reg[38:0]rq=0;reg[267:0]pci=0;reg[91:0]rqi=0;reg[543:0]rri=0;
wire[38:0]o[0:5];wire[42:0]og[0:5];wire[267:0]p[0:5],pg[0:5];wire[91:0]q[0:5],qg[0:5];wire[543:0]r[0:5],rg[0:5];wire[5:0]fault,fg;
for(genvar g=0;g<6;g=g+1)begin:cases
 localparam[29:0]BASE=(g/2==0)?30'h0:(g/2==1)?30'h14000000:30'h3c000000;
 wire[42:0]full={rq[38:32],BASE[29:26],rq[31:0]};
 dsdv_eng_tap_c #(.WEST(g%2))gold(ck,rn,4'd3,full,og[g],pci,pg[g],rqi,qg[g],rri,rg[g],fg[g]);
 dsdv_eng_tap_c_req39 #(.WEST(g%2),.PCBASE(BASE))dut(ck,rn,4'd3,rq,o[g],pci,p[g],rqi,q[g],rri,r[g],fault[g]);
end
function automatic[63:0]xs(input[63:0]x);reg[63:0]t;begin t=x^(x<<13);t=t^(t>>7);xs=t^(t<<17);end endfunction
integer seed=1,cycles=50000,c,j,k,mis=0,active=0;reg[63:0]s;
initial begin
if($value$plusargs("seed=%d",seed))begin end
if($value$plusargs("cycles=%d",cycles))begin end
s=64'hace1357902468bdf^64'(seed);
for(c=0;c<cycles;c=c+1)begin
 @(negedge ck);s=xs(s);rn=!(c<8 || c%10000<5);
 rq={s[6:0],s[32:7],((c%4==0)?s[37:33]:{4'd3,s[39]}),s[40]};
 for(k=0;k<8;k=k+1)begin s=xs(s);rri[k*64+:64]=s;end
 rri[543:512]=s[31:0];rri[0]=(c%7==0);
 s=xs(s);rqi={28'd0,s};if(c%4!=0)rqi=0;
 for(k=0;k<4;k=k+1)begin s=xs(s);pci[64*k+:64]=s;end
 pci[267:256]=s[11:0];pci[0]=(c%5==0);
 @(posedge ck);#0.1;
 for(j=0;j<6;j=j+1)begin
  if(q[j]!=0)active=active+1;
  if({o[j],p[j],q[j],r[j],fault[j]}!=={{og[j][42:36],og[j][31:0]},pg[j],qg[j],rg[j],fg[j]})begin
   if(mis<5)$display("REQ39_DIFF cycle=%0d case=%0d rco=%b pco=%b rqo=%b rro=%b fault=%b",c,j,o[j]!={og[j][42:36],og[j][31:0]},p[j]!=pg[j],q[j]!=qg[j],r[j]!=rg[j],fault[j]!=fg[j]);mis=mis+1;
  end
 end
end
$display("REQ39 %s seed=%0d cycles=%0d mis=%0d active=%0d",mis==0?"PASS":"FAIL",seed,cycles,mis,active);$finish;
end
endmodule
