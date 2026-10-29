`timescale 1ps/1fs
module tb_key_serial_chain;
 reg clk=0;always #416.5 clk=~clk;
 reg rst=0,clear=0,pv=0,rv=0,lv=0;reg[2:0]base=0;
 reg[7:0]pi=0,ri=0,grow=0;reg[4395:0]goldin=0;
 reg[3:0]iv=0;reg[7:0]rows[0:3];reg[1098:0]packets[0:3];
 wire[1111:0]rail[0:3];wire[3:0]nf;wire[4395:0]gold,actual;wire gf,df,loaded;
 ot_hnx_idxn_key_serial_seed seed(clk,rst,iv[0],base,rows[0],base[2],packets[0],rail[0],nf[0]);
 for(genvar p=1;p<4;p=p+1)begin:g
  ot_hnx_idxn_key_serial_merge node(clk,rst,rail[p-1],iv[p],base+3'(p),rows[p],base[2],packets[p],rail[p],nf[p]);
 end
 ot_hnx_idxn_keybuf_serial_np4 buf1(.clk(clk),.rst_n(rst),.clear(clear),.strap_lane_base(base),
 .ingest_v(rail[3][1111]),.ingest_lane(rail[3][1100:1099]),.ingest_index(rail[3][1109:1102]),.ingest_line(rail[3][1098:0]),
 .pre_v(pv),.pre_index(pi),.replay_v(rv),.replay_index(ri),.key_out(actual),.fault(df),.loaded(loaded));
 ot_hnx_idxn_keybuf_sliced_np4 ref1(.clk(clk),.rst_n(rst),.clear(clear),.pbase(base),
 .live_v(lv),.live_index(grow),.key_in(goldin),.pre_v(pv),.pre_index(pi),.replay_v(rv),.replay_index(ri),.key_out(gold),.fault(gf));
 function automatic[1098:0] value(input integer r,input integer p,input integer epoch);
 reg[1098:0]v;reg[31:0]x;
 begin
  x=32'hf31a91e1^(32'(r)*32'h01010101)^(32'(p)*32'h71e315d7)^(32'(epoch)*32'h91f3a517);v=0;
  for(integer j=0;j<1088;j=j+32)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);v[11+j+:32]=x;end
  v[10:1]=10'(p*128+r);v[0]=1;return v;
 end
 endfunction
 integer mut=0,checks=0,r;reg[1098:0]x;
 initial begin
  void'($value$plusargs("MUT=%d",mut));
  for(integer h=0;h<2;h=h+1)begin
   @(negedge clk);rst=0;iv=0;lv=0;pv=0;rv=0;clear=0;base=3'(h*4);
   repeat(4)@(posedge clk);@(negedge clk);rst=1;clear=1;
   @(posedge clk);#1;
   for(integer t=0;t<695;t=t+1)begin
    @(negedge clk);clear=0;iv=0;lv=0;
    for(integer p=0;p<4;p=p+1)begin
     r=(t-2*p)/4;
     if(t>=2*p&&(t-2*p)%4==0&&r<171)begin
      iv[p]=1;rows[p]=8'(r);x=value(r,h*4+p,h);packets[p]={x[0],x[10:1],x[1098:11]};
      if(mut==1&&r==3&&p==2)packets[p][1000]=~packets[p][1000];
      if(mut==2&&r==3&&p==1)packets[p][1088]=~packets[p][1088];
      if(mut==3&&r==3&&p==2)iv[p]=0;
      if(mut==4&&r==3&&p==3)iv[p]=0;
     end
    end
    if(mut==4&&t==17)begin iv[3]=1;rows[3]=3;x=value(3,h*4+3,h);packets[3]={x[0],x[10:1],x[1098:11]};end
    if(t>=7&&(t-7)%4==0&&(t-7)/4<171)begin
     r=(t-7)/4;grow=8'(r);lv=1;
     for(integer p=0;p<4;p=p+1)goldin[p*1099+:1099]=value(r,h*4+p,h);
    end
    @(posedge clk);#1;
    if(mut>=2&&(df||(|nf)))begin $display("KEY_CHAIN_CONTROL_CAUGHT mut=%0d t=%0d",mut,t);$finish;#1;$fatal(1,"finish did not terminate");end
    if(mut==0&&(df||gf||(|nf)))$fatal(1,"KEY_CHAIN_PREFILL t=%0d df=%b nf=%b",t,df,nf);
   end
   @(negedge clk);iv=0;lv=0;
   if(!loaded)$fatal(1,"KEY_CHAIN_NOT_LOADED");
   for(integer a=0;a<171;a=a+1)begin
    @(negedge clk);pv=1;pi=8'(a);rv=0;@(posedge clk);#1;
    @(negedge clk);pv=0;rv=1;ri=8'(a);#1;
    if(actual!==gold)$fatal(1,"KEY_CHAIN_PAYLOAD a=%0d base=%0d",a,base);
    checks=checks+4396;
    @(posedge clk);#1;if(df||gf||(|nf))$fatal(1,"KEY_CHAIN_REPLAY");
   end
  end
  if(mut!=0)$fatal(1,"KEY_CHAIN_MUTANT_MISSED");
  $display("KEY_CHAIN_PASS payload_checks=%0d rows=171 lanes=4 bases=0,4 seed=1 merge=3 SRAM=ACTUAL period_ps=833",checks);$finish;
 end
endmodule
