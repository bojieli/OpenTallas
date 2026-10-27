`timescale 1ns/100fs
module tb_idxnet_tx_contract;
reg ck=0;always #0.4165 ck=~ck;
reg rn=0;reg[275:0]vi=0,vo=0;wire[275:0]lo;wire[15:0]st;
dsdv_idx_tx_n32 #(.D(8192),.IB(64),.SRAM_MACRO(1))dut(.ck(ck),.rst(rn),.vi(vi),.vo(vo),.lo(lo),.st(st));
integer cycle=0,poison=0,lane=2,headers=0,beats=0;reg[275:0]a;reg[185:0]p;reg[511:0]w;
always@(posedge ck)begin
 #0.001;cycle++;
 if(lo[0])begin
  if(lo[7]&&lo[19:16]==1)begin
   headers++;$display("IDXNET_TX_HEADER physical_lane%0d quarter%0d",lo[5:4],lo[51:50]);
   if(lo[5:4]!==2'(lane)||lo[51:50]!==2'(lane))$fatal(1,"TX lane/qslot encoding unexpected");
  end
  if(!lo[6]&&!lo[7]&&lo[19:16]==2)begin
   beats++;
   for(integer j=0;j<16;j++)if(lo[20+16*j+:16]!==16'h3f80)
    $fatal(1,"IDXNET_SCORE_ALIAS position%0d expected3f80 got%h poison%0d fault%0d",j,lo[20+16*j+:16],poison,st[0]);
  end
 end
end
task drive(input[275:0]i,input[275:0]o);begin @(negedge ck);vi=i;vo=o;end endtask
task idle(input integer n);begin repeat(n)drive(0,0);end endtask
task scores(input integer base,input[15:0]code,input[7:0]tag,input integer l);
 begin
 a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(l);a[7]=1;a[19:16]=1;a[15:8]=tag;a[39:20]=20'(base);drive(a,0);idle(3);
 a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(l);a[19:16]=2;a[15:8]=tag;
 for(integer j=0;j<16;j++)a[20+16*j+:16]=code;drive(a,0);
 a=0;a[0]=1;a[3:1]=4;a[5:4]=2'(l);a[6]=1;a[35:20]=16'hffff;drive(a,0);idle(8);
 end
endtask
task packet(input[511:0]word);begin
 a=0;a[0]=1;a[3:1]=5;a[275:20]=word[255:0];drive(0,a);
 a[6]=1;a[275:20]=word[511:256];drive(0,a);idle(2);
end endtask
initial begin
 if($value$plusargs("POISON=%d",poison))begin end
 if($value$plusargs("LANE=%d",lane))begin end
 idle(8);rn=1;idle(20);
 scores(0,16'h3f80,8'h11,0);
 if(poison)scores(131072,16'h4000,8'h22,1);
 p=0;p[7:0]=8'h5c;p[10:8]=2;p[20:16]=8;p[22:21]=2'(lane);p[30:23]=8'h77;p[40:31]=16;p[60:41]=0;p[68:61]=8'h45;p[84:69]=80;p[87:85]=4;p[99:88]=100;
 a=0;a[0]=1;a[21+:186]=p;drive(0,a);idle(8);
 w=0;w[511:508]=3;w[507:500]=8'h45;w[335:320]=16'hffff;
 for(integer j=0;j<16;j++)w[20*j+:20]=20'(j);packet(w);
 w=0;w[511:508]=4;w[507:500]=8'h45;packet(w);idle(800);
 if(headers!=1||beats!=1||st[0]||!st[3])$fatal(1,"IDXNET_TX_COVERAGE headers%0d beats%0d st%h",headers,beats,st);
 $display("IDXNET_TX_BASE PASS cycles%0d score_words16 lane%0d",cycle,lane);$finish;
end
endmodule
