`timescale 1ns/1ps
module tb_hgi_ctlw_lane2_equiv;
 parameter integer MUT = 0;
 reg clk=0; always #1 clk=~clk; reg rst_n=0;
 reg [1:0] sl=0; reg st_go=0,dr_go=0; reg[143:0]lo=0,hi=0; reg[113:0]lb=0; reg[5:0]rv=0;reg[125:0]ds=0;
 reg[47:0]dlo=0,dhi=0;reg[37:0]dlb=0;reg[1:0]drv=0;reg[41:0]dds=0;
 reg[7:0]rcr=0,wcr=0,wdn=0;reg[2055:0]rr=0;reg[2047:0]rd=0;reg[63:0]dm=0;reg[7:0]rrv=0;
wire[127:0]r_rq;wire[2239:0]r_wq;wire[7:0]r_sv,r_cv,r_dv;wire[119:0]r_ss,r_cs,r_ds;wire[2047:0]r_sd;wire r_st,r_dr,r_ov;
wire[127:0]h_rq;wire[2239:0]h_wq;wire[7:0]h_sv,h_cv,h_dv;wire[119:0]h_ss,h_cs,h_ds;wire[2047:0]h_sd;wire h_st,h_dr,h_ov;
ot_hgi_su_ctlw_slice_pre_ref #(.NL(8),.LWB(18),.LQ(8),.LQSRAM(0)) ref0 ( .clk(clk), .rst_n(rst_n), .sl_i(sl), .wst_go_i(st_go), .wdr_go_i(dr_go),
 .lo_i(lo), .hi_i(hi), .lb_i(lb), .rv_i(rv), .dsec_i(ds), .d_lo_i(dlo), .d_hi_i(dhi), .d_lb_i(dlb), .d_rv_i(drv), .d_dsec_i(dds), .d_os_i(1'b0),
 .wst_dn_i(1'b1), .wdr_dn_i(1'b1), .ovf_i(1'b0), .wrq_cr(rcr), .wrr(rr), .wwq_cr(wcr), .wwq_done(wdn),
 .ldr_d(rd), .ldr_dm(dm), .ldr_rv(rrv),
 .wrq(r_rq), .wwq(r_wq), .lsw_v(r_sv), .lsw_sec(r_ss), .lsw_d(r_sd), .ldc_v(r_cv), .ldc_sec(r_cs), .ldr_v(r_dv), .ldr_sec(r_ds),
 .wst_dn(r_st), .wdr_dn(r_dr), .ovf(r_ov));
ot_hgi_su_ctlw_slice_h #(.NL(8),.LWB(18),.LQ(8),.MUT_W(MUT)) hier ( .clk(clk), .rst_n(rst_n), .sl_i(sl), .wst_go_i(st_go), .wdr_go_i(dr_go),
 .lo_i(lo), .hi_i(hi), .lb_i(lb), .rv_i(rv), .dsec_i(ds), .d_lo_i(dlo), .d_hi_i(dhi), .d_lb_i(dlb), .d_rv_i(drv), .d_dsec_i(dds), .d_os_i(1'b0),
 .wst_dn_i(1'b1), .wdr_dn_i(1'b1), .ovf_i(1'b0), .wrq_cr(hrcr), .wrr(hrr), .wwq_cr(hwcr), .wwq_done(hwdn),
 .ldr_d(hrd), .ldr_dm(hdm), .ldr_rv(hrrv),
 .wrq(h_rq), .wwq(h_wq), .lsw_v(h_sv), .lsw_sec(h_ss), .lsw_d(h_sd), .ldc_v(h_cv), .ldc_sec(h_cs), .ldr_v(h_dv), .ldr_sec(h_ds),
 .wst_dn(h_st), .wdr_dn(h_dr), .ovf(h_ov));

 // el1013-hbm-qdq: the physical cluster relays descriptor / go through f0 -> fm before the leaves (LAG = 2 edges), so the
 // hierarchy is the reference delayed by LAG: its responses are the reference's delayed by LAG, every output is compared
 // against the reference's LAG edges earlier, the combined flags LAG + 1 (the AND4 / OR4 register).
 localparam integer LAG = 2;
 localparam integer SW = 8+8+8+2056+2048+64+8, OW = 128+2240+8+8+8+120+120+120+2048;
 reg [SW-1:0] sp [0:LAG-1]; reg [OW-1:0] op [0:LAG-1]; reg [2:0] fp [0:LAG];
 wire[7:0]hrcr,hwcr,hwdn;wire[2055:0]hrr;wire[2047:0]hrd;wire[63:0]hdm;wire[7:0]hrrv;
 assign {hrcr,hwcr,hwdn,hrr,hrd,hdm,hrrv} = sp[LAG-1];
 wire[127:0]q_rq;wire[2239:0]q_wq;wire[7:0]q_sv,q_cv,q_dv;wire[119:0]q_ss,q_cs,q_ds;wire[2047:0]q_sd;
 assign {q_rq,q_wq,q_sv,q_cv,q_dv,q_ss,q_cs,q_ds,q_sd} = op[LAG-1];
 always @(posedge clk) begin
   sp[0] <= {rcr,wcr,wdn,rr,rd,dm,rrv}; op[0] <= {r_rq,r_wq,r_sv,r_cv,r_dv,r_ss,r_cs,r_ds,r_sd}; fp[0] <= {r_st,r_dr,r_ov};
   for (integer k=1;k<LAG;k=k+1) begin sp[k] <= sp[k-1]; op[k] <= op[k-1]; end
   for (integer k=1;k<=LAG;k=k+1) fp[k] <= fp[k-1];
 end
 initial begin for (integer k=0;k<LAG;k=k+1) begin sp[k]=0; op[k]=0; end for (integer k=0;k<=LAG;k=k+1) fp[k]=3'b110; end
 reg[127:0]rq_pipe[0:2];reg[119:0]ds_pipe[0:2];reg[7:0]dv_pipe[0:2];
 integer checks=0, cycles=0, sectors=0;
 always @(posedge clk) begin
   rq_pipe[0]<=r_rq;rq_pipe[1]<=rq_pipe[0];rq_pipe[2]<=rq_pipe[1];
   ds_pipe[0]<=r_ds;ds_pipe[1]<=ds_pipe[0];ds_pipe[2]<=ds_pipe[1];
   dv_pipe[0]<=r_dv;dv_pipe[1]<=dv_pipe[0];dv_pipe[2]<=dv_pipe[1];
   for(integer b=0;b<8;b=b+1) begin
     rcr[b]<=r_rq[b*16+15];wcr[b]<=r_wq[b*280+279];wdn[b]<=r_wq[b*280+279];
     rr[b*257+256]<=rst_n&&rq_pipe[2][b*16+15];rrv[b]<=rst_n&&dv_pipe[2][b];
     dm[b*8+:8]<=ds_pipe[2][b*15] ? 8'h00 : 8'ha5;
     for(integer j=0;j<8;j=j+1) begin
       rr[b*257+j*32+:32]<=32'(rq_pipe[2][b*16+:15])*8+32'(j)+32'h1a000000;
       rd[b*256+j*32+:32]<=32'(ds_pipe[2][b*15+:15])*8+32'(j)+32'h2b000000;
     end
   end
 end
 always @(negedge clk) begin
   if(rst_n && cycles>12) begin
     if(h_sv!==q_sv||h_cv!==q_cv||h_dv!==q_dv) $fatal(1,"CTLW_EQ strobes cycle=%0d MUT=%0d",cycles,MUT);
     for(integer b=0;b<8;b=b+1) begin
       if(h_rq[b*16+15]!==q_rq[b*16+15]||h_wq[b*280+279]!==q_wq[b*280+279]) $fatal(1,"CTLW_EQ lanevalid");
       if(q_rq[b*16+15]&&h_rq[b*16+:15]!==q_rq[b*16+:15]) $fatal(1,"CTLW_EQ rq bank=%0d",b);
       if(q_sv[b]&&(h_ss[b*15+:15]!==q_ss[b*15+:15]||h_sd[b*256+:256]!==q_sd[b*256+:256])) $fatal(1,"CTLW_EQ landing bank=%0d MUT=%0d",b,MUT);
       if(q_cv[b]&&h_cs[b*15+:15]!==q_cs[b*15+:15]) $fatal(1,"CTLW_EQ clear bank=%0d",b);
       if(q_dv[b]&&h_ds[b*15+:15]!==q_ds[b*15+:15]) $fatal(1,"CTLW_EQ drain bank=%0d MUT=%0d",b,MUT);
       if(q_wq[b*280+279]&&h_wq[b*280+:279]!==q_wq[b*280+:279]) $fatal(1,"CTLW_EQ publish bank=%0d",b);
       sectors=sectors+32'(q_sv[b])+32'(q_cv[b])+32'(q_dv[b]);
     end
     if({h_st,h_dr,h_ov}!==fp[LAG]) $fatal(1,"CTLW_EQ combined flags cycle=%0d",cycles);
     checks=checks+1;
   end
   cycles=cycles+1;
 end
 initial begin
   for(integer k=0;k<3;k=k+1)begin rq_pipe[k]=0;ds_pipe[k]=0;dv_pipe[k]=0;end
   repeat(10)@(posedge clk);@(negedge clk);rst_n=1;
   for(integer c=0;c<4;c=c+1)begin
     @(negedge clk);sl=2'(c);lo=0;hi=0;lb=0;rv=0;ds=0;dlo=0;dhi=0;dlb=0;drv=0;dds=0;
     lo[0+:24]=0;hi[0+:24]=1023;rv[0]=1;
     lo[4*24+:24]=2048;hi[4*24+:24]=3071;lb[4*19+:19]=2048;rv[4]=1;
     dlo[0+:24]=2048;dhi[0+:24]=3071;dlb[0+:19]=2048;drv[0]=1;
     repeat(10)@(negedge clk);st_go=1;@(negedge clk);st_go=0;
     repeat(128)@(negedge clk);if(!r_st||!h_st)$fatal(1,"CTLW_EQ stage liveness");
     dr_go=1;@(negedge clk);dr_go=0;repeat(128)@(negedge clk);
     if(!r_dr||!h_dr)$fatal(1,"CTLW_EQ drain liveness");
   end
   if(sectors<256)$fatal(1,"CTLW_EQ insufficient traffic %0d",sectors);
   $display("PASS HGI_CTLW_LANE2_EQ checks=%0d sectors=%0d slices=4 combine_added=1 lag=%0d",checks,sectors,LAG);$finish;
 end
endmodule
