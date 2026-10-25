`timescale 1ns/1ps
// COMPONENT CUT ONLY: actual VP native ingress -> VN G8/D64 -> VQ.
// Each context starts under reset; this does not model simultaneous die epochs,
// MU72 DLK/LP transport, or the physical regional clock/reset release.
module tb_norm_leaf_source;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,cv=0,swv=0,rbv=0;
 reg [159:0]cd=0;reg[9:0]swa=0;reg[255:0]swd=0;
 reg[3:0]sid=0;reg[2:0]leaf=0;
 reg[127:0]data[0:48];reg[31:0]rstd[0:0];reg[159:0]normr[0:0];
 integer cyc=0,np=0,ny=0,nxf=0,with_rstd=0,mut=0;
 string dir,rstd_path;
 wire hv,hh,hrv,hrhf,hqv,nv,wlv,mv,mq,mb,pv,yv,xfv,xfs,pf,nf,qf;
 wire[2:0]hj,hrj,wli,yi;wire[255:0]hd,hqd,wld;wire[127:0]y;
 wire[127:0]pre;wire[7:0]mi;wire[31:0]pd;wire[275:0]xf;
 function automatic[159:0]cmd(input integer op,input integer a0,input integer a1,input integer n);
  reg[159:0]v;begin v=0;v[3:0]=op;v[13:4]=a0;v[23:14]=a1;v[31:24]=n;cmd=v;end
 endfunction
 ot_s81sl_vp vp(.clk(clk),.rst_n(rst_n),.c_v(cv),.c_d(cd),
  .sw_v(swv),.sw_a(swa),.sw_m(8'h0f),.sw_d(swd),.cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),
  .lo_v(),.lo_d(),.s_v(),.s_d(),.x_rv(1'b0),.x_ra(10'd0),.x_qv(),.x_qd(),
  .x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),
  .hw_v(hv),.hw_j(hj),.hw_hf(hh),.hw_d(hd),.hr_v(hrv),.hr_j(hrj),.hr_hf(hrhf),
  .hq_v(hqv),.hq_d(hqd),.n_go(nv),.n_pre(pre),.m_v(mv),.m_q(mq),.m_b(mb),.m_i(mi),
  .wl_v(wlv),.wl_i(wli),.wl_d(wld),.fault(pf));
 ot_s81sl_vn vn(.clk(clk),.rst_n(rst_n),.hw_v(hv),.hw_j(hj),.hw_hf(hh),.hw_d(hd),
  .hr_v(hrv),.hr_j(hrj),.hr_hf(hrhf),.hq_v(hqv),.hq_d(hqd),.n_go(nv),.n_pre(pre),
  .wl_v(wlv),.wl_i(wli),.wl_d(wld),.rb_v(rbv),.rb_d(rstd[0]),
  .p_v(pv),.p_d(pd),.y_v(yv),.y_i(yi),.y(y),.fault(nf));
 ot_s81sl_vq #(.AQ_XMEM(2)) vq(.clk(clk),.rst_n(rst_n),.y_v(yv),.y_i(yi),.y(y),
  .u_v(1'b0),.u_i(3'd0),.u(256'd0),.sid(sid),.k(leaf),.m_v(mv),.m_q(mq),.m_b(mb),.m_i(mi),
  .um_v(1'b0),.um_q(1'b0),.um_b(1'b0),.um_i(8'd0),.xf_v(xfv),.xf_s(xfs),.xf(xf),.fault(qf));
 integer i;reg[127:0]value;
 always @(negedge clk)begin
  if(cyc==32)rst_n=1;
  cv=0;cd=0;swv=0;swa=0;swd=0;rbv=0;
  for(i=0;i<49;i=i+1)if(cyc==64+2*i)begin
   value=data[i];if(mut==1&&i==0)value[0]=~value[0];
   swv=1;swa=(i<32)?i:((i<48)?64+i-32:1008);swd={value,value};
  end
  if(cyc==192)begin cv=1;cd=cmd(3,0,0,0);end
  if(cyc==224)begin cv=1;cd=cmd(1,64,0,0);end
  if(cyc==248)begin cv=1;cd=normr[0];end
  // Only the gate may supply a source-traced XFIN result, never an expectation.
  if(with_rstd&&cyc==800)rbv=1;
 end
 always @(posedge clk)begin
  if(rst_n)begin
   if(pv)begin np++;$display("LEAF_PARTIAL sid=%0d leaf=%0d cycle=%0d data=%08h",sid,leaf,cyc,pd);end
   if(yv)begin ny++;$display("LEAF_Y sid=%0d leaf=%0d cycle=%0d i=%0d data=%064h",sid,leaf,cyc,yi,y);end
   if(xfv)begin nxf++;$display("LEAF_XF sid=%0d leaf=%0d cycle=%0d first=%b data=%069h",sid,leaf,cyc,xfs,xf);end
  end
  if(cyc==1200)begin
   if(np!=1||pf||nf||qf||(with_rstd&&(ny!=8||nxf!=4))||(!with_rstd&&(ny||nxf)))
    $fatal(1,"LEAF_SOURCE_FAIL partials=%0d y=%0d xf=%0d faults=%b%b%b",np,ny,nxf,pf,nf,qf);
   $display("LEAF_SOURCE_PASS sid=%0d leaf=%0d with_rstd=%0d",sid,leaf,with_rstd);$finish;
  end
  cyc<=cyc+1;
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"NO_INPUT_DIR");
  void'($value$plusargs("SID=%d",sid));void'($value$plusargs("LEAF=%d",leaf));void'($value$plusargs("MUT=%d",mut));
  if(leaf>4)$fatal(1,"BAD_LEAF");
  rstd[0]=0;$readmemh({dir,"/native_sw128.hex"},data);
  $readmemh({dir,"/native_normr160.hex"},normr);
  if($value$plusargs("ACTUAL_RSTD=%s",rstd_path))begin with_rstd=1;$readmemh(rstd_path,rstd);end
  $display("LEAF_SOURCE_SCOPE sid=%0d leaf=%0d VP_native_ingress VN_G8_D64 VQ_AQ_XMEM2 common_component_clock_only=1",sid,leaf);
 end
endmodule
