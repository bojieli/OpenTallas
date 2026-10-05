`timescale 1ns/1fs
// Two sectors only: actual CSR/LOAD/STORE/DMA64 plus lossless high service address.
// Sparse backend keys compare full stack/sector; low32 and other-stack aliases fail.
module tb_hbm_accel_loader_high_addr_crc;
 reg hc=0,mc=0,rst=0;always #0.5 hc=~hc;
 initial begin #0.137;forever #0.4165 mc=~mc;end
 reg av=0,wv=0,arv=0;reg[11:0] aa=0,ra=0;reg[31:0] wd=0;
 wire aready,wready,bv,arready,rv;wire[31:0] rd;wire irq,fault;
 wire ar,mrr,aw,wv64,wl,br;wire[63:0] ara,awa,wdata;wire[7:0] arlen,awlen,strb;wire[2:0] arsize,awsize;
 reg arr=1,awr=1,wr=1,rvalid=0,rlast=0,bvalid=0;reg[63:0] rdata=0;
 wire qv,qr,qwe,sv,sr,swe,rrdy;wire[36:0] qa;wire[255:0] qd,sd;wire[31:0] qs,ss;wire[15:0] qt,st;
 wire[1:0] stack;wire[33:0] sector;wire mapfault;
 reg reply_v=0,reply_we=0;reg[15:0] reply_tag=0;reg[255:0] reply_data=0;
 ot_hbm_accel_loader_host_addr_crc #(.CRC_MATRIX(1),.ENABLE(1),.ND(1),.ADDR_W(37),.STACK_W(2),.STACK_BYTES(64'd22500000000)) dut(
 .clk_host(hc),.rst_host_n(rst),.clk_mem(mc),.rst_mem_n(rst),
 .s_awvalid(av),.s_awready(aready),.s_awaddr(aa),.s_wvalid(wv),.s_wready(wready),.s_wdata(wd),.s_wstrb(4'hf),.s_bvalid(bv),.s_bready(1'b1),
 .s_arvalid(arv),.s_arready(arready),.s_araddr(ra),.s_rvalid(rv),.s_rready(1'b1),.s_rdata(rd),
 .h_awvalid(),.h_awready(1'b1),.h_awaddr(),.h_wvalid(),.h_wready(1'b1),.h_wdata(),.h_wstrb(),.h_bvalid(1'b0),.h_bready(),
 .h_arvalid(),.h_arready(1'b1),.h_araddr(),.h_rvalid(1'b0),.h_rready(),.h_rdata(32'b0),
 .h_dma_arvalid(1'b0),.h_dma_arready(),.h_dma_araddr(64'b0),.h_dma_rvalid(),.h_dma_rready(1'b1),.h_dma_rdata(),.h_dma_rresp(),.h_dma_rlast(),
 .h_dma_awvalid(1'b0),.h_dma_awready(),.h_dma_awaddr(64'b0),.h_dma_wvalid(1'b0),.h_dma_wready(),.h_dma_wdata(64'b0),.h_dma_wstrb(8'b0),.h_dma_bvalid(),.h_dma_bready(1'b1),.h_dma_bresp(),
 .m_arvalid(ar),.m_arready(arr),.m_araddr(ara),.m_arlen(arlen),.m_arsize(arsize),.m_rvalid(rvalid),.m_rready(mrr),.m_rdata(rdata),.m_rresp(2'b0),.m_rlast(rlast),
 .m_awvalid(aw),.m_awready(awr),.m_awaddr(awa),.m_awlen(awlen),.m_awsize(awsize),.m_wvalid(wv64),.m_wready(wr),.m_wdata(wdata),.m_wstrb(strb),.m_wlast(wl),.m_bvalid(bvalid),.m_bready(br),.m_bresp(2'b0),
 .req_v(qv),.req_rdy(qr),.req_we(qwe),.req_addr(qa),.req_wdata(qd),.req_wstrb(qs),.req_tag(qt),
 .rsp_v(reply_v),.rsp_rdy(rrdy),.rsp_we(reply_we),.rsp_tag(reply_tag),.rsp_data(reply_data),.irq(irq),.fault(fault));
 ot_hbm_accel_loader_addr_to_service #(.ENABLE(1),.ADDR_W(37),.STACK_W(2),.SECTOR_W(34),.STACK_BYTES(64'd22500000000)) map(
 .clk(mc),.rst_n(rst),.in_v(qv),.in_rdy(qr),.in_addr(qa),.in_we(qwe),.in_data(qd),.in_strb(qs),.in_tag(qt),
 .out_v(sv),.out_rdy(sr),.out_stack(stack),.out_sector(sector),.out_we(swe),.out_data(sd),.out_strb(ss),.out_tag(st),.fault(mapfault));
 localparam[36:0] TARGET=(37'd3<<35)+(37'd1<<34)+37'h100;
 localparam[63:0] SRC=64'h0000010000000fe0,DST=64'h0000020000000fe0;
 reg[255:0] payload[2],memory[2];reg[63:0] returned[8];
 integer memcy=0,writes=0,reads=0,acks=0,dmar=0,dmaw=0,dmaB=0,hostcy=0;
 assign sr=!reply_v&&!reply_pending&&(memcy%3!=0);
 reg reply_pending=0;integer reply_when=0,ack_debt_cycles=0;
 reg held=0;reg[36:0] heldaddr;reg[15:0] heldtag;
 always @(posedge mc)begin
 memcy<=memcy+1;
 if(reply_v&&rrdy)begin reply_v<=0;acks++;end
 if(reply_pending)begin ack_debt_cycles++;if(memcy>=reply_when)begin reply_v<=1;reply_pending<=0;end end
 if(writes+reads>acks && (dut.g_on.g_die[0].u_load.g_on.done||dut.g_on.g_die[0].u_store.g_on.done))$fatal(1,"done with actual ACK debt");
 if(held&&(!qv||qa!=heldaddr||qt!=heldtag))$fatal(1,"held high request changed");
 held<=qv&&!qr;if(qv&&!qr)begin heldaddr<=qa;heldtag<=qt;end
 if(sv&&sr)begin
 integer idx;
 if(stack!=3||sector!=34'((TARGET&37'h7ffffffff)>>5)&&sector!=34'(((TARGET&37'h7ffffffff)>>5)+1))$fatal(1,"address alias stack=%0d sector=%h raw=%h",stack,sector,qa);
 idx=int'(sector-34'((TARGET&37'h7ffffffff)>>5));
 if(swe)begin
 if(ss!==32'hffffffff)$fatal(1,"LOAD byte mask changed");
 for(integer byteidx=0;byteidx<32;byteidx++)if(ss[byteidx])memory[idx][byteidx*8+:8]<=sd[byteidx*8+:8];
 writes++;end else begin if(ss!==(st[15]?32'b0:32'hffffffff))$fatal(1,"owner-qualified read byte mask changed");reads++;end
 reply_pending<=1;reply_when<=memcy+6;reply_we<=swe;reply_tag<=st;reply_data<=swe?256'b0:memory[idx];
 end
 end
 integer rl=0,ri=0,wleft=0,wi=0;reg ractive=0,wactive=0,bpending=0;integer bwhen=0;
 always @(posedge hc)begin
 if(dmaw>dmaB&&dut.g_on.g_die[0].u_store.g_on.done)$fatal(1,"done before actual DMA B debt drained");
 hostcy<=hostcy+1;arr<=!ractive&&!rvalid;awr<=!wactive&&!bpending&&!bvalid;wr<=hostcy%5!=0;
 if(ar&&arr)begin
 if(arsize!=3||ara<SRC||ara>=SRC+64||((ara&4095)+8*(int'(arlen)+1)>4096))$fatal(1,"DMA64 high read translation/burst");
 dmar++;ractive=1;rl=int'(arlen)+1;ri=int'((ara-SRC)>>3);
 end
 if(rvalid&&mrr)begin rl--;ri++;if(rl==0)ractive=0;end
 if(!rvalid||mrr)begin rvalid<=ractive;if(ractive)begin rdata<=payload[ri/4][(ri%4)*64+:64];rlast<=rl==1;end end
 if(aw&&awr)begin
 if(awsize!=3||awa<DST||awa>=DST+64||((awa&4095)+8*(int'(awlen)+1)>4096))$fatal(1,"DMA64 high write translation/burst");
 dmaw++;wactive=1;wleft=int'(awlen)+1;wi=int'((awa-DST)>>3);
 end
 if(wv64&&wr)begin
 if(!wactive||wl!=(wleft==1)||strb!=8'hff)$fatal(1,"W owner/last/strb");
 returned[wi]=wdata;wi++;wleft--;if(wleft==0)begin wactive=0;bpending=1;bwhen=hostcy+7;end
 end
 if(bvalid&&br)begin bvalid<=0;dmaB++;end
 if(bpending&&hostcy>=bwhen&&!bvalid)begin bvalid<=1;bpending=0;end
 end
 task automatic csrwr(input[11:0] addr,input[31:0] data);
 @(negedge hc);av=1;wv=1;aa=addr;wd=data;@(posedge hc);while(!(aready&&wready))@(posedge hc);
 @(negedge hc);av=0;wv=0;while(!bv)@(posedge hc);@(negedge hc);
 endtask
 task automatic csrrd(input[11:0] addr,output[31:0] data);
 @(negedge hc);arv=1;ra=addr;@(posedge hc);while(!arready)@(posedge hc);@(negedge hc);arv=0;
 while(!rv)@(posedge hc);data=rd;@(negedge hc);
 endtask
 function automatic[31:0] fold(input[31:0] c,input[255:0] word);
 fold=c;for(integer i=0;i<256;i++)fold={fold[30:0],1'b0}^((fold[31]^word[i])?32'h04c11db7:0);
 endfunction
 task automatic command(input[11:0] bar,input[63:0] ha,input[36:0] da,input[31:0] hi,input[31:0] nb,input[31:0] crc,input integer expect_status);
 reg[31:0] status,cg,vg,count,dh;integer traffic;
 csrwr(bar+'h08,ha[31:0]);csrwr(bar+'h0c,ha[63:32]);csrwr(bar+'h10,da[31:0]);csrwr(bar+'h2c,hi);csrwr(bar+'h14,nb);csrwr(bar+'h18,crc);
 csrrd(bar+'h2c,dh);if(dh!=(hi&31))$fatal(1,"highCSR readback");traffic=dmar+dmaw+writes+reads;
 csrwr(bar,bar[6]?1:3);
 csrrd(bar+'h04,status);while(!status[8])csrrd(bar+'h04,status);
 csrrd(bar+'h1c,cg);csrrd(bar+'h20,vg);csrrd(bar+'h24,count);
 if(status[3:0]!=expect_status)$fatal(1,"status %h expect%0d",status,expect_status);
 if(expect_status==0&&(cg!=crc||vg!=crc||count!=nb/32))$fatal(1,"CRC/count");
 if(expect_status!=0&&traffic!=dmar+dmaw+writes+reads)$fatal(1,"invalid descriptor issued traffic");
 $display("HIGHADDR bar=%h byte=%h high=%h bytes=%0d status=%0d crc=%h",bar,da,hi,nb,status[3:0],cg);csrwr(bar+'h04,256);
 endtask
 initial begin
 reg[31:0] crc,seed,expected;reg[36:0] bad;reg[255:0] basis;
 // Exhaust every linear input basis against the untouched sequential oracle.
 for(integer j=0;j<288;j++)begin seed=0;basis=0;if(j<32)seed[j]=1;else basis[j-32]=1;expected=fold(seed,basis);
 if(dut.g_on.g_die[0].u_load.crc_fold(seed,basis)!==expected||dut.g_on.g_die[0].u_store.crc_fold(seed,basis)!==expected)$fatal(1,"literal CRC basis %0d",j);end
 payload[0]=256'hfedcba98765432100123456789abcdef112233445566778899aabbccddeeff00;
 payload[1]=~payload[0];memory[0]=0;memory[1]=0;for(integer i=0;i<8;i++)returned[i]=0;
 crc=fold(fold(32'hffffffff,payload[0]),payload[1]);repeat(8)@(negedge hc);rst=1;repeat(8)@(negedge hc);
 command('h800,SRC,TARGET,32'(TARGET>>32),64,crc,0);
 command('h840,DST,TARGET,32'(TARGET>>32),64,crc,0);
 for(integer i=0;i<8;i++)if(returned[i]!==payload[i/4][(i%4)*64+:64])$fatal(1,"returned mismatch%0d",i);
 if(writes!=2||reads!=4||acks!=6||dmar!=2||dmaw!=2||dmaB!=2||fault||mapfault)$fatal(1,"transaction counts/fault");
 bad=(37'd3<<35)+37'd22500000000;command('h800,SRC,bad,32'(bad>>32),32,crc,3);
 bad=(37'd3<<35)+37'd22499999968;command('h840,DST,bad,32'(bad>>32),64,crc,3);
 command('h800,SRC,TARGET,32'(TARGET>>32)|32'h20,64,crc,3);
 command('h840,64'hffffffffffffffe0,TARGET,32'(TARGET>>32),64,crc,3);
 command('h800,SRC,37'h1fffffffe0,31,64,crc,3);
 $display("CRC_MATRIX basis288 PASS fullLOADmask/all8DMAstrobes/actualACKdebt cycles=%0d",ack_debt_cycles);
 if(ack_debt_cycles==0)$fatal(1,"no actual ACK debt exercised");
 $display("PASS high_address_crc_component stack3 local_bit34 fullDMA64 two-sectors CRC=%h requests=%0d ACK=%0d B=%0d",crc,writes+reads,acks,dmaB);$finish;
 end
endmodule
