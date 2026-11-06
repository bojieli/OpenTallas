`timescale 1ns/1fs
module tb;reg ck=0,raw=0;always #0.4165 ck=~ck;wire rs,qref,qn,qp,qr;integer n=0,pm=0,rm=0,checks=0;
ot_dp_landing_root #(.SETTLE(8)) root(.clk(ck),.rst_raw_n(raw),.start(rs),.start_d());
start_reference ref0(.t_st_n0__clk(ck),.t_st_n1__clk(ck),.rs_R(rs),.rraw_R(raw),.pst_D(qref));

start_nominal good(.clk(ck),.rs_R(rs),.rraw_R(raw),.pst_D(qn));
start_pad_mutant mp(.clk(ck),.rs_R(rs),.rraw_R(raw),.pst_D(qp));
start_reset_mutant mr(.clk(ck),.rs_R(rs),.rraw_R(raw),.pst_D(qr));
realtime last=0;always@(posedge ck)begin if(last && $rtoi(($realtime-last)*1000000+0.5)!=833000)$fatal(1,"period");last=$realtime;end
always@(negedge ck)begin n++;raw=(n>=8&&n<80)||(n>=96&&n<180)||n>=196;#0.001;
if(qn!==qref)$fatal(1,"canonical carrier mismatch n%0d",n);checks++;if(qp!==qref)pm++;if(qr!==qref)rm++;
if(n==300)begin if(pm==0||rm==0)$fatal(1,"missed mutants %0d/%0d",pm,rm);$display("START_EXACT_PASS checks%0d PADmutant%0d RESETmutant%0d period833000fs cold+2warmreset",checks,pm,rm);$finish;end
end endmodule
