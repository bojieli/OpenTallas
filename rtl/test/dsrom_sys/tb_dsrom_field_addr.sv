`timescale 1ps/1ps
module tb_dsrom_field_addr;
localparam PHW=6,SAW=14,R=128,VAW=19,VRD=64,KMAX=6144,BST=2;
localparam BW=1+PHW+3+1+1+2+1+8+3+2+256+10+256+10+3+3+1+3+4+32+1024;
logic  clk;
logic  rst_n;
logic  go;
logic [PHW-1:0] i_ph;
logic [2:0] i_np;
logic [VAW-1:0] i_xbase;
logic [VAW-1:0] i_xps;
logic [VAW-1:0] i_obase;
logic [VAW-1:0] i_ops;
logic [1:0] i_fmt;
wire  ready [0:2];
wire  idle [0:2];
wire  x_re [0:2];
wire [VAW-1:0] x_addr [0:2];
logic [VRD*32-1:0] x_q;
wire [R-1:0] w_we [0:2];
wire [R*VAW-1:0] w_addr [0:2];
wire [R*32-1:0] w_data [0:2];
wire  f_cfg_go [0:2];
wire [PHW-1:0] f_cfg_ph [0:2];
wire [2:0] f_cfg_np [0:2];
wire  f_go [0:2];
wire  f_go_bf [0:2];
wire [1:0] f_go_tag [0:2];
wire  f_xs_v [0:2];
wire [7:0] f_xs_p [0:2];
wire [2:0] f_xs_b [0:2];
wire [1:0] f_xs_sv [0:2];
wire [255:0] f_xs_q0 [0:2];
wire [9:0] f_xs_e0 [0:2];
wire [255:0] f_xs_q1 [0:2];
wire [9:0] f_xs_e1 [0:2];
wire [2:0] f_xs_pos [0:2];
wire [2:0] f_xb_pos [0:2];
wire  f_xb_v [0:2];
wire [2:0] f_xb_b [0:2];
wire [3:0] f_xb_sv [0:2];
wire [31:0] f_xb_u [0:2];
wire [1023:0] f_xb_d [0:2];
wire [BW-1:0] f_bus [0:2];
logic [R-1:0] r_v;
logic [16*R-1:0] r_row;
logic [3*R-1:0] r_pos;
logic [32*R-1:0] r_fp32;
logic [16*R-1:0] r_bf16;
logic [R-1:0] r_e;
logic  f_fault;
wire  fault [0:2];
wire [31:0] phase_cycles [0:2];
wire  ev_go [0:2];
wire  ev_end [0:2];
wire [1:0] ev_tag [0:2];
wire [PHW:0] rom_pa0 [0:2];
wire [PHW:0] rom_pa1 [0:2];
wire [63:0] rom_pq0 [0:2];
wire [63:0] rom_pq1 [0:2];
wire [SAW-1:0] rom_sa [0:2];
wire [47:0] rom_sq [0:2];
ot_v41_spine_pq_w17w10 #(.PHW(PHW),.SAW(SAW),.R(R),.VAW(VAW),.VRD(VRD),.KMAX(KMAX),.BST(BST),.PQ(1)) baseline (
.clk(clk),
.rst_n(rst_n),
.go(go),
.i_ph(i_ph),
.i_np(i_np),
.i_xbase(i_xbase),
.i_xps(i_xps),
.i_obase(i_obase),
.i_ops(i_ops),
.i_fmt(i_fmt),
.ready(ready[0]),
.idle(idle[0]),
.x_re(x_re[0]),
.x_addr(x_addr[0]),
.x_q(x_q),
.w_we(w_we[0]),
.w_addr(w_addr[0]),
.w_data(w_data[0]),
.f_cfg_go(f_cfg_go[0]),
.f_cfg_ph(f_cfg_ph[0]),
.f_cfg_np(f_cfg_np[0]),
.f_go(f_go[0]),
.f_go_bf(f_go_bf[0]),
.f_go_tag(f_go_tag[0]),
.f_xs_v(f_xs_v[0]),
.f_xs_p(f_xs_p[0]),
.f_xs_b(f_xs_b[0]),
.f_xs_sv(f_xs_sv[0]),
.f_xs_q0(f_xs_q0[0]),
.f_xs_e0(f_xs_e0[0]),
.f_xs_q1(f_xs_q1[0]),
.f_xs_e1(f_xs_e1[0]),
.f_xs_pos(f_xs_pos[0]),
.f_xb_pos(f_xb_pos[0]),
.f_xb_v(f_xb_v[0]),
.f_xb_b(f_xb_b[0]),
.f_xb_sv(f_xb_sv[0]),
.f_xb_u(f_xb_u[0]),
.f_xb_d(f_xb_d[0]),
.f_bus(f_bus[0]),
.r_v(r_v),
.r_row(r_row),
.r_pos(r_pos),
.r_fp32(r_fp32),
.r_bf16(r_bf16),
.r_e(r_e),
.f_fault(f_fault),
.fault(fault[0]),
.phase_cycles(phase_cycles[0]),
.ev_go(ev_go[0]),
.ev_end(ev_end[0]),
.ev_tag(ev_tag[0]),
.rom_pa0(rom_pa0[0]),
.rom_pa1(rom_pa1[0]),
.rom_pq0(rom_pq0[0]),
.rom_pq1(rom_pq1[0]),
.rom_sa(rom_sa[0]),
.rom_sq(rom_sq[0]));
ot_v41_spine_pq_addr_w17w10 #(.PHW(PHW),.SAW(SAW),.R(R),.VAW(VAW),.VRD(VRD),.KMAX(KMAX),.BST(BST),.PQ(1),.ADDR_LOOKAHEAD(0)) off (
.clk(clk),
.rst_n(rst_n),
.go(go),
.i_ph(i_ph),
.i_np(i_np),
.i_xbase(i_xbase),
.i_xps(i_xps),
.i_obase(i_obase),
.i_ops(i_ops),
.i_fmt(i_fmt),
.ready(ready[1]),
.idle(idle[1]),
.x_re(x_re[1]),
.x_addr(x_addr[1]),
.x_q(x_q),
.w_we(w_we[1]),
.w_addr(w_addr[1]),
.w_data(w_data[1]),
.f_cfg_go(f_cfg_go[1]),
.f_cfg_ph(f_cfg_ph[1]),
.f_cfg_np(f_cfg_np[1]),
.f_go(f_go[1]),
.f_go_bf(f_go_bf[1]),
.f_go_tag(f_go_tag[1]),
.f_xs_v(f_xs_v[1]),
.f_xs_p(f_xs_p[1]),
.f_xs_b(f_xs_b[1]),
.f_xs_sv(f_xs_sv[1]),
.f_xs_q0(f_xs_q0[1]),
.f_xs_e0(f_xs_e0[1]),
.f_xs_q1(f_xs_q1[1]),
.f_xs_e1(f_xs_e1[1]),
.f_xs_pos(f_xs_pos[1]),
.f_xb_pos(f_xb_pos[1]),
.f_xb_v(f_xb_v[1]),
.f_xb_b(f_xb_b[1]),
.f_xb_sv(f_xb_sv[1]),
.f_xb_u(f_xb_u[1]),
.f_xb_d(f_xb_d[1]),
.f_bus(f_bus[1]),
.r_v(r_v),
.r_row(r_row),
.r_pos(r_pos),
.r_fp32(r_fp32),
.r_bf16(r_bf16),
.r_e(r_e),
.f_fault(f_fault),
.fault(fault[1]),
.phase_cycles(phase_cycles[1]),
.ev_go(ev_go[1]),
.ev_end(ev_end[1]),
.ev_tag(ev_tag[1]),
.rom_pa0(rom_pa0[1]),
.rom_pa1(rom_pa1[1]),
.rom_pq0(rom_pq0[1]),
.rom_pq1(rom_pq1[1]),
.rom_sa(rom_sa[1]),
.rom_sq(rom_sq[1]));
ot_v41_spine_pq_addr_w17w10 #(.PHW(PHW),.SAW(SAW),.R(R),.VAW(VAW),.VRD(VRD),.KMAX(KMAX),.BST(BST),.PQ(1),.ADDR_LOOKAHEAD(1)) dut (
.clk(clk),
.rst_n(rst_n),
.go(go),
.i_ph(i_ph),
.i_np(i_np),
.i_xbase(i_xbase),
.i_xps(i_xps),
.i_obase(i_obase),
.i_ops(i_ops),
.i_fmt(i_fmt),
.ready(ready[2]),
.idle(idle[2]),
.x_re(x_re[2]),
.x_addr(x_addr[2]),
.x_q(x_q),
.w_we(w_we[2]),
.w_addr(w_addr[2]),
.w_data(w_data[2]),
.f_cfg_go(f_cfg_go[2]),
.f_cfg_ph(f_cfg_ph[2]),
.f_cfg_np(f_cfg_np[2]),
.f_go(f_go[2]),
.f_go_bf(f_go_bf[2]),
.f_go_tag(f_go_tag[2]),
.f_xs_v(f_xs_v[2]),
.f_xs_p(f_xs_p[2]),
.f_xs_b(f_xs_b[2]),
.f_xs_sv(f_xs_sv[2]),
.f_xs_q0(f_xs_q0[2]),
.f_xs_e0(f_xs_e0[2]),
.f_xs_q1(f_xs_q1[2]),
.f_xs_e1(f_xs_e1[2]),
.f_xs_pos(f_xs_pos[2]),
.f_xb_pos(f_xb_pos[2]),
.f_xb_v(f_xb_v[2]),
.f_xb_b(f_xb_b[2]),
.f_xb_sv(f_xb_sv[2]),
.f_xb_u(f_xb_u[2]),
.f_xb_d(f_xb_d[2]),
.f_bus(f_bus[2]),
.r_v(r_v),
.r_row(r_row),
.r_pos(r_pos),
.r_fp32(r_fp32),
.r_bf16(r_bf16),
.r_e(r_e),
.f_fault(f_fault),
.fault(fault[2]),
.phase_cycles(phase_cycles[2]),
.ev_go(ev_go[2]),
.ev_end(ev_end[2]),
.ev_tag(ev_tag[2]),
.rom_pa0(rom_pa0[2]),
.rom_pa1(rom_pa1[2]),
.rom_pq0(rom_pq0[2]),
.rom_pq1(rom_pq1[2]),
.rom_sa(rom_sa[2]),
.rom_sq(rom_sq[2]));
function automatic [63:0] descriptor(input [5:0] ph);
 reg [63:0] v; reg [15:0] count, base;
 begin
 case (ph%5) 0:count=1;1:count=2;2:count=3;3:count=33;default:count=97;endcase
 base=16'hfff0+16'(ph*101);
 v=0;v[0]=ph[0];v[13:1]=13'd6144;v[29:14]=count;v[45:30]=base;v[61:46]=128;
 descriptor=v;
 end
endfunction
function automatic [47:0] word_at(input [13:0] a,input bit bf);
 reg [47:0] v;
 begin
 v=0; v[0]=1;
 if(bf) begin v[4]=1;v[15:8]=8'd47;end
 else begin v[13:12]=2'b11;v[8:1]=8'd11;v[11:9]=3'd7;end
 if(a[2:0]==3) v[0]=0;
 word_at=v;
 end
endfunction

assign rom_pq0[0]=descriptor(rom_pa0[0][PHW:1]);
assign rom_pq1[0]=0;
assign rom_sq[0]=word_at(rom_sa[0],baseline.fam);
assign rom_pq0[1]=descriptor(rom_pa0[1][PHW:1]);
assign rom_pq1[1]=0;
assign rom_sq[1]=word_at(rom_sa[1],off.fam);
assign rom_pq0[2]=descriptor(rom_pa0[2][PHW:1]);
assign rom_pq1[2]=0;
assign rom_sq[2]=word_at(rom_sa[2],dut.fam);
integer cycles=0,launches=0,ends=0,stalls=0,wraps=0,active_checks=0,writes=0,qbeats=0,bbeats=0;
integer head=0,tail=0,qt[0:127],qn[0:127],qp[0:127],np_by_tag[0:3];
integer j,k;
task automatic check;
 begin
 for(integer n=1;n<3;n=n+1) begin
 if ({ready[n],idle[n],x_re[n],x_addr[n],w_we[n],w_addr[n],w_data[n],fault[n],phase_cycles[n],ev_go[n],ev_end[n],ev_tag[n],f_cfg_go[n],f_go[n],f_xs_v[n],f_xb_v[n]} !==
     {ready[0],idle[0],x_re[0],x_addr[0],w_we[0],w_addr[0],w_data[0],fault[0],phase_cycles[0],ev_go[0],ev_end[0],ev_tag[0],f_cfg_go[0],f_go[0],f_xs_v[0],f_xb_v[0]}) $fatal(1,"DIFF public cycle=%0d",cycles);
 if(f_cfg_go[0] && {f_cfg_ph[n],f_cfg_np[n]} !== {f_cfg_ph[0],f_cfg_np[0]}) $fatal(1,"DIFF config");
 if(f_go[0] && {f_go_bf[n],f_go_tag[n]} !== {f_go_bf[0],f_go_tag[0]}) $fatal(1,"DIFF launch");
 if(f_xs_v[0] && {f_xs_p[n],f_xs_b[n],f_xs_sv[n],f_xs_q0[n],f_xs_e0[n],f_xs_q1[n],f_xs_e1[n],f_xs_pos[n]} !== {f_xs_p[0],f_xs_b[0],f_xs_sv[0],f_xs_q0[0],f_xs_e0[0],f_xs_q1[0],f_xs_e1[0],f_xs_pos[0]}) $fatal(1,"DIFF q");
 if(f_xb_v[0] && {f_xb_b[n],f_xb_sv[n],f_xb_u[n],f_xb_d[n],f_xb_pos[n]} !== {f_xb_b[0],f_xb_sv[0],f_xb_u[0],f_xb_d[0],f_xb_pos[0]}) $fatal(1,"DIFF BF");
 end
 if(baseline.sm_run) begin
 active_checks=active_checks+1;
 if(rom_sa[2] !== rom_sa[0] || dut.fam !== baseline.fam || dut.nbeat !== baseline.nbeat || dut.sbase !== baseline.sbase ||
 {dut.sm_i,dut.sm_pos,dut.sm_tag,dut.sw,dut.sw_v,dut.s_ok} !== {baseline.sm_i,baseline.sm_pos,baseline.sm_tag,baseline.sw,baseline.sw_v,baseline.s_ok}) $fatal(1,"DIFF address/state cycle=%0d",cycles);
 if(baseline.sw_v&&!baseline.s_ok) stalls=stalls+1;
 if(baseline.s_adv&&baseline.s_last) wraps=wraps+1;
 end
 end
endtask
task automatic tick;
 begin
 #416;clk=1;#1;cycles=cycles+1;
 if(rst_n) check();
 if(ev_go[0]) launches=launches+1;
 if(ev_end[0]) begin
 ends=ends+1;qt[tail]=int'(ev_tag[0]);qn[tail]=np_by_tag[ev_tag[0]];qp[tail]=0;tail=tail+1;
 end
 if(f_xs_v[0])qbeats=qbeats+1;
 if(f_xb_v[0])bbeats=bbeats+1;
 writes=writes+$countones(w_we[0]);
 #416;clk=0;
 r_v=0;
 if(head<tail) begin
 r_v='1;
 for(integer r=0;r<R;r=r+1)begin r_row[16*r+:16]={2'(qt[head]),14'(r)};r_pos[3*r+:3]=3'(qp[head]);end
 if(qp[head]==qn[head])head=head+1;else qp[head]=qp[head]+1;
 end
 if(cycles>100000) $fatal(1,"FIXTURE incomplete run=%0d tag=%0d i=%0d need=%0d have=%0d accepted=%0d ends=%0d",baseline.sm_run,baseline.sm_tag,baseline.sm_i,baseline.need_q,baseline.have[baseline.spar],launches,ends);
 end
endtask
initial begin
 clk=0;rst_n=0;go=0;i_ph=0;i_np=0;i_xbase=0;i_xps=8192;i_obase=0;i_ops=256;i_fmt=1;
 r_v=0;r_row=0;r_pos=0;r_e=0;f_fault=0;r_fp32=0;r_bf16=0;
 for(k=0;k<64;k=k+1)x_q[32*k+:32]=32'h3f800000+32'(k*1024);
 for(k=0;k<R;k=k+1)begin r_fp32[32*k+:32]=32'h3f000000+32'(k);r_bf16[16*k+:16]=16'h3f00;end
 tick();tick();rst_n=1;tick();
 for(j=0;j<20;j=j+1)begin
 while(!ready[0])tick();
 i_ph=6'(j);i_np=3'(j%8);i_fmt=2'(j%3);i_obase=19'(j*4096);i_xbase=19'(j*8192);
 np_by_tag[j%4]=j%8;go=1;tick();go=0;
 end
 while(!idle[0] || head!=tail)tick();
 repeat(8)tick();
 if(fault[0] || launches!=20 || ends!=20 || stalls==0 || wraps==0 || qbeats==0 || bbeats==0 || writes==0) $fatal(1,"COVERAGE count/fault");
 f_fault=1;tick();f_fault=0;tick();if(!fault[0]||!fault[2])$fatal(1,"FAULT missing");
 rst_n=0;tick();tick();rst_n=1;tick();if(fault[0]||fault[2]||!idle[0])$fatal(1,"RESET failure");
 $display("PASS full_spine R=128 KMAX=6144 SAW=14 cycles=%0d launches=%0d ends=%0d stalls=%0d wraps=%0d active=%0d writes=%0d qbeats=%0d bbeats=%0d",cycles,launches,ends,stalls,wraps,active_checks,writes,qbeats,bbeats);
 $finish;
end
endmodule
