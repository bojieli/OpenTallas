`timescale 1ns/1ps
module tb_s81_owned_capture;
reg clk=0; always #0.4165 clk=~clk;
reg rst=0; reg [6:0] fv_in=0; reg [1127:0] fd_in=0;
reg [7:0] tid=0; reg [63:0] cs_n=0,cs_s=0; reg [274:0] dl_in=0; reg [32:0] ul_in=0;
wire [6:0] sv,srv,slo,nv,nrv,nlo; wire [1127:0] sd,srd,sld,nd,nrd,nld;
wire [274:0] ndl,nrdl; wire [32:0] nul,nrul;
reg [6:0] srl=0,nrl=0; reg [1127:0] srdl,nrfdl;
ownership_serial_ref sr(clk,rst,fv_in,fd_in,srv,srd);
ot_s81_hc_ctfx_cap sc(clk,rst,fv_in,fd_in,sv,sd,slo,sld);
ownership_nt_ref #(.CHAIN_STEP(6)) nr(.clk(clk),.rst_in(rst),.fv_in(fv_in),.fd_in(fd_in),.fv(nrv),.fdx(nrd),.tid(tid),.cs_n(cs_n),.cs_s(cs_s),.dl_in(dl_in),.dl_out(nrdl),.ul_in(ul_in),.ul_out(nrul));
ot_s81_hc_ctfx_nt #(.CHAIN_STEP(6)) nc(.clk(clk),.rst_in(rst),.fv_in(fv_in),.fd_in(fd_in),.fv(nv),.fdx(nd),.fv_local(nlo),.fdx_local(nld),.tid(tid),.cs_n(cs_n),.cs_s(cs_s),.dl_in(dl_in),.dl_out(ndl),.ul_in(ul_in),.ul_out(nul));
// Frozen region's actual capture/reset edges, before relocation into leaf owners.
always @(posedge clk or negedge rst) if (!rst) begin srl<=0;nrl<=0;end else begin srl<=srv;nrl<=nrv;end
always @(posedge clk) begin srdl<=srd;nrfdl<=nrd;end
integer i,k,errors=0,resets=0;
initial begin
for(i=0;i<10000;i=i+1) begin
@(negedge clk);
if(i<5 || i%173==0 || i%173==1) begin rst=0;resets=resets+1;end else rst=1;
fv_in=$urandom;tid=$urandom;cs_n={$urandom,$urandom};cs_s={$urandom,$urandom};ul_in={$urandom,$urandom};
for(k=0;k<35;k=k+1) fd_in[32*k+:32]=$urandom;fd_in[1127:1120]=$urandom;
for(k=0;k<8;k=k+1) dl_in[32*k+:32]=$urandom;dl_in[274:256]=$urandom;
@(posedge clk);#0.05;
if(i>4 && ({sv,sd,slo,sld,nv,nd,nlo,nld,ndl,nul} !== {srv,srd,srl,srdl,nrv,nrd,nrl,nrfdl,nrdl,nrul})) errors=errors+1;
end
$display("OWNED_CAPTURE cycles=10000 reset_cycles=%0d errors=%0d",resets,errors);
if(errors) $fatal(1,"owned capture lockstep FAIL");
$display("OWNED_CAPTURE PASS");$finish;
end
endmodule
