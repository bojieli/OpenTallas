`timescale 1ns/1ps
// Selected mapped native ASTK service: K-score/EXP/Z and actual e SRAM.
// Legacy P.V leaves, node inputs and their64clock roots are absent. The new
// native P.V service consumes er_data through the existing EP memory ports.
// All availability outputs are integrity observations; they never move slots.
// Static AGE0 is unsealed and rejected by the selected EP/CTL implementations.
module qkd_astk_native_stack_s #(
 parameter integer RL=1,STATIC_SCHEDULE=1,
 parameter integer EXP_START_AGE=0,LMAX_START_AGE=0,Z_START_AGE=0,Z_STRIDE=4
)(
  input wire ck_c,
  input wire [3:0] ck_z,
  input wire [31:0] ck_x,
  input wire [7:0] ck_e,
  input wire ck_r,
  input wire rst_n,
  input wire [1:0] st,
  input wire [539:0] aq,
  input wire [35:0] am,
  output wire [562:0] ap,
  output wire af,
  output wire [20:0] lt,
  input wire er_v,
  input wire [10:0] er_addr,
  output wire er_rsp_v,
  output wire [10:0] er_rsp_addr,
  output wire [63:0] er_data,
  output wire [15:0] exp_committed,
  output wire score_committed,
  input wire [424:0] so0,
  input wire [424:0] so1,
  input wire [424:0] so2,
  input wire [424:0] so3,
  input wire [424:0] so4,
  input wire [424:0] so5,
  input wire [424:0] so6,
  input wire [424:0] so7,
  output wire [633:0] si0,
  output wire [633:0] si1,
  output wire [633:0] si2,
  output wire [633:0] si3,
  output wire [633:0] si4,
  output wire [633:0] si5,
  output wire [633:0] si6,
  output wire [633:0] si7
);
 wire [3399:0] raw_so={so7,so6,so5,so4,so3,so2,so1,so0},ep_so;
 wire [5071:0] ep_si,raw_si;
 wire er_fault;
 wire [7:0] ep_lane_fault;
 wire [31:0] ex_lane_fault;
 qkd_astk_native_er_service u_er(.ck(ck_r),.rst_n(rst_n),.read_v(er_v),.read_addr(er_addr),
  .engine_so(raw_so),.astk_so(ep_so),.astk_si(ep_si),.engine_si(raw_si),
  .response_v(er_rsp_v),.response_addr(er_rsp_addr),.response_data(er_data),.fault(er_fault));
 assign si0=raw_si[0+:634];
 assign si1=raw_si[634+:634];
 assign si2=raw_si[1268+:634];
 assign si3=raw_si[1902+:634];
 assign si4=raw_si[2536+:634];
 assign si5=raw_si[3170+:634];
 assign si6=raw_si[3804+:634];
 assign si7=raw_si[4438+:634];
 wire [571:0] cq;
 wire [266:0] cx;
 wire [137:0] czi;
 wire [564:0] full_ap;
 wire ctl_fault;
 qkd_astk_ctl_tp8 #(.STATIC_SCHEDULE(STATIC_SCHEDULE),.LMAX_START_AGE(LMAX_START_AGE),
  .Z_START_AGE(Z_START_AGE),.Z_STRIDE(Z_STRIDE)) u_ctl(.ck(ck_c),.rst_n(rst_n),.st(st),.aq(aq),.am(am),
  .lt(lt),.ap(full_ap),.af(ctl_fault),.qo(cq),.xi(cx),.co(),.px(263'd0),.py(263'd0),.zi(czi),.fx(1'b0),.fy(1'b0),.fz(zf[4]));
 assign ap={full_ap[564:45],full_ap[42:0]};
 assign score_committed=cq[534];
 wire [571:0] qi[0:8];
 wire [266:0] xo[0:8];
 wire [650:0] zo[0:8];
 wire [521:0] ro[0:8];
 assign xo[0]=0;assign zo[0]=0;
 ot_hdc_delay #(.W(572),.D(RL),.RESET(1)) u_cq(.clk(ck_r),.rst_n(rst_n),.d(cq),.q(qi[8]));
 ot_hdc_delay #(.W(267),.D(RL),.RESET(1)) u_cx(.clk(ck_r),.rst_n(rst_n),.d(xo[8]),.q(cx));
 assign ro[8]={zo[8][650:139],zo[8][10:7],zo[8][6:3],zo[8][2],zo[8][0]};
 genvar e,h,z;
 generate for(e=0;e<8;e=e+1)begin:g_ep
  wire [266:0] xi;
  wire [650:0] zi;
  wire [263:0] xa;
  wire [135:0] xe;
  ot_hdc_delay #(.W(267),.D(RL),.RESET(1)) u_x(.clk(ck_r),.rst_n(rst_n),.d(xo[e]),.q(xi));
  ot_hdc_delay #(.W(651),.D((e%2)?0:RL),.RESET(1)) u_z(.clk(ck_r),.rst_n(rst_n),.d(zo[e]),.q(zi));
  ot_hdc_delay #(.W(572),.D(RL),.RESET(1)) u_q(.clk(ck_r),.rst_n(rst_n),.d(qi[e+1]),.q(qi[e]));
  ot_hdc_delay #(.W(522),.D(RL),.RESET(1)) u_r(.clk(ck_r),.rst_n(rst_n),.d(ro[e+1]),.q(ro[e]));
  // Relative ages compensate command-chain skew and preserve the real chunk
  // chain's9edge joins plus the alternating RL relay. Profile trace must seal
  // these values against the selected native transport before qualification.
  qkd_astk_ep #(.STATIC_SCHEDULE(STATIC_SCHEDULE),.HEADS(1),
   .EXP_START_AGE(EXP_START_AGE+9*e+RL*(e+e/2))) u_ep(
   .ck(ck_e[e]),.rst_n(rst_n),.sq({st,3'(e)}),.so(ep_so[425*e+:425]),.si(ep_si[634*e+:634]),
   .qi(qi[e]),.xi(xi),.xo(xo[e+1]),.zi(zi),.zo(zo[e+1]),.ri(ro[e]),.xa(xa),.xe(xe),.cr(1'b0),
   .ui(536'd0),.uo(),.di(536'd0),.do_(),.pi(263'd0),.po(),.ci(6'd0),.co(),
   .kui(4'd0),.kuo(),.kdi(4'd0),.kdo(),.tui(1'b0),.tuo(),.tdi(1'b0),.tdo(),.fi(1'b0),.fo(ep_lane_fault[e]));
  for(h=0;h<4;h=h+1)begin:g_ex
   qkd_astk_ex u_ex(.ck(ck_x[4*e+h]),.rst_n(rst_n),.xa(xa[66*h+:66]),.xe(xe[34*h+:34]),
    .ui(536'd0),.uo(),.di(536'd0),.do_(),.pi(263'd0),.po(),.ci(6'd0),.co(),
    .kui(4'd0),.kuo(),.kdi(4'd0),.kdo(),.tui(1'b0),.tuo(),.tdi(1'b0),.tdo(),.fi(1'b0),.fo(ex_lane_fault[4*e+h]));
  end
 end endgenerate
 wire [137:0] zn[0:4];
 wire [4:0] zf;
 assign zf[0]=0;
 assign zn[0]={zo[8][138:11],zo[8][10:7],zo[8][6:3],zo[8][2],zo[8][0]};
 generate for(z=0;z<4;z=z+1)begin:g_zn
  qkd_astk_zn u_zn(.ck(ck_z[z]),.rst_n(rst_n),.zc({2'(z),st}),.tc(cq[14:0]),.zi(zn[z]),.zo(zn[z+1]),
   .fi(zf[z]),.fo(zf[z+1]));
 end endgenerate
 assign czi=zn[4];
 reg [15:0] visibility;
 integer n;
 always @*begin
  visibility=0;
  for(n=0;n<8;n=n+1)visibility=visibility|ep_si[634*n+537+:16];
 end
 assign exp_committed=visibility;
 reg visibility_fault;
 reg legacy_fault;
 integer lf;
 always @(posedge ck_r or negedge rst_n)
  if(!rst_n)legacy_fault<=0;else for(lf=0;lf<8;lf=lf+1)
   if(raw_so[425*lf+412])legacy_fault<=1;
 always @(posedge ck_r or negedge rst_n)
  if(!rst_n)visibility_fault<=0;else if(er_v&&!visibility[er_addr[6:3]])visibility_fault<=1;
 // Arithmetic errors and real SO fault return through EP XO bit0 into CTL.
 wire observed_fault=ctl_fault|er_fault|visibility_fault|legacy_fault|(|ep_lane_fault)|(|ex_lane_fault);
 reg retained_fault;
 always @(posedge ck_r or negedge rst_n)
  if(!rst_n)retained_fault<=0;else if(observed_fault)retained_fault<=1;
 assign af=observed_fault|retained_fault;
endmodule
