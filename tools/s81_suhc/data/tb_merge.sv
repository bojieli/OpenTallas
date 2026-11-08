`timescale 1ns/1ps
module tb_merge;
reg clk=0;always #0.5 clk=~clk;
reg rst_n=0,iv=0,ifin=0;reg[4:0]iblk=0;reg[63:0]iy=0;reg[1:0]if_=0;
wire gv,cv,mv,nv;wire[63:0]gy,cy,my,ny;wire[1:0]gf,cf,mf,nf;
ot_hdc_v41x_attn_merge_x #(.H(2),.DPT(8),.MLEV(5),.FPL(5),.F12(1)) gold(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(gv),.oy(gy),.of_(gf));
codex_svc_merge_head_groups #(.H(2),.GROUP(1)) candidate(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(cv),.oy(cy),.of_(cf));
codex_svc_merge_head_groups #(.H(2),.GROUP(1),.MUT(1)) data_mutant(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(mv),.oy(my),.of_(mf));
codex_svc_merge_head_groups #(.H(2),.GROUP(1),.MUT(2)) valid_mutant(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(nv),.oy(ny),.of_(nf));
integer checked=0,words=0,bad=0,md=0,nd=0,i,epoch;reg[31:0]rng=32'h4d534c31;
always@(negedge clk)if(rst_n)begin
 checked=checked+1;
 if(gv!==cv)bad=bad+1;
 if(gv)begin
  words=words+1;if({gy,gf}!=={cy,cf})bad=bad+1;
  if(gv!==mv||{gy,gf}!=={my,mf})md=md+1;
  if(gv!==nv||{gy,gf}!=={ny,nf})nd=nd+1;
 end
end
initial begin
 repeat(8)@(negedge clk);rst_n=1;
 for(epoch=0;epoch<4;epoch=epoch+1)begin
  for(i=0;i<512;i=i+1)begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   iv=(i%7!=0);ifin=(i%16==15);iblk=(i/8)%32;
   iy={32'h3f000000|(rng&32'h007fffff),32'h3f000000|((rng^32'h24582311)&32'h007fffff)};
   if_=(i%113==0)?2'b10:0;@(negedge clk);
  end
  iv=0;ifin=0;if(epoch%2==0)repeat(5)@(negedge clk);else repeat(50)@(negedge clk);
  // Warm reset after real inflight work; every grouped copy sees the same reset.
  rst_n=0;repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);
 end
 $display("MERGE_HEAD_CUT checked=%0d words=%0d bad=%0d data_mut=%0d valid_mut=%0d cycles_added=0",checked,words,bad,md,nd);
 if(bad||words<32||md==0||nd==0)$fatal(1,"MERGE_HEAD_CUT FAIL");
 $display("MERGE_HEAD_CUT PASS");$finish;
end
endmodule
