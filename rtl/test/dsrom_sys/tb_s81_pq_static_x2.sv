`timescale 1ns/1ps
module tb_s81_pq_static_x2;
 reg ck=0; always #5 ck=~ck;
 reg rst=0; reg [1632:0] f_bus=0;reg f_fault=0;reg[2:0] xws=0,xes=0;
 wire[1100:0] xw,xe;wire fc;
 dsfd_pq_lx dut(.ck(ck),.rst(rst),.f_bus(f_bus),.f_fault(f_fault),.xws(xws),.xes(xes),.xw(xw),.xe(xe),.f_fault_c(fc));
 reg [1100:0] expword;reg[1067:0] xb;reg[564:0] lowword;reg[282:0] x0;reg[265:0] x1;reg[14:0] cc;
 reg expfault,sticky=0,collision;integer i,j,mode,qbeats=0,bbeats=0,cmds=0;reg[31:0] rng=32'h81cafe;
 function [31:0] step(input[31:0] x);begin step={x[30:0],x[31]^x[21]^x[1]^x[0]};end endfunction
 initial begin
  repeat(3) @(negedge ck);rst=1;
  for(i=0;i<20000;i=i+1)begin
   @(negedge ck);
   // Distinct pseudorandom data at every native broadcast position. Independent
   // decoder below uses the public native ordering, never internal DUT wires.
   for(j=0;j<1633;j=j+1)begin rng=step(rng);f_bus[j]=rng[0];end
   mode=i%10;f_bus[1632]=0;f_bus[1619]=0;f_bus[1618]=0;f_bus[1615]=0;f_bus[1063]=0;
   case(mode)
    0,1,2,3:begin f_bus[1063]=1;bbeats=bbeats+1;end
    4:begin f_bus[1618]=1;bbeats=bbeats+1;end
    5,6,7:begin f_bus[1615]=1;qbeats=qbeats+1;end
    8:begin f_bus[1632]=1;f_bus[1619]=1;cmds=cmds+1;end
    9:begin end
   endcase
   // Ready status varies even under consecutive full-rate words. Static mode
   // must be invariant to it, including permanent not-ready and not-live.
   xws=i%8;xes=(i+3)%8;f_fault=(i%991==0);
   // Exercise collision diagnostics only at the very end, after thousands of
   // no-ready full-rate transfers have proved no ready-induced sticky fault.
   if(i==19998)begin f_bus[1063]=1;f_bus[1615]=1;end
   cc={f_bus[1622:1620],1'b0,f_bus[1631:1623],f_bus[1632],f_bus[1619]};
   x0={f_bus[1615],f_bus[1603:1602],f_bus[1069:1067],f_bus[1614:1607],f_bus[1606:1604],f_bus[1345:1336],f_bus[1601:1346]};
   x1={f_bus[1079:1070],f_bus[1335:1080]};
   xb={f_bus[1023:0],f_bus[1055:1024],f_bus[1059:1056],f_bus[1062:1060],f_bus[1063],f_bus[1066:1064],f_bus[1618]};
   if(f_bus[1063]||f_bus[1618])begin lowword={cc,xb[1067:802],17'd0,xb[801:536],1'b1};expword={xb[535:0],lowword};end
   else expword={536'd0,cc,x1,x0,(f_bus[1615]|f_bus[1619]|f_bus[1632])};
   collision=(f_bus[1063]&&(f_bus[1615]||f_bus[1619]||f_bus[1632]))||(f_bus[1618]&&f_bus[1615]);
   expfault=f_fault|collision|sticky;if(collision)sticky=1;
   @(posedge ck);#1;
   if(xw!==expword||xe!==expword||fc!==expfault)begin $display("STATIC_X2 FAIL cycle=%0d mode=%0d fault=%0b/%0b",i,mode,fc,expfault);$fatal(1,"lane/fault mismatch");end
  end
  $display("STATIC_X2 PASS cycles=20000 compared_bits=44040000 bf=%0d q=%0d commands=%0d latency=1 ready_independent=1",bbeats,qbeats,cmds);$finish;
 end
endmodule
