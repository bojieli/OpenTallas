`timescale 1ns/1ps
module union_lane_tb;
 reg [1632:0] native_in;
 wire [1084:0] lane_tx;
 reg inject_bad=0;
 wire [1084:0] lane_rx=inject_bad ? (lane_tx | (1085'd3 << 23)) : lane_tx;
 wire [1632:0] native_out,bypass_out;
 wire protocol_fault,bypass_fault;
 ot_s81_pq_union_lane #(.ENABLE(1)) dut(.*);
 ot_s81_pq_union_lane bypass(.native_in(native_in),.lane_tx(),.lane_rx(lane_rx),
 .native_out(bypass_out),.protocol_fault(bypass_fault));
 reg cfg,go,gobf,qv,bv;
 reg [8:0] ph;
 reg [2:0] np,b,pos;
 reg [1:0] tag,sv;
 reg [7:0] p;
 reg [255:0] q0,q1;
 reg [9:0] e0,e1;
 reg [3:0] bsv;
 reg [31:0] u;
 reg [1023:0] d;
 wire ocfg,ogo,ogobf,oqv,obv;
 wire [8:0] oph;
 wire [2:0] onp,oqb,obfb,oqp,obfp;
 wire [1:0] otag,osv;
 wire [7:0] op;
 wire [255:0] oq0,oq1;
 wire [9:0] oe0,oe1;
 wire [3:0] obsv;
 wire [31:0] ou;
 wire [1023:0] od;
 assign {ocfg,oph,onp,ogo,ogobf,otag,oqv,op,oqb,osv,oq0,oe0,oq1,oe1,oqp,obfp,obv,obfb,obsv,ou,od}=native_out;
 integer i,j,checked=0;
 task pack;begin
 native_in={cfg,ph,np,go,gobf,tag,qv,p,b,sv,q0,e0,q1,e1,pos,pos,bv,b,bsv,u,d};end endtask
 initial begin
  for(i=0;i<6000;i=i+1)begin
   cfg=$random;ph=$random;np=$random;go=$random;gobf=$random;tag=$random;
   qv=(i%3==0);bv=(i%3==1);p=$random;b=$random;sv=$random;e0=$random;e1=$random;
   pos=$random;bsv=$random;u=$random;
   for(j=0;j<8;j=j+1)begin q0[32*j+:32]=$random;q1[32*j+:32]=$random;end
   for(j=0;j<32;j=j+1)d[32*j+:32]=$random;
   pack();#1;
   if(protocol_fault)$fatal(1,"legal packet rejected");
   if(bypass_out!==native_in || bypass_fault)$fatal(1,"default bypass changed native data");
   if({ocfg,oph,onp,ogo,ogobf,otag,oqv,obv,oqb,obfb,oqp,obfp}!==
      {cfg,ph,np,go,gobf,tag,qv,bv,b,b,pos,pos})$fatal(1,"fixed identity mismatch");
   if(qv && {op,osv,oq0,oe0,oq1,oe1}!=={p,sv,q0,e0,q1,e1})$fatal(1,"Q payload mismatch");
   if(bv && {obsv,ou,od}!=={bsv,u,d})$fatal(1,"BF payload mismatch");
   checked=checked+1;
  end
  qv=1;bv=1;pack();#1;
  if(!protocol_fault || lane_tx!==0)$fatal(1,"both-valid input was not rejected");
  qv=1;bv=0;pack();inject_bad=1;#1;
  if(!protocol_fault || native_out!==0)$fatal(1,"both-valid receive was not rejected");
  inject_bad=0;pack();native_in[1060]=~native_in[1060];#1;
  // Native low1024=d; next32=u; next4=bsv; next3=BF b. Alias corruption.
  if(!protocol_fault || lane_tx!==0)$fatal(1,"duplicate family identity corruption missed");
  $display("PASS W2 6000 packets:2000Q/2000BF/2000idle,full fixed identity,default bypass,both-valid andalias rejection");$finish;
 end
endmodule
