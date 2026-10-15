`timescale 1ns/1ps
module tb_dma_calendar_wrap;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg [31:0] cycle=32'hfffffff0;reg mv_v=0;reg [2055:0] rr=0;reg [11:0] wa=0;
wire src,done,fault,quiet;wire [2311:0] wd;
wire [226:0] mv={21'd8,20'd1,16'd1,32'd0,40'h100000,3'd0,2'd0,16'd1,32'd64,40'd0,3'd0,2'd1};
ot_hgi_dma_back_static engine(.clk(clk),.rst_n(rst_n),.cycle(cycle),.mv_v(mv_v),.mv(mv),.issue_at(32'hfffffff8),.drain_at(32'h10),.mv_wb_bank(1'b0),.mv_wb_epoch(16'h7777),
 .mv_src(src),.mv_done(done),.mv_fault(fault),.quiet(quiet),.busy(),.rq(),.rr(rr),.wb_reserve_v(),.wb_reserve_bank(),.wb_fill_bank(),.wb_reserve_epoch(),.wb_fill_epoch(),.wb_reserve_sectors(),.wb_reserve_base(),.wb_fill_start(),.wb_ready(1'b1),.wd(wd),.wa(wa));
integer i,ns=0,nw=0,nd=0;reg [31:0] at;
initial begin
repeat(3)@(negedge clk);rst_n=1;
for(i=0;i<60;i=i+1)begin
at=cycle;mv_v=i==0;rr=0;wa=0;
// Declared VM response boundary stimulus at rq+8, real landing macro inside DUT.
if(cycle==0)rr[256:0]={1'b1,256'h123456789abcdef};
if(cycle==32'h20)wa=1;
@(posedge clk);#1;
if(fault)$fatal(1,"calendar/posted-counter wrap fault at%h",at);
if(src)begin ns=ns+1;if(at!=1)$fatal(1,"wrap source timing");end
if(wd[288])begin nw=nw+1;if(at!=32'h12||wd[287:256]!=32'h8000||wd[255:0]!==256'h123456789abcdef)$fatal(1,"wrap landing SRAM output");end
if(done)begin nd=nd+1;if(at<=32'h20)$fatal(1,"wrap early fence");end
@(negedge clk);cycle=cycle+1;
end
if(ns!=1||nw!=1||nd!=1||!quiet)$fatal(1,"wrap transaction incomplete");
$display("PASS DMA absolute calendar crosses32bit wrap, real landing read/source/posted-fence exact");$finish;
end
endmodule
