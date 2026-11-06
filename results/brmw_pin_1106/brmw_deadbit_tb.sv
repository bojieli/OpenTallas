module tb;
reg clk=0; reg [15:0] r_wsel; reg zlo,zhi; reg [255:0] qq_lo,qq_hi; reg [9:0] qe_lo,qe_hi; reg [25:0] bsel; reg [63:0] lane_en_i; wire [2047:0] a,b,c;
ot_hgi_sm_xload_cl2_bdring #(.PMAX(8),.NR(32)) u0(.clk(clk),.r_wsel(r_wsel),.zlo(zlo),.zhi(zhi),.qq_lo(qq_lo),.qq_hi(qq_hi),.qe_lo(qe_lo),.qe_hi(qe_hi),.bsel({1'b0,bsel[24:0]}),.lane_en_i(lane_en_i),.bq_d(a));
ot_hgi_sm_xload_cl2_bdring #(.PMAX(8),.NR(32)) u1(.clk(clk),.r_wsel(r_wsel),.zlo(zlo),.zhi(zhi),.qq_lo(qq_lo),.qq_hi(qq_hi),.qe_lo(qe_lo),.qe_hi(qe_hi),.bsel({1'b1,bsel[24:0]}),.lane_en_i(lane_en_i),.bq_d(b));
ot_hgi_sm_xload_cl2_bdring #(.PMAX(8),.NR(32)) um(.clk(clk),.r_wsel(r_wsel),.zlo(zlo),.zhi(zhi),.qq_lo(qq_lo),.qq_hi(qq_hi),.qe_lo(qe_lo),.qe_hi(qe_hi),.bsel({1'b0,~bsel[24],bsel[23:0]}),.lane_en_i(lane_en_i),.bq_d(c));
integer checks=0,mut=0;
initial begin
for(integer n=0;n<180;n=n+1)begin
r_wsel=16'hffff; zlo=1;zhi=1;lane_en_i=64'hffffffffffffffff;
for(integer w=0;w<8;w=w+1)begin qq_lo[w*32+:32]=$random;qq_hi[w*32+:32]=$random;end
qe_lo=$random;qe_hi=$random;bsel=$random;
#5;clk=1;#5;clk=0;
if(n>=5)begin
if(a!==b)$fatal(1,"deadbit differs");
if(u0.beat_w[0][12]!==2048'b0 ||u0.beat_w[1][12]!==2048'b0)$fatal(1,"lastbeat nonzero");
checks=checks+1;if(a!==c)mut=mut+1;
end
end
if(mut==0)$fatal(1,"mutant not detected");
$display("PASS checks=%0d deadbit_diffs=0 beat12_zero=both mutant_bit24_diffs=%0d",checks,mut);$finish;
end
endmodule
