`timescale 1ns/1ps
module tb_qkd_host_class_plane;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg rx_v=0;reg[527:0]rx_d=0;wire rx_cr;
 wire host_v,ctrl_v,ing_v;wire[511:0]host_d,ctrl_d,ing_d;wire[1:0]ing_cls;
 reg host_cr=0,ctrl_cr=0;reg[4:0]ing_crn=0;wire[23:0]credit_return,peer_credit;wire r_fault;
 qkd_host_rx_class #(.MUT(MUT==1),.STRAPPED(1))rx(.die_id(3'd0),.ck(ck),.rst_n(rst_n),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),
 .host_v(host_v),.host_d(host_d),.host_cr(host_cr),.ctrl_v(ctrl_v),.ctrl_d(ctrl_d),.ctrl_cr(ctrl_cr),
 .ing_v(ing_v),.ing_cls(ing_cls),.ing_d(ing_d),.ing_crn(ing_crn),.credit_return(credit_return),.peer_credit(peer_credit),.fault(r_fault));
 reg th_v=0,tc_v=0,ti_v=0;reg[511:0]th_d=0,tc_d=0;reg[63:0]ti_d=0;
 wire th_cr,tc_cr,ti_cr;reg[23:0]ret=0,peer=0;reg irq=0,tx_cr=0;wire tx_v,t_fault;wire[527:0]tx_d;
 qkd_host_tx_class #(.MUT(MUT==2))tx(.ck(ck),.rst_n(rst_n),.host_v(th_v),.host_d(th_d),.host_cr(th_cr),
 .ctrl_v(tc_v),.ctrl_d(tc_d),.ctrl_cr(tc_cr),.ing_v(ti_v),.ing_d(ti_d),.ing_cr(ti_cr),
 .credit_return(ret),.peer_credit(peer),.irq(irq),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.fault(t_fault));
 integer checks=0,ridx=0,phy_pending=0,total=0,counts[0:7];reg allow=0;
 reg[511:0]expected[0:31];reg[3:0]classes[0:31];
 function[511:0]pat(input integer k);begin for(integer j=0;j<16;j++)pat[j*32+:32]=32'(k)*32'h9e3779b9+32'(j)*32'h1234567;end endfunction
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 task tick;begin @(posedge ck);#1;end endtask
 task send(input[3:0]cls,input[511:0]d);begin expected[ridx]=d;classes[ridx]=cls;ridx++;
 @(negedge ck);rx_v=1;rx_d={cls,12'd0,d};@(negedge ck);rx_v=0;end endtask
 integer received=0;integer expected_ing_class;
 always @(posedge ck)if(rst_n)begin
  host_cr<=host_v;ctrl_cr<=ctrl_v;ing_crn<=5'(ing_v);
  if(host_v||ctrl_v||ing_v)begin
   check((host_v&&classes[received]==0)||(ctrl_v&&classes[received]==1)||
    (ing_v&&classes[received]>=2&&classes[received]<=4),"RX class exact");
   check((host_v?host_d:ctrl_v?ctrl_d:ing_d)==expected[received],"RX512 exact all bits");
   if(ing_v)check(ing_cls==classes[received]-2,"original ingest class preserved");received++;
  end
  tx_cr<=0;
  if(tx_v)begin
   integer cls,n;
   cls=tx_d[527:524];n=counts[cls];counts[cls]++;total++;phy_pending++;
   check(tx_d[523:512]==0,"TX reserved header exact");
   case(cls)
    0:check(tx_d[511:0]==pat(n+100),"HOST TX512 exact");
    1:check(tx_d[511:0]==pat(n+200),"CTRL TX512 exact");
    5:check(tx_d[511:64]==0&&tx_d[63:0]==64'(n+300),"INGEST completion exact");
    6:check(tx_d[511:1]==0&&tx_d[0]==irq,"IRQ level exact");
    7:check(tx_d[23:0]==24'h100404,"credit counters exact");
    default:$fatal(1,"bad output class");
   endcase
  end
  if(allow&&phy_pending!=0)begin tx_cr<=1;phy_pending--;end
 end
 initial begin
  for(integer j=0;j<8;j++)counts[j]=0;
  repeat(4)tick();rst_n=1;repeat(4)tick();
  send(0,pat(1));send(1,pat(2));send(2,pat(3));send(3,pat(4));send(4,pat(5));repeat(10)tick();
  check(received==5&&!r_fault,"full native ingress classes");
  // Original adapter physical queue4 stops TX independently of peer class windows.
  @(negedge ck);for(integer j=0;j<4;j++)begin th_v=1;tc_v=1;ti_v=1;th_d=pat(j+100);tc_d=pat(j+200);ti_d=j+300;@(negedge ck);end
  th_v=0;tc_v=0;ti_v=0;repeat(12)tick();check(total==4&&!t_fault,"physical credit stop");
  allow=1;repeat(70)tick();check(counts[0]==4&&counts[1]==4&&counts[5]==4&&!t_fault,"all three independent queues complete");
  // Capacity-free reports are a separate class, not application writes.
  @(negedge ck);ret=24'h100404;@(negedge ck);ret=0;repeat(12)tick();check(counts[7]==1,"capacity returned");
  irq=1;repeat(12)tick();check(counts[6]==1&&!t_fault,"IRQ event delivery");
  // Peer returned class credits reopen HOST while other class windows remain zero.
  @(negedge ck);peer=24'h000004;@(negedge ck);peer=0;repeat(5)tick();
  send(7,512'h040404);repeat(8)tick();check(peer_credit==0&&!r_fault,"credit packet consumed once");
  // Reserved upper class bits fail closed.
  @(negedge ck);rx_v=1;rx_d={4'd0,12'd1,512'd0};@(negedge ck);rx_v=0;repeat(5)tick();check(r_fault,"invalid header rejected");
  $display("PASS HOST_CLASS_PLANE checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
