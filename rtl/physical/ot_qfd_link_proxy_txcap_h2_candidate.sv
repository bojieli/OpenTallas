`timescale 1ns/1ps
// Separate body/TX-clock leaf: relocates the existing proxy TX148 stage.
// Both entries are synchronous phase-family deliveries at their own phi-R.
// New physical profile, not the old CLOSED P12 abstract. No latency increase.
module qfd_link_adp128_p12_txcap_h2 #(parameter integer MUT=0)(
 input wire ck,ck_tx,rst_n,c_v,input wire[127:0]c_d,output wire c_cr,r_v,
 output wire[127:0]r_d,input wire r_cr,tx_up,output reg tx_v,
 output reg[146:0]tx_flit,input wire rx_v,input wire[146:0]rx_flit,output wire fault);
 wire tv;wire[146:0]tf;
 qfd_link_adp128_p12 #(.MUT(MUT))u_body(.ck(ck),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.c_cr(c_cr),
  .r_v(r_v),.r_d(r_d),.r_cr(r_cr),.tx_up(tx_up),.tx_v(tv),.tx_flit(tf),.rx_v(rx_v),.rx_flit(rx_flit),.fault(fault));
 always @(posedge ck_tx)tx_flit<=tf;
 always @(posedge ck_tx or negedge rst_n)if(!rst_n)tx_v<=0;else tx_v<=tv;
endmodule
module qfd_link_adp512_proxy_txcap_h2_candidate #(parameter integer ENABLE_PROXY=0,MUT=0)(
 input wire[77:0]ck,input wire rst_n,c_v,input wire[1023:0]c_d,
 output wire c_cr,r_v,output wire[1023:0]r_d,input wire r_cr,tx_up,
 output wire tx_v,output wire[1042:0]tx_flit,input wire rx_v,input wire[1042:0]rx_flit,output wire fault);
 generate if(!ENABLE_PROXY)begin:g_old
  qfd_link_adp512 #(.MUT(MUT))u_old(.ck(ck[0]),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.c_cr(c_cr),.r_v(r_v),.r_d(r_d),.r_cr(r_cr),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),.rx_v(rx_v),.rx_flit(rx_flit),.fault(fault));
 end else begin:g_new
  wire[1023:0]cd,rd_raw,rhalf;wire cv;wire[7:0]cc,rv,lf,tv,cback,rback,rff;
  wire[7:0]c_ret;wire[1:0]rh_v,rh_cr,rh_f;wire rg_f,pg_f;wire[1023:0]rg_d;wire rg_v;
  // Credits9 = five actual receiver slots + four real collector slots.
  // R-half heads receive only end-receiver returned credits, not collector pops.
  qfd_proxy_fifo #(.W(1024),.DEPTH(4),.INIT_OUT(12),.CW(8),.FCW(12),.MUT((MUT==1||MUT==3||MUT==5)?MUT:0))u_chead
  (.ck(ck[0]),.rst_n(rst_n),.d(c_d),.v(c_v),.cr(c_cr),.out_cr(c_ret),
   .external_fault({pg_f,rg_f,rh_f,rff}),.q(cd),.qv(cv),.fault(fault));
  wire[1043:0]rx_pipe;wire rx_pipe_v;wire[1023:0]tx_payload;wire[151:0]tx_headers;wire[7:0]tx_valid;
  genvar g,j;
  for(g=0;g<8;g=g+1)begin:g_lane
   wire[3*128-1:0]cp;wire[2:0]cpv,cpcr;
   wire[3*128-1:0]rp;wire[2:0]rpv,rpcr,rpf;
   wire[146:0]tf,rf;wire up;wire rxp;wire[147:0]rx_leg;wire rx_leg_v;
   wire[127:0]c_final;wire c_final_v;
   for(j=0;j<3;j=j+1)begin:g_cpipe
    qfd_proxy_stage #(.W(128))u(.ck(ck[12+3*g+j]),.rst_n(rst_n),
     .d(j==0?cd[128*g+:128]:cp[128*(j-1)+:128]),.v(j==0?cv:cpv[j-1]),
     .q(cp[128*j+:128]),.qv(cpv[j]),.cr_in(j==2?cc[g]:cpcr[j+1]),.cr_out(cpcr[j]));
   end
   if(MUT==4&&g==7)begin:g_epoch_mut
    qfd_proxy_stage #(.W(128))u(.ck(ck[0]),.rst_n(rst_n),.d(cp[256+:128]),.v(cpv[2]),.q(c_final),.qv(c_final_v),.cr_in(1'b0),.cr_out());
   end else begin:g_epoch_ok assign c_final=cp[256+:128];assign c_final_v=cpv[2];end
   assign c_ret[g]=cpcr[0];
   for(j=0;j<3;j=j+1)begin:g_rpipe
    qfd_proxy_stage #(.W(128),.VW(2))u(.ck(ck[36+3*g+j]),.rst_n(rst_n),
     .d(j==0?rd_raw[128*g+:128]:rp[128*(j-1)+:128]),
     .v(j==0?{lf[g],rv[g]}:{rpf[j-1],rpv[j-1]}),
     .q(rp[128*j+:128]),.qv({rpf[j],rpv[j]}),
     .cr_in(j==2?rh_cr[g/4]:rpcr[j+1]),.cr_out(rpcr[j]));
   end
   assign rhalf[128*g+:128]=rp[256+:128];assign rback[g]=rpcr[0];assign cback[g]=rpv[2];assign rff[g]=rpf[2];
   wire[146:0]tx_leg;wire tx_leg_v;wire[1043:0]rx_all;
   assign rx_all=rx_pipe;
   // ExistingTXcapture relocatedinto the typedtwo-root leaf, noaddedcycle.
   assign tx_leg=tf;assign tx_leg_v=tv[g];
   assign tx_payload[128*g+:128]=tx_leg[18+:128];assign tx_headers[19*g+:19]={tx_leg[146],tx_leg[17:0]};assign tx_valid[g]=tx_leg_v;
   qfd_proxy_stage #(.W(148))urx(.ck(ck[69+g]),.rst_n(rst_n),.d({rx_all[1043],rx_all[1042],rx_all[18+128*g+:128],rx_all[17:0]}),.v(rx_pipe_v),.q(rx_leg),.qv(rx_leg_v),.cr_in(1'b0),.cr_out());
   assign up=rx_leg[147];assign rxp=rx_leg_v;assign rf=rx_leg[146:0];
   qfd_link_adp128_p12_txcap_h2 #(.MUT(MUT==2&&g==7?2:0))u_leaf(.ck(ck[4+g]),.ck_tx(ck[60+g]),.rst_n(rst_n),.c_v(c_final_v),.c_d(c_final),.c_cr(cc[g]),
    .r_v(rv[g]),.r_d(rd_raw[128*g+:128]),.r_cr(rback[g]),.tx_up(up),.tx_v(tv[g]),.tx_flit(tf),.rx_v(rxp),.rx_flit(rf),.fault(lf[g]));
  end
  // RX common pin capture plus lane-specific registered delivery.
  qfd_proxy_stage #(.W(1044))u_rx_common(.ck(ck[68]),.rst_n(rst_n),.d({tx_up,rx_flit}),.v(rx_v),.q(rx_pipe),.qv(rx_pipe_v),.cr_in(1'b0),.cr_out());
  qfd_proxy_phy_guard u_pg(.ck(ck[3]),.rst_n(rst_n),.d({tx_headers[18],tx_payload,tx_headers[17:0]}),.headers(tx_headers),.v(tx_valid),.q(tx_flit),.qv(tx_v),.fault(pg_f));
  for(j=0;j<2;j=j+1)begin:g_rhead
   qfd_proxy_fifo #(.W(512),.DEPTH(16),.INIT_OUT(9),.VW(8))u(.ck(ck[1+j]),.rst_n(rst_n),.d(rhalf[512*j+:512]),.v(cback),.cr(rh_cr[j]),.out_cr(r_cr),.external_fault(1'b0),.q(rg_d[512*j+:512]),.qv(rh_v[j]),.fault(rh_f[j]));
  end
  qfd_proxy_fifo #(.W(1024),.DEPTH(4),.INIT_OUT(5),.VW(2))u_rg(.ck(ck[77]),.rst_n(rst_n),.d(rg_d),.v(rh_v),.cr(),.out_cr(r_cr),.external_fault(1'b0),.q(r_d),.qv(r_v),.fault(rg_f));
 end endgenerate
endmodule
