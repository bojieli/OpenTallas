`timescale 1ns/1ps
module tb_ot_hbm_smh_rp7s_f_retime #(parameter integer MUT=0);
reg clk=0; always #5 clk=~clk; reg rst_n=0; integer cyc,bad=0,nc=0;
reg [8:0] xss_a1=0;
reg [4:0] xss_g1=0;
reg [6:0] xss_a2=0;
reg [4:0] xss_g2=0;
reg [4:0] attn=0;
reg [817:0] rin_s=0;
reg [2068:0] xi_b=0;
reg [49:0] xi_g0=0;
reg [99:0] xi_gp=0;
wire [817:0] old_rout_s,new_rout_s;
reg [817:0] expected_rout_s[0:9];
always @(posedge clk) begin expected_rout_s[0]<=old_rout_s; for(integer j=1;j<=9;j=j+1) expected_rout_s[j]<=expected_rout_s[j-1]; end
wire [199:0] old_gout,new_gout;
reg [199:0] expected_gout[0:15];
always @(posedge clk) begin expected_gout[0]<=old_gout; for(integer j=1;j<=15;j=j+1) expected_gout[j]<=expected_gout[j-1]; end
ot_hbm_smh_rp6s_f #(.MUT(0)) u_old (.ck_u(clk), .ck_t(clk), .ck_c(clk), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .attn(attn), .rin_s(rin_s), .xi_b(xi_b), .xi_g0(xi_g0), .xi_gp(xi_gp), .rout_s(old_rout_s), .gout(old_gout));
ot_hbm_smh_rp7s_f #(.MUT(MUT)) u_new (.ck_t(clk), .ck_upn(clk), .ck_upne(clk), .ck_c(clk), .ck_cpw(clk), .ck_cw(clk), .ck_ce(clk), .ck_cpe(clk), .ck_u(clk), .ck_xs(clk), .ck_mpse(clk), .rst_n(rst_n), .xss_a1(xss_a1), .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .attn(attn), .rin_s(rin_s), .xi_b(xi_b), .xi_g0(xi_g0), .xi_gp(xi_gp), .rout_s(new_rout_s), .gout(new_gout));
initial begin for(cyc=0;cyc<3000;cyc=cyc+1) begin @(negedge clk); if(cyc==32) rst_n=1;
xss_a1<={$urandom};
xss_g1<={$urandom};
xss_a2<={$urandom};
xss_g2<={$urandom};
attn<=5'd13;
rin_s<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
xi_b<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
xi_g0<={$urandom,$urandom};
xi_gp<={$urandom,$urandom,$urandom,$urandom};
if(cyc>256) begin
nc=nc+1; if(new_rout_s !== expected_rout_s[8]) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH rout_s cyc=%0d old=%h new=%h",cyc,expected_rout_s[8],new_rout_s); end
nc=nc+1; if(new_gout !== expected_gout[14]) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH gout cyc=%0d old=%h new=%h",cyc,expected_gout[14],new_gout); end
end end
$display("R7_RETIME %s h=s v=f MUT=%0d compared=%0d mismatches=%0d",bad==0 ? "PASS":"FAIL",MUT,nc,bad);
if(bad) $fatal(1,"retiming mismatch"); $finish; end endmodule
