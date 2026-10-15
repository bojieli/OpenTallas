`timescale 1ns/1ps
module host_su_axi_tb;
localparam integer B=@BITS@,N=@EDGES@,W=@WRITES@,M=@MACROS@;
logic clk=0;always #5 clk=~clk;
logic rst_n=0;logic[11:0] awaddr=0,araddr=0;logic awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
logic[31:0] wdata=0;logic[3:0] wstrb=15;
wire awready,wready,bvalid,arready,rvalid;wire[1:0] bresp,rresp;wire[31:0] rdata;
wire block_ready,busy,valid,done,fault;wire[15:0] edge_index;wire[B-1:0] command;
reg[279:0] config_words[0:W-1];reg[B-1:0] expected_words[0:N-1];string dir;
integer cycles=0,launch_edge=-1,seen=0,replays=0;reg busy_old=0;
host_su_axi_install #(.LINE_BITS(B),.EDGES(N),.COLS((B+255)/256),.DICT_ENTRIES(@ENTRIES@),.DICT_BANKS(@BANKS@),.MACROS(M)) dut(
 .clk(clk),.rst_n(rst_n),.clk_macro({M{clk}}),
 .s_awaddr(awaddr),.s_awvalid(awvalid),.s_awready(awready),.s_wdata(wdata),.s_wstrb(wstrb),.s_wvalid(wvalid),.s_wready(wready),
 .s_bresp(bresp),.s_bvalid(bvalid),.s_bready(bready),.s_araddr(araddr),.s_arvalid(arvalid),.s_arready(arready),
 .s_rdata(rdata),.s_rresp(rresp),.s_rvalid(rvalid),.s_rready(rready),
 .block_ready(block_ready),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
task automatic tick;@(posedge clk);#1;endtask
task automatic reset_target;
 @(negedge clk);rst_n=0;awvalid=0;wvalid=0;bready=0;arvalid=0;rready=0;tick();@(negedge clk);rst_n=1;tick();
endtask
// Independently accepted AW/W channels, stable held B response, full strobes.
task automatic wr(input logic[11:0] a,input logic[31:0] d,input logic[1:0] expected,input integer skew=0,input integer stall=0,input logic[3:0] strobe=15);
 @(negedge clk);awaddr=a;wdata=d;wstrb=strobe;awvalid=(skew!=2);wvalid=(skew!=1);
 #1;if((awvalid&&!awready)||(wvalid&&!wready))$fatal(1,"HOST_SU_AXI unexpected AW/W block");
 tick();@(negedge clk);
 if(skew==1)begin awvalid=0;repeat(2)tick();@(negedge clk);wvalid=1;tick();@(negedge clk);end
 if(skew==2)begin wvalid=0;repeat(2)tick();@(negedge clk);awvalid=1;tick();@(negedge clk);end
 awvalid=0;wvalid=0;tick();
 if(!bvalid||bresp!=expected)$fatal(1,"HOST_SU_AXI response addr=%h got=%b want=%b",a,bresp,expected);
 repeat(stall)begin tick();if(!bvalid||bresp!=expected||awready||wready)$fatal(1,"HOST_SU_AXI B stability");end
 @(negedge clk);bready=1;tick();@(negedge clk);bready=0;
endtask
task automatic rd(input logic[11:0] a,input logic[1:0] expected,input integer stall=0);
 reg[31:0] held;
 @(negedge clk);araddr=a;arvalid=1;tick();@(negedge clk);arvalid=0;
 if(!rvalid||rresp!=expected)$fatal(1,"HOST_SU_AXI read response");held=rdata;
 repeat(stall)begin tick();if(!rvalid||rdata!==held||rresp!=expected)$fatal(1,"HOST_SU_AXI R stability");end
 @(negedge clk);rready=1;tick();@(negedge clk);rready=0;
endtask
always @(posedge clk)begin
 #2;cycles=cycles+1;
 if(!rst_n)begin busy_old=0;launch_edge=-1;seen=0;end
 else begin
  if(busy&&!busy_old)begin launch_edge=cycles;seen=0;end
  if(valid)begin
   if(launch_edge<0||cycles!=launch_edge+3+seen||edge_index!=seen||command!==expected_words[seen]||done!=(seen==N-1)||fault)
    $fatal(1,"HOST_SU_AXI exact edge=%0d actual=%0d cycle=%0d launch=%0d",seen,edge_index,cycles,launch_edge);
   seen=seen+1;
  end
  if(done)begin if(seen!=N)$fatal(1,"HOST_SU_AXI premature done");replays=replays+1;end
  busy_old=busy;
 end
end
task automatic execute;
 integer before_replays;
 before_replays=replays;wr('hf44,1,0);
 for(integer i=0;i<N+5;i=i+1)begin tick();if(replays>before_replays)break;end
 if(replays!=before_replays+1)$fatal(1,"HOST_SU_AXI execute timeout");
 tick();if(valid||busy||done||command!='0)$fatal(1,"HOST_SU_AXI tail");
endtask
initial begin
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
 $readmemh({dir,"/config.mem"},config_words);$readmemh({dir,"/expected.mem"},expected_words);
 reset_target();
 wr('hf38,0,2,1,3);wr('hf34,32'h80000000,2,2,3);wr('hf40,0,2);wr('hf44,1,2);wr('hf30,0,2);wr('hf40,N,2,0,0,3);
 rd('hf30,2,3);rd('hf3c,0,3);
 // Empty SRAMs never qualify merely because simulation initializes to zero.
 wr('hf3c,1,0);repeat(3)tick();if(block_ready||!fault)$fatal(1,"HOST_SU_AXI missing row falsely ready");
 reset_target();
 // All eight payload chunks are required; true bank16 overflow reaches error.
 wr('hf34,M,0);for(integer j=0;j<8;j=j+1)wr('hf38,0,(j==7)?2:0);
 if(!fault||block_ready)$fatal(1,"HOST_SU_AXI invalid bank not rejected");
 reset_target();
 for(integer i=0;i<W;i=i+1)begin
  if(config_words[i][263])$fatal(1,"HOST_SU_AXI row padding nonzero");
  wr('hf34,{9'b0,config_words[i][262:256],config_words[i][279:264]},0);
  for(integer j=0;j<8;j=j+1)wr('hf38,config_words[i][j*32+:32],0);
 end
 if(block_ready||fault)$fatal(1,"HOST_SU_AXI install state");
 wr('hf3c,1,0);
 for(integer i=0;i<W+2;i=i+1)begin tick();if(block_ready||fault)break;end
 if(!block_ready||fault)$fatal(1,"HOST_SU_AXI installed image not ready");
 rd('hf3c,0,3);wr('hf40,N,0,1,3);rd('hf40,0,3);
 execute();execute();
 $display("HOST_SU_AXI_PASS edges=%0d writes=%0d macros=%0d replays=%0d",N,W,M,replays);$finish;
end
endmodule
