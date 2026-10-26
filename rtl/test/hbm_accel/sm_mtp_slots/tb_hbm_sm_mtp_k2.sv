`timescale 1ns/1ps
module tb_hbm_sm_mtp_k2;
 parameter integer MUT=0;
 localparam integer P=6,ROWS=8,TERMS=32;
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0,iv=0,first=0,last=0,fp4=0;
 reg [15:0] tag0=0,tag1=0;reg [531:0] w=0,x0=0,x1=0;
 wire [1:0] ov,ff;wire[63:0] yy;wire[31:0] tt;
 ot_hbm_sm_mtp_k2 #(.MUT_SLOT_ALIAS(MUT==1),.MUT_CONTEXT_ALIAS(MUT==2)) dut(.clk(clk),.rst_n(rst_n),.iv(iv),.first(first),.last(last),
  .fp4(fp4),.tag0(tag0),.tag1(tag1),.weight(w),.x0(x0),.x1(x1),.ov(ov),.fault(ff),.result(yy),.otag(tt));
 reg sv=0,sfirst=0,slast=0;reg[15:0] stag=0;reg[531:0] sw=0,sx=0;
 wire sov,sf;wire[31:0] sy;wire[15:0] st;
 ot_hbm_accel_smh_bdc #(.IL(8)) serial(.clk(clk),.rst_a(rst_n),.i_v(sv),.i_first(sfirst),.i_last(slast),
  .i_fp4(fp4),.i_tag(stag),.i_w(sw),.i_x(sx),.ov(sov),.y(sy),.otag(st),.fault(sf));
 reg[31:0] refval[0:47],got[0:47];reg[47:0] refseen=0,seen=0;
 integer cycle=0,lastserial=0,lastdual=0,count=0,errors=0,i,j,k,pos,row,g,mode,iss0,iss1,reads0=0,reads1=0;
 // Declared external FP8 operands. Exact native serial BDC arithmetic is the
 // comparison boundary; no internal DUT result or memory is reference-filled.
 function automatic [531:0] operand(input integer a,input integer b,input integer c);
  integer lane,idx;reg[531:0] z;begin z=0;
  for(lane=0;lane<2;lane=lane+1)begin
   for(idx=0;idx<32;idx=idx+1)z[256*lane+8*idx+:8]=8'h20+((a*13+b*7+c*3+idx+lane*5)%24);
   z[512+lane*10+:10]=10'd0;
  end operand=z;end
 endfunction
 function automatic [531:0] xoperand(input integer a,input integer b,input integer c);
  reg[531:0] z;begin z=operand(a,b,c);xoperand={z[531:522],z[511:256],z[521:512],z[255:0]};end
 endfunction
 always @(negedge clk) if(rst_n)begin
  cycle=cycle+1;
  if(sov)begin
   if(st>=48||refseen[st])$fatal(1,"serial duplicate tag %0d",st);
   refval[st]=sy;refseen[st]=1;lastserial=cycle;
  end
  for(integer q=0;q<2;q=q+1)if(ov[q])begin
   if(tt[q*16+:16]>=48||seen[tt[q*16+:16]])$fatal(1,"dual duplicate tag");
   got[tt[q*16+:16]]=yy[q*32+:32];seen[tt[q*16+:16]]=1;lastdual=cycle;
  end
  if(sf||(|ff))$fatal(1,"native arithmetic fault");
 end
 initial begin
  repeat(12)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  iss0=cycle;
  // Six serial positions, 8 hardware interleave rows, 32 real block terms.
  for(pos=0;pos<P;pos=pos+1)for(k=0;k<TERMS;k=k+1)for(row=0;row<ROWS;row=row+1)begin
   @(posedge clk);#0.05;sv=1;sfirst=(k==0);slast=(k==TERMS-1);stag=pos*ROWS+row;
   sw=operand(0,row,k);sx=xoperand(pos+1,0,k);reads0=reads0+1;
  end
  @(posedge clk);#0.05;sv=0;repeat(100)@(negedge clk);
  if(refseen!={48{1'b1}})$fatal(1,"serial incomplete %h",refseen);
  iss1=cycle;
  // One declared weight word for each (term,row), retained over three fixed
  // passes. Each pass issues 2 independent positions on 2 actual BDC sets.
  // Ring recurrence is 24 cycles: (row*3+pass), not an IL8 alias.
  for(k=0;k<TERMS;k=k+1)for(row=0;row<ROWS;row=row+1)begin
   reads1=reads1+1;
   for(g=0;g<3;g=g+1)begin
    @(posedge clk);#0.05;iv=1;first=(k==0);last=(k==TERMS-1);
    tag0=(2*g)*ROWS+row;tag1=(2*g+1)*ROWS+row;
    w=operand(0,row,k);x0=xoperand(2*g+1,0,k);x1=xoperand(2*g+2,0,k);
   end
  end
  @(posedge clk);#0.05;iv=0;repeat(120)@(negedge clk);
  if(seen!={48{1'b1}})$fatal(1,"dual incomplete %h",seen);
  for(i=0;i<48;i=i+1)begin count=count+1;if(got[i]!==refval[i])begin errors=errors+1;$display("MISMATCH tag=%0d got=%h expected=%h",i,got[i],refval[i]);end end
  if(errors)$fatal(1,"K2 mismatch errors=%0d",errors);
  $display("PASS K2 P6 exact=%0d terms=%0d serial_issue_cycles=%0d dual_issue_cycles=%0d serial_completion=%0d dual_completion=%0d weight_reads_serial=%0d shared=%0d accumulator_contexts_per_set=24",count,TERMS,P*ROWS*TERMS,3*ROWS*TERMS,lastserial-iss0,lastdual-iss1,reads0,reads1);
  $finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
