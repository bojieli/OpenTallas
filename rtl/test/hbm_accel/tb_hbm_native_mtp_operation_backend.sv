`timescale 1ns/1ps
module tb_hbm_native_mtp_operation_backend;
 parameter integer OP=0,IDX=0,NCOL=6,POS=1048570,MUT=0,ECC=0,MISSING=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,iv=0,cv=0,cr=0;reg [3:0] ik=0;reg [63:0] ipc=0;
 reg [200:0] cmd=0;reg [31:0] sd=0,rv=0;reg [1023:0] rd=0;
 wire ready,done,cf,busy,fault,av;wire [16:0] am;wire [31:0] lj,seq,count;wire [3:0] gen;wire [7:0] epoch;
 wire [31:0] lv;wire [63:0] pc;wire [33:0] tok;wire [39:0] pos;wire [145:0] owner;
 integer t,k,cycles=0;reg [31:0] q=0;reg [63:0] qpc=0;
 ot_hbm_native_mtp_operation_backend #(.ENABLE(1)) dut(
 .clk(clk),.rst_n(rst_n),.external_fault(1'b0),.backend_quiescent(1'b1),
 .install_v(iv),.install_kind(ik),.install_pc(ipc),.noise_token(17'd129279),
 .cmd_v(cv),.cmd_ready(ready),.cmd(cmd),.cmd_job(32'h12345678),.cmd_generation(4'ha),.cmd_sequence(32'd999),.cmd_epoch(8'h81),
 .cpl_v(done),.cpl_ready(cr),.cpl_job(lj),.cpl_generation(gen),.cpl_sequence(seq),.cpl_epoch(epoch),.cpl_fault(cf),
 .am_v(av),.am_idx(am),.launch_v(lv),.launch_pc(pc),.launch_token(tok),.launch_pos(pos),.launch_owner(owner),
 .sm_done(sd),.sm_fault(32'b0),.res_v(rv),.res_data(rd),.busy(busy),.fault(fault),.st_launches(count));
 always @(posedge clk)begin
  if(|lv)begin
   if(lv!==32'hffffffff||tok[16:0]!==tok[33:17]||pos[19:0]!==pos[39:20])$fatal(1,"paired launch");
   if(owner[72:0]!=={pos[19:0],tok[16:0],4'ha,32'h12345678})$fatal(1,"real owner");
   $display("LAUNCH kind=%0d token=%0d pos=%0d pc0=%0d pc1=%0d",pc[31:0]/100-1,tok[16:0],pos[19:0],pc[31:0],pc[63:32]);
  end
  if(av)$display("ARGMAX token=%0d",am);
  q<=lv;qpc<=pc;sd<=q;rv<=0;rd<=0;
  if(qpc[31:0]==500 || qpc[31:0]==1100)begin
   rv<=q;for(k=0;k<32;k=k+1)rd[k*32+:32]<=32'd129279;
  end
 end
 initial begin
 @(negedge clk);rst_n=1;
 for(t=0;t<11;t=t+1)begin iv=1;ik=t;ipc={32'(100*(t+1)+1),32'(100*(t+1))};if(MISSING&&t==7)iv=0;@(negedge clk);end
 iv=0;
 if(ECC==1)dut.template_pc[0][0]=~dut.template_pc[0][0];
 if(ECC==2)begin dut.template_pc[0][0]=~dut.template_pc[0][0];dut.template_pc[0][1]=~dut.template_pc[0][1];end
 cmd[3:0]=OP;cmd[11:4]=IDX;cmd[15:12]=NCOL;cmd[47:16]=POS;cmd[64:48]=17'd131071;
 for(t=0;t<8;t=t+1)cmd[65+t*17+:17]=131071-t;
 cv=1;@(negedge clk);cv=0;
 while(!done)begin @(negedge clk);cycles=cycles+1;if(cycles>1500)$fatal(1,"finite35 launch mechanism deadlock");end
 if(lj!=32'h12345678||gen!=4'ha||seq!=999||epoch!=8'h81)$fatal(1,"native completion identity");
 $display("COMPLETE fault=%0d launches=%0d cycles=%0d",cf,count,cycles);
 repeat(5)begin @(negedge clk);if(!done)$fatal(1,"completion not held");end
 cr=1;@(negedge clk);$finish;
 end
endmodule
