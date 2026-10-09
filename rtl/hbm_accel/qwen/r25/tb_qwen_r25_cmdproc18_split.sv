`timescale 1ns/1ps
module tb_qwen_r25_cmdproc18_split;
reg ck=0;always #1 ck=~ck;
reg rst=1;
reg [342:0] f_loader=0;
wire [147:0] xl;
wire [15:0] xb,xt;
tri [826:0] cNE,cNW,cSE,cSW;
wire [63:0] t_su_NE,t_su_NW,t_su_SE,t_su_SW,t_barrier;
wire [24:0] t_coll;
reg [17:0] north_token=0,south_token=0;
integer north_launches=0,south_launches=0;
for(genvar k=0;k<8;k=k+1)begin
 assign cNE[44+k*103]=1'b1;assign cNW[44+k*103]=1'b1;
 assign cSE[44+k*103]=1'b1;assign cSW[44+k*103]=1'b1;
end
assign cNE[42]=0;assign cNW[42]=0;assign cSE[42]=0;assign cSW[42]=0;
hfd_cmdproc_n_qwen18 n(.cNE(cNE),.cNW(cNW),.ck(ck),.rst(rst),.f_barrier(64'd0),.f_coll(33'd0),.t_barrier(t_barrier),.t_coll(t_coll),.t_su_NE(t_su_NE),.t_su_NW(t_su_NW),.xb(xb),.xl(xl),.xt(xt));
hfd_cmdproc_s_qwen18 s(.cSE(cSE),.cSW(cSW),.ck(ck),.rst(rst),.f_loader(f_loader),.f_router(64'd0),.t_su_SE(t_su_SE),.t_su_SW(t_su_SW),.xb(xb),.xl(xl),.xt(xt));
always @(negedge ck)begin
 if(n.w_cpN_launch_v)begin
 north_launches=north_launches+1;
 if(n.w_cpN_launch_token!==north_token || n.w_cpN_launch_pos!==20'hfffff || n.w_cpN_cpl_job!==32'hfedcba98 || n.w_cpN_cpl_generation!==4'hd)$fatal(1,"N_TUPLE_TRUNCATION");
 end
 if(s.w_cpS_launch_v)begin
 south_launches=south_launches+1;
 if(s.w_cpS_launch_token!==south_token || s.w_cpS_launch_pos!==20'hfffff || s.w_cpS_cpl_job!==32'hfedcba98 || s.w_cpS_cpl_generation!==4'hd)$fatal(1,"S_TUPLE_TRUNCATION");
 end
end
function [147:0] tuple(input reg we,input reg [7:0] addr,input reg [63:0] word,input reg db,input reg [17:0] token);
 tuple={4'hd,32'hfedcba98,20'hfffff,token,db,word,addr,we};
endfunction
task tick;begin @(posedge ck);#0.1;@(negedge ck);#0.1;end endtask
integer i,old_n,old_s;
initial begin
 repeat(20)tick;rst=0;repeat(20)tick;
 f_loader={47'd0,tuple(1,0,(64'd1<<60)|(64'hffff<<44)|64'h1234,0,0),tuple(1,0,(64'd1<<60)|(64'hffff<<44)|64'h1234,0,0)};repeat(16)tick;
 f_loader={47'd0,tuple(1,1,64'd2<<60,0,0),tuple(1,1,64'd2<<60,0,0)};repeat(16)tick;
 f_loader=0;repeat(16)tick;
 for(i=0;i<3;i=i+1)begin
 north_token=(i==0)?18'd131072:((i==1)?18'd151935:18'd131071);
 south_token=(i==0)?18'd151935:((i==1)?18'd131071:18'd131072);
 old_n=north_launches;old_s=south_launches;
 f_loader={47'd0,tuple(0,0,0,1,north_token),tuple(0,0,0,1,south_token)};tick;
 f_loader=0;repeat(80)tick;
 if(north_launches!=old_n+1||south_launches!=old_s+1)$fatal(1,"split launches missing/duplicated");
 if(t_su_NE!=={46'd0,north_token} || t_su_NW!=={46'd0,north_token} || t_su_SE!=={46'd0,south_token} || t_su_SW!=={46'd0,south_token})$fatal(1,"SU_TOKEN_TRUNCATION");
 end
 $display("QWEN_CMDPROC18_SPLIT_PASS north_launches=%0d south_launches=%0d boundary_tokens=131071,131072,151935 NSM16 RDREG2 loader343 split148",north_launches,south_launches);$finish;
end
endmodule
