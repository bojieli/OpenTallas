`timescale 1ns/1ps
module tb_hbm_host_dma_shared64;
reg clk=0,rst=0;always #5 clk=~clk;
reg[95:0] av=0,awv=0,wv=0,wl=0,rr={96{1'b1}},br={96{1'b1}};
reg[6143:0] aa=0,awa=0,wd=0;reg[767:0] al=0,awl=0,ws={768{1'b1}};
reg[287:0] sz=0;reg arready=0,awready=0,rvalid=0,rlast=0,wready=0,bvalid=0;
wire[95:0] aok,awok,rv,wok,bv;wire ma,maw,mw,mrl,mb,mwl,fault;wire[63:0] addr;wire[7:0] len;
ot_hbm_host_dma_shared64 #(.ENABLE(1),.ND(96)) dut(
 .clk(clk),.rst_n(rst),.arvalid(av),.arready(aok),.araddr(aa),.arlen(al),.arsize(sz),
 .rvalid(rv),.rready(rr),.awvalid(awv),.awready(awok),.awaddr(awa),.awlen(awl),.awsize(sz),
 .wvalid(wv),.wready(wok),.wdata(wd),.wstrb(ws),.wlast(wl),.bvalid(bv),.bready(br),
 .m_arvalid(ma),.m_arready(arready),.m_araddr(addr),.m_arlen(len),
 .m_rvalid(rvalid),.m_rready(mrl),.m_rdata(64'd99),.m_rresp(2'd0),.m_rlast(rlast),
 .m_awvalid(maw),.m_awready(awready),.m_wvalid(mw),.m_wready(wready),.m_wlast(mwl),
 .m_bvalid(bvalid),.m_bready(mb),.m_bresp(2'd0),.fault(fault));
task step;begin @(posedge clk);#1;end endtask
integer i;
initial begin
 repeat(3)step();rst=1;@(negedge clk);av[95]=1;aa[95*64+:64]=64'h123456789;al[95*8+:8]=3;
 for(i=0;i<100&&!ma;i=i+1)step();if(!ma||len!=3||addr!=64'h123456789)$fatal(1,"rank95 fullburst");
 repeat(3)step();if(addr!=64'h123456789||aok!=0)$fatal(1,"AR hold");
 @(negedge clk);arready=1;step();@(negedge clk);av=0;arready=0;
 for(i=0;i<4;i=i+1)begin @(negedge clk);rvalid=1;rlast=i==3;#1;if(!mrl||!rv[95]||rv[94:0]!=0)$fatal(1,"R ownership");step();end
 @(negedge clk);rvalid=0;rlast=0;awv[0]=1;awl[7:0]=1;awready=1;
 for(i=0;i<100&&!maw;i=i+1)step();step();@(negedge clk);awv=0;awready=0;bvalid=1;
 #1;if(mb||bv!=0)$fatal(1,"B before data");bvalid=0;wv[0]=1;wready=1;wl[0]=0;step();
 @(negedge clk);wl[0]=1;#1;if(!mw||!mwl||!wok[0])$fatal(1,"W last retained");step();
 @(negedge clk);wv=0;bvalid=1;#1;if(!mb||!bv[0])$fatal(1,"B owner");step();
 @(negedge clk);bvalid=0;av[1]=1;al[15:8]=3;arready=1;
 for(i=0;i<100&&!ma;i=i+1)step();step();@(negedge clk);av=0;arready=0;rvalid=1;rlast=1;
 #1;if(mrl||rv!=0)$fatal(1,"early RLAST accepted");step();if(!fault)$fatal(1,"early RLAST fault");
 $display("PASS_SHARED64_RANK95_BURST_HOLD_B_AFTER_DATA_FOREIGN_LAST_HOLD");$finish;
end
endmodule
