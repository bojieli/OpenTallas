`timescale 1ns/1fs
module tb_pma_544_512;
 parameter integer MUT=0;
 reg fc=0,pc=0,rst_n=0;
 // Actual declared ratio: coded FEC period17ns, physical period16ns.
 // At 1.2GHz physical this means 1.1294117647GHz FEC, NOT 1.2GHz.
 always #8.5 fc=~fc;
 always #8 pc=~pc;
 integer f=0,p=0,checked=0;
 reg ws=0,ps=0,ds=0,rs=0;
 reg [543:0] d=0;
 wire [511:0] pins;wire pv;
 wire [543:0] q;wire qv,wf,rf,dwf,drf;
 function automatic [543:0] pattern(input integer n);
  integer k;begin for(k=0;k<544;k=k+1)pattern[k]=((n*71+k*13)>>(k%17))&1;pattern[31:0]=n;end
 endfunction
 ot_hbm_pma_block_gearbox #(.MUT(MUT==1?1:0)) tx(fc,pc,rst_n,ws,ps,d,1'b1,pins,pv,wf,rf,{4{fc}});
 ot_hbm_pma_block_gearbox #(.WI(512),.NI(17),.WO(544),.NO(16)) rx(pc,fc,rst_n,ds,rs,pins,pv,q,qv,dwf,drf,{4{pc}});
 always @(negedge fc)begin d=pattern(f+1);ws=(f+1==16);rs=(f+1==64);end
 always @(negedge pc)begin ps=(p+1==(MUT==2?20:40));ds=(p+1==41);end
 always @(posedge pc)p=p+1;
 always @(posedge fc)begin
  f=f+1;#0.000001;
  if(rst_n && (wf||rf||dwf||drf))$fatal(1,"ownership fault f%0d",f);
  if(f>=64)begin
   if(!qv || q!==pattern(f-48))$fatal(1,"coded bit mismatch f%0d",f);
   checked=checked+1;
  end
  if(checked==4096)begin $display("PASS PMA544->512->544 exact4096 words, all544 bits, 16/17 ratio");$finish;end
 end
 initial begin #100;rst_n=1;end
 initial begin #80000;$fatal(1,"timeout");end
endmodule
