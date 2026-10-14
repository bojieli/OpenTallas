`timescale 1ns/1ps
// Default-off transport candidate: explicit real credit pools, registered seams.
// Independent root ports are delivered at phi-R; functional common-clock proof
// does not establish physical clock delivery, pin reach or slot fit.
module qfd_proxy_stage #(parameter integer W=128,VW=1,CW=1)(
 input wire ck,rst_n,input wire[W-1:0]d,input wire[VW-1:0]v,
 output reg[W-1:0]q,output reg[VW-1:0]qv,
 input wire[CW-1:0]cr_in,output reg[CW-1:0]cr_out);
 always @(posedge ck)q<=d;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin qv<=0;cr_out<=0;end
 else begin qv<=v;cr_out<=cr_in;end
endmodule
module qfd_proxy_fifo #(parameter integer W=1024,DEPTH=4,INIT_OUT=12,VW=1,CW=1,FCW=1,MUT=0)(
 input wire ck,rst_n,input wire[W-1:0]d,input wire[VW-1:0]v,
 output reg cr,input wire[CW-1:0]out_cr,input wire[FCW-1:0]external_fault,
 output reg[W-1:0]q,output reg qv,output reg fault);
 localparam integer AW=$clog2(DEPTH),NG=W/128;
 reg rs0,rs;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin rs0<=0;rs<=0;end else begin rs0<=1;rs<=rs0;end
 reg[W-1:0]ci_d;reg[VW-1:0]ci_v;reg[CW-1:0]cr_q;reg[FCW-1:0]ff_q;
 always @(posedge ck)ci_d<=d;
 always @(posedge ck or negedge rs)if(!rs)begin ci_v<=0;cr_q<=0;ff_q<=0;end
 else begin ci_v<=v;cr_q<=out_cr;ff_q<=external_fault;end
 reg[AW:0]n;reg[7:0]oc;
 wire push=&ci_v;
 wire pop=(n!=0)&&(oc!=0)&&!fault;
 (* keep="true",dont_touch="true" *)reg[NG*AW-1:0]wp,rp;
 (* keep="true",dont_touch="true" *)reg[NG-1:0]pv;
 genvar g;
 generate for(g=0;g<NG;g=g+1)begin:g_bank
  reg[127:0]mem[0:DEPTH-1];
  wire[AW-1:0]wa=wp[g*AW+:AW],ra=rp[g*AW+:AW];
  always @(posedge ck)begin
   if(pv[g])mem[wa]<=ci_d[128*g+:128];
   q[128*g+:128]<=mem[ra]^((MUT==1&&g==0)?128'd1:128'd0);
  end
  always @(posedge ck or negedge rs)if(!rs)begin wp[g*AW+:AW]<=0;rp[g*AW+:AW]<=0;pv[g]<=0;end
  else begin
   pv[g]<=&v;
   if(push)wp[g*AW+:AW]<=(wa==DEPTH-1)?0:wa+1'b1;
   if(pop)rp[g*AW+:AW]<=(ra==DEPTH-1)?0:ra+1'b1;
  end
 end endgenerate
 always @(posedge ck or negedge rs)if(!rs)begin n<=0;oc<=INIT_OUT+((MUT==3)?1:0)-((MUT==5)?1:0);cr<=0;qv<=0;fault<=0;end
 else begin
  n<=n+(push?1'b1:1'b0)-(pop?1'b1:1'b0);
  oc<=oc-(pop?8'd1:8'd0)+(cr_q[0]?8'd1:8'd0);
  cr<=pop;qv<=pop;
  if((push&&n==DEPTH&&!pop)||(ci_v!=0&&ci_v!={VW{1'b1}})||
     (cr_q!=0&&cr_q!={CW{cr_q[0]}})||(|ff_q)||
     (cr_q[0]&&oc==INIT_OUT+((MUT==3)?1:0)&&!pop))fault<=1;
 end
endmodule
// Full128/RXD512 leaf has real12-word input store and13 initial R credits.
// It is a NEW parameter profile, not a renamed CLOSED IBUF4/OCRED4 leaf.
module qfd_link_adp128_p12 #(parameter integer MUT=0)(
 input wire ck,rst_n,c_v,input wire[127:0]c_d,output wire c_cr,r_v,
 output wire[127:0]r_d,input wire r_cr,tx_up,output wire tx_v,
 output wire[146:0]tx_flit,input wire rx_v,input wire[146:0]rx_flit,output wire fault);
 // Creditreturn is a registered input boundary, like capturedDATA/FDI.
 reg r_cr_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)r_cr_q<=0;else r_cr_q<=r_cr;
 ot_qfd_link_adapter #(.W(128),.IBUF(12),.OCRED(12),.RXD(512),.SRAM(1),.PINREG(1),.NG(1),.MUT(MUT))u_body
 (.clk(ck),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.c_cr(c_cr),.r_v(r_v),.r_d(r_d),.r_cr(r_cr_q),
 .tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),.rx_v(rx_v),.rx_flit(rx_flit),.fault(fault));
endmodule
module qfd_proxy_phy_guard(input wire ck,rst_n,input wire[1042:0]d,
 input wire[151:0]headers,input wire[7:0]v,output reg[1042:0]q,output reg qv,output reg fault);
 reg[1042:0]cap_d;reg[151:0]cap_h;reg[7:0]cap_v;integer i;reg equal;
 always @(posedge ck)begin cap_d<=d;cap_h<=headers;q<=cap_d;end
 always @*begin equal=1;for(i=1;i<8;i=i+1)if(cap_h[19*i+:19]!=cap_h[0+:19])equal=0;end
 always @(posedge ck or negedge rst_n)if(!rst_n)begin cap_v<=0;qv<=0;fault<=0;end
 else begin cap_v<=v;qv<=(&cap_v)&&equal&&!fault;
  if((cap_v!=0&&cap_v!=8'hff)||((|cap_v)&&!equal))fault<=1;
 end
endmodule
module qfd_link_adp512_proxy_candidate #(parameter integer ENABLE_PROXY=0,MUT=0)(
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
   qfd_proxy_stage #(.W(147))utx(.ck(ck[60+g]),.rst_n(rst_n),.d(tf),.v(tv[g]),.q(tx_leg),.qv(tx_leg_v),.cr_in(1'b0),.cr_out());
   assign tx_payload[128*g+:128]=tx_leg[18+:128];assign tx_headers[19*g+:19]={tx_leg[146],tx_leg[17:0]};assign tx_valid[g]=tx_leg_v;
   qfd_proxy_stage #(.W(148))urx(.ck(ck[69+g]),.rst_n(rst_n),.d({rx_all[1043],rx_all[1042],rx_all[18+128*g+:128],rx_all[17:0]}),.v(rx_pipe_v),.q(rx_leg),.qv(rx_leg_v),.cr_in(1'b0),.cr_out());
   assign up=rx_leg[147];assign rxp=rx_leg_v;assign rf=rx_leg[146:0];
   qfd_link_adp128_p12 #(.MUT(MUT==2&&g==7?2:0))u_leaf(.ck(ck[4+g]),.rst_n(rst_n),.c_v(c_final_v),.c_d(c_final),.c_cr(cc[g]),
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
