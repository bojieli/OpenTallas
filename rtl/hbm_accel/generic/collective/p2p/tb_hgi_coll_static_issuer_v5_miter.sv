`timescale 1ns/1ps
// H-NETLIST/COLL-CTL 1045: every-edge miter of ot_hgi_coll_static_issuer_v5 against the original
// ot_hgi_coll_static_issuer over randomized programmes: random row sets, banks and metadata through the real cfg37
// protocol; loop ids drawn from a small set (several loop-ending rows share a lid, nested loops), counts
// 0/1/2/3/small/0x80000000/0xffffffff, halts, missing rows (fetch faults), restarts without reset (loops cleared by
// start), stray cfg / start while busy (faults). Every port compared every edge: busy, done, fault, uop_v, uop,
// iteration, uop_pc. +SEED=n +PROGS=n. -DMUT_RELOAD builds the v5 issuer with an off-by-one loop decision.
module tb_hgi_coll_static_issuer_v5_miter;
`ifdef MUT_RELOAD
 localparam integer MR=1;
`else
 localparam integer MR=0;
`endif
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [36:0] cfg=0;reg start=0;reg [5:0] start_pc=0;
 wire rb,rd,rf,rv,nb,nd,nf,nv;wire [1535:0] ru,nu;wire [31:0] ri,ni;wire [5:0] rp,np;
 ot_hgi_coll_static_issuer ref_i(.clk_control(clk),.clk_mem({3{clk}}),.rst_n(rst_n),.cfg(cfg),.start(start),
  .start_pc(start_pc),.busy(rb),.done(rd),.fault(rf),.uop_v(rv),.uop(ru),.iteration(ri),.uop_pc(rp));
 ot_hgi_coll_static_issuer_v5 #(.MUT_RELOAD(MR)) dut(.clk_control(clk),.clk_mem({3{clk}}),.rst_n(rst_n),.cfg(cfg),
  .start(start),.start_pc(start_pc),.busy(nb),.done(nd),.fault(nf),.uop_v(nv),.uop(nu),.iteration(ni),.uop_pc(np));
 integer checks=0,mism=0,seed=1,progs=300,loops_taken=0,halts=0,faults=0,iters_max=0;
 always @(negedge clk) if(rst_n)begin
  checks=checks+1;
  if(rb!==nb||rd!==nd||rf!==nf||rv!==nv||ru!==nu||ri!==ni||rp!==np)begin
   mism=mism+1;
   if(mism<6)$display("MISMATCH t=%0t busy %b/%b done %b/%b fault %b/%b uop_v %b/%b it %0d/%0d pc %0d/%0d uop_eq %b",
     $time,rb,nb,rd,nd,rf,nf,rv,nv,ri,ni,rp,np,ru===nu);
  end
  if(rv && ri>iters_max)iters_max=ri;
 end
 task automatic tick;begin @(posedge clk);#1;end endtask
 task automatic send(input [3:0] op,input [31:0] data);begin cfg={1'b1,op,data};tick;cfg=0;end endtask
 function automatic [31:0] rcount(input integer k);
  case(k%9)
   0:rcount=0;1:rcount=1;2:rcount=2;3:rcount=3;4:rcount=4+($urandom%13);
   5:rcount=32'h8000_0000;6:rcount=32'hffff_ffff;7:rcount=2+($urandom%5);default:rcount=0;
  endcase
 endfunction
 integer p,r,b,f,nr,t,w,lidset;reg [63:0] meta;reg [31:0] cnt;
 initial begin
  if(!$value$plusargs("SEED=%d",seed))seed=1;
  if(!$value$plusargs("PROGS=%d",progs))progs=300;
  void'($urandom(seed));
  for(p=0;p<progs;p=p+1)begin
   rst_n=0;cfg=0;start=0;repeat(3)tick;rst_n=1;tick;
   nr=1+($urandom%14);lidset=1+($urandom%4);
   for(r=0;r<nr;r=r+1)begin
    for(b=0;b<3;b=b+1)if(($urandom%60)!=0)begin
     send(0,{24'd0,2'(b),6'(r)});
     for(f=0;f<16;f=f+1)send(1,$urandom);
    end
    cnt=rcount($urandom);
    meta=0;meta[5:0]=$urandom%nr;meta[11:6]=$urandom%nr;meta[43:12]=cnt;
    meta[44]=(r==nr-1)?(($urandom%3)!=0):(($urandom%7)==0);meta[50:45]=$urandom%lidset;
    if(($urandom%5)==0)meta[50:45]=6'(r);
    if(($urandom%50)!=0)begin send(0,{24'd0,2'd0,6'(r)});send(2,meta[31:0]);send(3,meta[63:32]);end
   end
   for(w=0;w<3;w=w+1)begin
    start_pc=$urandom%nr;start=1;tick;start=0;start_pc=0;
    for(t=0;t<400;t=t+1)begin
     if(($urandom%300)==0)begin start=1;start_pc=$urandom%nr;end
     if(($urandom%400)==0)cfg={1'b1,4'd2,32'h1234};
     tick;start=0;cfg=0;
     if(rv && ri!=0)loops_taken=loops_taken+1;
     if(rd)halts=halts+1;
    end
    repeat(4)tick;
   end
   if(rf)faults=faults+1;
  end
  if(mism==0)$display("ISSUER_V5_MITER PASS seed%0d progs%0d checks%0d iter_nonzero%0d max_iter%0d halts%0d faulted_progs%0d",
    seed,progs,checks,loops_taken,iters_max,halts,faults);
  else begin $display("ISSUER_V5_MITER FAIL mismatches%0d checks%0d",mism,checks);$fatal(1,"miter mismatch");end
  $finish;
 end
endmodule
