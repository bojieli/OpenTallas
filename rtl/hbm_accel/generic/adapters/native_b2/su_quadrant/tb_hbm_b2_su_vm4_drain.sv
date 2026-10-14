`timescale 1ps/1fs
`default_nettype none
module tb_hbm_b2_su_vm4_drain #(parameter integer MUT=0,PHASE=61,NSEC=512,PAIR=0);
 reg vclk=0;always #555.5555 vclk=~vclk; // Actual VM period1111.111ps, three edges per3333.333ps interval
 reg [3:0] cclk=0;for(genvar q=0;q<4;q=q+1)begin:clocks
  initial begin #(PHASE+q*17);forever #416.666625 cclk[q]=~cclk[q];end // Actual engine833.33325ps, four edges per interval
 end
 reg rst_n=0;initial begin #6000;rst_n=1;end
 wire [32*16-1:0] rq;wire [31:0] rc;wire [32*257-1:0] rr;wire [32*280-1:0] wq;wire [31:0] wc,wd,fault;wire [4*8*18-1:0] status;
 wire [31:0] cdrained,vdrained;wire [31:0] prc,pwc,pwd,dd;wire [32*257-1:0] prr;
 ot_hbm_b2_su_vm4_drain #(.MUT(MUT)) vehicle(.cclk(cclk),.vclk(vclk),.rst_n(rst_n),.permit(4'hf),.mirror(4'b0),.crq(rq),.crq_credit(rc),.crr(rr),.cwq(wq),.cwq_credit(wc),.cwq_done(wd),
  .peer_rq('0),.peer_rq_credit(prc),.peer_rr(prr),.peer_wq('0),.peer_wq_credit(pwc),.peer_wq_done(pwd),.dma_q('0),.dma_done(dd),.fault(fault),.bank_status(status),.cdrained(cdrained),.vdrained(vdrained));
 function automatic [255:0] value(input integer q,s);
  for(integer w=0;w<8;w=w+1)value[w*32+:32]=32'h12345678^(q<<24)^(s*8+w);
 endfunction
 wire [3:0] finished;integer checked[0:3];
 for(genvar q=0;q<4;q=q+1)begin:client
  localparam LWB=16,LSW=13;
  reg stgo=0,drgo=0;wire stdn,drdn,ov;
  wire [7:0] sv,cv,drv;wire [8*LSW-1:0] ss,cs,ds;wire [8*256-1:0] sd;
  reg [8*256-1:0] drdata=0;reg [63:0] drm=0;reg [7:0] drvalid=0;
  reg [143:0] lo=0,hi=0;reg [6*17-1:0] lb=0;reg [5:0] rv=1;
  reg [47:0] dlo=0,dhi=0;reg [33:0] dlb=0;
  wire dummygo,dummydr,dummyos;wire [143:0] dummylo,dummyhi;wire [101:0] dummylb;wire [5:0] dummyrv;wire [125:0] dummys;wire [47:0] dummydlo,dummydhi;wire [33:0] dummydlb;wire [1:0] dummydrv;wire [41:0] dummyds;
  `ifdef NATIVE_PAIR
  ot_hgi_su_ctlw_native_h #(.LWB(16),.LQ(10),.LQSRAM(1)) ctl(.clk(cclk[q]),.clk_p0(cclk[q]),.clk_p1(cclk[q]),.clk_p2(cclk[q]),.clk_p3(cclk[q]),
`else
  ot_hgi_su_ctlw_native_q #(.LWB(16),.LQ(10),.LQSRAM(1)) ctl(.clk(cclk[q]),
`endif
.rst_n(rst_n),.wst_go_i(stgo),.wdr_go_i(drgo),.lo_i(lo),.hi_i(hi),.lb_i(lb),.rv_i(rv),.dsec_i(126'b0),
   .d_lo_i(dlo),.d_hi_i(dhi),.d_lb_i(dlb),.d_rv_i(2'b01),.d_dsec_i(42'b0),.d_os_i(1'b0),.sl_i(2'(q)),
   .wst_go_o(dummygo),.wdr_go_o(dummydr),.d_os_o(dummyos),.lo_o(dummylo),.hi_o(dummyhi),.lb_o(dummylb),.rv_o(dummyrv),.dsec_o(dummys),
   .d_lo_o(dummydlo),.d_hi_o(dummydhi),.d_lb_o(dummydlb),.d_rv_o(dummydrv),.d_dsec_o(dummyds),.wst_dn_i(1'b1),.wdr_dn_i(1'b1),.ovf_i(1'b0),
   .wrq(rq[q*8*16+:8*16]),.wrq_cr(rc[q*8+:8]),.wrr(rr[q*8*257+:8*257]),.wwq(wq[q*8*280+:8*280]),.wwq_cr(wc[q*8+:8]),.wwq_done(wd[q*8+:8]),
   .lsw_v(sv),.lsw_sec(ss),.lsw_d(sd),.ldc_v(cv),.ldc_sec(cs),.ldr_v(drv),.ldr_sec(ds),.ldr_d(drdata),.ldr_dm(drm),.ldr_rv(drvalid),.wst_dn(stdn),.wdr_dn(drdn),.ovf(ov));
  reg done=0;assign finished[q]=done;
  integer ro[0:7],rcount[0:7],wo[0:7],wcount[0:7];
  initial for(integer b=0;b<8;b=b+1)begin ro[b]=0;rcount[b]=0;wo[b]=0;wcount[b]=0;end
  always @(posedge cclk[q])if(rst_n)for(integer b=0;b<8;b=b+1)begin
   if(cdrained[q*8+b]&&(ro[b]!=0||rcount[b]!=0||wo[b]!=0||wcount[b]!=0))$fatal(1,"premature drain quarter%0d bank%0d obligations=%0d/%0d/%0d/%0d",q,b,ro[b],rcount[b],wo[b],wcount[b]);
   ro[b]=ro[b]+rq[(q*8+b)*16+15]-rr[(q*8+b)*257+256];
   rcount[b]=rcount[b]+rq[(q*8+b)*16+15]-rc[q*8+b];
   wo[b]=wo[b]+wq[(q*8+b)*280+279]-wd[q*8+b];
   wcount[b]=wcount[b]+wq[(q*8+b)*280+279]-wc[q*8+b];
  end
  initial begin checked[q]=0;hi[23:0]=NSEC*8-1;dhi[23:0]=NSEC*8-1;
   wait(rst_n);repeat(24)@(negedge cclk[q]);drgo=1;@(negedge cclk[q]);drgo=0;
   wait(!drdn);wait(drdn);repeat(8)@(negedge cclk[q]);stgo=1;@(negedge cclk[q]);stgo=0;
   wait(!stdn);wait(stdn);repeat(8)@(negedge cclk[q]);
   if(checked[q]!=NSEC)$fatal(1,"quarter%0d missing payload sectors got%0d expected%0d",q,checked[q],NSEC);done=1;
  end
  always @(posedge cclk[q])if(rst_n)begin
   drvalid<=drv;
   for(integer b=0;b<8;b=b+1)begin
    drdata[b*256+:256]<=value(q,ds[b*LSW+:LSW]);drm[b*8+:8]<=8'hff;
    if(sv[b])begin
     if(ss[b*LSW+:LSW]>=NSEC||ss[b*LSW+:LSW]%8!=b||sd[b*256+:256]!==value(q,ss[b*LSW+:LSW]))$fatal(1,"native payload mismatch quarter%0d bank%0d sector%0d",q,b,ss[b*LSW+:LSW]);
     checked[q]=checked[q]+1;
    end
   end
   if(ov||(|fault[q*8+:8]))$fatal(1,"native client fault quarter%0d bank0 obligations=%0d/%0d/%0d/%0d next=%0d/%0d/%0d/%0d df=%b cf=%b vf=%b fifo=%h",q,vehicle.quad[q].lane[0].link.rresp,vehicle.quad[q].lane[0].link.rcred,vehicle.quad[q].lane[0].link.wcred,vehicle.quad[q].lane[0].link.wcommit,vehicle.quad[q].lane[0].link.nrresp,vehicle.quad[q].lane[0].link.nrcred,vehicle.quad[q].lane[0].link.nwcred,vehicle.quad[q].lane[0].link.nwcommit,vehicle.quad[q].lane[0].link.df,vehicle.quad[q].lane[0].link.cf,vehicle.quad[q].lane[0].link.vf,vehicle.quad[q].lane[0].link.faults);
  end
 end
 initial begin wait(&finished);repeat(16)@(negedge vclk);if(cdrained!==32'hffffffff||vdrained!==32'hffffffff)$fatal(1,"native drain incomplete source%h VM%h",cdrained,vdrained);$display("NATIVE_SU_VM4_DRAIN PASS quarters=4 sectors=%0d words=%0d LQ=10 RRS=3 WRS=3 client_edges=4 vm_edges=3 phase=%0d",4*NSEC,32*NSEC,PHASE);$finish;end
 initial begin #30000000;$fatal(1,"native4 timeout checked=%0d,%0d,%0d,%0d",checked[0],checked[1],checked[2],checked[3]);end
endmodule
`default_nettype wire
