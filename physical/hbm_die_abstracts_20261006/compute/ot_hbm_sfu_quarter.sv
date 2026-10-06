`timescale 1ns/1ps
// Canonical 64-lane SFU quarter. No software or unbounded queue. Actual ports
// are derived from the real engines; historical 1024b stubs are not bindings.
// New top defaults off and has no parent physical qualification.
module ot_hbm_sfu_quarter #(parameter integer ENABLE=0,LANES=64)(
 input wire clk,rst_n,
 input wire req_v,output wire req_r,input wire [31:0] req_tag,
 input wire [2:0] req_fn,input wire [LANES*32-1:0] req_x,
 output wire rsp_v,input wire rsp_r,output wire [31:0] rsp_tag,
 output wire [LANES*32-1:0] rsp_y,output wire rsp_error,
 output wire fault
);
 generate if(!ENABLE)begin:g_off
  assign req_r=0;assign rsp_v=0;assign rsp_tag=0;assign rsp_y=0;assign rsp_error=0;assign fault=0;
 end else begin:g_on
  localparam integer IW=LANES*32+35,OW=LANES*32+33;
  wire launch,engine_clk,engine_rst_n,engine_error_seen;wire [IW-1:0] payload;
  wire [OW-1:0] response;
  wire [LANES*32-1:0] y;
  wire [LANES-1:0] v,f;
  wire [2:0] fn=payload[LANES*32+:3];
  wire [31:0] tag=payload[LANES*32+3+:32];
  ot_hbm_compute_held_exec #(.IW(IW),.OW(OW)) u_hold(
   .clk(clk),.rst_n(rst_n),.req_v(req_v),.req_r(req_r),.req_d({req_tag,req_fn,req_x}),
   .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_d(response),.launch(launch),.engine_clk(engine_clk),.engine_rst_n(engine_rst_n),.engine_error_seen(engine_error_seen),.engine_d(payload),
   .engine_v(&v),.engine_q({tag,(|f)|engine_error_seen,y}),.engine_fault(|f),.fault(fault));
  assign {rsp_tag,rsp_error,rsp_y}=response;
  for(genvar i=0;i<LANES;i=i+1)begin:g_lane
   ot_hbm_sfu_result_c12 u(
    .clk(engine_clk),.rst_n(engine_rst_n),.v(launch),.fn(fn),.x(payload[i*32+:32]),
    .vo(v[i]),.y(y[i*32+:32]),.fault(f[i]));
  end
 end endgenerate
endmodule

// EXP/SIGM/SILU reproduce the adopted c12 lane's S-stage arithmetic. Side
// operations use its exact engine with a completion port on the result flop.
// One held operation means fn and input numerator remain stable through retire.
module ot_hbm_sfu_result_c12(
 input wire clk,rst_n,v,input wire [2:0] fn,input wire [31:0] x,
 output wire vo,output wire [31:0] y,output wire fault
);
 localparam integer DE=94;
 wire exp_select=fn==1;wire sig_select=fn==4||fn==5;
 wire [31:0] ey,den,num,dy,sy;
 wire ev,dv,sv,ef,df,sf,af;
 wire [DE:0] sig_v;
 wire [6:0] den_v;
 ot_hdc_v41x_exp #(.LM(6),.LA(6)) u_exp(
  .clk(clk),.rst_n(rst_n),.v(v&&(exp_select||sig_select)),
  .x(exp_select?x:{~x[31],x[30:0]}),.y(ey),.vo(ev),.fault(ef));
 ot_hdc_vline #(.D(DE)) u_sig_v(.clk(clk),.rst_n(rst_n),.v(v&&sig_select),.vd(sig_v));
 ot_hdc_qadd_lat #(.KEEP(1),.LAT(6)) u_den(clk,rst_n,sig_v[DE],ey,32'h3f800000,den,af);
 ot_hdc_delay #(.W(32),.D(DE+6)) u_num(
  .clk(clk),.rst_n(rst_n),.d(fn==5?x:32'h3f800000),.q(num));
 ot_hdc_vline #(.D(6)) u_den_v(.clk(clk),.rst_n(rst_n),.v(sig_v[DE]),.vd(den_v));
 ot_dsrom_fdiv_f12 u_div(
  .clk(clk),.rst_n(rst_n),.v(den_v[6]),.a(num),.b(den),.y(dy),.vo(dv),.fault(df));
 ot_hbm_sfu_side_result_c12 #(.MLAT(6),.ALAT(6),.DDIV(21),.SIDEX(4),.FSQ(1)) u_side(
  .clk(clk),.rst_n(rst_n),.v(v&&(fn==2||fn==3||fn==6||fn==7)),
  .fn(fn),.x(x),.fn_out(fn),.y(sy),.fault(sf),.vo(sv));
 // NONE also retires through a real result register.
 reg nv;reg [31:0] ny;
 always @(posedge clk or negedge rst_n)if(!rst_n)nv<=0;else nv<=v&&fn==0;
 always @(posedge clk)ny<=x;
 assign vo=(ev&&exp_select)|dv|sv|nv;
 assign y=({32{ev&&exp_select}}&ey)|({32{dv}}&dy)|({32{sv}}&sy)|({32{nv}}&ny);
 assign fault=ef|(|af)|df|sf;
endmodule
