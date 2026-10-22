`timescale 1ns/1ps
module tb_ot_hbm_smh_rp7n_m_retime #(parameter integer MUT=0);
reg clk=0; always #5 clk=~clk; reg rst_n=0; reg ref_rst_n=0;
always @(posedge clk) ref_rst_n<=rst_n; // priced r7 boot +1
integer cyc,bad=0,nc=0;
reg [8:0] xs_a1=0;
reg [4:0] xs_g1=0;
reg [6:0] xs_a2=0;
reg [4:0] xs_g2=0;
reg [4:0] attn=0;
reg [817:0] rin_n=0;
reg [2068:0] bin=0;
reg [99:0] gin=0;
wire [817:0] old_rout_n,new_rout_n;
reg [817:0] expected_rout_n[0:6];
always @(posedge clk) begin expected_rout_n[0]<=old_rout_n; for(integer j=1;j<=6;j=j+1) expected_rout_n[j]<=expected_rout_n[j-1]; end
wire [2068:0] old_bout,new_bout;
reg [2068:0] expected_bout[0:6];
always @(posedge clk) begin expected_bout[0]<=old_bout; for(integer j=1;j<=6;j=j+1) expected_bout[j]<=expected_bout[j-1]; end
wire [2068:0] old_xo_b,new_xo_b;
reg [2068:0] expected_xo_b[0:3];
always @(posedge clk) begin expected_xo_b[0]<=old_xo_b; for(integer j=1;j<=3;j=j+1) expected_xo_b[j]<=expected_xo_b[j-1]; end
wire [49:0] old_xo_g0,new_xo_g0;
reg [49:0] expected_xo_g0[0:9];
always @(posedge clk) begin expected_xo_g0[0]<=old_xo_g0; for(integer j=1;j<=9;j=j+1) expected_xo_g0[j]<=expected_xo_g0[j-1]; end
wire [99:0] old_xo_gp,new_xo_gp;
reg [99:0] expected_xo_gp[0:9];
always @(posedge clk) begin expected_xo_gp[0]<=old_xo_gp; for(integer j=1;j<=9;j=j+1) expected_xo_gp[j]<=expected_xo_gp[j-1]; end
ot_hbm_smh_rp6n_m #(.MUT(0)) u_old (.ck_u(clk), .ck_t(clk), .ck_c(clk), .ck_m(clk), .rst_n(ref_rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(old_rout_n), .bout(old_bout), .xo_b(old_xo_b), .xo_g0(old_xo_g0), .xo_gp(old_xo_gp));
ot_hbm_smh_rp7n_m #(.MUT(MUT)) u_new (.ck_m(clk), .ck_t(clk), .ck_tpw(clk), .ck_tpe(clk), .ck_cpw(clk), .ck_c(clk), .ck_cpe(clk), .ck_u(clk), .ck_xs(clk), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(new_rout_n), .bout(new_bout), .xo_b(new_xo_b), .xo_g0(new_xo_g0), .xo_gp(new_xo_gp));
initial begin for(cyc=0;cyc<3000;cyc=cyc+1) begin @(negedge clk); if(cyc==32) rst_n=1;
xs_a1<={$urandom};
xs_g1<={$urandom};
xs_a2<={$urandom};
xs_g2<={$urandom};
attn<=5'd13;
rin_n<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
bin<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
gin<={$urandom,$urandom,$urandom,$urandom};
if(cyc>256) begin
nc=nc+1; if(new_rout_n !== expected_rout_n[5]) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH rout_n cyc=%0d old=%h new=%h",cyc,expected_rout_n[5],new_rout_n); end
nc=nc+1; if(new_bout !== expected_bout[5]) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH bout cyc=%0d old=%h new=%h",cyc,expected_bout[5],new_bout); end
nc=nc+1; if(new_xo_b !== expected_xo_b[2]) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH xo_b cyc=%0d old=%h new=%h",cyc,expected_xo_b[2],new_xo_b); end
nc=nc+1; if(new_xo_g0 !== expected_xo_g0[8]) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH xo_g0 cyc=%0d old=%h new=%h",cyc,expected_xo_g0[8],new_xo_g0); end
nc=nc+1; if(new_xo_gp !== expected_xo_gp[8]) begin bad=bad+1; if(bad<6) $display("R7_MISMATCH xo_gp cyc=%0d old=%h new=%h",cyc,expected_xo_gp[8],new_xo_gp); end
end end
$display("R7_RETIME %s h=n v=m MUT=%0d compared=%0d mismatches=%0d",bad==0 ? "PASS":"FAIL",MUT,nc,bad);
if(bad) $fatal(1,"retiming mismatch"); $finish; end endmodule
