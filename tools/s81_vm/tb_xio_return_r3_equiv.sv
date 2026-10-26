`timescale 1ns/1ps
// r3 dsfd_vm_xio_return vs frozen r2 (xio_return_r2_ref.sv): every output, every cycle, random inputs on every cycle
// including through async reset assertion and release (the rn qualification edge), many warm resets.  Exact (!==).
module tb #(parameter integer SEED=1);
 reg ck=0,rst_n=0;always #3 ck=~ck;
 reg[2:0]v=0;reg[5:0]lane=0;reg[3:0]ev=0;reg[2047:0]ed=0;reg[10:0]xgo=0;
 wire[512:0]crs0,crs1;wire qv0,qv1,gv0,gv1,f0,f1;wire[511:0]qd0,qd1;wire[510:0]gd0,gd1;
 dsfd_vm_xio_return_r2_ref ref0(ck,rst_n,v,lane,ev,ed,xgo,crs0,qv0,qd0,gv0,gd0,f0);
 dsfd_vm_xio_return dut(ck,rst_n,v,lane,ev,ed,xgo,crs1,qv1,qd1,gv1,gd1,f1);
 integer s,c,k,nres=0,nf=0,nq=0,ng=0,nc=0,nrel=0;
 always @(negedge ck)begin
  if({crs1,qv1,qd1,gv1,gd1,f1}!=={crs0,qv0,qd0,gv0,gd0,f0})
   $fatal(1,"R3 EQUIV cycle%0d crs%0b qv%0b qd%0b gv%0b gd%0b fault old%0b new%0b",c,crs1!==crs0,qv1!==qv0,qd1!==qd0,gv1!==gv0,gd1!==gd0,f0,f1);
  nf=nf+(f0===1);nq=nq+(qv0===1);ng=ng+(gv0===1);nc=nc+(crs0[0]===1);
  // random stimulus, changed on the falling edge, active through reset
  v=$urandom(s)%8;lane=$urandom(s);ev=($urandom(s)%3==0)?$urandom(s):0;
  for(k=0;k<64;k=k+1)ed[32*k+:32]=$urandom(s);
  if($urandom(s)%4==0)ed[50:49]=0;
  xgo=($urandom(s)%5==0)?{1'b1,10'($urandom(s))}:{1'b0,10'($urandom(s))};
  c=c+1;
 end
 // asynchronous reset pulses at non-edge-aligned times
 initial begin
  s=SEED;c=0;#7.3;rst_n=1;
  repeat(400)begin
   #(1.0*($urandom(s)%240)+0.7);rst_n=0;nres=nres+1;
   #(1.0*($urandom(s)%20)+0.4);rst_n=1;
  end
  $display("XIO_RETURN_R3_EQUIV PASS seed%0d cycles%0d resets%0d faultcycles%0d qv%0d gv%0d crs%0d",SEED,c,nres,nf,nq,ng,nc);$finish;
 end
endmodule
