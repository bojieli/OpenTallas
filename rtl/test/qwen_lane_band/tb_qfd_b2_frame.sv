`timescale 1ns/1ps
// Exercise BOTH real production frame consumers and the optimized QOTS_SMALL path.
module tb_qfd_b2_frame;
 parameter integer MUT=0;
 reg ck=0; always #5 ck=~ck;
 reg rst_n=0;
 reg [15:0] pt;
 reg [112:0] tag;
 ot_qwen_me_spctl_w12 #(.GT(3072),.SMIN(7),.TCUT(7),.NW(18),.BANDF(MUT==1 ? 1:2)) u_ctl (.clk(ck),.rst_n(rst_n));
 ot_qwen_me_spport_w12 #(.GT(3072),.SMIN(7),.TCUT(7),.NW(18),.PQ(1),.TREE_LAT(7),.BANDF(MUT==2 ? 1:2),.QOTS_SMALL(1)) u_port
   (.clk(ck),.rst_n(rst_n),.ck_mul(16'd0),.pt_id(pt),.a_f_e2(tag),.a_v_e2(1'b1),.lv_in(512'd0),.scale_q(256'd0));
 integer s,p,h,k,g,ok,checks=0,nactive,ots,step;
 reg [16:0] want,cf,pf;
 initial begin
  pt=0;tag=0;repeat(3) @(negedge ck);rst_n=1;
  for(s=7;s<=12;s=s+1) begin
   nactive=0;
   for(p=0;p<24;p=p+1) begin
    h=p/4;k=p%4;
    if(s<=9) begin ok=k<(1<<(9-s));g=h*(1<<(9-s))+k;end
    else begin ok=h==0 && k<(3072>>s);g=k;end
    want={1'(ok),16'(g)};
    cf=u_ctl.bframe(4'(s),p);pf=u_port.bframe(4'(s),p);
    if(cf!==want || pf!==want) $fatal(1,"frame s%0d p%0d want%h ctl%h port%h",s,p,want,cf,pf);
    for(step=0;step<4;step=step+1) begin
     ots=(step==0)?1:(step==1)?8:(step==2)?23:16777215;
     pt=p; tag={1'b1,1'b1,1'b0,1'b0,4'(s),24'd17,24'(ots),19'd0,19'd0,19'd16384};
     @(negedge ck);
     if(u_port.e_gok[0]!==1'(ok)) $fatal(1,"active s%0d p%0d",s,p);
     if(ok && u_port.e_qots!==24'(g*ots)) $fatal(1,"qots s%0d p%0d g%0d ots%0d got%0d",s,p,g,ots,u_port.e_qots);
     checks=checks+1;
    end
    nactive=nactive+ok;
   end
   if(nactive!=(3072>>s)) $fatal(1,"coverage s%0d active%0d",s,nactive);
   if(s<=11 && nactive==0) $fatal(1,"vacuous production split%0d",s);
  end
  $display("PASS qfd_b2_frame actual controller+port, QOTS_SMALL rows, checks=%0d; split12 explicitly empty",checks);$finish;
 end
endmodule
