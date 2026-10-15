`timescale 1ns/1ps
module tb_station_caller;
reg ck=0;always #5 ck=~ck;
reg rst=0;reg[4095:0]cd;reg[1535:0]ca,ka;reg[2047:0]kd;reg[63:0]cv,kv;
reg[499:0]bd;reg[2:0]bv;
wire[1535:0]oqca,oqka;wire[2047:0]oqkd;wire[63:0]oqcv,oqkv;
ot_qfd_sp_su64_station_candidate #(.STATION_CUT(1),.EXTERNAL_EMBED(1),.VL(14),.LMIN(15)) dut(
 .clk(ck),.rst_n(rst),.ck_octet({8{ck}}),.ck_red_input(ck),.ck_head({64{ck}}),.ck_exp({64{ck}}),.ck_rcp({64{ck}}),.ck_rsq({64{ck}}),.ck_lane({64{ck}}),.ck_align({16{ck}}),.ck_red({9{ck}}),
 .crom_q(cd),.crom_addr(oqca),.kv_waddr(oqka),.kv_wdata(oqkd),.crom_re(oqcv),.kv_we(oqkv));
reg[63:0]lv,ls,ll;reg[127:0]lr;reg[1535:0]la;reg[2047:0]ld;
wire[2075:0]rr;wire[499:0]bqr;wire[2:0]bvqr;
group_reference gr(.clk(ck),.rst_n(dut.rs),.b_d(bd),.b_v(bv),.b_q(bqr),.b_vq(bvqr));
reducer_reference rref(.clk(ck),.rst_c(dut.rs),.l_ov(lv),.l_red(lr),.l_redsq(ls),.l_last(ll),.l_raddr(la),.l_out(ld),.q(rr));
integer i,j,g;reg[31:0]seed=32'hacdef123;
initial begin
 cd=0;ca=0;ka=0;kd=0;cv=0;kv=0;bd=0;bv=7;lv=0;lr=0;ls=0;ll=0;la=0;ld=0;
 // Explicit component-boundary stimuli replace unmodeled arithmetic child outputs.
 force dut.s_crom_addr=ca;force dut.s_kv_waddr=ka;force dut.s_kv_wdata=kd;force dut.s_crom_re=cv;force dut.s_kv_we=kv;
 force dut.station_b_d=bd;force dut.station_b_v=bv;
 force dut.u_su.l_ov=lv;force dut.u_su.l_red=lr;force dut.u_su.l_redsq=ls;force dut.u_su.l_last=ll;force dut.u_su.l_raddr=la;force dut.u_su.l_out=ld;
 #1;rst=1;#1;rst=0;
 for(i=0;i<128;i=i+1)begin
 @(negedge ck);#1;rst=(i%19!=0);
 for(j=0;j<64;j=j+1)begin
 seed=(seed<<1)^({32{seed[31]}}&32'h04c11db7);
 la[24*j+:24]=seed;ld[32*j+:32]=seed;lv[j]=seed[3];ls[j]=seed[4];ll[j]=seed[5];lr[2*j+:2]=i%4;
 ca[24*j+:24]=seed;ka[24*j+:24]=~seed;kd[32*j+:32]=seed;cv[j]=seed[4];kv[j]=seed[5];
 cd[64*j+:64]={seed,~seed};if(j<15)bd[32*j+:32]=seed;
 end
 bd[499:480]=seed;bv=7;
 @(posedge ck);#1;
 if(dut.crq_q0!==cd||{oqca,oqka,oqkd}!=={ca,ka,kd}||{oqcv,oqkv}!== (rst?{cv,kv}:128'd0))$fatal(1,"FAIL caller CROM/KV slicing/reset cycle%0d",i);
 for(g=0;g<8;g=g+1)begin
 if(dut.station_b_q[500*g+:500]!==bqr||dut.station_b_vq[3*g+:3]!==bvqr)$fatal(1,"FAIL caller broadcast/reset g%0d cycle%0d",g,i);
 end
 if({dut.u_su.rd_v,dut.u_su.rd_mx,dut.u_su.rd_sq,dut.u_su.rd_last,dut.u_su.rd_addr,dut.u_su.rd_x}!==rr)$fatal(1,"FAIL caller reducer cycle%0d",i);
 end
 $display("PASS caller checked=128 octets=8 native_slices_two_resets_reducer");$finish;
end
endmodule
