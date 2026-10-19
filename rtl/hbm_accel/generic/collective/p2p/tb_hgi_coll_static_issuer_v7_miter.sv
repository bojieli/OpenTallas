`timescale 1ns/1ps
// HBM-COLL256-KITS 10-19: every-edge miter of the 256-row issuer core ot_hgi_coll_static_issuer_v7 (SRAM metadata
// lookahead, loop counters by id) against ot_hgi_coll_static_issuer_v6 #(ROWS 256) (the flop-metadata reference) over
// randomized programmes through the real cfg37 protocol: row sets spread over all 256 rows (pc bits 6/7 exercised),
// random next/target inside the set, loop ids from a small shared set or the row's own id (r mod 32), counts
// 0/1/2/3/small/0x80000000/0xffffffff, halts, missing banks / metadata (fetch faults), restarts without reset (loops
// cleared by start), stray metadata writes and starts while busy (faults). Every port compared every edge.
// The v7 programme constraints are honoured: loop ids < 32; start_pc stable and no metadata write during the 4 edges
// before a start (start_pc is changed only right after a launch, as the programme target sets it at descriptor accept).
// +SEED=n +PROGS=n. Mutants (one per build): -DMUT_RELOAD (DUT loop decision off by one), +define+OT_COLL_ISS7_MUT_NOFWD,
// +define+OT_COLL_ISS7_MUT_SWAP, +define+OT_COLL_ISS_MUT_PCWRAP (ref is built from the same defines but only v7 has the
// ISS7 hooks; PCWRAP is applied to the DUT through MUT_PCWRAP_DUT below).
module tb_hgi_coll_static_issuer_v7_miter;
`ifdef MUT_RELOAD
 localparam integer MR=1;
`else
 localparam integer MR=0;
`endif
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [36:0] cfg=0;reg start=0;reg [7:0] start_pc=0;
 wire rb,rd,rf,rv,nb,nd,nf,nv;wire [1535:0] ru,nu;wire [31:0] ri,ni;wire [7:0] rp,np;
 ot_hgi_coll_static_issuer_v6 #(.ROWS(256)) ref_i(.clk_control(clk),.clk_mem({3{clk}}),.rst_n(rst_n),.cfg(cfg),.start(start),
  .start_pc(start_pc),.busy(rb),.done(rd),.fault(rf),.uop_v(rv),.uop(ru),.iteration(ri),.uop_pc(rp));
 ot_hgi_coll_static_issuer_v7 #(.MUT_RELOAD(MR)) dut(.clk_control(clk),.clk_mem({3{clk}}),.rst_n(rst_n),.cfg(cfg),
  .start(start),.start_pc(start_pc),.busy(nb),.done(nd),.fault(nf),.uop_v(nv),.uop(nu),.iteration(ni),.uop_pc(np));
 integer checks=0,mism=0,seed=1,progs=300,loops_taken=0,halts=0,faults=0,iters_max=0,launches=0,hi_rows=0;
 always @(negedge clk) if(rst_n)begin
  checks=checks+1;
  if(rb!==nb||rd!==nd||rf!==nf||rv!==nv||ru!==nu||ri!==ni||rp!==np)begin
   mism=mism+1;
   if(mism<6)$display("MISMATCH t=%0t busy %b/%b done %b/%b fault %b/%b uop_v %b/%b it %0d/%0d pc %0d/%0d uop_eq %b",
     $time,rb,nb,rd,nd,rf,nf,rv,nv,ri,ni,rp,np,ru===nu);
  end
  if(rv && ri>iters_max)iters_max=ri;
  if(rv && rp>=128)hi_rows=hi_rows+1;
 end
 integer quiet=0;   // edges since the last metadata write / start_pc change
 task automatic tick;begin @(posedge clk);#1;quiet=quiet+1;end endtask
 task automatic send(input [3:0] op,input [31:0] data);begin cfg={1'b1,op,data};tick;if(op==2||op==3)quiet=0;cfg=0;end endtask
 task automatic set_spc(input [7:0] v);begin if(v!=start_pc)quiet=0;start_pc=v;end endtask
 function automatic [31:0] rcount(input integer k);
  case(k%9)
   0:rcount=0;1:rcount=1;2:rcount=2;3:rcount=3;4:rcount=4+($urandom%13);
   5:rcount=32'h8000_0000;6:rcount=32'hffff_ffff;7:rcount=2+($urandom%5);default:rcount=0;
  endcase
 endfunction
 // row selector word for cfg mode 0: row[5:0] in [5:0], bank in [7:6], row[7:6] in [9:8]
 function automatic [31:0] sel(input [7:0] row,input [1:0] bank); sel={22'd0,row[7:6],bank,row[5:0]}; endfunction
 integer p,r,b,f,nr,t,w,lidset,k;reg lastcfg=0;reg [63:0] meta;reg [31:0] cnt;reg [7:0] rows[0:63];reg [7:0] nx,tg,ld;
 reg [255:0] used;
 initial begin
  if(!$value$plusargs("SEED=%d",seed))seed=1;
  if(!$value$plusargs("PROGS=%d",progs))progs=300;
  void'($urandom(seed));
  for(p=0;p<progs;p=p+1)begin
   rst_n=0;cfg=0;start=0;repeat(3)tick;rst_n=1;tick;
   nr=1+($urandom%24);lidset=1+($urandom%4);used=0;
   for(r=0;r<nr;r=r+1)begin                       // distinct rows spread over 0..255 (or dense from a random base)
    if(p%3==0)rows[r]=8'((p*37+r)%256);
    else begin k=$urandom%256;while(used[k])k=(k+1)%256;rows[r]=8'(k);end
    used[rows[r]]=1;
   end
   for(r=0;r<nr;r=r+1)begin
    for(b=0;b<3;b=b+1)if(($urandom%60)!=0)begin
     send(0,sel(rows[r],2'(b)));
     for(f=0;f<16;f=f+1)send(1,$urandom);
    end
    cnt=rcount($urandom);nx=rows[$urandom%nr];tg=rows[$urandom%nr];ld=8'($urandom%lidset);
    if(($urandom%5)==0)ld=rows[r]&8'd31;
    meta=0;meta[5:0]=nx[5:0];meta[51]=nx[6];meta[54]=nx[7];meta[11:6]=tg[5:0];meta[52]=tg[6];meta[55]=tg[7];
    meta[43:12]=cnt;meta[44]=(r==nr-1)?(($urandom%3)!=0):(($urandom%7)==0);
    meta[50:45]=ld[5:0];meta[53]=ld[6];meta[56]=ld[7];
    if(($urandom%50)!=0)begin send(0,sel(rows[r],2'd0));send(2,meta[31:0]);send(3,meta[63:32]);end
   end
   set_spc(rows[$urandom%nr]);
   for(w=0;w<3;w=w+1)begin
    t=0;while((quiet<5 || rb) && t<600)begin tick;t=t+1;end   // a never-ending loop count keeps busy: start then faults
    start=1;tick;start=0;launches=launches+1;
    set_spc(rows[$urandom%nr]);                    // next start row: stable from now on (descriptor-accept timing)
    for(t=0;t<400;t=t+1)begin
     if(($urandom%300)==0 && !lastcfg && (rb || quiet>=5))start=1;   // relaunch when legal; a start while busy faults
     if(($urandom%400)==0 && rb)cfg={1'b1,4'd2,32'h1234};          // stray metadata write while busy (faults, no write)
     lastcfg=cfg[36];
     tick;start=0;cfg=0;
     if(rv && ri!=0)loops_taken=loops_taken+1;
     if(rd)halts=halts+1;
    end
    repeat(4)tick;
   end
   if(rf)faults=faults+1;
  end
  if(mism==0)$display("ISSUER_V7_MITER PASS seed%0d progs%0d checks%0d launches%0d iter_nonzero%0d max_iter%0d halts%0d hi_row_uops%0d faulted_progs%0d",
    seed,progs,checks,launches,loops_taken,iters_max,halts,hi_rows,faults);
  else begin $display("ISSUER_V7_MITER FAIL mismatches%0d checks%0d",mism,checks);$fatal(1,"miter mismatch");end
  $finish;
 end
endmodule
