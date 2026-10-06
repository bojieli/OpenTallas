`timescale 1ns/1ps
module tb_hbm_su_ctl_c13_flags;
localparam N=8,M=8,AW=24,NW=16;
reg clk=0; always #5 clk=~clk;
reg  rst_n;
reg  go;
reg [NW-1:0] i_nout;
reg [NW-1:0] i_nin;
reg [1:0] i_asrc;
reg [1:0] i_bsrc;
reg [1:0] i_csrc;
reg [1:0] i_dsrc;
reg [AW-1:0] i_abase;
reg [AW-1:0] i_aso;
reg [AW-1:0] i_asi;
reg [AW-1:0] i_aibase;
reg [1:0] i_aind;
reg [AW-1:0] i_bbase;
reg [AW-1:0] i_bso;
reg [AW-1:0] i_bsi;
reg  i_bhalf;
reg [AW-1:0] i_cbase;
reg [AW-1:0] i_cso;
reg [AW-1:0] i_csi;
reg  i_cpair;
reg [AW-1:0] i_dbase;
reg [AW-1:0] i_dso;
reg [AW-1:0] i_dsi;
reg  i_arnd;
reg  i_arelu;
reg  i_amin;
reg  i_cclip;
reg [2:0] i_m1;
reg [1:0] i_m2;
reg [2:0] i_qm;
reg [2:0] i_ad;
reg [2:0] i_sfu;
reg [2:0] i_e1;
reg [1:0] i_e2;
reg  i_rnd;
reg [1:0] i_dst;
reg [AW-1:0] i_obase;
reg [AW-1:0] i_oso;
reg [AW-1:0] i_osi;
reg [AW-1:0] i_orow;
reg [1:0] i_red;
reg  i_redsq;
reg  i_redwhole;
reg  i_redtree;
reg  i_redrnd;
reg [AW-1:0] i_rbase;
reg [AW-1:0] i_rso;
reg [31:0] i_imm1;
reg [31:0] i_imm2;
reg [31:0] i_imm3;
reg [1:0] i_ch_src;
reg [7:0] i_ch_seq;
reg [15:0] i_ch_lead;
reg [15:0] i_ch_mul;
reg [7:0] x_seq;
reg [7:0] x_dseq;
reg [15:0] x_cnt;
reg [N*32-1:0] vi_q;
reg [4*N*32-1:0] rd_q;
wire ready;
ot_hdc_v41x_vec #(.N(N),.M(M),.AW(AW),.NW(NW),.MLAT(6),.ALAT(6),.OPR(1),.DDIV(21),.SIDEX(4),.FSQ(1),.CAPR(1),.RPAD(1),.RSL(2),.RTAP(1),.ROUT(1),.BCAST_STAGES(7),.RET_STAGES(8),.CTL12(1),.CTL13(1)) u(
.clk(clk),
.rst_n(rst_n),
.go(go),
.i_nout(i_nout),
.i_nin(i_nin),
.i_asrc(i_asrc),
.i_bsrc(i_bsrc),
.i_csrc(i_csrc),
.i_dsrc(i_dsrc),
.i_abase(i_abase),
.i_aso(i_aso),
.i_asi(i_asi),
.i_aibase(i_aibase),
.i_aind(i_aind),
.i_bbase(i_bbase),
.i_bso(i_bso),
.i_bsi(i_bsi),
.i_bhalf(i_bhalf),
.i_cbase(i_cbase),
.i_cso(i_cso),
.i_csi(i_csi),
.i_cpair(i_cpair),
.i_dbase(i_dbase),
.i_dso(i_dso),
.i_dsi(i_dsi),
.i_arnd(i_arnd),
.i_arelu(i_arelu),
.i_amin(i_amin),
.i_cclip(i_cclip),
.i_m1(i_m1),
.i_m2(i_m2),
.i_qm(i_qm),
.i_ad(i_ad),
.i_sfu(i_sfu),
.i_e1(i_e1),
.i_e2(i_e2),
.i_rnd(i_rnd),
.i_dst(i_dst),
.i_obase(i_obase),
.i_oso(i_oso),
.i_osi(i_osi),
.i_orow(i_orow),
.i_red(i_red),
.i_redsq(i_redsq),
.i_redwhole(i_redwhole),
.i_redtree(i_redtree),
.i_redrnd(i_redrnd),
.i_rbase(i_rbase),
.i_rso(i_rso),
.i_imm1(i_imm1),
.i_imm2(i_imm2),
.i_imm3(i_imm3),
.i_ch_src(i_ch_src),
.i_ch_seq(i_ch_seq),
.i_ch_lead(i_ch_lead),
.i_ch_mul(i_ch_mul),
.x_seq(x_seq),
.x_dseq(x_dseq),
.x_cnt(x_cnt),
.vi_q(vi_q),
.rd_q(rd_q),.ready(ready));
integer k,accepted=0,emits=0; reg[31:0] seed=32'h37251617;
function [31:0] rng(input [31:0] x);reg[31:0] y;begin y=x^(x<<13);y=y^(y>>17);rng=y^(y<<5);end endfunction
initial begin
rst_n=0;
go=0;
i_nout=0;
i_nin=0;
i_asrc=0;
i_bsrc=0;
i_csrc=0;
i_dsrc=0;
i_abase=0;
i_aso=0;
i_asi=0;
i_aibase=0;
i_aind=0;
i_bbase=0;
i_bso=0;
i_bsi=0;
i_bhalf=0;
i_cbase=0;
i_cso=0;
i_csi=0;
i_cpair=0;
i_dbase=0;
i_dso=0;
i_dsi=0;
i_arnd=0;
i_arelu=0;
i_amin=0;
i_cclip=0;
i_m1=0;
i_m2=0;
i_qm=0;
i_ad=0;
i_sfu=0;
i_e1=0;
i_e2=0;
i_rnd=0;
i_dst=0;
i_obase=0;
i_oso=0;
i_osi=0;
i_orow=0;
i_red=0;
i_redsq=0;
i_redwhole=0;
i_redtree=0;
i_redrnd=0;
i_rbase=0;
i_rso=0;
i_imm1=0;
i_imm2=0;
i_imm3=0;
i_ch_src=0;
i_ch_seq=0;
i_ch_lead=0;
i_ch_mul=0;
x_seq=0;
x_dseq=0;
x_cnt=0;
vi_q=0;
rd_q=0;
for(k=0;k<2000;k=k+1) begin
@(negedge clk);rst_n=(k>2&&k!=499);if(!rst_n)accepted=0;go=ready&&rst_n;seed=rng(seed);
if(go) begin
i_nout=1+(seed%2);i_nin=1+((seed>>4)%16);
i_red=0;i_redwhole=0;i_redtree=0;i_bhalf=0;i_cpair=0;
i_asi=1;i_bsi=1;i_csi=1;i_dsi=1;i_osi=1;
i_aso=i_nin;i_bso=i_bhalf?(i_nin>>1):i_nin;i_cso=i_nin;i_dso=i_bso;i_oso=i_nin;
i_sfu=accepted[0] ? (seed>>16)%7 : 0;i_m1=(seed>>20)%4;i_ad=(seed>>24)%4;i_e1=(seed>>28)%4;
i_ch_src=0;i_ch_seq=accepted-1;i_ch_lead=0;i_ch_mul=256;accepted=accepted+1;end
x_cnt=x_cnt+1;x_dseq=accepted-1;x_seq=accepted-1;
@(posedge clk);#1;
if(rst_n) begin
if(u.emit !== u.emit_c) begin $display("STATE pst=%d av=%b start=%b ck=%b ch=%b emit=%b ec=%b promote=%b nextemit=%b cp=%d qred=%d ared=%d",u.pst,u.a_v,u.a_started,u.ck_r,u.ch_r,u.emit,u.emit_c,u.promote,u.ctl_next_emit,u.cpF,u.q_red,u.a_red); $fatal(1,"registered emit mismatch cycle=%0d",k); end
if(u.promote !== u.promote_c)$fatal(1,"registered promotion mismatch cycle=%0d",k);
if(u.ctl_s2_bank[0] !== u.s2_go)$fatal(1,"registered setup mismatch cycle=%0d",k);
if(u.emit)emits=emits+1;end
end
if(accepted<10||emits<10)$fatal(1,"insufficient controller coverage %0d %0d",accepted,emits);
$display("PASS_C13_FLAGS cycles=2000 accepted=%0d emits=%0d exact_nextstate_no_extra_vectorcycle",accepted,emits);$finish;end
endmodule
