`timescale 1ns/1ps
module host_su_tb #(parameter integer MUT_READY=0);
localparam integer B=@BITS@,N=@EDGES@,W=@WRITES@,M=@MACROS@,FIRST_DICT=@DICT@;
logic clk=0;always #5 clk=~clk;
logic rst_n=0,cfg_v=0,validate_v=0,launch_v=0;
logic[15:0] cfg_bank=0,length=N;logic[6:0] cfg_row=0;logic[255:0] cfg_data=0;
wire cfg_ready,cfg_accept,block_ready,busy,valid,done,fault;
wire[15:0] edge_index;wire[B-1:0] command;
reg[279:0] config_words[0:W-1];reg[B-1:0] expected_words[0:N-1];
string dir;integer data_mut,addr_mut,phase_mut,mode;
host_su_target #(.LINE_BITS(B),.EDGES(N),.DICT_ENTRIES(@ENTRIES@),.DICT_BANKS(@BANKS@),.MACROS(M),.MUT_READY(MUT_READY)) dut(
 .clk(clk),.rst_n(rst_n),.clk_macro({M{clk}}),.cfg_v(cfg_v),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
 .cfg_ready(cfg_ready),.cfg_accept(cfg_accept),.validate_v(validate_v),.launch_v(launch_v),.length(length),
 .block_ready(block_ready),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
task automatic tick;@(posedge clk);#1;endtask
task automatic reset_target;
 @(negedge clk);rst_n=0;cfg_v=0;validate_v=0;launch_v=0;tick();@(negedge clk);rst_n=1;tick();
 if(block_ready||fault||busy||valid) $fatal(1,"HOST_SU reset state");
endtask
task automatic install(input integer omit);
 for(integer i=0;i<W;i=i+1) begin
  @(negedge clk);
  cfg_bank=config_words[i][279:264];cfg_row=config_words[i][262:256];cfg_data=config_words[i][255:0];
  if(config_words[i][263])$fatal(1,"HOST_SU packed row overflow");
  cfg_v=!((omit==1&&cfg_bank==0&&cfg_row==0)||(omit==2&&cfg_bank==FIRST_DICT&&cfg_row==0));
  if(data_mut&&cfg_bank==FIRST_DICT&&cfg_row==0)cfg_data=cfg_data^256'b1;
  if(addr_mut&&cfg_bank==0&&cfg_row==0)cfg_data=cfg_data^256'b1;
  #1;if(cfg_v&&!cfg_accept)$fatal(1,"HOST_SU unexpected installation refusal");
  tick();if(fault||block_ready)$fatal(1,"HOST_SU install state");
 end
 @(negedge clk);cfg_v=0;
 repeat(2)tick();
endtask
task automatic validate_image;
 @(negedge clk);validate_v=1;tick();@(negedge clk);validate_v=0;
 for(integer i=0;i<W+2;i=i+1)begin
  tick();if(block_ready||fault)return;
 end
 $fatal(1,"HOST_SU validation timeout");
endtask
task automatic execute;
 @(negedge clk);launch_v=1;tick();if(!busy||valid)$fatal(1,"HOST_SU launch edge");
 @(negedge clk);launch_v=0;
 repeat(2)begin tick();if(valid)$fatal(1,"HOST_SU early valid");end
 for(integer e=0;e<N;e=e+1)begin
  tick();if(!valid||edge_index!=e||command!==expected_words[(e+phase_mut)%N]||fault||done!=(e==N-1))
   $fatal(1,"HOST_SU exact mismatch edge=%0d idx=%0d valid=%b done=%b fault=%b",e,edge_index,valid,done,fault);
 end
 tick();if(valid||busy||done||command!='0)$fatal(1,"HOST_SU tail");
endtask
initial begin
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
 data_mut=$test$plusargs("MUT_DATA");addr_mut=$test$plusargs("MUT_ADDR");phase_mut=$test$plusargs("MUT_PHASE");
 $readmemh({dir,"/config.mem"},config_words);$readmemh({dir,"/expected.mem"},expected_words);
 // Both absent physical index and dictionary rows must block launch.
 for(integer missing=1;missing<=2;missing=missing+1)begin
  reset_target();install(missing);validate_image();
  if(block_ready||!fault)$fatal(1,"HOST_SU missing row falsely ready kind=%0d",missing);
 end
 reset_target();@(negedge clk);cfg_v=1;cfg_bank=M;cfg_row=0;cfg_data=0;#1;
 if(cfg_accept)$fatal(1,"HOST_SU out of range accepted");tick();
 if(!fault||block_ready)$fatal(1,"HOST_SU out of range no fault");
 reset_target();@(negedge clk);cfg_v=1;cfg_bank=0;cfg_row=0;cfg_data='1;#1;
 if(cfg_accept)$fatal(1,"HOST_SU dictionary reference accepted");tick();
 if(!fault)$fatal(1,"HOST_SU dictionary reference no fault");
 reset_target();install(0);validate_image();
 if(!block_ready||fault)$fatal(1,"HOST_SU complete image not ready");
 execute();execute();
 // Configuration after validation invalidates readiness until another scan.
 @(negedge clk);cfg_v=1;cfg_bank=config_words[0][279:264];cfg_row=config_words[0][262:256];cfg_data=config_words[0][255:0];
 tick();if(block_ready)$fatal(1,"HOST_SU stale validation");
 @(negedge clk);cfg_v=0;repeat(2)tick();validate_image();if(!block_ready)$fatal(1,"HOST_SU revalidate");
 // Installation while executing must fault; it must not reach native SRAM.
 @(negedge clk);launch_v=1;tick();@(negedge clk);launch_v=0;cfg_v=1;#1;
 if(cfg_accept)$fatal(1,"HOST_SU busy config accepted");tick();if(!fault)$fatal(1,"HOST_SU busy config no fault");
 $display("HOST_SU_PASS edges=%0d writes=%0d macros=%0d replay=1 negatives=5",N,W,M);$finish;
end
endmodule
