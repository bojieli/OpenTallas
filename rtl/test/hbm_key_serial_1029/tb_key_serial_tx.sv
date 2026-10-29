`timescale 1ps/1fs
module tb_key_serial_tx;
 reg clk=0;always #416.5 clk=~clk;
 reg rst_n=0,clear=0,iv=0,pv=0,rv=0,lv=0;
 reg[2:0]base=0;reg[1:0]lane=0;reg[7:0]row=0,pi=0,ri=0;
 reg[1098:0]line=0;reg[4395:0]parallel=0;
 wire[4395:0]gold,actual;wire gf,bf,af,loaded;
 ot_hnx_idxn_keybuf_sliced_np4 #(.NP(4)) refbuf(.clk(clk),.rst_n(rst_n),.clear(clear),.pbase(base),
 .live_v(lv),.live_index(row),.key_in(parallel),.pre_v(pv),.pre_index(pi),.replay_v(rv),.replay_index(ri),.key_out(gold),.fault(gf));
 reg[4395:0]source_packets;
 wire[1111:0]tx;wire txfault;
 always @*begin
  source_packets=0;
  source_packets[int'(lane)*1099+:1099]={line[0],line[10:1],line[1098:11]};
  if(mut==6&&row==8'd3&&lane==2'd0)source_packets[2*1099+1098]=1;
 end
 ot_hnx_idxn_key_serial_tx sender(.clk(clk),.rst_n(rst_n),.strap_lane_base(base),.slot_v(iv),.slot_lane(lane),.slot_row(row),.slot_cohort(base[2]),.source_packets(source_packets),.tx(tx),.fault(txfault));
 assign af=bf|txfault;
 ot_hnx_idxn_keybuf_serial_np4 dut(.clk(clk),.rst_n(rst_n),.clear(clear),.strap_lane_base(base),
 .ingest_v(tx[1111]),.ingest_lane(tx[1100:1099]),.ingest_index(tx[1109:1102]),.ingest_line(tx[1098:0]),.pre_v(pv),.pre_index(pi),
 .replay_v(rv),.replay_index(ri),.key_out(actual),.fault(bf),.loaded(loaded));
 function automatic[1098:0] value(input integer r,input integer p,input integer epoch);
 reg[1098:0]v;reg[31:0]x;
 begin
  x=32'hf31a91e1^(32'(r)*32'h01010101)^(32'(p)*32'h71e315d7)^(32'(epoch)*32'h91f3a517);v=0;
  for(integer j=0;j<1088;j=j+32)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);v[11+j+:32]=x;end
  v[10:1]=10'(p*128+r);v[0]=1;return v;
 end
 endfunction
 integer mut=0,checks=0;
 task automatic replay(input integer a,input bit next);
 begin
  @(negedge clk);pv=1;pi=8'(a);rv=0;
  @(posedge clk);#1;
  @(negedge clk);pv=0;rv=1;ri=8'(a);#1;
  if(gold!==actual)$fatal(1,"SERIAL_DATA_MUTANT_CHECK a=%0d base=%0d",a,base);
  checks=checks+4396;
  @(posedge clk);#1;
  if(gf||af)$fatal(1,"SERIAL_FAULT a=%0d gf=%b af=%b",a,gf,af);
 end
 endtask
 initial begin
  void'($value$plusargs("MUT=%d",mut));
  for(integer h=0;h<2;h=h+1)begin
   @(negedge clk);rst_n=0;iv=0;pv=0;rv=0;lv=0;clear=0;base=3'(h*4);
   repeat(3)@(posedge clk);
   @(negedge clk);rst_n=1;clear=1;
   @(posedge clk);#1;
   for(integer a=0;a<171;a=a+1)begin
    for(integer p=0;p<4;p=p+1)parallel[p*1099+:1099]=value(a,h*4+p,h);
    for(integer p=0;p<4;p=p+1)begin
     @(negedge clk);clear=0;iv=1;lane=2'(p);row=8'(a);line=parallel[p*1099+:1099];lv=(p==3);
     if(a==3&&p==1&&mut==1)line[1]=~line[1];
     if(a==3&&p==2&&mut==2)iv=0;
     if(a==3&&p==0&&mut==3)lane=1;
     if(a==3&&p==0&&mut==4)begin pv=1;pi=0;end
     if(a==3&&p==1&&mut==5)line[1000]=~line[1000];
     @(posedge clk);#1;
     if(((mut>=1&&mut<=4)||mut==6)&&af)begin $display("SERIAL_MUTANT_CAUGHT mut=%0d row=%0d lane=%0d",mut,a,p);$finish;#1;$fatal(1,"finish did not terminate");end
     if(mut==0&&(af||gf))$fatal(1,"SERIAL_PREFILL_FAULT row=%0d lane=%0d",a,p);
    end
   end
   @(negedge clk);iv=0;lv=0;pv=0;rv=0;
   @(posedge clk);#1;
   if(!loaded)$fatal(1,"SERIAL_NOT_LOADED");
   for(integer a=0;a<171;a=a+1)replay(a,0);
   for(integer a=170;a>=0;a=a-1)replay(a,0);
  end
  if(mut!=0)$fatal(1,"SERIAL_MUTANT_MISSED mut=%0d",mut);
  $display("KEY_SERIAL_TX_PASS payload_checks=%0d rows=171 lanes=4 bases=0,4 SRAM=ACTUAL period_ps=833",checks);$finish;
 end
endmodule
