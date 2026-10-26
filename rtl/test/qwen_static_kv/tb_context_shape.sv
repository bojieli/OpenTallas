`timescale 1ns/1ps
module tb_context_shape;
 parameter integer MUT=0;
 reg [13:0] t;reg [1:0] s;reg [2:0] g;reg v;reg [8:0] o;
 wire [8:0] count;wire [7:0] k0;wire kb;wire [9:0] sec;wire last,bad;
 qkd_kv_context_shape #(.MUT(MUT))dut(t,s,g,v,o,count,k0,kb,sec,last,bad);
 string path;integer f,rc,ti,si,gi,vi,oi,ni,seci,n=0;
 initial begin
 if(!$value$plusargs("CASES=%s",path))$fatal(1,"missing expected cases");
 f=$fopen(path,"r");if(!f)$fatal(1,"missing cases file");
 while(!$feof(f))begin
 rc=$fscanf(f,"%d %d %d %d %d %d %d\n",ti,si,gi,vi,oi,ni,seci);
 if(rc==7)begin
 t=14'(ti);s=2'(si);g=3'(gi);v=1'(vi);o=9'(oi);#1;
 if(count!==9'(ni)||(ni!=0&&sec!==10'(seci))||last!==(oi+1==ni)||bad!==(oi>=ni))
 $fatal(1,"FAIL context shape T%0d s%0d g%0d v%0d o%0d count%0d/%0d sec%0d/%0d",ti,si,gi,vi,oi,count,ni,sec,seci);
 n++;
 end else if(rc!=-1)$fatal(1,"bad case row");
 end
 $display("PASS context shape %0d actual hardware ordinal/count/end vectors",n);$finish;
 end
endmodule
