`timescale 1ns/1ps
module tb_smj;
reg clk=0;always #5 clk=~clk;
reg rst=0;reg load=0,selected=0,ip=0;reg[2:0]ij=0;reg[511:0]data_i=0;
reg jst=0;reg[3:0]kind=4;reg[7:0]jid=0;reg[3:0]cfg=0;
reg rv=0,rp=0;reg[2:0]rj=0;reg[511:0]held,bad;wire[511:0]stream;
dsdv_svc_smj_payload_n32 u_actual_payload(.clk(clk),.d(data_i),.q(stream));
always @(posedge clk or negedge rst) if(!rst)begin held<=0;rv<=0;rp<=0;rj<=0;end else begin
 rv<=load&&selected;if(load)begin held<=data_i;rp<=ip;rj<=ij;end end
always @(posedge clk)begin bad<=data_i^512'd1;end
reg ev=0,ov=0,dv=0;reg[511:0]ed=0;reg[255:0]od=0;
wire[2:0]sv,pv,cv,csv,wv,fu,fo,alive,den;wire[6:0]nv[0:2];wire[2:0]lt[0:2];wire[31:0]scale[0:2],sink[0:2];wire[4:0]csi[0:2];wire[63:0]csd[0:2];wire[511:0]dout[0:2],wd[0:2];wire[13:0]wa[0:2];wire[15:0]wm[0:2];wire[7:0]rjid[0:2];
genvar g;generate for(g=0;g<3;g=g+1)begin:smq
wire[511:0]rd=(g==0)?held:(g==1)?stream:bad;
wire mux_v,mux_p;wire[2:0]mux_j;wire[511:0]mux_d;wire collision;
dsdv_svc_rs_se u_se(.ck(clk),.rst(rst),.t_v((cycles%64)==24||(cycles%64)==49),.t_tag({16'd12,4'b1111}),.t_y(ed[127:0]),.t_f(4'd0),.tjob(10'd16),.go(jst),.sm_rv(rv),.sm_rp(rp),.sm_rj(rj),.sm_rd(rd),.r_v(mux_v),.r_p(mux_p),.r_j(mux_j),.r_d(mux_d),.rcol(collision));
ot_s81_su_smq u(.clk(clk),.rst_in(rst),.cfg_g(cfg),.j_st(jst),.j_kind(kind),.j_jid(jid),.r_v(mux_v),.r_p(mux_p),.r_j(mux_j),.r_d(mux_d),
.s_v(sv[g]),.p_v(pv[g]),.c_v(cv[g]),.c_nv(nv[g]),.c_lt(lt[g]),.c_scale(scale[g]),.c_sink(sink[g]),.cs_v(csv[g]),.cs_i(csi[g]),.cs_d(csd[g]),.d_o(dout[g]),
.e_v(ev),.e_d(ed),.o_vi(ov),.o_di(od),.den_v(dv),.f_i(8'd0),.w_v(wv[g]),.w_a(wa[g]),.w_m(wm[g]),.w_d(wd[g]),.o_fu(fu[g]),.o_fo(fo[g]),.o_alive(alive[g]),.o_den(den[g]),.o_rjid(rjid[g]));
end endgenerate
integer cycles=0,validchecks=0,opchecks=0,cschecks=0,cfgchecks=0,negative=0,invaliddiff=0;
always @(posedge clk)begin #1;
 if(rst)begin
 cycles=cycles+1;
 if(rv)begin validchecks++;if(held!==stream)$fatal(1,"producer valid mismatch");end
 else if(held!==stream)invaliddiff++;
 if({sv[0],pv[0],cv[0],csv[0],wv[0],fu[0],fo[0],alive[0],den[0],rjid[0]} !== {sv[1],pv[1],cv[1],csv[1],wv[1],fu[1],fo[1],alive[1],den[1],rjid[1]})$fatal(1,"control mismatch");
 if(sv[0]||pv[0])begin opchecks++;if(dout[0]!==dout[1])$fatal(1,"operand mismatch");if(dout[0]!==dout[2])negative++;end
 if(cv[0])begin cfgchecks++;if({nv[0],lt[0],scale[0],sink[0]}!=={nv[1],lt[1],scale[1],sink[1]})$fatal(1,"config mismatch");end
 if(csv[0])begin cschecks++;if({csi[0],csd[0]}!=={csi[1],csd[1]})$fatal(1,"cos mismatch");end
 if(wv[0]&&{wa[0],wm[0],wd[0]}!=={wa[1],wm[1],wd[1]})$fatal(1,"write mismatch");
 end
end
integer i,k,phase;
initial begin
 repeat(6)@(negedge clk);rst=1;
 for(i=0;i<8192;i=i+1)begin
 @(negedge clk);phase=i%64;
 for(k=0;k<16;k=k+1)data_i[k*32+:32]=$urandom;
 ed={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};od=ed[255:0];
 jst=(phase==8);if(phase==8)begin kind=(i/64)%2?5:4;jid=jid+1;cfg=cfg+1;end
 load=0;selected=1;ip=0;ij=0;
 if(phase>=12&&phase<=16)begin load=1;ip=1;ij=3'(phase-12);if(kind==4&&phase>13)load=0;end
 if(phase>=20&&phase<=38)begin load=(phase%5!=0);ip=0;end
 if(phase==42)begin load=1;selected=0;end
 ev=(phase==45);ov=(phase==46);dv=(phase==47);
 if(i==255||i==2047||i==4095)begin rst=0;load=0;jst=0;repeat(5)@(negedge clk);rst=1;end
 if(i==1023||i==3071)begin #2;rst=0;#1;rst=1;end
 end
 @(negedge clk);load=0;jst=0;ev=0;ov=0;dv=0;repeat(12)@(negedge clk);
 if(validchecks<1000||opchecks<1000||cschecks<1000||cfgchecks<20||negative<1000||invaliddiff<1000)$fatal(1,"insufficient coverage");
 $display("SMJ_ACTUAL_SMQ PASS cycles=%0d valid=%0d operands=%0d cos=%0d config=%0d negative=%0d invalid_differences=%0d",cycles,validchecks,opchecks,cschecks,cfgchecks,negative,invaliddiff);$finish;
end
endmodule
