`timescale 1ns/1ps
module tb_dma_back_static_guards;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [31:0] cycle=0;always @(posedge clk)if(!rst_n)cycle<=0;else cycle<=cycle+1;
reg mv_v=0;reg [226:0] mv=0;wire fault;wire [135:0] rq;wire [2311:0] wd;wire reserve;
ot_hgi_dma_back_static engine(.clk(clk),.rst_n(rst_n),.cycle(cycle),.mv_v(mv_v),.mv(mv),.issue_at(32'd20),.drain_at(32'd200),.mv_wb_bank(1'b0),.mv_wb_epoch(16'd1),
 .mv_src(),.mv_done(),.mv_fault(fault),.quiet(),.busy(),.rq(rq),.rr(2056'd0),.wb_reserve_v(reserve),.wb_reserve_bank(),.wb_fill_bank(),.wb_reserve_epoch(),.wb_fill_epoch(),.wb_reserve_sectors(),.wb_reserve_base(),.wb_fill_start(),.wb_ready(1'b1),.wd(wd),.wa(12'd0));
integer c;
function automatic [226:0] command;
command={21'd64,20'd1,16'd1,32'd256,40'h100000,3'd0,2'd0,16'd1,32'd64,40'd0,3'd0,2'd1};
endfunction
initial begin
for(c=0;c<7;c=c+1)begin
rst_n=0;mv_v=0;repeat(3)@(negedge clk);rst_n=1;mv=command();
case(c)
0:begin mv[44:5]=40'd65472;mv[205:186]=2;end // main->mirror crossing
1:begin mv[44:5]=40'd98240;mv[205:186]=2;end // mirror past98304
2:mv[134:98]=37'h800100000; // wrong own-stack
3:mv[134:98]=37'd22499999968; // row crosses actual stack capacity
4:mv[205:186]=129; // exceeds real landing reservation
6:begin mv[226:206]=8;mv[205:186]=2;mv[169:138]=32;end // partial lanes between rows are not dense WB beats
5:mv[169:138]=32'd512; // non-dense destination unsupported by WB block
endcase
if(c==5)mv[205:186]=2;
mv_v=1;@(negedge clk);mv_v=0;repeat(3)@(negedge clk);
if(!fault)$fatal(1,"invalid descriptor guard missing case%0d",c);
repeat(5)begin
if(reserve||rq[16]||rq[33]||rq[50]||rq[67]||rq[84]||rq[101]||rq[118]||rq[135]||wd[288]||wd[577]||wd[866]||wd[1155]||wd[1444]||wd[1733]||wd[2022]||wd[2311])$fatal(1,"invalid descriptor issued work case%0d",c);
@(negedge clk);
end
end
$display("PASS DMA static descriptor guards: main/mirror bounds,ownstack,stackcapacity,landingcapacity,unsupportedstride,partial-multirow all fail closed");$finish;
end
endmodule
