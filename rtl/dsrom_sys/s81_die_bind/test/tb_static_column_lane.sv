`timescale 1ns/1ps
// PHW10 (main 6e672546b): f_bus 1,634 b, cc = {np 3, ph 10, cfg, go} (S-BIND 2026-10-15 bench refresh)
module tb_static_column_lane;
 parameter integer PHASE=2, STAGES=2;
 reg wc=0,rc=0,wr=0,rr=0;
 always #5 wc=~wc;initial begin #(PHASE);forever #5 rc=~rc;end
 reg [1633:0] f_bus=0; wire [1100:0] xw,xe,lane;wire ef,fault;
 wire [282:0] x0;wire [265:0] x1;wire [14:0] cc;wire [1067:0] bf;
 dsfd_pq_lx enc(.ck(wc),.rst(wr),.f_bus(f_bus),.f_fault(1'b0),.xws(3'b000),.xes(3'b000),.xw(xw),.xe(xe),.f_fault_c(ef));
 ot_s81_static_column_lane #(.STAGES(STAGES)) col(wc,wr,xw,rc,rr,lane,x0,x1,cc,bf,fault);
 reg [1100:0] gold[0:4095];reg [1067:0] bf_gold[0:4095];reg[1100:0] prev=0,nextword;reg[1067:0] xb;
 integer wi=0,ri=0,j,k,mode,checked=0;reg[31:0] rng=32'h81ad4521;
 always @(negedge wc) if(wr)begin
   for(k=0;k<1634;k=k+1)begin rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]}; f_bus[k]=rng[0];end
   mode=wi%6;f_bus[1633]=0;f_bus[1619]=0;f_bus[1618]=0;f_bus[1615]=0;f_bus[1063]=0;
   case(mode)0,1: f_bus[1063]=1;2:f_bus[1618]=1;3:f_bus[1615]=1;4:begin f_bus[1633]=1;f_bus[1619]=1;end endcase
 end
 always @(posedge wc)begin
   if(!wr) begin wi=0;prev=0;end
   else begin
     gold[wi]=prev;bf_gold[wi]={prev[549:284],prev[266:1],prev[1100:565]};
     xb={f_bus[1023:0],f_bus[1055:1024],f_bus[1059:1056],f_bus[1062:1060],f_bus[1063],f_bus[1066:1064],f_bus[1618]};
     if(f_bus[1063]||f_bus[1618])nextword={xb[535:0],f_bus[1622:1620],f_bus[1632:1623],f_bus[1633],f_bus[1619],xb[1067:802],17'd0,xb[801:536],1'b1};
     else nextword={536'd0,f_bus[1622:1620],f_bus[1632:1623],f_bus[1633],f_bus[1619],f_bus[1079:1070],f_bus[1335:1080],f_bus[1615],f_bus[1603:1602],f_bus[1069:1067],f_bus[1614:1607],f_bus[1606:1604],f_bus[1345:1336],f_bus[1601:1346],(f_bus[1615]|f_bus[1619]|f_bus[1633])};
     prev=nextword;wi=wi+1;
   end
 end
 always @(posedge rc)if(!rr)ri=0;else begin
   #1;j=ri-4-STAGES;
   if(j>=0)begin
     if(lane!==gold[j] || bf!==bf_gold[j] || x0!==gold[j][283:1] || x1!==gold[j][549:284] || cc!==gold[j][564:550])$fatal(1,"composed mismatch r_edge%0d phase%0d",ri,PHASE);
     if(fault)$fatal(1,"unexpected epoch fault");checked=checked+1;
   end
   ri=ri+1;
 end
 initial begin
   #30;@(negedge wc);#1;wr=1;@(posedge wc);#0.1;rr=1;
   repeat(2000)@(negedge wc);
   #1;$display("STATIC_COLUMN_LANE PASS phase=%0d stages=%0d checked=%0d",PHASE,STAGES,checked);$finish;
 end
endmodule
