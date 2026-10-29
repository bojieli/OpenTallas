`timescale 1ns/1ps
module tb_collar;
parameter integer FAN=1,MUT=0;
reg clk=0;always #5 clk=~clk;
reg rst=0,cv=0,gcv=0,dv=0,lv=0;reg[11:0]addr=0;reg[255:0]data=0;
wire[768:0]prm,gprm;wire[288:0]native_cfg;wire ready,fault,start_v,gr,gf,gs;
wire[1:0]go,ggo;wire[220:0]rec,grec;wire pw,gpw;wire[7:0]pa,gpa;wire[255:0]pd,gpd;
ot_hbm_static_cfg_collar_idx256r_r2048 #(.FAN32(FAN),.MUT(MUT)) dut(.clk(clk),.clk_in(clk),.rst_n(rst),.tgt(8'h78),.cfg_v(cv),.cfg_target(8'h78),.cfg_addr(addr),.cfg_data(data),.desc_v(dv),.launch_v(lv),.c_busy(2'b0),.c_done(1'b0),.c_fault(5'b0),.pw_we(pw),.pw_addr(pa),.pw_data(pd),.prm(prm),.native_cfg(native_cfg),.start_v(start_v),.go(go),.rec(rec),.ready(ready),.active(),.fault(fault));
ot_hbm_static_cfg_collar_idx256r #(.FAN32(FAN)) gold(.clk(clk),.clk_in(clk),.rst_n(rst),.tgt(8'h78),.cfg_v(gcv),.cfg_target(8'h78),.cfg_addr(addr),.cfg_data(data),.desc_v(dv),.launch_v(lv),.c_busy(2'b0),.c_done(1'b0),.c_fault(5'b0),.pw_we(gpw),.pw_addr(gpa),.pw_data(gpd),.prm(gprm),.start_v(gs),.go(ggo),.rec(grec),.ready(gr),.active(),.fault(gf));
task tick;begin @(posedge clk);#1;end endtask
task reset;begin @(negedge clk);rst=0;cv=0;gcv=0;dv=0;lv=0;repeat(5)tick();@(negedge clk);rst=1;repeat(30)tick();end endtask
task wr(input[11:0]a,input[255:0]d,input both);begin @(negedge clk);addr=a;data=d;cv=1;gcv=both;tick();@(negedge clk);cv=0;gcv=0;repeat(4)tick();end endtask
task arm;begin @(negedge clk);dv=1;tick();@(negedge clk);dv=0;repeat(5)tick();end endtask
task launch;begin @(negedge clk);lv=1;tick();@(negedge clk);lv=0;end endtask
reg[288:0]cfg;reg[255:0]row;integer r,i,seen;
task install(input bad);begin
 for(r=0;r<6;r=r+1)wr(12'h800+12'(r),0,1);
 wr(12'hE01,0,1);
 for(r=0;r<8;r=r+1)wr(12'hC00+12'(r),0,1);
 cfg=0;for(r=0;r<4;r=r+1)begin cfg[r*68+:17]=17'(r*8192+128);cfg[r*68+17+:17]=17'(r*8192+512);cfg[r*68+34+:17]=4;cfg[r*68+51+:17]=512;end
 cfg[276:272]=2;cfg[288:277]=128;if(bad)cfg[68+:17]=128;
 wr(12'h806,cfg[255:0],0);
end endtask
initial begin
 reset();install(0);arm();if(ready)$fatal(1,"missing row accepted");
 wr(12'h807,{223'b0,cfg[288:256]},0);arm();if(!ready||fault||!gr||gf)$fatal(1,"valid publication refused");
 if(native_cfg!==cfg||prm!==gprm)$fatal(1,"publisher fields mismatch");
 for(r=0;r<4;r=r+1)if(native_cfg[r*68+13+:2]!==2'(r))$fatal(1,"role SID mismatch");
 launch();seen=0;repeat(24)begin tick();if(start_v)seen=seen+1;if({start_v,go,pw,ready,fault}!=={gs,ggo,gpw,gr,gf})$fatal(1,"legacy date mismatch");end
 if(seen!=1)$fatal(1,"launch date missing");
 reset();install(1);wr(12'h807,{223'b0,cfg[288:256]},0);arm();if(ready)$fatal(1,"wrong SID accepted");launch();repeat(5)tick();if(!fault||start_v)$fatal(1,"wrong SID not failclosed");
 reset();install(0);row={223'b0,cfg[288:256]};row[33]=1;wr(12'h807,row,0);if(!fault)$fatal(1,"reserved row bits accepted");
 $display("NATIVE_CFG PASS fan=%0d explicit4SID missingrow wrongSID reserved launchsameedge",FAN);$finish;
end
endmodule
