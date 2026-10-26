`timescale 1ns/1ps
module tb;
 reg ck=0; always #0.5 ck=~ck;
 reg rst_n=0; reg [14:0] tc=0; reg [137:0] zi=0;
 wire [137:0] zo_g,zo_n,zo_b; wire fo_g,fo_n,fo_b;
 qkd_astk_zn_head_p_gold #(.ZC(4'd0)) u_g(.ck(ck),.rst_n(rst_n),.tc(tc),.zi(zi),.zo(zo_g),.fo(fo_g));
 qkd_astk_zn_head_p #(.ZC(4'd0)) u_n(.ck(ck),.rst_n(rst_n),.tc(tc),.zi(zi),.zo(zo_n),.fo(fo_n));
 qkd_astk_zn_head_p_bad #(.ZC(4'd0)) u_b(.ck(ck),.rst_n(rst_n),.tc(tc),.zi(zi),.zo(zo_b),.fo(fo_b));
 wire [63:0] exp_we,new_we,bad_we;
 genvar r,g;
 generate for(r=0;r<16;r=r+1)begin:gr
  for(g=0;g<4;g=g+1)begin:gg
   assign exp_we[4*r+g]=u_g.put && u_g.k==4'(r);
   assign new_we[4*r+g]=u_n.g_sd_row[r].we[g];
   assign bad_we[4*r+g]=u_b.g_sd_row[r].we[g];
  end
 end endgenerate
 integer n=0,j,checks=0,mis=0,wm=0,sm=0,mut=0,drain_edges=0,start_edges=0,reset_edges=0;
 always @(negedge ck) if(n>8)begin
  checks=checks+1;
  if({zo_g,fo_g}!={zo_n,fo_n})begin mis=mis+1;if(mis<4)$display("OUTPUT mismatch n=%0d",n);end
  if(exp_we!=new_we)begin wm=wm+1;if(wm<6)$display("ENABLE mismatch n=%0d stl=%0d start=%b exp=%h new=%h",n,u_g.stl,u_g.start,exp_we,new_we);end
  if(exp_we!=bad_we)mut=mut+1;
  for(j=0;j<16;j=j+1)if(u_g.sd[j]!=u_n.sd[j])begin sm=sm+1;if(sm<4)$display("STORE mismatch n=%0d row=%0d",n,j);end
  if(u_g.stl==0 && u_g.put)drain_edges=drain_edges+1;
  if(u_g.start)start_edges=start_edges+1;
  if(!u_g.rn_q)reset_edges=reset_edges+1;
 end
 initial begin
  for(n=0;n<16000;n=n+1)begin
   @(posedge ck);#0.15;
   rst_n=!(n<4 || (n>=333 && n<=335) || (n>=9000 && n<=9004));
   zi={$urandom,$urandom,$urandom,$urandom,$urandom};
   zi[0]=($urandom%10!=0);zi[6]=($urandom%4==0);
   tc={$urandom};tc[0]=(n==20 || n==100 || n==131 || n==200 || n==232 || ($urandom%500==0));
   // Directed always-eligible stream through the first32-cycle drain boundary.
   if(n>=10 && n<80)begin zi[0]=1;zi[6]=0;zi[5:2]=4'(n);tc[14:1]=14'h3fff;tc[0]=(n==20);end
   // Equal upper threshold exercises the strict low-bound comparison.
   if(n>=1000 && n<6000)tc[14:1]={1'b0,zi[5:2],9'($urandom)};
  end
  repeat(3)@(negedge ck);
  $display("ASTK6 MITER checks=%0d output_mis=%0d enable_mis=%0d store_mis=%0d mutant_mis=%0d writes=%0d starts=%0d resets=%0d",checks,mis,wm,sm,mut,drain_edges,start_edges,reset_edges);
  if(mis||wm||sm||mut==0||drain_edges<100||start_edges<4||reset_edges<4)$fatal(1,"ASTK6 FAIL");
  $display("ASTK6 PASS; drain-count mutant CAUGHT");$finish;
 end
endmodule
