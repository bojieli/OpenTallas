`timescale 1ns/1ps
// SQC-CB16b 2026-10-22: cycle-exact equivalence of the native-census leaf ot_qfd_xs_leaf_fo32 against the CLOSED w130
// leaf configuration ot_qfd_xs_leaf #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1), .BANK_PIPE(0)).
// Identical pins into both; EVERY output (write chain wo_*/co_*, answer q_v/q/q_bad) is compared on EVERY edge.
// Stimulus: seeded random writes (all d codes incl. 11, random w_off / wo / masks / epochs), clears, reads on both
// tiles at II 4 (incl. disabled elements, collisions and reads of cleared epochs), writes concurrent with reads.
module tb_qfd_xs_leaf_fo32;
 parameter integer MUT=0, GRP=8, NG=3, NQ=6, NOPS=4000, SEED=7;
 reg clk=0,rst_n=0;
 always #1 clk=~clk;
 reg w_v=0,w_ep=0,c_v=0,c_ep=0,r_v=0,r_t=0,r_ep=0;
 reg [5:0] w_off=0;
 reg [63:0] w_m=0;
 reg [1023:0] w_d=0;
 reg [71:0] w_ctl=0;
 reg [27:0] r_p=0;
 wire rv_,rep_,rcv,rcep,dv_,dep_,dcv,dcep,rqv,dqv,rqb,dqb;
 wire [5:0] roff,doff; wire [63:0] rm,dm,rq,dq; wire [1023:0] rd,dd_; wire [71:0] rctl,dctl;
 ot_qfd_xs_leaf #(.NCH(4),.READ_PIN_PIPE(1),.FILL_PIPE(1),.BANK_PIPE(0)) ref_leaf
  (.clk,.rst_n,.w_v,.w_ep,.w_off,.w_m,.w_d,.w_ctl,.c_v,.c_ep,
   .wo_v(rv_),.wo_ep(rep_),.wo_off(roff),.wo_m(rm),.wo_d(rd),.wo_ctl(rctl),.co_v(rcv),.co_ep(rcep),
   .r_v,.r_t,.r_ep,.r_p,.q_v(rqv),.q(rq),.q_bad(rqb));
 ot_qfd_xs_leaf_fo32 #(.GRP(GRP),.NG(NG),.NQ(NQ),.MUT(MUT)) dut
  (.clk,.rst_n,.w_v,.w_ep,.w_off,.w_m,.w_d,.w_ctl,.c_v,.c_ep,
   .wo_v(dv_),.wo_ep(dep_),.wo_off(doff),.wo_m(dm),.wo_d(dd_),.wo_ctl(dctl),.co_v(dcv),.co_ep(dcep),
   .r_v,.r_t,.r_ep,.r_p,.q_v(dqv),.q(dq),.q_bad(dqb));
 integer edges=0,answers=0,good=0,bad=0,errors=0;
 always @(negedge clk)if(rst_n)begin
  edges=edges+1;
  if({rv_,rep_,roff,rm,rd,rctl,rcv,rcep}!=={dv_,dep_,doff,dm,dd_,dctl,dcv,dcep})begin
    errors=errors+1; if(errors<5)$display("MISMATCH write chain edge=%0d",edges);
  end
  if({rqv,rq,rqb}!=={dqv,dq,dqb})begin
    errors=errors+1; if(errors<5)$display("MISMATCH answer edge=%0d ref=%b/%h/%b dut=%b/%h/%b",edges,rqv,rq,rqb,dqv,dq,dqb);
  end
  if(rqv)begin answers=answers+1; if(rqb)bad=bad+1; else good=good+1; end
 end
 task tick;begin @(negedge clk);#0.1;end endtask
 integer seed,i,l,t,j,ph;
 initial begin
  seed=SEED;
  repeat(3)tick();rst_n=1;
  // claim + fill both epochs of both tiles (d = 00, full mask)
  for(i=0;i<4;i=i+1)begin
   c_v=1;c_ep=i%2;tick();c_v=0;
   w_v=1;w_ep=i%2;w_m=~64'd0;w_off=0;w_ctl=0;w_ctl[9*(i/2)+8]=1;
   for(l=0;l<64;l=l+1)w_d[16*l+:16]=16'h1000+i*256+l;
   tick();w_v=0;tick();
  end
  for(i=0;i<NOPS;i=i+1)begin
   ph=i%4;
   // random write (about half the edges), random rotation / tile windows / d codes / masks
   w_v=($random(seed)%2==0);w_ep=$random(seed);w_off=$random(seed);
   w_m={$random(seed),$random(seed)};if($random(seed)%4==0)w_m=~64'd0;
   w_ctl={$random(seed),$random(seed),$random(seed)};
   for(l=0;l<32;l=l+1)w_d[32*l+:32]=$random(seed);
   c_v=($random(seed)%23==0);c_ep=$random(seed);
   // reads: a request on tile ph/2 every 4 edges (II 4 alternating -> each tile every 8), sometimes off-schedule
   r_v=(ph==0)||($random(seed)%17==0);r_t=(i/4)%2;if($random(seed)%13==0)r_t=~r_t;r_ep=$random(seed);
   for(j=0;j<4;j=j+1)begin r_p[7*j+:6]=$random(seed);r_p[7*j+6]=($random(seed)%5!=0);end
   tick();
  end
  w_v=0;c_v=0;r_v=0;repeat(16)tick();
  if(errors!=0)begin $display("FAIL errors=%0d edges=%0d answers=%0d",errors,edges,answers);$fatal(1,"FAIL fo32 leaf");end
  if(answers<NOPS/8 || good==0 || bad==0)begin $display("FAIL coverage answers=%0d good=%0d bad=%0d",answers,good,bad);$fatal(1,"FAIL coverage");end
  $display("PASS fo32 leaf equivalence edges=%0d answers=%0d good=%0d bad=%0d GRP=%0d NG=%0d NQ=%0d added_edges=0",edges,answers,good,bad,GRP,NG,NQ);
  $finish;
 end
endmodule
