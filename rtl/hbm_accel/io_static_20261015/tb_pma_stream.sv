`timescale 1ns/1fs
module tb_pma_stream;
 parameter integer MUT=0;
 reg fc=0,pc=0,rst_n=0;
 // Actual declared ratio: coded FEC period17ns, physical period16ns.
 // At 1.2GHz physical this means 1.1294117647GHz FEC, NOT 1.2GHz.
 always #8.5 fc=~fc;
 real phase=0.0,ppm=0.0;integer words=4096;
 initial begin
  if($value$plusargs("phase=%f",phase))begin end
  if($value$plusargs("ppm=%f",ppm))begin end
  if($value$plusargs("words=%d",words))begin end
  #(phase);forever #(8.0*(1.0+ppm/1000000.0))pc=~pc;
 end
 integer f=0,p=0,checked=0;
 reg ws=0,ps=0,ds=0,rs=0;
 reg [543:0] d=0;
 wire [511:0] pins;wire pv;
 wire [543:0] q;wire qv,wf,rf,dwf,drf;
 function automatic [543:0] pattern(input integer n);
  integer k;begin for(k=0;k<544;k=k+1)pattern[k]=((n*71+k*13)>>(k%17))&1;pattern[31:0]=n;end
 endfunction
 ot_hbm_pma_stream_gearbox #(.MUT(MUT==1?1:0)) tx(fc,pc,rst_n,ws,ps,d,1'b1,pins,pv,wf,rf);
 ot_hbm_pma_stream_gearbox #(.WI(512),.WO(544)) rx(pc,fc,rst_n,ds,rs,pins,pv,q,qv,dwf,drf);
 always @(negedge fc)begin d=pattern(f+1);ws=(f+1==16);rs=(f+1==29);end
 always @(negedge pc)begin ps=(p+1==(MUT==2?16:23));ds=(p+1==24);end
 always @(posedge pc)p=p+1;
 always @(posedge fc)begin
  f=f+1;#0.000001;
  if(rst_n && (wf||rf||dwf||drf))$fatal(1,"ownership fault f%0d",f);
  if(f>=29)begin
   if(!qv || q!==pattern(f-13))$fatal(1,"coded bit mismatch f%0d",f);
   checked=checked+1;
  end
  if(checked==words)begin $display("PASS STREAM PMA544->512->544 exact%0d words, all544 bits, 16/17 ratio phase%f ppm%f",checked,phase,ppm);$finish;end
 end
 initial begin #100;rst_n=1;end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
