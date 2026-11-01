`timescale 1ns/1fs
module tb_pdsk;
reg ck=0;always #0.416500 ck=~ck;
reg rst_n=0;integer cyc=0,phase,j,k,n,errors=0,checks=0,mutants=0;
reg[4:0]pv_old=0,pv_new=0;reg[159:0]pd=0;
wire[5:0]v,f;wire[6:0]ix[0:5];wire[31:0]data[0:5];
integer count[0:1];integer mut_seen[0:1];
ot_s81sl_xrt1 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'd668),.QDELAYS(128'd0)) u_0 (.clk(ck),.rst_n(rst_n),.sid(4'd0),.dl_ev(1'd0),.dl_e(1075'd0),.dl_wv(1'd0),.dl_w(1075'd0),.dl_vv(1'd0),.dl_vb(275'd0),.ci_dir(),.ci_b(),.c_v(),.c_d(),.sw_v(),.sw_a(),.sw_m(),.sw_d(),.lo_v(5'd0),.lo_d(1280'd0),.p_v(pv_old),.p_d(pd),.rb_v(),.rb_d(),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'd0),.eg_c(2'd0),.eg_d(32'd0),.g_v(),.g_c(),.g_d(),.x_go(),.x_mode(),.x_eps(),.x_scale(),.x_sv(v[0]),.x_si(ix[0]),.x_s(data[0]),.x_rbv(1'd0),.x_rbd(32'd0),.is_v(),.is_d(),.cfg_v(),.cfg_d(),.fault(f[0]));
ot_s81sl_xrt1 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'd512),.QDELAYS(128'd0)) u_1 (.clk(ck),.rst_n(rst_n),.sid(4'd0),.dl_ev(1'd0),.dl_e(1075'd0),.dl_wv(1'd0),.dl_w(1075'd0),.dl_vv(1'd0),.dl_vb(275'd0),.ci_dir(),.ci_b(),.c_v(),.c_d(),.sw_v(),.sw_a(),.sw_m(),.sw_d(),.lo_v(5'd0),.lo_d(1280'd0),.p_v(pv_new),.p_d(pd),.rb_v(),.rb_d(),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'd0),.eg_c(2'd0),.eg_d(32'd0),.g_v(),.g_c(),.g_d(),.x_go(),.x_mode(),.x_eps(),.x_scale(),.x_sv(v[1]),.x_si(ix[1]),.x_s(data[1]),.x_rbv(1'd0),.x_rbd(32'd0),.is_v(),.is_d(),.cfg_v(),.cfg_d(),.fault(f[1]));
ot_s81sl_xrt1 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'd576),.QDELAYS(128'd0)) u_2 (.clk(ck),.rst_n(rst_n),.sid(4'd0),.dl_ev(1'd0),.dl_e(1075'd0),.dl_wv(1'd0),.dl_w(1075'd0),.dl_vv(1'd0),.dl_vb(275'd0),.ci_dir(),.ci_b(),.c_v(),.c_d(),.sw_v(),.sw_a(),.sw_m(),.sw_d(),.lo_v(5'd0),.lo_d(1280'd0),.p_v(pv_new),.p_d(pd),.rb_v(),.rb_d(),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'd0),.eg_c(2'd0),.eg_d(32'd0),.g_v(),.g_c(),.g_d(),.x_go(),.x_mode(),.x_eps(),.x_scale(),.x_sv(v[2]),.x_si(ix[2]),.x_s(data[2]),.x_rbv(1'd0),.x_rbd(32'd0),.is_v(),.is_d(),.cfg_v(),.cfg_d(),.fault(f[2]));
ot_s81sl_xrt3 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'd668),.QDELAYS(128'd0)) u_3 (.clk(ck),.rst_n(rst_n),.sid(4'd6),.dl_ev(1'd0),.dl_e(1075'd0),.dl_wv(1'd0),.dl_w(1075'd0),.dl_vv(1'd0),.dl_vb(275'd0),.ci_dir(),.ci_b(),.bi(1046'd0),.bo(),.c_v(),.c_d(),.sw_v(),.sw_a(),.sw_m(),.sw_d(),.lo_v(5'd0),.lo_d(1280'd0),.p_v(pv_old),.p_d(pd),.rb_v(),.rb_d(),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'd0),.eg_c(2'd0),.eg_d(32'd0),.g_v(),.g_c(),.g_d(),.x_go(),.x_mode(),.x_eps(),.x_scale(),.x_sv(v[3]),.x_si(ix[3]),.x_s(data[3]),.x_rbv(1'd0),.x_rbd(32'd0),.is_v(),.is_d(),.cfg_v(),.cfg_d(),.fault(f[3]));
ot_s81sl_xrt3 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'd512),.QDELAYS(128'd0)) u_4 (.clk(ck),.rst_n(rst_n),.sid(4'd6),.dl_ev(1'd0),.dl_e(1075'd0),.dl_wv(1'd0),.dl_w(1075'd0),.dl_vv(1'd0),.dl_vb(275'd0),.ci_dir(),.ci_b(),.bi(1046'd0),.bo(),.c_v(),.c_d(),.sw_v(),.sw_a(),.sw_m(),.sw_d(),.lo_v(5'd0),.lo_d(1280'd0),.p_v(pv_new),.p_d(pd),.rb_v(),.rb_d(),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'd0),.eg_c(2'd0),.eg_d(32'd0),.g_v(),.g_c(),.g_d(),.x_go(),.x_mode(),.x_eps(),.x_scale(),.x_sv(v[4]),.x_si(ix[4]),.x_s(data[4]),.x_rbv(1'd0),.x_rbd(32'd0),.is_v(),.is_d(),.cfg_v(),.cfg_d(),.fault(f[4]));
ot_s81sl_xrt3 #(.FACE_LAND(1),.FOREG(0),.PDSK(15'd576),.QDELAYS(128'd0)) u_5 (.clk(ck),.rst_n(rst_n),.sid(4'd6),.dl_ev(1'd0),.dl_e(1075'd0),.dl_wv(1'd0),.dl_w(1075'd0),.dl_vv(1'd0),.dl_vb(275'd0),.ci_dir(),.ci_b(),.bi(1046'd0),.bo(),.c_v(),.c_d(),.sw_v(),.sw_a(),.sw_m(),.sw_d(),.lo_v(5'd0),.lo_d(1280'd0),.p_v(pv_new),.p_d(pd),.rb_v(),.rb_d(),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'd0),.eg_c(2'd0),.eg_d(32'd0),.g_v(),.g_c(),.g_d(),.x_go(),.x_mode(),.x_eps(),.x_scale(),.x_sv(v[5]),.x_si(ix[5]),.x_s(data[5]),.x_rbv(1'd0),.x_rbd(32'd0),.is_v(),.is_d(),.cfg_v(),.cfg_d(),.fault(f[5]));
initial begin count[0]=0;count[1]=0;mut_seen[0]=0;mut_seen[1]=0;end
always @(negedge ck) begin
 if(cyc==64)rst_n=1;
 pv_old=0;pv_new=0;
 if(cyc>=100&&cyc<100+64*24)begin
  phase=(cyc-100)%24;j=(cyc-100)/24;
  for(k=0;k<5;k=k+1)begin pd[32*k+:32]=32'h3f000000|(32'(j)<<8)|32'(k);if(phase==k)pv_old[k]=1;if(phase==(k==3?3:4))pv_new[k]=1;end
 end
end
always @(posedge ck)begin cyc=cyc+1;#0.000001;
 if(cyc>90)for(integer h=0;h<2;h=h+1)begin
  checks=checks+1;
  if(f[3*h]||f[3*h+1]||v[3*h]!==v[3*h+1]||(v[3*h]&&{ix[3*h],data[3*h]}!=={ix[3*h+1],data[3*h+1]}))begin errors=errors+1;if(errors<8)$display("BAD cycle%0d hb%0d v%b f%b",cyc,h,v,f);end
  if(v[3*h])begin
   if(count[h]<5)$display("PDSK_SERIALIZER_FIRST cls%0d leaf%0d cycle%0d aligned_input_epoch104 fixed_edges%0d",h,ix[3*h],cyc,cyc-104-int'(ix[3*h]));
   if(ix[3*h]!==7'(count[h]%5)||data[3*h] !== (32'h3f000000|(32'(count[h]/5)<<8)|32'(count[h]%5)))errors=errors+1;
   count[h]=count[h]+1;
  end
  if(f[3*h+2])mut_seen[h]=1;
 end
 if(cyc==1700)begin
  if(count[0]!=320||count[1]!=320||!mut_seen[0]||!mut_seen[1])errors=errors+1;
  $display("PDSK_LOCKSTEP checks%0d words%0d/%0d mutants%0d/%0d errors%0d clock_ps833",checks,count[0],count[1],mut_seen[0],mut_seen[1],errors);
  if(errors==0)$display("PDSK_LOCKSTEP_PASS");else $fatal(1,"PDSK_LOCKSTEP_FAIL");$finish;
 end
end
endmodule
