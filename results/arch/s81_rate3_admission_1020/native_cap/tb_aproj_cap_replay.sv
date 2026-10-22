`timescale 1ns/1ps
module tb_aproj_cap_replay;
 reg ck=0,rst_n=0;always #0.5 ck=~ck;
 reg [279:0] rt_w=0,rt_e=0;reg cfg_v=0;reg [159:0] cfg_d=0;
 wire [5:0] sv;wire [71:0] sa;wire [191:0] sd;wire [3:0] nv;wire [47:0] na;wire [127:0] nd;wire fault;
 ot_s81sl_capc5c dut(.rst_n(rst_n),.rt_w(rt_w),.rt_e(rt_e),.cfg_v(cfg_v),.cfg_d(cfg_d),
 .cw_s_v(sv),.cw_s_a(sa),.cw_s_d(sd),.cw_n_v(nv),.cw_n_a(na),.cw_n_d(nd),.fault(fault),
 .ck_rt(ck),.ck_cw(ck),.ck_ce(ck),.ck_rn(ck),.ck_rs(ck));
 wire [9:0] valid={nv,sv};wire [119:0] addresses={na,sa};wire [319:0] values={nd,sd};
 reg [720:0] stim[0:2047];reg [47:0] expected[0:511];reg seen[0:511];
 integer edge_n=0,T=1100,N=0,errors=0,writes=0,p,j,found;reg [47:0] actual;string dir;
 initial begin
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR");
 if(!$value$plusargs("T=%d",T)) T=1100;if(!$value$plusargs("N=%d",N)) $fatal(1,"N");
 for(j=0;j<512;j=j+1)seen[j]=0;
 $readmemh({dir,"/stim.hex"},stim);$readmemh({dir,"/expected.hex"},expected);
 #5.2 rst_n=1;
 end
 always @(negedge ck) if(rst_n && edge_n<2048)begin {cfg_v,cfg_d,rt_e,rt_w}=stim[edge_n];end
 always @(posedge ck) if(rst_n)begin
 edge_n<=edge_n+1;
 #0.05;
 if(edge_n>150 && $isunknown(valid))begin $display("CAP_UNKNOWN %0d",edge_n);errors=errors+1;end
 for(p=0;p<10;p=p+1)if(valid[p]===1'b1)begin
 actual={3'(p/2),1'(p%2),addresses[12*p+:12],values[32*p+:32]};found=-1;
 for(j=0;j<N;j=j+1)if(expected[j]===actual && !seen[j])found=j;
 $display("CAP_WRITE %0d %0d %0d %0d %08h",edge_n,p/2,p%2,addresses[12*p+:12],values[32*p+:32]);
 if(found<0)begin $display("CAP_BAD_WRITE %012h",actual);errors=errors+1;end else seen[found]=1;
 writes=writes+1;
 end
 if(edge_n>=T)begin
 for(j=0;j<N;j=j+1)if(!seen[j])begin $display("CAP_MISSING %012h",expected[j]);errors=errors+1;end
 if(fault!==1'b0)begin $display("CAP_FAULT %b",fault);errors=errors+1;end
 $display("CAP_REPLAY_END edges=%0d writes=%0d expected=%0d errors=%0d fault=%b",edge_n,writes,N,errors,fault);
 if(errors==0)$display("PASS actual_aproj_to_candidate_CAP");else $display("FAIL actual_aproj_to_candidate_CAP");$finish;
 end
 end
endmodule
