// Additive width-selected STORE successor; DADDR_HI=0x2c, explicit spans.
`timescale 1ns/1ps
// STORE descriptor: actual MREQ reads -> ordered CDC -> AXI writes -> B drain.
// CSR offsets match the original loader; CTRL[0] starts STORE. ENABLE defaults off.
// No completion until every sector is accepted by W AND every real B arrives.
module ot_hbm_accel_store_addr_crc #(
 parameter integer CRC_MATRIX=0, ADDR_W=32, STACK_W=0,
 parameter [63:0] STACK_BYTES=0,
 parameter integer ENABLE=0,BURST=16,MAXOUT=32,VOUT=16,TW=16,CDC_AW=5
)(
 input wire clk_host,rst_host_n,
 input wire s_awvalid,output wire s_awready,input wire[11:0] s_awaddr,
 input wire s_wvalid,output wire s_wready,input wire[31:0] s_wdata,
 output reg s_bvalid,input wire s_bready,
 input wire s_arvalid,output wire s_arready,input wire[11:0] s_araddr,
 output reg s_rvalid,input wire s_rready,output reg[31:0] s_rdata,
 output reg m_awvalid,input wire m_awready,output reg[63:0] m_awaddr,output reg[7:0] m_awlen,
 output wire[2:0] m_awsize,output wire[1:0] m_awburst,
 output wire m_wvalid,input wire m_wready,output wire[255:0] m_wdata,
 output wire[31:0] m_wstrb,output wire m_wlast,
 input wire m_bvalid,output wire m_bready,input wire[1:0] m_bresp,
 output wire irq,input wire clk_mem,rst_mem_n,
 output wire req_v,input wire req_rdy,output wire req_we,output wire[ADDR_W-1:0] req_addr,
 output wire[255:0] req_wdata,output wire[31:0] req_wstrb,output wire[TW-1:0] req_tag,
 input wire rsp_v,output wire rsp_rdy,input wire[TW-1:0] rsp_tag,input wire rsp_we,input wire[255:0] rsp_data
);
 // Literal LSB-first 256-bit CRC32 linear map from mem_compiler/ecc.py.
 // Same state feedback and acceptance edge; no added register or byte reorder.
 function automatic [31:0] crc_fold(input [31:0] s, input [255:0] w);
 reg fb;integer i;
 begin
 if(CRC_MATRIX)begin
 crc_fold[0]=^(s & 32'h9108245d) ^ ^(w & 256'h826880efa40da72d78c17d03f5a36f178bc1851a6378032be771ea80ba241089);
 crc_fold[1]=^(s & 32'hb3186ce7) ^ ^(w & 256'hc35cc098760b74bbc4a1c3820f72d89c4e21479752c402be14c91fc0e73618cd);
 crc_fold[2]=^(s & 32'hf738fd93) ^ ^(w & 256'he3c6e0a39f081d709a919cc2f21a0359acd126d1ca1a0274ed156560c9bf1cef);
 crc_fold[3]=^(s & 32'hee71fb26) ^ ^(w & 256'h71e37051cf840eb84d48ce61790d01acd6689368e50d013a768ab2b064df8e77);
 crc_fold[4]=^(s & 32'h4debd211) ^ ^(w & 256'hba9938c743cfa0715e651a334925efc1e0f5ccae11fe83b6dc34b3d8884bd7b2);
 crc_fold[5]=^(s & 32'h0adf807f) ^ ^(w & 256'hdf241c8c05ea7715d7f3f01a513198f77bbb634d6b8742f0896bb36cfe01fb50);
 crc_fold[6]=^(s & 32'h15bf00fe) ^ ^(w & 256'h6f920e4602f53b8aebf9f80d2898cc7bbdddb1a6b5c3a17844b5d9b67f00fda8);
 crc_fold[7]=^(s & 32'hba7625a1) ^ ^(w & 256'hb5a187cca5773ae80d3d810561ef092a552f5dc93999d397c52b065b85a46e5d);
 crc_fold[8]=^(s & 32'he5e46f1e) ^ ^(w & 256'hd8b84309f6b63a597e5fbd814554eb82a1562bfeffb4eae005e469ad78f627a7);
 crc_fold[9]=^(s & 32'hcbc8de3d) ^ ^(w & 256'h6c5c2184fb5b1d2cbf2fdec0a2aa75c150ab15ff7fda757002f234d6bc7b13d3);
 crc_fold[10]=^(s & 32'h06999827) ^ ^(w & 256'hb446902dd9a029bb27569263a4f655f723940fe5dc953993e608f0ebe4199960);
 crc_fold[11]=^(s & 32'h9c3b1412) ^ ^(w & 256'hd84bc8f948ddb3f0eb6a343227d845ec1a0b82e88d329fe2147592f54828dc39);
 crc_fold[12]=^(s & 32'ha97e0c78) ^ ^(w & 256'hee4d649300637ed50d74671ae64f4de186c4446e25e14cdaed4b23fa1e307e95);
 crc_fold[13]=^(s & 32'h52fc18f0) ^ ^(w & 256'h7726b2498031bf6a86ba338d7327a6f0c362223712f0a66d76a591fd0f183f4a);
 crc_fold[14]=^(s & 32'ha5f831e1) ^ ^(w & 256'h3b935924c018dfb5435d19c6b993d37861b1111b89785336bb52c8fe878c1fa5);
 crc_fold[15]=^(s & 32'h4bf063c2) ^ ^(w & 256'h1dc9ac92600c6fdaa1ae8ce35cc9e9bc30d8888dc4bc299b5da9647f43c60fd2);
 crc_fold[16]=^(s & 32'h06e8e3d8) ^ ^(w & 256'h8c8c56a6940b90c028163b725bc79bc993adc15c812617e649a558bf1bc71760);
 crc_fold[17]=^(s & 32'h0dd1c7b1) ^ ^(w & 256'h46462b534a05c860140b1db92de3cde4c9d6e0ae40930bf324d2ac5f8de38bb0);
 crc_fold[18]=^(s & 32'h1ba38f63) ^ ^(w & 256'h232315a9a502e4300a058edc96f1e6f264eb7057204985f99269562fc6f1c5d8);
 crc_fold[19]=^(s & 32'h37471ec7) ^ ^(w & 256'h11918ad4d28172180502c76e4b78f3793275b82b9024c2fcc934ab17e378e2ec);
 crc_fold[20]=^(s & 32'h6e8e3d8f) ^ ^(w & 256'h08c8c56a6940b90c028163b725bc79bc993adc15c812617e649a558bf1bc7176);
 crc_fold[21]=^(s & 32'hdd1c7b1f) ^ ^(w & 256'h046462b534a05c860140b1db92de3cde4c9d6e0ae40930bf324d2ac5f8de38bb);
 crc_fold[22]=^(s & 32'h2b30d262) ^ ^(w & 256'h805ab1b53e5d896e786125ee3ccc7178ad8f321f117c9b747e577fe2464b0cd4);
 crc_fold[23]=^(s & 32'hc7698099) ^ ^(w & 256'hc245d8353b23639a44f1eff4ebc557abdd061c15ebc64e91d85a5571990196e3);
 crc_fold[24]=^(s & 32'h8ed30133) ^ ^(w & 256'h6122ec1a9d91b1cd2278f7fa75e2abd5ee830e0af5e32748ec2d2ab8cc80cb71);
 crc_fold[25]=^(s & 32'h1da60266) ^ ^(w & 256'h3091760d4ec8d8e6913c7bfd3af155eaf74187057af193a47616955c664065b8);
 crc_fold[26]=^(s & 32'haa442091) ^ ^(w & 256'h9a203be90369cb5e305f40fd68dbc5e2f0614698de00caf9dc7aa02e89042255);
 crc_fold[27]=^(s & 32'h54884122) ^ ^(w & 256'h4d101df481b4e5af182fa07eb46de2f17830a34c6f00657cee3d50174482112a);
 crc_fold[28]=^(s & 32'ha9108245) ^ ^(w & 256'h26880efa40da72d78c17d03f5a36f178bc1851a6378032be771ea80ba2410895);
 crc_fold[29]=^(s & 32'h5221048b) ^ ^(w & 256'h1344077d206d396bc60be81fad1b78bc5e0c28d31bc0195f3b8f5405d120844a);
 crc_fold[30]=^(s & 32'ha4420917) ^ ^(w & 256'h09a203be90369cb5e305f40fd68dbc5e2f0614698de00caf9dc7aa02e8904225);
 crc_fold[31]=^(s & 32'h4884122e) ^ ^(w & 256'h04d101df481b4e5af182fa07eb46de2f17830a34c6f00657cee3d50174482112);
 end else begin
 crc_fold=s;for(i=0;i<256;i=i+1)begin fb=crc_fold[31]^w[i];crc_fold={crc_fold[30:0],1'b0}^(fb?32'h04c11db7:0);end 
 end
 end
 endfunction
 generate if(!ENABLE)begin:g_off
 assign s_awready=0;assign s_wready=0;assign s_arready=0;
 always @*begin s_bvalid=0;s_rvalid=0;s_rdata=0;m_awvalid=0;m_awaddr=0;m_awlen=0;end
 assign m_awsize=0;assign m_awburst=0;assign m_wvalid=0;assign m_wdata=0;assign m_wstrb=0;assign m_wlast=0;assign m_bready=0;assign irq=0;
 assign req_v=0;assign req_we=0;assign req_addr=0;assign req_wdata=0;assign req_wstrb=0;assign req_tag=0;assign rsp_rdy=0;
 end else begin:g_on
 localparam integer VB=$clog2(VOUT);
 initial if(CDC_AW<2 || VOUT<2 || (VOUT&(VOUT-1)) || VOUT>=(1<<TW) || BURST<1 || BURST>128 || MAXOUT<1 || MAXOUT>255)$fatal(1,"STORE geometry");
 reg[63:0] haddr;reg[ADDR_W-1:0] daddr;reg[31:0] nbytes,crc_exp,crc_got,vcrc_got,sectors,cycles;
 reg[3:0] status;reg busy,done,cmd_pending,mem_complete,axi_err;
 reg[31:0] nsec,aw_sec,w_sec;reg[63:0] aw_next;reg[8:0] w_left;
 reg[7:0] outstanding;

        localparam integer LOCAL_W=ADDR_W-STACK_W;
        localparam integer HI_W=ADDR_W-32;
        initial if(ADDR_W<32||ADDR_W>64||STACK_W<0||STACK_W>2||LOCAL_W<5||STACK_BYTES>(65'h1<<LOCAL_W)) $fatal(1,"loader address geometry");
        reg daddr_invalid;
        wire [ADDR_W:0] d_end={1'b0,daddr}+(ADDR_W+1)'(nbytes);
        wire [ADDR_W:0] local_end={1'b0,(daddr & ADDR_W'((65'h1<<LOCAL_W)-1))}+(ADDR_W+1)'(nbytes);
        wire [64:0] host_end={1'b0,haddr}+65'(nbytes);
        wire desc_bad=daddr_invalid || d_end>(65'h1<<ADDR_W) || local_end>(65'h1<<LOCAL_W) || (STACK_BYTES!=0&&local_end>STACK_BYTES) || host_end>65'h10000000000000000;

 wire wr=s_awvalid&&s_wvalid&&!s_bvalid;
 assign s_awready=wr;assign s_wready=wr;assign s_arready=s_arvalid&&!s_rvalid;
 wire start=wr&&s_awaddr[7:0]==0&&s_wdata[0]&&!busy;
 wire cmd_rdy,cv,crdy,dv,drdy,kv,krdy,cplv;
 wire[ADDR_W+31:0] cd;wire[255:0] dd,kd;wire[67:0] cpld;
 wire overflow0,overflow1,overflow2;
 wire[31:0] remaining=nsec-aw_sec,to4k=128-{25'b0,aw_next[11:5]};
 wire[31:0] len0=remaining<BURST?remaining:BURST;
 wire[31:0] len=len0<to4k?len0:to4k;
 assign m_awsize=5;assign m_awburst=1;
 assign m_wvalid=busy&&w_left!=0&&dv;
 assign m_wdata=dd;assign m_wstrb='1;assign m_wlast=w_left==1;
 wire aw=m_awvalid&&m_awready,w=m_wvalid&&m_wready,b=m_bvalid&&m_bready;
 assign drdy=w;assign m_bready=busy&&outstanding!=0;
 wire data_ovf=overflow0||overflow1||overflow2;
 always @(posedge clk_host or negedge rst_host_n)if(!rst_host_n)begin
 haddr<=0;daddr<=0;daddr_invalid<=0;nbytes<=0;crc_exp<=0;crc_got<='1;vcrc_got<=0;sectors<=0;cycles<=0;status<=0;busy<=0;done<=0;
 cmd_pending<=0;mem_complete<=0;axi_err<=0;nsec<=0;aw_sec<=0;w_sec<=0;aw_next<=0;w_left<=0;outstanding<=0;
 s_bvalid<=0;s_rvalid<=0;s_rdata<=0;m_awvalid<=0;m_awaddr<=0;m_awlen<=0;
 end else begin
 if(s_bvalid&&s_bready)s_bvalid<=0;
 if(wr)begin s_bvalid<=1;case(s_awaddr[7:0])
 'h04:if(s_wdata[8])done<=0;
 'h08:if(!busy)haddr[31:0]<=s_wdata;
 'h0c:if(!busy)haddr[63:32]<=s_wdata;
 'h10:if(!busy)daddr<=(daddr & ~ADDR_W'(32'hffffffff)) | ADDR_W'(s_wdata);
 'h2c:if(!busy)begin daddr<=ADDR_W'({s_wdata,32'b0}|(64'(daddr)&64'hffffffff));daddr_invalid<=|(s_wdata>>HI_W);end
 'h14:if(!busy)nbytes<=s_wdata;
 'h18:if(!busy)crc_exp<=s_wdata;
 default:;endcase end
 if(s_rvalid&&s_rready)s_rvalid<=0;
 if(s_arvalid&&s_arready)begin s_rvalid<=1;case(s_araddr[7:0])
 'h00:s_rdata<={31'b0,busy};'h04:s_rdata<={23'b0,done,4'b0,status};
 'h08:s_rdata<=haddr[31:0];'h0c:s_rdata<=haddr[63:32];'h10:s_rdata<=32'(daddr);'h2c:s_rdata<=32'(64'(daddr)>>32);'h14:s_rdata<=nbytes;
 'h18:s_rdata<=crc_exp;'h1c:s_rdata<=crc_got;'h20:s_rdata<=vcrc_got;'h24:s_rdata<=sectors;'h28:s_rdata<=cycles;
 default:s_rdata<=0;endcase end
 if(start)begin
 done<=0;status<=0;crc_got<='1;vcrc_got<=0;sectors<=0;cycles<=0;mem_complete<=0;axi_err<=0;
 if(desc_bad||nbytes==0||nbytes[4:0]!=0||haddr[4:0]!=0||daddr[4:0]!=0)begin done<=1;status<=3;end
 else begin busy<=1;cmd_pending<=1;nsec<=nbytes>>5;aw_sec<=0;w_sec<=0;aw_next<=haddr;outstanding<=0;end
 end
 if(cmd_pending&&cmd_rdy)cmd_pending<=0;
 if(busy)cycles<=cycles+1;
 if(busy&&!m_awvalid&&w_left==0&&aw_sec!=nsec&&outstanding<MAXOUT)begin m_awvalid<=1;m_awaddr<=aw_next;m_awlen<=len[7:0]-1'b1;end
 if(aw)begin m_awvalid<=0;w_left<={1'b0,m_awlen}+1'b1;aw_sec<=aw_sec+{24'b0,m_awlen}+1;aw_next<=aw_next+(({56'b0,m_awlen}+1)<<5);end
 if(w)begin w_left<=w_left-1'b1;w_sec<=w_sec+1'b1;crc_got<=crc_fold(crc_got,dd);end
 if(aw||b)outstanding<=outstanding+aw-b;
 if(b&&m_bresp!=0)axi_err<=1;
 if(busy&&cplv)begin mem_complete<=1;vcrc_got<=cpld[31:0];sectors<=cpld[63:32];if(cpld[67:64]!=0)status<=5;end
 if(busy&&mem_complete&&w_sec==nsec&&aw_sec==nsec&&outstanding==0&&!m_awvalid&&w_left==0)begin
 busy<=0;done<=1;
 if(axi_err)status<=4;else if(status!=0||overflow0)status<=5;
 else if(crc_got!=crc_exp)status<=1;else if(vcrc_got!=crc_exp)status<=2;else status<=0;
 end
 end
 assign irq=done;
 ot_gpu_cdc_fifo #(.ENABLE(1),.W(ADDR_W+32),.AW(2)) u_cmd(.wclk(clk_host),.wrst_n(rst_host_n),.in_v(cmd_pending),.in_rdy(cmd_rdy),.in_d({nsec,daddr}),.rclk(clk_mem),.rrst_n(rst_mem_n),.out_v(cv),.out_rdy(crdy),.out_d(cd),.ovf_fault(overflow0));
 ot_gpu_cdc_fifo #(.ENABLE(1),.W(256),.AW(CDC_AW)) u_data(.wclk(clk_mem),.wrst_n(rst_mem_n),.in_v(kv),.in_rdy(krdy),.in_d(kd),.rclk(clk_host),.rrst_n(rst_host_n),.out_v(dv),.out_rdy(drdy),.out_d(dd),.ovf_fault(overflow1));
 // Ordered memory data and memory completion are separate held CDC records.
 reg completion_v;reg[67:0] completion_d;wire completion_rdy;
 ot_gpu_cdc_fifo #(.ENABLE(1),.W(68),.AW(2)) u_cpl(.wclk(clk_mem),.wrst_n(rst_mem_n),.in_v(completion_v),.in_rdy(completion_rdy),.in_d(completion_d),.rclk(clk_host),.rrst_n(rst_host_n),.out_v(cplv),.out_rdy(1'b1),.out_d(cpld),.ovf_fault(overflow2));
 reg active,fault;reg[ADDR_W-1:0] base;reg[31:0] total,issued,retired,mcrc;
 reg[VOUT-1:0] live,valid;reg[TW-1:0] tags[VOUT];reg[255:0] rob[VOUT];
 wire[VB-1:0] slot=issued[VB-1:0],head=retired[VB-1:0],rs=rsp_tag[VB-1:0];
 wire send=req_v&&req_rdy;
 assign req_v=active&&issued!=total&&!live[slot];assign req_we=0;assign req_addr=base+(ADDR_W'(issued)<<5);
 assign req_wdata=0;assign req_wstrb=0;assign req_tag=TW'(issued);
 assign rsp_rdy=1;
 assign kv=active&&valid[head];
 // kdata is a sector; no completion/ready is inferred from a timer.
 wire[255:0] ordered_data=rob[head];
 assign kd=ordered_data;
 wire fold=kv&&krdy;
 assign crdy=!active&&!completion_v&&!fault;
 always @(posedge clk_mem or negedge rst_mem_n)if(!rst_mem_n)begin
 active<=0;fault<=0;base<=0;total<=0;issued<=0;retired<=0;mcrc<='1;live<=0;valid<=0;completion_v<=0;completion_d<=0;
 end else begin
 if(completion_v&&completion_rdy)completion_v<=0;
 if(cv&&crdy)begin active<=1;base<=cd[ADDR_W-1:0];total<=cd[ADDR_W+:32];issued<=0;retired<=0;mcrc<='1;live<=0;valid<=0;end
 if(send)begin issued<=issued+1'b1;tags[slot]<=req_tag;live[slot]<=1;end
 if(rsp_v&&rsp_rdy)begin
 if(!active||rsp_we||!live[rs]||valid[rs]||tags[rs]!=rsp_tag)fault<=1;
 else begin rob[rs]<=rsp_data;valid[rs]<=1;end
 end
 if(fold)begin mcrc<=crc_fold(mcrc,ordered_data);retired<=retired+1'b1;valid[head]<=0;live[head]<=0;end
 if(active&&retired==total)begin active<=0;completion_v<=1;completion_d<={(fault||overflow1||overflow2)?4'd5:4'd0,retired,mcrc};end
 end
 end endgenerate
endmodule
