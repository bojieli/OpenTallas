`timescale 1ns/1ps
module tb_entry39;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst_n=0;reg[3:0]sid=15;reg[38:0]q=0;reg[267:0]pci=0;reg[91:0]rqi=0;reg[543:0]rri=0;
 wire[42:0]arco,brco;wire[267:0]apco,bpco;wire[91:0]arqo,brqo;wire[543:0]arro,brro;wire af,bf;
 integer checks=0,errors=0,requests=0,mut=0,seed=17,i,j,rounds=0;
 wire[38:0]qc=q^(mut?(39'd1<<31):39'd0);
 dsdv_eng_tap reference(.ck(ck),.rst_n(rst_n),.sid(sid),.rci({q[38:32],4'd0,q[31:0]}),.rco(arco),.pci(pci),.pco(apco),.rqi(rqi),.rqo(arqo),.rri(rri),.rro(arro),.fault(af));
 dsdv_eng_tap_entry39 candidate(.ck(ck),.rst_n(rst_n),.sid(sid),.rci(qc),.rco(brco),.pci(pci),.pco(bpco),.rqi(rqi),.rqo(brqo),.rri(rri),.rro(brro),.fault(bf));
 initial begin
  if($test$plusargs("MUT_PACK"))mut=1;
  for(rounds=0;rounds<3;rounds++)begin
   seed=17+rounds*191;
   for(i=0;i<20000;i++)begin
    @(negedge ck);rst_n=(i%128)>=8;
    q[38:32]=7'($random(seed));q[31:6]=26'($random(seed));q[5:1]={sid,1'($random(seed))};q[0]=rst_n&&i%8==7;
    if(q[0])requests++;
    for(j=0;j<8;j++)pci[j*32+5+:32]=$random(seed);
    pci[4:0]=0;rqi=0;
    for(j=0;j<17;j++)rri[j*32+:32]=$random(seed);
    rri[0]=0;rri[1]=0;rri[272]=0;rri[273]=0;
    @(posedge ck);#0.05;checks++;
    if({arco,apco,arqo,arro,af}!=={brco,bpco,brqo,brro,bf})errors++;
   end
  end
  $display("ENTRY39 checks=%0d requests=%0d mismatches=%0d mutant=%0d",checks,requests,errors,mut);
  if(errors!=0)$fatal(1,"ENTRY39 mismatch");if(requests==0)$fatal(1,"ENTRY39 missing requests");$display("ENTRY39_PASS");$finish;
 end
endmodule
