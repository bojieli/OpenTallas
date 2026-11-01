`timescale 1ps/1fs
module tb_v_transit;
reg ck=0;always #416.5 ck=~ck;reg rst_n=0;reg[275:0]vs=0,vn=0;
wire[275:0]seq_s,seq_n;wire[275:0]gs[0:6],gn[0:6];wire gf;integer cyc=0,errors=0,seen=0,mut=0;reg[275:0]hs[0:1023],hn[0:1023];integer age[0:3];integer counts[0:3];
assign gn[0]=vs;assign gs[6]=vn;
for(genvar g=0;g<6;g++)begin:st
 if(g==2)begin
 ot_dsdv_vstop #(.V(276),.JREG(0)) v(.clk(ck),.rst_n(rst_n),.tap_k(8'h81),.sink_k(8'h81),.bk_uid(8'd0),
  .vi_s(gn[g]),.vo_n(gn[g+1]),.vi_n(gs[g+1]),.vo_s(gs[g]),.in_nv(1'b0),.in_n(276'd0),.in_sv(1'b0),.in_s(276'd0),.fault(gf));
 end else begin
 dsdv_gunit_pass #(.W(276),.N(2)) up(.clk(ck),.rst_n(rst_n),.d(gn[g]),.q(gn[g+1]));
 dsdv_gunit_pass #(.W(276),.N(2)) dn(.clk(ck),.rst_n(rst_n),.d(gs[g+1]),.q(gs[g]));
 end
end
dsdv_seq_host_mux #(.SELR(1),.STATIC_KS6(0)) seq(.ck(ck),.rst_n(rst_n),.tap_k(8'h01),.sink_k(8'h01),.vi_s(vs),.vi_n(vn),.vo_s(seq_s),.vo_n(seq_n),
 .f_host(515'd0),.f_lf(4'd0),.f_ks(53'd0),.s_jd_w(2'd0),.s_jd_e(2'd0),.s_hc_w(9'd0),.s_hc_e(9'd0),.st_rg_w(2'd0),.st_rg_e(2'd0),.mu_rt_7n(32'd0),.mu_rt_0n(32'd0));
function automatic[275:0]beat(input integer c,input integer direction);integer tr,fr;reg[275:0]x;begin
 x=0;if(c>=100&&c<612)begin tr=(c-100)/16;fr=(c-100)%16;if(fr<4)begin
 x={8{32'h12345678+32'(17*tr+fr+direction)}};x[275:256]=20'habcde+20'(16*tr+fr+direction);x[7:0]=8'(fr+direction);
 if(fr==0)begin x[0]=1;x[3:1]=3'(1+tr%2);x[8:4]=1;x[20:13]=8'(tr);end
 end end beat=x;end endfunction
always @(negedge ck)begin if(cyc==32)rst_n=1;vs=beat(cyc,0);vn=beat(cyc,1);hs[cyc]=vs;hn[cyc]=vn;end
task automatic check(input integer which,input[275:0]out,input integer direction);integer found;begin
 if(out!=0&&cyc>70)begin found=-1;for(integer j=1;j<32;j++)if(cyc>=j&&out==(direction?hn[cyc-j]:hs[cyc-j]))found=j;
 if(found<0)begin errors++;if(errors<5)$display("V_TRANSIT_BAD which%0d cyc%0d data%h",which,cyc,out);end
 else begin if(age[which]<0)age[which]=found;else if(age[which]!=found+mut)errors++;counts[which]++;end end
end endtask
always @(posedge ck)begin cyc=cyc+1;#0.001;check(0,gn[6],0);check(1,gs[0],1);check(2,seq_n,0);check(3,seq_s,1);
 if(cyc==800)begin for(integer i=0;i<4;i++)begin $display("V_TRANSIT channel%0d age%0d words%0d",i,age[i],counts[i]);if(counts[i]!=128)errors++;end
 if(gf)errors++;$display("V_TRANSIT_RESULT errors%0d clock833",errors);if(errors==0)$display("V_TRANSIT_PASS");else $fatal(1,"V_TRANSIT_FAIL");$finish;end end
initial begin mut=$test$plusargs("mut_phase");for(integer i=0;i<1024;i++)begin hs[i]=0;hn[i]=0;end for(integer j=0;j<4;j++)begin age[j]=-1;counts[j]=0;end end
endmodule
