`timescale 1ns/1ps
`ifndef GB_FLAG
`define GB_FLAG 1
`endif
module tb_gb_spine;
reg clk=0;always #0.5 clk=~clk;
reg rst=0,go=0;reg[9:0] ph=0;
reg[1:0] rv=0;reg[31:0] rrow=0;
reg[2047:0] xq=0;
wire[63:0] pword=(64'd1<<46)|(64'd1<<14)|(64'd256<<1)|ph[0];
wire [1:0][0:0] ready;
wire [1:0][0:0] idle;
wire [1:0][0:0] x_re;
wire [1:0][18:0] x_addr;
wire [1:0][1:0] w_we;
wire [1:0][37:0] w_addr;
wire [1:0][63:0] w_data;
wire [1:0][0:0] f_cfg_go;
wire [1:0][9:0] f_cfg_ph;
wire [1:0][2:0] f_cfg_np;
wire [1:0][0:0] f_go;
wire [1:0][0:0] f_go_bf;
wire [1:0][1:0] f_go_tag;
wire [1:0][0:0] f_xs_v;
wire [1:0][7:0] f_xs_p;
wire [1:0][2:0] f_xs_b;
wire [1:0][1:0] f_xs_sv;
wire [1:0][255:0] f_xs_q0;
wire [1:0][9:0] f_xs_e0;
wire [1:0][255:0] f_xs_q1;
wire [1:0][9:0] f_xs_e1;
wire [1:0][2:0] f_xs_pos;
wire [1:0][2:0] f_xb_pos;
wire [1:0][0:0] f_xb_v;
wire [1:0][2:0] f_xb_b;
wire [1:0][3:0] f_xb_sv;
wire [1:0][31:0] f_xb_u;
wire [1:0][1023:0] f_xb_d;
wire [1:0][0:0] fault;
wire [1:0][31:0] phase_cycles;
wire [1:0][0:0] ev_go;
wire [1:0][0:0] ev_end;
wire [1:0][1:0] ev_tag;
wire [1:0][10:0] rom_pa0;
wire [1:0][10:0] rom_pa1;
wire [1:0][13:0] rom_sa;
legacy_spine #(.PQ(1)) s0(.clk(clk),.rst_n(rst),.go(go),.i_ph(ph),.i_np(3'd0),.i_xbase(19'd0),.i_xps(19'd256),.i_obase(19'd0),.i_ops(19'd1),.i_fmt(2'd1),.x_q(xq),.r_v(rv),.r_row(rrow),.r_pos(6'd0),.r_fp32(64'd0),.r_bf16(32'd0),.r_e(2'd0),.f_fault(1'b0),.rom_pq0(pword),.rom_pq1(64'd0),.rom_sq(48'h1001),.ready(ready[0]),.idle(idle[0]),.x_re(x_re[0]),.x_addr(x_addr[0]),.w_we(w_we[0]),.w_addr(w_addr[0]),.w_data(w_data[0]),.f_cfg_go(f_cfg_go[0]),.f_cfg_ph(f_cfg_ph[0]),.f_cfg_np(f_cfg_np[0]),.f_go(f_go[0]),.f_go_bf(f_go_bf[0]),.f_go_tag(f_go_tag[0]),.f_xs_v(f_xs_v[0]),.f_xs_p(f_xs_p[0]),.f_xs_b(f_xs_b[0]),.f_xs_sv(f_xs_sv[0]),.f_xs_q0(f_xs_q0[0]),.f_xs_e0(f_xs_e0[0]),.f_xs_q1(f_xs_q1[0]),.f_xs_e1(f_xs_e1[0]),.f_xs_pos(f_xs_pos[0]),.f_xb_pos(f_xb_pos[0]),.f_xb_v(f_xb_v[0]),.f_xb_b(f_xb_b[0]),.f_xb_sv(f_xb_sv[0]),.f_xb_u(f_xb_u[0]),.f_xb_d(f_xb_d[0]),.fault(fault[0]),.phase_cycles(phase_cycles[0]),.ev_go(ev_go[0]),.ev_end(ev_end[0]),.ev_tag(ev_tag[0]),.rom_pa0(rom_pa0[0]),.rom_pa1(rom_pa1[0]),.rom_sa(rom_sa[0]));
ot_v41_spine_pq_static_w17w10 #(.PQ(1),.QX_GO_BOUNDARY(`GB_FLAG)) s1(.clk(clk),.rst_n(rst),.go(go),.i_ph(ph),.i_np(3'd0),.i_xbase(19'd0),.i_xps(19'd256),.i_obase(19'd0),.i_ops(19'd1),.i_fmt(2'd1),.x_q(xq),.r_v(rv),.r_row(rrow),.r_pos(6'd0),.r_fp32(64'd0),.r_bf16(32'd0),.r_e(2'd0),.f_fault(1'b0),.rom_pq0(pword),.rom_pq1(64'd0),.rom_sq(48'h1001),.ready(ready[1]),.idle(idle[1]),.x_re(x_re[1]),.x_addr(x_addr[1]),.w_we(w_we[1]),.w_addr(w_addr[1]),.w_data(w_data[1]),.f_cfg_go(f_cfg_go[1]),.f_cfg_ph(f_cfg_ph[1]),.f_cfg_np(f_cfg_np[1]),.f_go(f_go[1]),.f_go_bf(f_go_bf[1]),.f_go_tag(f_go_tag[1]),.f_xs_v(f_xs_v[1]),.f_xs_p(f_xs_p[1]),.f_xs_b(f_xs_b[1]),.f_xs_sv(f_xs_sv[1]),.f_xs_q0(f_xs_q0[1]),.f_xs_e0(f_xs_e0[1]),.f_xs_q1(f_xs_q1[1]),.f_xs_e1(f_xs_e1[1]),.f_xs_pos(f_xs_pos[1]),.f_xb_pos(f_xb_pos[1]),.f_xb_v(f_xb_v[1]),.f_xb_b(f_xb_b[1]),.f_xb_sv(f_xb_sv[1]),.f_xb_u(f_xb_u[1]),.f_xb_d(f_xb_d[1]),.fault(fault[1]),.phase_cycles(phase_cycles[1]),.ev_go(ev_go[1]),.ev_end(ev_end[1]),.ev_tag(ev_tag[1]),.rom_pa0(rom_pa0[1]),.rom_pa1(rom_pa1[1]),.rom_sa(rom_sa[1]));
reg gdelay=0;reg[1:0] tdelay=0;
always@(posedge clk or negedge rst)if(!rst)gdelay<=0;else gdelay<=f_go[1]&&!f_go_bf[1];
always@(posedge clk)tdelay<=f_go_tag[1];
wire effective_go=f_go_bf[1]?f_go[1]:gdelay;
wire[1:0] effective_tag=f_go_bf[1]?f_go_tag[1]:tdelay;
integer t,err=0,ng=0,nend=0,retwait=0;reg[1:0] rettag=0;
initial begin
 for(t=0;t<600;t=t+1)begin
  @(negedge clk); rst=t>=12;go=(t==24||t==30||t==36);ph=(t==30)?1:0;xq={64{32'(t)}};
  rv=0;
  if(retwait>0)begin retwait=retwait-1;if(retwait==0)begin rv=1;rrow={16'd0,rettag,14'd0};end end
  if(ev_end[0])begin nend=nend+1;retwait=3;rettag=ev_tag[0];end
  #0.01;
  if(t>20)begin
   if({ready[0],idle[0],x_re[0],x_addr[0],w_we[0],w_addr[0],w_data[0],f_cfg_go[0],f_cfg_ph[0],f_cfg_np[0],f_xs_v[0],f_xs_p[0],f_xs_b[0],f_xs_sv[0],f_xs_q0[0],f_xs_e0[0],f_xs_q1[0],f_xs_e1[0],f_xs_pos[0],f_xb_pos[0],f_xb_v[0],f_xb_b[0],f_xb_sv[0],f_xb_u[0],f_xb_d[0],fault[0],phase_cycles[0],ev_end[0],rom_pa0[0],rom_pa1[0],rom_sa[0]}!=={ready[1],idle[1],x_re[1],x_addr[1],w_we[1],w_addr[1],w_data[1],f_cfg_go[1],f_cfg_ph[1],f_cfg_np[1],f_xs_v[1],f_xs_p[1],f_xs_b[1],f_xs_sv[1],f_xs_q0[1],f_xs_e0[1],f_xs_q1[1],f_xs_e1[1],f_xs_pos[1],f_xb_pos[1],f_xb_v[1],f_xb_b[1],f_xb_sv[1],f_xb_u[1],f_xb_d[1],fault[1],phase_cycles[1],ev_end[1],rom_pa0[1],rom_pa1[1],rom_sa[1]})begin err=err+1;if(err<8)$display("OTHER_DIFF edge%0d",t);end
   if(f_go[0]!==effective_go)begin err=err+1;if(err<8)$display("GO_DIFF edge%0d",t);end
   if(f_go[0])begin ng=ng+1;if(f_go_tag[0]!==effective_tag)begin err=err+1;$display("TAG_DIFF %0d",t);end end
   if(fault[0]||fault[1])begin err=err+1;if(err<8)$display("FAULT edge%0d",t);end
  end
 end
 if(ng!=3||nend!=3)begin err=err+1;$display("VACUOUS gos%0d ends%0d",ng,nend);end
 if(err)begin $display("GB_SPINE FAIL %0d",err);$fatal(1,"miter");end
 $display("GB_SPINE PASS gos%0d ends%0d",ng,nend);$finish;
end
endmodule
// Quantizer is an abstract equal-latency provider, outside the GO scheduler
// mechanism. Numeric exactness remains the primitive/full-frame gate.
module ot_hdc_actquant(input clk,rst_n,v,fp4,input[1023:0]x,output vo,output[255:0]q,output signed[9:0]e,output[511:0]y,output fault);
reg[12:0]vp;reg[255:0]qp[0:12];integer i;
always@(posedge clk)begin if(!rst_n)vp<=0;else vp<={vp[11:0],v};qp[0]<=x[255:0];for(i=1;i<13;i=i+1)qp[i]<=qp[i-1];end
assign vo=vp[12];assign q=qp[12];assign e=0;assign y=0;assign fault=0;
endmodule
