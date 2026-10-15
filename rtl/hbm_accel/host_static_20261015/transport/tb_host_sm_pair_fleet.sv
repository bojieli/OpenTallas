`timescale 1ns/1ps
`default_nettype none
module tb_host_sm_pair_fleet;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg[11:0]s_awaddr=0,s_araddr=0;reg s_awvalid=0,s_wvalid=0,s_arvalid=0;
 wire s_awready,s_wready,s_arready;reg[31:0]s_wdata=0;reg[3:0]s_wstrb=15;
 wire[1:0]s_bresp,s_rresp;wire s_bvalid,s_rvalid;reg s_bready=0,s_rready=0;wire[31:0]s_rdata;
 wire cfg_begin_v,cfg_commit_v,cfg_we,launch_v,fault;
 wire[7:0]cfg_target;wire[15:0]cfg_epoch,launch_epoch,start_loops;wire[10:0]cfg_addr,start_limit;wire[255:0]cfg_data;wire[9:0]start_base;
 wire[31:0][290:0]calendar;wire[31:0]calendar_v,done,target_ready,target_active,target_fault;
 wire[31:0][31:0]ordinal;wire[31:0][15:0]target_ready_epoch;
 ot_hbm_host_sm_pair_fleet #(.MUT(MUT)) dut(.*);
 reg[255:0]image0[0:32767],image1[0:32767];reg[290:0]expected[0:32767];string dir;
 integer cyc=0,launch_edge=-1,checked=0,writes=0,begins=0,commits=0,last_ack=-100,scenario=0;
 reg check_run=0;reg[31:0]done_seen=0;integer total=2048;
 always @(posedge clk)begin
 cyc=cyc+1;#0.01;
 if(|dut.av)begin
 last_ack=cyc;
 for(integer n=0;n<32;n++)if(dut.av[n]&&dut.ar[n]==0)case(dut.ak[n])0:writes++;1:begins++;2:commits++;endcase
 end
 if(launch_v)begin
  if(!check_run)$fatal(1,"HOST_SM_PAIR_FAIL unexpectedlaunch");
  launch_edge=cyc;done_seen=0;
 end
 if(check_run&&launch_edge>=0)begin
  if(fault||(|target_fault))$fatal(1,"HOST_SM_PAIR_FAIL executionfault");
  if(calendar_v!=0&&calendar_v!=32'hffffffff)$fatal(1,"HOST_SM_PAIR_FAIL skew");
  if(calendar_v!=0)begin
   for(integer n=0;n<32;n++)begin
    if(cyc-launch_edge<5||ordinal[n]!==32'(cyc-launch_edge-5)||ordinal[n]>=total||calendar[n]!==expected[n*1024+(ordinal[n]%1024)]||done[n]!==1'(ordinal[n]==total-1))
      $fatal(1,"HOST_SM_PAIR_FAIL phase/data sm%0d phase%0d ordinal%0d",n,cyc-launch_edge,ordinal[n]);
    checked++;
   end
  end
  if(cyc-launch_edge>=5&&cyc-launch_edge<total+5&&calendar_v!=32'hffffffff)$fatal(1,"HOST_SM_PAIR_FAIL calendarbubble");
  done_seen=done_seen|done;
 end
 end
 task automatic write(input[11:0]address,input[31:0]data,input[1:0]response,input bit actual_ack);
 integer ticks,ack_before;reg[1:0]held;bit awtake,wtake;
 begin
 ack_before=last_ack;
 // AW and W acceptance is recorded independently on each real handshake edge.
 @(negedge clk);s_awaddr=address;s_awvalid=1;s_wdata=data;s_wvalid=1;s_bready=0;
 ticks=0;
 while(s_awvalid||s_wvalid)begin
 @(posedge clk);awtake=s_awvalid&&s_awready;wtake=s_wvalid&&s_wready;
 @(negedge clk);if(awtake)s_awvalid=0;if(wtake)s_wvalid=0;
 ticks++;if(ticks>100)$fatal(1,"HOST_SM_PAIR_FAIL AXItimeout");
 end
 while(!s_bvalid)begin @(negedge clk);ticks++;if(ticks>200)$fatal(1,"HOST_SM_PAIR_FAIL ACKtimeout");end
 if(s_bresp!==response)$fatal(1,"HOST_SM_PAIR_FAIL BRESP addr%h got%0d want%0d",address,s_bresp,response);
 if(actual_ack&&(last_ack==ack_before||last_ack>=cyc))$fatal(1,"HOST_SM_PAIR_FAIL prematureBRESP withoutactualmacroACK");
 held=s_bresp;
 repeat(2)begin @(negedge clk);if(!s_bvalid||s_bresp!==held)$fatal(1,"HOST_SM_PAIR_FAIL heldBRESP");end
 s_bready=1;@(negedge clk);s_bready=0;
 end endtask
 task automatic frame(input[255:0]data,input bit error);
 for(integer wordn=0;wordn<8;wordn++)write(12'hf24,data[wordn*32+:32],wordn==7&&error?2:0,wordn==7);
 endtask
 task automatic images(input integer epoch);
 $readmemh($sformatf("%s/epoch%0d_plane0.hex",dir,epoch),image0);
 $readmemh($sformatf("%s/epoch%0d_plane1.hex",dir,epoch),image1);
 $readmemh($sformatf("%s/epoch%0d_logical.hex",dir,epoch),expected);
 endtask
 task automatic range_setup(input integer epoch);
 write(12'hf28,32'(1024<<12),0,0);write(12'hf2c,2,0,0);write(12'hf58,32'(epoch),0,0);
 endtask
 initial begin
 if(!$value$plusargs("IMAGES=%s",dir))$fatal(1,"needIMAGES");
 if($value$plusargs("case=%d",scenario))begin end
 repeat(5)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);images(1);
 if(scenario==1)begin range_setup(1);write(12'hf30,1,2,0);if(launch_v||!fault)$fatal(1,"HOST_SM_PAIR_FAIL prematurelaunch");end
 else if(scenario>=2)begin
 write(12'hf4c,32'h180,0,1);
 if(scenario==2)begin write(12'hf20,128,0,0);write(12'hf24,image0[0][31:0],0,0);write(12'hf50,32'h180,2,0);end
 if(scenario==3)begin write(12'hf20,32'((1024<<8)|128),0,0);frame(image1[0],1);end
 if(scenario==4)begin write(12'hf20,128,0,0);frame(image0[0]^(256'b1<<223),1);end
 if(scenario==5)write(12'hf50,32'h180,2,1);
 if(scenario==6)write(12'hf4c,32'h180,2,1);
 if(!fault)$fatal(1,"HOST_SM_PAIR_FAIL missingstickyfault");
 end else begin
 for(integer epoch=1;epoch<=2;epoch++)begin
 images(epoch);
 for(integer sm=0;sm<32;sm++)begin
 write(12'hf4c,32'((epoch<<8)|(128+sm)),0,1);
 write(12'hf20,32'(128+sm),0,0);
 for(integer pc=0;pc<1024;pc++)begin frame(image0[sm*1024+pc],0);frame(image1[sm*1024+pc],0);end
 write(12'hf50,32'((epoch<<8)|(128+sm)),0,1);
 end
 if(target_ready!==32'hffffffff)$fatal(1,"HOST_SM_PAIR_FAIL actualready");
 range_setup(epoch);check_run=1;launch_edge=-1;done_seen=0;
 write(12'hf30,1,0,0);
 while(done_seen!=32'hffffffff)@(negedge clk);
 repeat(15)@(negedge clk);check_run=0;launch_edge=-1;
 end
 if(writes!=131072||begins!=64||commits!=64||checked!=131072)$fatal(1,"HOST_SM_PAIR_FAIL counts writes%0d begins%0d commits%0d outputs%0d",writes,begins,commits,checked);
 $display("HOST_SM_PAIR_PASS targets=32 actualSRAMs=64 epochs=2 frames=%0d outputs=%0d launch_phase=5 II=1 cycles=%0d",writes,checked,cyc);$finish;
 end
 $display("HOST_SM_PAIR_NEGATIVE_PASS case=%0d actualwrites=%0d",scenario,writes);$finish;
 end
 initial begin #50000000;$fatal(1,"HOST_SM_PAIR_FAIL timeout");end
endmodule
`default_nettype wire
