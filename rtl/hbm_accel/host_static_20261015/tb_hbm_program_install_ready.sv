`timescale 1ns/1ps
// Two real F20 targets feeding two actual mapped programme SRAM calendars.
module tb_hbm_program_install_ready;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,cv=0,dv=0,lv=0;
reg[7:0] ct=0;reg[11:0] ca=0,db=0;reg[12:0] dl=1;reg[15:0] loops=1;reg[255:0] data=0;
wire[1:0] ready,tf,pwe,ps,active,done,cf,valid;
wire[9:0] pa[0:1],pb[0:1];wire[255:0] pd[0:1];wire[10:0] pl[0:1];wire[15:0] pn[0:1];
wire[186:0] out[0:1];wire[31:0] ordinal[0:1];
integer starts[0:1],writes[0:1];integer cyc=0;
for(genvar k=0;k<2;k=k+1)begin:t
 ot_static_program_target #(.TARGET(8'(56+k)),.PCW(10)) target(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_target(ct),.cfg_addr(ca),.cfg_data(data),
 .desc_v(dv),.desc_base(db),.desc_limit(dl),.desc_loops(loops),.launch_v(lv),.program_active(active[k]),
 .program_cfg_we(pwe[k]),.program_cfg_addr(pa[k]),.program_cfg_data(pd[k]),.program_start_v(ps[k]),.program_start_base(pb[k]),
 .program_start_limit(pl[k]),.program_start_loops(pn[k]),.configured(ready[k]),.fault(tf[k]));
 ot_vms_calendar_static #(.W(187)) consumer(.clk(clk),.rst_n(rst_n),.cfg_we(pwe[k]),.cfg_addr(pa[k]),.cfg_data(pd[k]),
 .start_v(ps[k]),.start_base(pb[k]),.start_limit(pl[k]),.start_loops(pn[k]),.calendar(out[k]),.calendar_v(valid[k]),
 .ordinal(ordinal[k]),.active(active[k]),.done(done[k]),.fault(cf[k]));
end
always @(posedge clk)for(integer k=0;k<2;k++)if(!rst_n)begin starts[k]<=0;writes[k]<=0;end
else begin if(ps[k])starts[k]<=starts[k]+1;if(pwe[k])writes[k]<=writes[k]+1;end
task tick;begin @(posedge clk);#1;cyc++;@(negedge clk);end endtask
task reset;begin rst_n=0;cv=0;dv=0;lv=0;ct=0;db=0;dl=1;loops=1;repeat(4)tick;rst_n=1;repeat(5)tick;end endtask
function automatic[186:0] value(input integer pc,input integer epoch);
 value=187'h123456789012345678900fedef1e2d3c4b5a69 ^(187'(pc)*187'h178951178951178951178951178951) ^ (187'(epoch)<<128);
endfunction
task write_row(input integer q,input integer row,input integer epoch);
 begin ct=8'(56+q);ca=12'(row);data=0;data[255:240]=16'hc7a1;data[233:224]=10'(row);data[186:0]=value(row,epoch);cv=1;tick;cv=0;end
endtask
task settle;begin repeat(5)tick;end endtask
task descriptor(input integer q,input integer base,input integer count,input integer lp);
 begin ct=8'(56+q);db=12'(base);dl=13'(base+count);loops=16'(lp);dv=1;tick;dv=0;end
endtask
task ready_exact(input integer q,input integer rows);
 begin
 for(integer j=1;j<=rows+2;j++)begin
  tick;
  if(j<rows+2 && ready[q])$fatal(1,"readiness advertised before exact row scan j%0d rows%0d",j,rows);
 end
 if(!ready[q]||tf[q])$fatal(1,"valid installed range not ready q%0d ready%b tf%b",q,ready,tf);
 end
endtask
task run_exact(input integer q,input integer base,input integer count,input integer lp,input integer epoch);
 integer lc;
 begin
 lv=1;lc=cyc+1;tick;lv=0;
 while(cyc<lc+6)begin if(|valid)$fatal(1,"programme began before fixed boundary edge");tick;end
 for(integer j=0;j<count*lp;j++)begin
  if(!valid[q] || valid[1-q] || out[q]!==value(base+j%count,epoch) || ordinal[q]!==32'(j))
   $fatal(1,"actual mapped SRAM wrong fixed output q%0d j%0d",q,j);
  if(j==count*lp-1 && !done[q])$fatal(1,"missing programme completion");
  tick;
 end
 if(|valid || |tf || |cf)$fatal(1,"trailing data or normal programme fault");
 settle;
 end
endtask
task reject_range(input integer q,input integer rows);
 begin
 repeat(rows+5)tick;
 if(ready[q] || !tf[q])$fatal(1,"missing installed row was accepted q%0d",q);
 lv=1;tick;lv=0;repeat(10)tick;
 if(starts[0]||starts[1]||valid!=0)$fatal(1,"invalid range launched or replayed");
 end
endtask
integer which=-1,old_writes;
initial begin
 if(!$value$plusargs("CASE=%d",which))which=-1;
 if(which==-1||which==0)begin
 reset;write_row(0,39,1);write_row(0,37,1);write_row(0,38,1);settle;
 descriptor(0,37,3,2);ready_exact(0,3);run_exact(0,37,3,2,1);
 if(starts[0]!=1||starts[1]!=0)$fatal(1,"wrong sparse launch count");
 end
 for(integer miss=0;miss<3;miss++)if(which==-1||which==miss+1)begin
 reset;for(integer j=0;j<3;j++)if(j!=miss)write_row(0,37+j,1);settle;
 descriptor(0,37,3,1);reject_range(0,3);
 end
 if(which==-1||which==4)begin
 reset;for(integer j=0;j<3;j++)write_row(0,37+j,1);settle;
 descriptor(0,37,3,1);ready_exact(0,3);run_exact(0,37,3,1,1);
 // Actual SRAM rows38/39 retain old valid payloads; the new image generation must not inherit them.
 write_row(0,37,2);settle;descriptor(0,37,3,1);repeat(8)tick;
 if(ready[0]||!tf[0])$fatal(1,"stale previous-generation rows accepted");
 lv=1;tick;lv=0;repeat(10)tick;if(starts[0]!=1)$fatal(1,"stale image emitted a new start");
 end
 if(which==-1||which==5)begin
 reset;for(integer j=0;j<3;j++)write_row(0,37+j,1);settle;
 descriptor(0,37,3,1);tick;lv=1;tick;lv=0;repeat(10)tick;
 if(starts[0]!=0||!tf[0])$fatal(1,"early launch was dynamically delayed or accepted");
 end
 if(which==-1||which==6)begin
 reset;write_row(0,1024,1);settle;
 if(!tf[0]||writes[0]!=0||ready[0]||tf[1])$fatal(1,"invalid write reached macro or wrong target");
 end
 if(which==-1||which==7)begin
 reset;write_row(0,37,1);write_row(1,91,2);settle;
 descriptor(0,37,1,1);ready_exact(0,1);run_exact(0,37,1,1,1);
 descriptor(1,91,1,2);ready_exact(1,1);run_exact(1,91,1,2,2);
 if(starts[0]!=1||starts[1]!=1)$fatal(1,"multi-target global launch replayed consumed target");
 end
 if(which==-1||which==8)begin
 reset;write_row(0,37,1);settle;
 descriptor(0,37,1,1);ready_exact(0,1);run_exact(0,37,1,1,1);
 descriptor(0,37,1,2);tick;
 if(ready[0])$fatal(1,"resident rearm advertised before transport");tick;
 if(!ready[0]||tf[0])$fatal(1,"unchanged resident range needlessly rescanned");
 run_exact(0,37,1,2,1);
 if(starts[0]!=2||writes[0]!=1)$fatal(1,"descriptor-only resident image reuse failed");
 end
 if(which==-1||which==9)begin
 reset;for(integer j=0;j<1024;j++)write_row(0,j,3);settle;
 descriptor(0,0,1024,1);ready_exact(0,1024);run_exact(0,0,1024,1,3);
 if(writes[0]!=1024)$fatal(1,"full-shape actual write count");
 end
 if(which==-1||which==10)begin
 reset;write_row(0,37,1);settle;descriptor(0,37,1,32);ready_exact(0,1);
 lv=1;tick;lv=0;repeat(6)tick;old_writes=writes[0];write_row(0,37,2);settle;
 if(!tf[0]||writes[0]!=old_writes)$fatal(1,"active programme write was not refused");
 end
 if(which==-1||which==11)begin
 reset;ct=56;ca=37;data=0;data[239:224]=37;cv=1;tick;cv=0;settle;
 if(!tf[0]||writes[0]!=0||ready[0])$fatal(1,"bad programme magic written to real SRAM");
 end
 if(which==-1||which==12)begin
 reset;ct=56;ca=37;data=0;data[255:240]=16'hc7a1;data[239:224]=38;cv=1;tick;cv=0;settle;
 if(!tf[0]||writes[0]!=0||ready[0])$fatal(1,"wrong programme PC written to real SRAM");
 end
 if(which==-1||which==13)begin
 reset;write_row(0,37,1);descriptor(0,37,1,1);
 for(integer j=1;j<=4;j++)begin tick;if(j<4 && ready[0])$fatal(1,"readiness raced actual SRAM write commit");end
 if(!ready[0]||tf[0])$fatal(1,"committed single-row range not ready");run_exact(0,37,1,1,1);
 end
 if(which==-1||which==14)begin
 reset;write_row(1,37,1);settle;descriptor(0,37,1,1);reject_range(0,1);
 if(writes[0]!=0||writes[1]!=1||tf[1])$fatal(1,"another target write polluted installation state");
 end
 $display("PROGRAM_INSTALL_READY PASS case=%0d actual2x1024x256 macros sparse/missing/generation/invalid/multi-target/full1024 fixed edges",which);$finish;
end
endmodule
