// el1011-q-kvd 2026-10-12: ot_qfd_kv_landing_ecc PIPE 2 (pin flops + syndrome register + correction) against the
// original one-register structure (PIPE 0), cycle-shifted by 2, 40k random words (single / double bit errors, CE / UE,
// sticky fault, mid-run reset).  MUTB != 0 builds the PIPE 2 instance with MUT 1 (no correction) -> must FAIL.
// Prints "EQ PASS ..." / "EQ FAIL ...".  physical/sys_takeover/landing_ecc_pipe_bench.sh runs it.
module tb_qfd_landing_ecc_pipe;
 parameter integer IL=1, MUT=0, MUTB=0;
 reg clk=0, rst=0; always #1 clk=~clk;
 reg v; reg [287:0] code; reg [16:0] sec; reg [7:0] row;
 wire ov1,ov2; wire [255:0] d1,d2; wire [16:0] s1,s2; wire [7:0] r1,r2;
 wire ce1,ce2,ue1,ue2,f1,f2; wire [31:0] c1,c2;
 ot_qfd_kv_landing_ecc #(.ENABLE(1),.MUT(MUT),.INTERLEAVED(IL),.PIPE(0)) b(clk,rst,v,code,sec,row,ov1,d1,s1,r1,ce1,ue1,f1,c1);
 ot_qfd_kv_landing_ecc #(.ENABLE(1),.MUT(MUTB!=0 ? 1 : MUT),.INTERLEAVED(IL),.PIPE(2)) c(clk,rst,v,code,sec,row,ov2,d2,s2,r2,ce2,ue2,f2,c2);
 reg [255+64+3*32:0] h0 [0:3]; integer nd=0, ia, ib; integer i, err=0, n, k, nue=0, nce=0; reg [71:0] cw;
 function automatic [71:0] enc(input [63:0] d); reg [71:0] c; integer p,k,j; begin c=0;j=0;
  for(p=1;p<=71;p=p+1) if((p&(p-1))!=0) begin c[p-1]=d[j]; j=j+1; end
  for(k=0;k<7;k=k+1) for(p=1;p<=71;p=p+1) if((p&(1<<k))!=0 && p!=(1<<k)) c[(1<<k)-1]^=c[p-1];
  c[71]=^c[70:0]; enc=c; end endfunction
 wire [256+17+8+5+32-1:0] A={ov1,d1,s1,r1,ce1,ue1,f1,c1}, C={ov2,d2,s2,r2,ce2,ue2,f2,c2};
 wire ce0=ce1, ue0=ue1;
 reg [$bits(A)-1:0] q1,q2;
 initial begin
  v=0; code=0; sec=0; row=0; repeat(3) @(posedge clk); rst=1;
  for(i=0;i<40000;i=i+1) begin
   @(negedge clk);
   v=($random%4)!=0; sec=$random; row=$random;
   for(k=0;k<4;k=k+1) begin cw=enc({$random,$random});
     n=$random%64; if(n<0) n=-n;
     if(i>30000 && (n==3)) begin nd=nd+1; ia=$unsigned($random)%72; ib=(ia+1+$unsigned($random)%71)%72; cw[ia]=~cw[ia]; cw[ib]=~cw[ib]; end
     else if(n<20) begin ia=$unsigned($random)%72; cw[ia]=~cw[ia]; end
     if(IL) code[k*72+:72]=cw; else begin
       // non-interleaved layout: data bits then check bits (inverse of unpack)
       code[k*64+:64]=0; code[256+k*8+:8]=0;
       begin : pk integer p,j,m; j=0;m=0; for(p=1;p<=71;p=p+1) if((p&(p-1))!=0) begin code[k*64+j]=cw[p-1]; j=j+1; end else begin code[256+k*8+m]=cw[p-1]; m=m+1; end
         code[256+k*8+7]=cw[71]; end
     end
   end
   if(i==35000) begin rst=0; #0.1 rst=1; end
  end
  $display("doubles %0d",nd); $display("EQ %s IL %0d MUT %0d err %0d ue %0d ce %0d", err==0?"PASS":"FAIL", IL, MUT, err, nue, nce); $finish;
 end
 always @(posedge clk) begin q1<=A; q2<=q1;
   if(rst && $time>20 && !(i>=35000 && i<35004) && q2!==C) begin err=err+1; if(err<4) $display("P2 mismatch t=%0t",$time); end
   if(ue0) nue=nue+1; if(ce0) nce=nce+1;
 end
endmodule
