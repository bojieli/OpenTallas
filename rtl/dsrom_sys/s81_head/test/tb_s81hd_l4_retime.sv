`timescale 1ns/1ps
// Full B element, real ROM model and identical logical weights re-skewed for
// SK11/SK4. Compare all128 emitted row roots; valid timing changes by119 clocks.
module tb_s81hd_l4_retime #(parameter integer A_MODE=0);
  localparam integer ROWS_T=A_MODE!=0 ? 32:128;
  localparam integer CADENCE=A_MODE!=0 ? 256:64;
  localparam integer DELTA=A_MODE!=0 ? 126:119;
  reg clk=0;always #5 clk=~clk;
  reg rst_n=0,go=0;reg [255:0] gx=0,nx=0;
  wire gv,nv,gf,nf;wire [31:0] gy,ny;
  wire gov,nov,glv,nlv,gd,nd;wire [31:0] god,nod,gld,nld,gbits,nbits,gkey,nkey;wire [16:0] grow,nrow;
  reg gbv=0,nbv=0;reg [31:0] gbd=0,nbd=0;
  assign gv=A_MODE!=0 ? glv:gov;assign nv=A_MODE!=0 ? nlv:nov;
  assign gy=A_MODE!=0 ? gld:god;assign ny=A_MODE!=0 ? nld:nod;
  ot_s81hd_elem #(.LV(A_MODE!=0 ? 8:6),.PAD(A_MODE!=0 ? 0:2),.JOIN(A_MODE),.ROWS(ROWS_T),.CUT(9'h1ff),.SPLIT9(1),
      .FADD_L4(0),.IOREG(1),.SAFE(1),.INSTANCE("gold")) gold (
      .clk(clk),.rst_n(rst_n),.go(go),.row0(17'd0),.x(gx),.b_v(gbv),.b_d(gbd),
      .o_v(gov),.o_d(god),.l_v(glv),.l_d(gld),.head_v(),.head_d(),.head_row(),
      .done(gd),.best_row(grow),.best_bits(gbits),.best_key(gkey),.fault(gf));
  ot_s81hd_elem #(.LV(A_MODE!=0 ? 8:6),.PAD(A_MODE!=0 ? 0:2),.JOIN(A_MODE),.ROWS(ROWS_T),.CUT(9'h1ff),.SPLIT9(1),
      .FADD_L4(1),.IOREG(1),.SAFE(1),.INSTANCE("new")) candidate (
      .clk(clk),.rst_n(rst_n),.go(go),.row0(17'd0),.x(nx),.b_v(nbv),.b_d(nbd),
      .o_v(nov),.o_d(nod),.l_v(nlv),.l_d(nld),.head_v(),.head_d(),.head_row(),
      .done(nd),.best_row(nrow),.best_bits(nbits),.best_key(nkey),.fault(nf));
  function automatic [15:0] activation(input integer logical_word,lane);
    integer k;
    begin k=((logical_word%CADENCE)+CADENCE)%CADENCE;
      activation=16'h3c80 | 16'((k*13+lane*7)%128);
      if((k+lane)%5==0) activation[15]=1'b1;
    end
  endfunction
  reg [31:0] gq[0:127],nq[0:127];integer ng=0,nn=0,nc=0,bad=0,cyc,j;
  integer firstg=-1,firstn=-1,lastg=-1,lastn=-1;
  initial begin
    repeat(5) @(negedge clk);rst_n=1;
    for(cyc=0;cyc<9000;cyc=cyc+1) begin
      go=(cyc==0);
      gbv=A_MODE!=0 && cyc>=263 && cyc<263+32*256 && (cyc-263)%256==0;
      nbv=A_MODE!=0 && cyc>=144 && cyc<144+32*256 && (cyc-144)%256==0;
      gbd=32'h3d000000+32'(cyc>=263 ? (cyc-263)/256:0);
      nbd=32'h3d000000+32'(cyc>=144 ? (cyc-144)/256:0);
      for(j=0;j<16;j=j+1) begin
        gx[16*j+:16]=activation(cyc-5-11*(j%8),j);
        nx[16*j+:16]=activation(cyc-5-4*(j%8),j);
      end
      @(negedge clk);
      if(gf || nf) $fatal(1,"FAULT cycle=%0d old=%b new=%b",cyc,gf,nf);
      if(gv) begin
        if(ng>=ROWS_T) $fatal(1,"extra gold root");
        gq[ng]=gy;if(firstg<0) firstg=cyc;
        if(lastg>=0 && cyc-lastg!=CADENCE) $fatal(1,"gold cadence");
        lastg=cyc;ng=ng+1;
      end
      if(nv) begin
        if(nn>=ROWS_T) $fatal(1,"extra candidate root");
        nq[nn]=ny;if(firstn<0) firstn=cyc;
        if(lastn>=0 && cyc-lastn!=CADENCE) $fatal(1,"candidate cadence");
        lastn=cyc;nn=nn+1;
      end
      while(nc<ng && nc<nn) begin
        if(gq[nc]!==nq[nc]) begin
          if(bad<8) $display("DIFF row=%0d old=%h new=%h",nc,gq[nc],nq[nc]);bad=bad+1;
        end
        nc=nc+1;
      end
    end
    if(nc!=ROWS_T || bad!=0) $fatal(1,"FAIL rows=%0d mismatches=%0d old=%0d new=%0d",nc,bad,ng,nn);
    if(firstg-firstn!=DELTA || lastg-lastn!=DELTA) $fatal(1,"latency old=%0d..%0d new=%0d..%0d",firstg,lastg,firstn,lastn);
    if(A_MODE!=0 && (!gd || !nd || {grow,gbits,gkey}!=={nrow,nbits,nkey})) $fatal(1,"ARGMAX differs");
    $display("PASS mode=%0d rows=%0d cadence=%0d old=%0d..%0d new=%0d..%0d saved=%0d",A_MODE,nc,CADENCE,firstg,lastg,firstn,lastn,DELTA);$finish;
  end
endmodule
