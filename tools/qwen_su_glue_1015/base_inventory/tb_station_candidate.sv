`timescale 1ns/1ps
module tb_station_candidate;
parameter integer DM=0,RM=0,RDM=0,CM=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,b_rst_n=0;reg[511:0]cd;reg[639:0]od;reg[15:0]ov;reg[499:0]bd;reg[2:0]bv;
wire[511:0]cq,cqr;wire[639:0]oq,oqr;wire[15:0]ovq,ovqr;wire[499:0]bq,bqr;wire[2:0]bvq,bvqr;
wire candidate_clk=(CM!=0)?~clk:clk;
ot_qfd_su_octet_station_candidate #(.DATA_MUT(DM),.RESET_MUT(RM)) dut(.clk(candidate_clk),.rst_n(rst_n),.b_rst_n(b_rst_n),.crom_d(cd),.crom_q(cq),.os_d(od),.os_q(oq),.os_v(ov),.os_vq(ovq),.b_d(bd),.b_q(bq),.b_v(bv),.b_vq(bvq));
ot_hdc_delay #(.W(512),.D(1)) cref(.clk(clk),.rst_n(rst_n),.d(cd),.q(cqr));
ot_hdc_delay #(.W(640),.D(1)) oref(.clk(clk),.rst_n(rst_n),.d(od),.q(oqr));
ot_hdc_delay #(.W(16),.D(1),.RESET(1)) vref(.clk(clk),.rst_n(rst_n),.d(ov),.q(ovqr));
group_reference gref(.clk(clk),.rst_n(b_rst_n),.b_d(bd),.b_v(bv),.b_q(bqr),.b_vq(bvqr));
reg[63:0]lv,ls,ll;reg[127:0]lr;reg[1535:0]la;reg[2047:0]ld;
wire[2075:0]rq,rr;
ot_qfd_su_reducer_station_candidate #(.DATA_MUT(RDM)) rdut(.clk(clk),.rst_n(b_rst_n),.l_ov(lv),.l_red(lr),.l_redsq(ls),.l_last(ll),.l_raddr(la),.l_out(ld),.rd_v(rq[2075]),.rd_mx(rq[2074]),.rd_sq(rq[2073]),.rd_last(rq[2072]),.rd_addr(rq[2071:2048]),.rd_x(rq[2047:0]));
reducer_reference rref(.clk(clk),.rst_c(b_rst_n),.l_ov(lv),.l_red(lr),.l_redsq(ls),.l_last(ll),.l_raddr(la),.l_out(ld),.q(rr));
integer i,j,checked=0;reg[31:0]seed=32'hca551234;
function[31:0]nextword(input[31:0]x);begin nextword=(x<<1)^{32{ x[31]}}&32'h04c11db7;end endfunction
initial begin
 cd=0;od=0;ov=0;bd=0;bv=7;lv=0;lr=0;ls=0;ll=0;la=0;ld=0;
 // Distinct outer and engine reset histories exercise the actual reset split.
 #1;rst_n=1;b_rst_n=1;#1;rst_n=0;b_rst_n=0;
 for(i=0;i<500;i=i+1)begin
 @(negedge clk);#1;
 rst_n=(i%37!=0);b_rst_n=(i%29!=0);bv=7;
 for(j=0;j<64;j=j+1)begin
 seed=nextword(seed);ld[32*j+:32]=seed;la[24*j+:24]=seed[23:0];lv[j]=seed[3];ls[j]=seed[4];ll[j]=seed[5];lr[2*j+:2]=i%4;
 if(j<16)cd[32*j+:32]=seed;
 if(j<20)od[32*j+:32]=seed;
 if(j<15)bd[32*j+:32]=seed;
 end
 bd[499:480]=seed[19:0];ov=seed[15:0];
 @(posedge clk);#1;
 if({cq,oq,ovq,bq,bvq,rq}!=={cqr,oqr,ovqr,bqr,bvqr,rr})begin
 $display("FAIL station cycle=%0d octet=%0d group_reset=%0d reducer=%0d",i,{cq,oq,ovq,bq}!=={cqr,oqr,ovqr,bqr},bvq!==bvqr,rq!==rr);$fatal(1,"station mismatch");end
 checked=checked+1;
 end
 $display("PASS station checked=500 inactive_SUM_MAX_reset_clock_edges");$finish;
end
endmodule
