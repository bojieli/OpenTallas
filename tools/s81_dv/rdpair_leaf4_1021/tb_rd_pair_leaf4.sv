`timescale 1ns/1ps
// Required one-pair native path cut: current XRT/RSTOPT/VP and actual slice DL4 relays.
module tb_rd_pair_leaf4;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,preload=0;integer mode=0,mut=0,cyc=0,rdpin=-1,bad=0,commits=0;
 reg[1103:0]line=0;reg[9:0]pa=128;reg[255:0]pd=256'hc065a100c065a101c065a102c065a103c065a104c065a105c065a106c065a107;
 wire[3:0]sid1=(mode==2)?4'd6:4'd5;
 wire[275:0]vo[0:1];wire[1103:0]roe[0:1],row[0:1],cib[0:1];wire[2:0]cid[0:1];
 wire[4:0]cv[0:1],swv[0:1],lov[0:1];wire[159:0]cd[0:1];
 wire[49:0]swa[0:1];wire[39:0]swm[0:1];wire[1279:0]swd[0:1],lod[0:1];wire[1:0]rf,xf,pf;
 wire[1:0]pcv,pswv,lv,qv;wire[159:0]pcd[0:1];wire[9:0]pswa[0:1];wire[7:0]pswm[0:1];wire[255:0]pswd[0:1],ld[0:1],qd[0:1];
 reg[1:0]rv=0;reg[9:0]ra=0;
 wire[275:0]vwire=(mode==1)?(vo[0]^(mut==1&&vo[0][0]?(276'd1<<17):276'd0)):276'd0;
 wire[1103:0]ewire=(mode==2)?roe[0]:1104'd0;
 function automatic[1103:0]ctl(input integer target,input[159:0]body);
  reg[185:0]p;begin p=0;p[15:0]=16'd16;p[20:16]=target;p[25:21]=(target==0)?1:0;p[185:26]=body;
   ctl=0;ctl[0]=1;ctl[8:4]=1;ctl[21+:186]=p;end
 endfunction
 task tick(input integer n);repeat(n)@(negedge clk);endtask
 genvar k;
 generate for(k=0;k<2;k=k+1)begin:g
  wire de,dw,dv;wire[1103:0]e,w;wire[275:0]v;
  ot_s81sl_rstopt r(.clk(clk),.rst_n(rst_n),.sid(k==0?4'd4:sid1),.ri_w(k==0?line:ewire),.ri_e(1104'd0),
   .ro_e(roe[k]),.ro_w(row[k]),.vi(k==1?vwire:276'd0),.vo(vo[k]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),
   .nx_eo(173'd0),.nx_wo(173'd0),.dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(v),.ci_dir(cid[k]),.ci_b(cib[k]),.fault(rf[k]));
  ot_s81sl_xrt x(.clk(clk),.rst_n(rst_n),.sid(k==0?4'd4:sid1),.dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(v),
   .ci_dir(cid[k]),.ci_b(cib[k]),.bi(1104'd0),.c_v(cv[k]),.c_d(cd[k]),.sw_v(swv[k]),.sw_a(swa[k]),.sw_m(swm[k]),.sw_d(swd[k]),
   .lo_v(lov[k]),.lo_d(lod[k]),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),
   .eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(xf[k]));
  // Exact W594 down / W667 up layouts and DL4 from ot_s81sl_slice u_dn/u_up.
  wire[435:0]down={cv[k][0],cd[k],(k==0&&preload)?1'b1:swv[k][0],(k==0&&preload)?pa:swa[k][9:0],
                       (k==0&&preload)?8'hff:swm[k][7:0],(k==0&&preload)?pd:swd[k][255:0]};
  // Control, SW, capture, norm and ENG faces retain the production word offsets.
  wire[157:0]unused_dn;wire[409:0]unused_up;
  ot_s81sl_rly #(.W(594),.D(4))dn(.clk(clk),.d({down,158'd0}),
   .q({pcv[k],pcd[k],pswv[k],pswa[k],pswm[k],pswd[k],unused_dn}));
  ot_s81sl_rly #(.W(667),.D(4))up(.clk(clk),.d({lv[k],ld[k],410'd0}),.q({lov[k][0],lod[k][255:0],unused_up}));
  assign lov[k][4:1]=0;assign lod[k][1279:256]=0;
  ot_s81sl_vp u(.clk(clk),.rst_n(rst_n),.c_v(pcv[k]),.c_d(pcd[k]),.sw_v(pswv[k]),.sw_a(pswa[k]),.sw_m(pswm[k]),.sw_d(pswd[k]),
   .cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),.lo_v(lv[k]),.lo_d(ld[k]),
   .x_rv(rv[k]),.x_ra(ra),.x_qv(qv[k]),.x_qd(qd[k]),.x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),
   .hq_v(1'b0),.hq_d(256'd0),.fault(pf[k]));
 end endgenerate
 integer xrcommand=-1,vpcommand=-1,vppair=-1,xrpair=-1,ciedge=-1,vout=-1,eout=-1,xrwrite=-1,vpwrite=-1,commit=-1;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(rst_n)begin
   if(line[0]&&line[21+16+:5]==0)rdpin=cyc;
   if(rdpin>=0)begin
    if(cv[0][0])xrcommand=cyc;
    if(pcv[0])vpcommand=cyc;
    if(lv[0])vppair=cyc;
    if(lov[0][0])xrpair=cyc;
    if(cib[0][0]&&cib[0][3:1]==4)ciedge=cyc;
    if(vo[0][0])vout=cyc;
    if(roe[0][0]&&roe[0][3:1]==4)eout=cyc;
    if(swv[mode==0?0:1][0])xrwrite=cyc;
    if(pswv[mode==0?0:1])vpwrite=cyc;
    if((mode==0&&g[0].u.u_b0.w_ce_in)||(mode!=0&&g[1].u.u_b0.w_ce_in))begin commits=commits+1;commit=cyc;end
   end
  end
 end
 reg[159:0]cfg,cmd;
 initial begin
  void'($value$plusargs("MODE=%d",mode));void'($value$plusargs("MUT=%d",mut));
  if(mode<0||mode>2)$fatal(1,"unsupported path");
  tick(32);rst_n=1;tick(32);preload=1;tick(1);preload=0;tick(16);
  cfg=0;cfg[3:0]=(mode==0)?0:((mode==1)?4:1);cfg[6:4]=4;cfg[11:7]=1;
  cfg[27:12]=16'd1<<((mode==0)?4:((mode==1)?5:6));cfg[40:31]=(mode==0)?480:692;cfg[44]=(mode==0);
  line=ctl(4,cfg);tick(1);line=0;tick(8);cmd=6|(128<<4)|(1<<24);line=ctl(0,cmd);tick(1);line=0;
  tick(80);ra=(mode==0)?480:692;rv=(mode==0)?1:2;tick(1);rv=0;
  wait(qv[mode==0?0:1]);@(negedge clk);if(qd[mode==0?0:1]!==pd)bad=bad+1;tick(8);
  if((|rf)||(|xf)||(|pf)||commits!=1)bad=bad+1;
  if(xrcommand-rdpin!=5||vpcommand-rdpin!=9||vppair-rdpin!=14||xrpair-rdpin!=18)bad=bad+1;
  if(mode==0&&(ciedge-rdpin!=22||xrwrite-rdpin!=25||vpwrite-rdpin!=29||commit-rdpin!=30))bad=bad+1;
  if(mode==1&&(vout-rdpin!=23||xrwrite-rdpin!=29||vpwrite-rdpin!=33||commit-rdpin!=34))bad=bad+1;
  $display("RDPAIR_LEAF4 mode=%0d mut=%0d bad=%0d rf=%h xf=%h pf=%h commits=%0d CTL=%0d XRcmd=%0d VPcmd=%0d VPlo=%0d XRlo=%0d CI=%0d Vout=%0d Eout=%0d XRsw=%0d VPsw=%0d SRAMcommit=%0d",mode,mut,bad,rf,xf,pf,commits,rdpin,xrcommand,vpcommand,vppair,xrpair,ciedge,vout,eout,xrwrite,vpwrite,commit);
  if(bad)$fatal(1,"RDPAIR_LEAF4 FAIL");$display("RDPAIR_LEAF4 PASS");$finish;
 end
 initial begin tick(512);$fatal(1,"finite static calendar failed");end
endmodule
