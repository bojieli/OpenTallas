`timescale 1ns/1ps
module tb;
reg clk=0;always #0.5 clk=~clk;
reg rst_n=0,iv=0,ifin=0;reg[4:0]iblk=0;reg[127:0]iy=0;reg[3:0]if_=0;
wire g_ov;
wire [127:0] g_oy;
wire [3:0] g_of_;
ot_hdc_v41x_attn_merge_x #(.H(4),.DPT(8),.MLEV(5),.FPL(5),.F12(1)) u_g(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(g_ov),.oy(g_oy),.of_(g_of_));
wire c_ov;
wire [127:0] c_oy;
wire [3:0] c_of_;
codex_svc_merge_h4_pin  u_c(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(c_ov),.oy(c_oy),.of_(c_of_));
wire m_ov;
wire [127:0] m_oy;
wire [3:0] m_of_;
codex_svc_merge_h4_pin #(.MUT(1)) u_m(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(m_ov),.oy(m_oy),.of_(m_of_));
wire n_ov;
wire [127:0] n_oy;
wire [3:0] n_of_;
codex_svc_merge_h4_pin #(.MUT(2)) u_n(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(n_ov),.oy(n_oy),.of_(n_of_));
reg gv0=0,gv1=0;reg[127:0]gy0,gy1;reg[3:0]gf0,gf1;integer warm=0,checks=0,words=0,bad=0,md=0,nd=0,i,e,h;reg[31:0]r=32'h4a495131;
always@(posedge clk)begin
 gy0<=g_oy;gy1<=gy0;gf0<=g_of_;gf1<=gf0;
 if(!rst_n)begin gv0<=0;gv1<=0;warm<=0;end else begin gv0<=g_ov;gv1<=gv0;warm<=warm+1;end
end
always@(negedge clk)if(rst_n&&warm>8)begin
 checks=checks+1;if(gv1!==c_ov)bad=bad+1;
 if(gv1)begin words=words+1;if({gy1,gf1}!=={c_oy,c_of_})bad=bad+1;if(gv1!==m_ov||{gy1,gf1}!=={m_oy,m_of_})md=md+1;if(gv1!==n_ov||{gy1,gf1}!=={n_oy,n_of_})nd=nd+1;end
end
initial begin
 for(e=0;e<4;e=e+1)begin
  rst_n=0;iv=0;ifin=0;repeat(64)@(negedge clk);rst_n=1;repeat(16)@(negedge clk);
  for(i=0;i<512;i=i+1)begin
   r={r[30:0],r[31]^r[21]^r[1]^r[0]};iv=(i%7!=0);ifin=(i%16==15);iblk=(i/8)%32;
   for(h=0;h<4;h=h+1)iy[h*32+:32]=32'h3f000000|((r^(h*32'h154321))&32'h007fffff);
   if_=(i%113==0)?4'b1010:0;@(negedge clk);
  end
  iv=0;ifin=0;if(e%2==0)repeat(5)@(negedge clk);else repeat(64)@(negedge clk);
 end
 $display("MERGE_H4_PIN_BOUNDARY checks=%0d words=%0d bad=%0d data_mut=%0d valid_mut=%0d data_cycles=2 reset_cycles=1",checks,words,bad,md,nd);
 if(bad||words<32||md==0||nd==0)$fatal(1,"MERGE_H4_PIN_BOUNDARY FAIL");$display("MERGE_H4_PIN_BOUNDARY PASS");$finish;
end
endmodule
