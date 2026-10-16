`timescale 1ns/1ps
module tb_context_front;
 parameter integer MUT=0;
 reg ck=0;always #0.512 ck=~ck;
 reg rn=0,we=0,kg=0,vg=0;reg[7:0]addr=0;reg[63:0]data=0;reg[13:0]T=1;
 wire[3:0]go;wire[2:0]nminus1;wire calfault,calidle;
 qkd_kv_context_front_cal #(.MUT(MUT==10?1:0))cal(ck,rn,we,addr,data,kg,vg,T,go,nminus1,calfault,calidle);
 reg[293:0]ci=0;wire[293:0]co;wire[15:0]ep;wire put,freed,hold,idle,ovf,gof;wire[15:0]stalls;wire[5:0]occupancy;
 qkd_kv_hbm_context_front #(.MUT(MUT==10?0:MUT))front(.pll_hbm(ck),.hrst(rn),.co_in(ci),.epoch_in(16'd711),.blk_go(go[0]),.blk_nminus1(nminus1),
 .co_out(co),.epoch_out(ep),.compiled_hbm_put(put),.blk_freed(freed),.hold(hold),.stall_edges(stalls),.occupancy(occupancy),.idle(idle),.fault_overflow(ovf),.fault_go(gof));
 integer expected[0:255];integer tick=0,origin=-99999,rel,n=0,seen=0,groups=0,blocks=0,frees=0,total=0,peak=0;
 integer f,rc,ti,si,gi,nk,nv,pass,sec;string path;
 function automatic[293:0]word(input integer sec);
 reg[293:0]w;begin w=0;w[0]=1;w[7:1]=7'(sec);w[11:9]=3'(sec>>7);for(integer j=0;j<8;j++)w[26+32*j+:32]=32'h00abc123^32'(sec*311+j*103);word=w;end
 endfunction
 task config_word(input integer ad,input integer value);
 begin we=1;addr=8'(ad);data=64'(value);@(negedge ck);we=0;repeat(3)@(negedge ck);end endtask
 initial begin
 if(!$value$plusargs("CASES=%s",path))$fatal(1,"missing cases");f=$fopen(path,"r");if(!f)$fatal(1,"case open");
 repeat(6)@(negedge ck);rn=1;repeat(5)@(negedge ck);
 config_word(2,32);config_word(4,511);config_word(5,511);
 while(!$feof(f))begin
 rc=$fscanf(f,"%d %d %d %d %d\n",ti,si,gi,nk,nv);if(rc!=5)$fatal(1,"bad header");T=14'(ti);config_word(0,(si<<3)|gi);
 for(pass=0;pass<2;pass++)begin
 n=pass==0?nk:nv;for(integer i=0;i<n;i++)begin rc=$fscanf(f,"%d ",sec);expected[i]=sec;end
 seen=0;blocks=0;frees=0;kg=pass==0;vg=pass==1;@(negedge ck);kg=0;vg=0;
 repeat(330)@(negedge ck);
 if(seen!=n||blocks!=(n+7)/8||frees!=(n+7)/8||!idle||!calidle)$fatal(1,"FAIL context front count T%0d s%0d g%0d pass%0d seen%0d/%0d blocks%0d frees%0d idle%0b",ti,si,gi,pass,seen,n,blocks,frees,idle);
 groups++;
 end
 end
 $display("PASS context front %0d passes %0d actual words, peak%0d, zero dummy reads/hold/stalls",groups,total,peak);$finish;
 end
 always @(negedge ck)begin
 ci=0;if(rel>=7&&rel<7+n)ci=word(expected[rel-7]);
 end
 always @(posedge ck)begin
 tick++;if(kg||vg)origin=tick;rel=tick-origin;#0.001;
 if(rn)begin
 if(put)begin
 if(seen>=n || co!==word(expected[seen]) || ep!=711 || rel!=34+seen)$fatal(1,"FAIL context front data/timeline pass%0d word%0d edge%0d expected%0d",pass,seen,rel,34+seen);
 seen++;total++;
 end
 if(go[0])begin if(nminus1!==3'((blocks+1)*8>n?n-8*blocks-1:7))$fatal(1,"FAIL context front compiled block length");blocks++;end
 if(freed)frees++;
 if(occupancy>peak)peak=occupancy;
 if(calfault||ovf||gof||hold||stalls)$fatal(1,"FAIL context front fault/hold cal%0b ov%0b go%0b hold%0b stalls%0d",calfault,ovf,gof,hold,stalls);
 end
 end
endmodule
