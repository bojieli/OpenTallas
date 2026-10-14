`timescale 1ns/1ps
module tb_loader_native_endpoint;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg req_v=0,req_we=0,rsp_rdy=0,translation_valid=1;
 reg [31:0]req_addr=0,req_wstrb='1;reg[255:0]req_wdata=0;reg[15:0]req_tag=0;
 reg[4:0]translated_pc=0;reg[29:0]translated_addr=0;
 wire req_rdy,rsp_v,rsp_we,wr_v,rd_v,busy,fault,rd_rsp_rdy;
 wire[15:0]rsp_tag,rd_tag;wire[255:0]rsp_data;wire[290:0]wr_packet;
 wire[4:0]rd_pc;wire[29:0]rd_addr;
 reg wr_rdy=0,wr_ack=0,rd_rdy=0,rd_rsp_v=0,service_fault=0;
 reg[4:0]rd_rsp_pc=0;reg[15:0]rd_rsp_tag=0;reg[3:0]rd_rsp_beat=0;reg[255:0]rd_rsp_data=0;
 ot_hbm_loader_native_endpoint #(.ENABLE(1)) dut(.*);
 task tick;begin @(posedge clk);#1;end endtask
 task reset;begin @(negedge clk);rst_n=0;req_v=0;wr_ack=0;rd_rsp_v=0;service_fault=0;tick;@(negedge clk);rst_n=1;tick;end endtask
 integer i,j,mode;reg[255:0]expected;reg[290:0]saved;
 initial begin
 mode=0;if(!$value$plusargs("mode=%d",mode))mode=0;reset;
 if(mode!=0)begin
 @(negedge clk);
 case(mode)
 1:begin req_v=1;req_addr=1;end
 2:begin req_v=1;req_we=1;req_wstrb=1;end
 3:wr_ack=1;
 4:rd_rsp_v=1;
 5:begin req_v=1;translation_valid=0;end
 endcase
 tick;if(!fault||rsp_v||wr_v||rd_v)$fatal(1,"negative not rejected");
 $display("PASS negative mode=%0d",mode);$finish;
 end
 for(i=0;i<64;i=i+1)begin
 @(negedge clk);req_v=1;req_we=i%2;req_addr=i*32;translated_pc=i%32;translated_addr=i*7;
 req_tag=16'h8000+i;expected={8{32'h12345678+i}};req_wdata=expected;
 tick;if(!busy)$fatal(1,"not accepted");@(negedge clk);req_v=0;
 if(req_we)begin
 saved=wr_packet;
 for(j=0;j<(i%5)+1;j=j+1)begin tick;if(!wr_v||wr_packet!==saved||rsp_v)$fatal(1,"write stall");end
 if(saved!=={expected,translated_addr,translated_pc})$fatal(1,"write map");
 @(negedge clk);wr_rdy=1;tick;@(negedge clk);wr_rdy=0;
 for(j=0;j<4;j=j+1)begin tick;if(rsp_v)$fatal(1,"accept credited as completion");end
 @(negedge clk);wr_ack=1;tick;@(negedge clk);wr_ack=0;
 end else begin
 for(j=0;j<(i%5)+1;j=j+1)begin tick;if(!rd_v||rd_pc!==translated_pc||rd_addr!==translated_addr||rd_tag!==req_tag)$fatal(1,"read stall");end
 @(negedge clk);rd_rdy=1;tick;@(negedge clk);rd_rdy=0;
 for(j=0;j<4;j=j+1)begin tick;if(rsp_v)$fatal(1,"early read");end
 @(negedge clk);rd_rsp_v=1;rd_rsp_pc=translated_pc;rd_rsp_tag=req_tag;rd_rsp_data=expected;
 tick;@(negedge clk);rd_rsp_v=0;
 end
 for(j=0;j<3;j=j+1)begin
 tick;if(!rsp_v||rsp_tag!==req_tag||rsp_we!==req_we||rsp_data!==(req_we?256'b0:expected)||req_rdy)$fatal(1,"held reply");
 end
 @(negedge clk);rsp_rdy=1;tick;@(negedge clk);rsp_rdy=0;
 if(fault||busy)$fatal(1,"retirement");
 end
 // A malformed read reply must not create loader success.
 @(negedge clk);req_v=1;req_we=0;tick;@(negedge clk);req_v=0;rd_rdy=1;tick;
 @(negedge clk);rd_rdy=0;rd_rsp_v=1;rd_rsp_tag=req_tag^1;tick;
 if(!fault||rsp_v||rd_rsp_rdy)$fatal(1,"tag mismatch not fenced");
 $display("PASS 64 sectors stalls visibility identity held replies mismatch");$finish;
 end
endmodule
