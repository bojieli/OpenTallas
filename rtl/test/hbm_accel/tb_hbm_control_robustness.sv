`timescale 1ns/1ps
module tb_hbm_control_robustness;
 reg clk=0;always #5 clk=~clk;
 reg por=0,pg=0,lock=0,bd=0,bp=0,fatal=0,requal=0;
 reg [3:0] phy=0,links=0;
 wire pr,cr,cmd,ready;wire [3:0] phr,lr,state;wire local_reset;
 ot_hbm_reset_seq rs(clk,por,pg,lock,phy,links,bd,bp,fatal,requal,pr,phr,lr,cr,cmd,ready,state);
 ot_hbm_reset_release rr(clk,cmd,local_reset);
 reg [15:0] ce=0,ue=0;reg hp=0,lu=0,su=0,clear=0,idle=0;
 wire fault,irq;wire [31:0] cause,nce,nue;
 ot_hbm_fault_agg fa(clk,por,ce,ue,hp,lu,su,clear,idle,fault,irq,cause,nce,nue);
 reg job_v=0;wire jr,hrv,dbv,busy;wire [73:0] hrd;wire [2:0] status;
 ot_hbm_token_loop #(.EXTERNAL_FAULT_EN(1)) tl(
 .clk(clk),.rst_n(por),.post_en(1'b1),.external_fault(fault),.job_v(job_v),.job_rdy(jr),
 .job_id(32'd9),.job_tok(17'd8),.job_pos(20'd42),.job_ngen(20'd50),.job_eos(17'd1),.job_eos_en(1'b1),.job_maxpos(21'd1048576),.job_mtp(1'b0),
 .host_stop(1'b0),.hr_v(hrv),.hr_rdy(1'b0),.hr_d(hrd),.db_v(dbv),.db_rdy(1'b1),
 .cpl_v(1'b0),.cpl_token(17'b0),.cpl_status(4'b0),.mtp_v(1'b0),.mtp_n(3'b0),.mtp_tok(102'b0),.busy(busy),.last_status(status));
 task tick;begin @(posedge clk);#1;end endtask
 task settle;integer j;begin for(j=0;j<7;j=j+1)tick;end endtask
 integer i;
 initial begin
  #1;por=0;tick;por=1;settle;
  if(state!=0 || pr || cmd)$fatal(1,"unpowered boot release");
  pg=1;settle;if(state!=1 || !pr || phr)$fatal(1,"PLL stage");
  lock=1;settle;if(state!=2 || phr!=15 || lr)$fatal(1,"PHY stage");
  phy=15;settle;if(state!=3 || lr!=15 || cr)$fatal(1,"LINK stage");
  links=15;settle;if(state!=4 || !cr || cmd)$fatal(1,"BIST stage");
  bd=1;bp=1;settle;if(!ready || !local_reset)$fatal(1,"ready stage");
  lock=0;settle;if(state!=6 || cmd || local_reset)$fatal(1,"lock loss reset");
  lock=1;requal=1;tick;requal=0;settle;if(!ready)$fatal(1,"requalification");
  // Every CE is counted without stopping; every UE source survives busy clear.
  for(i=0;i<16;i=i+1) begin ce=16'b1<<i;tick;ce=0;end
  if(nce!=16 || fault)$fatal(1,"correctable handling");
  job_v=1;tick;job_v=0;settle;if(!busy)$fatal(1,"no waiting job");
  ue=16'h1;clear=1;idle=0;tick;ue=0;clear=0;settle;
  if(busy || status!=4 || !hrv || hrd[72:70]!=4 || hrd[16:0]!=0)$fatal(1,"fault abort without completion");
  for(i=1;i<16;i=i+1) begin ue=16'b1<<i;tick;ue=0;end
  hp=1;lu=1;su=1;tick;hp=0;lu=0;su=0;
  if(cause!=32'he000ffff || nue!=16)$fatal(1,"sticky cause map");
  clear=1;idle=1;ue=16'h4;tick;clear=0;ue=0;
  if(!fault || cause!=4 || !irq)$fatal(1,"UE clear priority");
  clear=1;tick;clear=0;if(fault || cause)$fatal(1,"idle clear");
  $display("PASS reset/fault/token abort");$finish;
 end
 initial begin #20000;$fatal(1,"bench watchdog");end
endmodule
