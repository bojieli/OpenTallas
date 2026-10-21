`timescale 1ns/1ps
module tb_cr2;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[7:0]tap_k=0,sink_k=0;
 reg[275:0]vi_s=0,vi_n=0;reg[514:0]f_host=0;reg[3:0]f_lf=0;
 reg[52:0]f_ks=0;reg[1:0]s_jd_w=0,s_jd_e=0,st_rg_w=0,st_rg_e=0;
 reg[8:0]s_hc_w=0,s_hc_e=0;
 wire[275:0]vo_s[0:2],vo_n[0:2];wire[76:0]t_host[0:2];wire[53:0]t_kd[0:2];wire[32:0]s_j[0:2];
 wire[291:0]s_hw_w[0:2],s_hw_e[0:2];wire cw_v[0:2];wire[9:0]cw_a[0:2];wire[255:0]cw_d[0:2];
 wire[1566:0]out[0:2];
 for(genvar i=0;i<3;i=i+1)begin:g
  if(i==0)begin:r
   dsdv_seq_host #(.V(276),.STAGE(0),.MUT(0),.RL(1))u(.ck(ck),.rst_n(rst_n),.tap_k(tap_k),.sink_k(sink_k),.vi_s(vi_s),.vi_n(vi_n),.vo_s(vo_s[i]),.vo_n(vo_n[i]),.f_host(f_host),.t_host(t_host[i]),.f_lf(f_lf),.f_ks(f_ks),.t_kd(t_kd[i]),.s_j(s_j[i]),.s_jd_w(s_jd_w),.s_jd_e(s_jd_e),.s_hw_w(s_hw_w[i]),.s_hw_e(s_hw_e[i]),.s_hc_w(s_hc_w),.s_hc_e(s_hc_e),.st_rg_w(st_rg_w),.st_rg_e(st_rg_e),.cw_v(cw_v[i]),.cw_a(cw_a[i]),.cw_d(cw_d[i]));
  end else begin:c
   dsdv_seq_host_cr2 #(.V(276),.STAGE(0),.MUT(0),.RL(1),.RUNG_MUT(i==2?1:0))u(.ck(ck),.rst_n(rst_n),.tap_k(tap_k),.sink_k(sink_k),.vi_s(vi_s),.vi_n(vi_n),.vo_s(vo_s[i]),.vo_n(vo_n[i]),.f_host(f_host),.t_host(t_host[i]),.f_lf(f_lf),.f_ks(f_ks),.t_kd(t_kd[i]),.s_j(s_j[i]),.s_jd_w(s_jd_w),.s_jd_e(s_jd_e),.s_hw_w(s_hw_w[i]),.s_hw_e(s_hw_e[i]),.s_hc_w(s_hc_w),.s_hc_e(s_hc_e),.st_rg_w(st_rg_w),.st_rg_e(st_rg_e),.cw_v(cw_v[i]),.cw_a(cw_a[i]),.cw_d(cw_d[i]));
  end
  assign out[i]={vo_s[i],vo_n[i],t_host[i],t_kd[i],s_j[i],s_hw_w[i],s_hw_e[i],cw_v[i],cw_a[i],cw_d[i]};
 end
 integer checks=0,errors=0,mutant=0;reg[31:0]rng=32'h92831a7;
 function automatic[31:0]step(input[31:0]x);step=(x<<1)^{32{ x[31]^x[21]^x[1]^x[0]}};endfunction
 initial begin
  for(integer epoch=0;epoch<3;epoch=epoch+1)begin
   @(negedge ck);rst_n=0;f_host=0;f_ks=0;vi_s=0;vi_n=0;repeat(12)@(negedge ck);rst_n=1;
   for(integer c=0;c<1800;c=c+1)begin
    rng=step(rng);f_lf=0;s_hc_w=0;s_hc_e=0;s_jd_w=0;s_jd_e=0;st_rg_w=rng[23:22];st_rg_e=rng[25:24];
    for(integer b=0;b<9;b=b+1)begin rng=step(rng);vi_s=(vi_s<<32)^rng;rng=step(rng);vi_n=(vi_n<<32)^rng;end
    // Rung-only graph/age witness: no HOST/job transaction or malformed descriptor.
    f_host=0;f_ks=0;
    @(posedge ck);#1;
    if(c>200)begin checks=checks+1;if(out[1]!==out[0])begin errors=errors+1;if(errors<4)$display("CR2_MISMATCH e=%0d c=%0d",epoch,c);end
     if(out[2]!==out[0])mutant=mutant+1;
    end
    @(negedge ck);
   end
  end
  $display("CR2_RESULT checks=%0d output_bits=1567 errors=%0d missing_rung_mismatches=%0d",checks,errors,mutant);
  if(checks<4500||errors!=0||mutant<1000)$fatal(1,"compact+rungs constructor qualification");$finish;
 end
endmodule
