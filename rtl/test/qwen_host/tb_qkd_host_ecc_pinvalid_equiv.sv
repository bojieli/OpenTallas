`timescale 1ns/1ps
module tb_qkd_host_ecc_pinvalid_equiv;
 parameter PIPE=2,ENABLE=1,INTERLEAVED=1,PIN_MUT=0;
 reg ck=0;always #0.833 ck=~ck;
 reg rst=0,v=0;reg[287:0]code=0;reg[16:0]sec=0;reg[7:0]row=0;
 wire av,bv,ace,bce,aue,bue,af,bf;wire[255:0]ad,bd;wire[16:0]as,bs;wire[7:0]ar,br;wire[31:0]ac,bc;
 ot_qfd_kv_landing_ecc #(.ENABLE(ENABLE),.PIPE(PIPE),.INTERLEAVED(INTERLEAVED))reference(
 .hclk(ck),.h_rst_n(rst),.i_v(v),.i_code(code),.i_sec(sec),.i_row(row),.o_v(av),.o_data(ad),.o_sec(as),.o_row(ar),.ce(ace),.ue(aue),.fault(af),.ce_count(ac));
 ot_qfd_kv_landing_ecc_pinvalid_candidate #(.ENABLE(ENABLE),.PIPE(PIPE),.INTERLEAVED(INTERLEAVED),.PINVALID(1),.PIN_MUT(PIN_MUT))candidate(
 .hclk(ck),.h_rst_n(rst),.i_v(v),.i_code(code),.i_sec(sec),.i_row(row),.o_v(bv),.o_data(bd),.o_sec(bs),.o_row(br),.ce(bce),.ue(bue),.fault(bf),.ce_count(bc));
 function automatic[71:0]encode(input[63:0]data);
  reg[71:0]c;integer j;begin c=0;j=0;
  for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin c[p-1]=data[j];j++;end
  for(integer k=0;k<7;k++)for(integer p=1;p<=71;p++)if((p&(1<<k))!=0&&p!=(1<<k))c[(1<<k)-1]^=c[p-1];
  c[71]=^c[70:0];encode=c;end
 endfunction
 function automatic[287:0]packcode(input[255:0]data);
  reg[287:0]a,b;integer j;begin a=0;b=0;
  for(integer w=0;w<4;w++)begin a[w*72+:72]=encode(data[w*64+:64]);j=0;
   for(integer p=1;p<=71;p++)if((p&(p-1))!=0)begin b[w*64+j]=a[w*72+p-1];j++;end
   for(integer k=0;k<7;k++)b[256+w*8+k]=a[w*72+(1<<k)-1];b[256+w*8+7]=a[w*72+71];
  end packcode=INTERLEAVED?a:b;end
 endfunction
 integer edges=0,goods=0,ces=0,ues=0;reg[31:0]rng=32'h7adf83b1;reg[255:0]data;
 always @(posedge ck)begin #0.01;
  edges++;
  if({av,ace,aue,af,ac,as,ar,ad}!=={bv,bce,bue,bf,bc,bs,br,bd})$fatal(1,"PINVALID exact output/latency mismatch PIPE%0d ENABLE%0d INTERLEAVED%0d edge%0d valid%0b/%0b UE%0b sticky%0b",PIPE,ENABLE,INTERLEAVED,edges,av,bv,aue,af);
  if(av)goods++;if(ace)ces++;if(aue)ues++;
 end
 task tick;begin @(negedge ck);#0.02;end endtask
 initial begin
  repeat(5)tick();rst=1;
  for(integer n=0;n<4096;n++)begin
   tick();rng=(rng>>1)^((rng&1)?32'hd0000001:0);
   for(integer w=0;w<8;w++)data[w*32+:32]=rng^(32'h9e3779b9*(n*8+w+1));
   code=packcode(data);v=n%7!=0;sec=17'(n*19);row=8'(n);
   if(n%31==7)code[9]^=1'b1; // CE
   if(n%97==39)begin code[9]^=1'b1;code[10]^=1'b1;end // UE/sticky quarantine
   if(n%173==172)begin rst=0;v=0;repeat(3)tick();rst=1;end
  end
  v=0;repeat(10)tick();
  if(ENABLE&&PIPE==2&&!(ces&&ues&&goods))$fatal(1,"missing CE/UE/normal meaningful coverage");
  $display("PASS ECC_PINVALID_EQUIV edges%0d goods%0d CE%0d UE%0d PIPE%0d ENABLE%0d INTERLEAVED%0d",edges,goods,ces,ues,PIPE,ENABLE,INTERLEAVED);$finish;
 end
endmodule
