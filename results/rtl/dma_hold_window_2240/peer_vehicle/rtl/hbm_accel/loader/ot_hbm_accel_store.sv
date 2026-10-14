`timescale 1ns/1ps
// STORE descriptor: actual MREQ reads -> ordered CDC -> AXI writes -> B drain.
// CSR offsets match the original loader; CTRL[0] starts STORE. ENABLE defaults off.
// No completion until every sector is accepted by W AND every real B arrives.
module ot_hbm_accel_store #(
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
 output wire req_v,input wire req_rdy,output wire req_we,output wire[31:0] req_addr,
 output wire[255:0] req_wdata,output wire[31:0] req_wstrb,output wire[TW-1:0] req_tag,
 input wire rsp_v,output wire rsp_rdy,input wire[TW-1:0] rsp_tag,input wire rsp_we,input wire[255:0] rsp_data
);
 function automatic[31:0] crc_fold(input[31:0] s,input[255:0] w);
 reg fb;integer i;begin crc_fold=s;for(i=0;i<256;i=i+1)begin fb=crc_fold[31]^w[i];crc_fold={crc_fold[30:0],1'b0}^(fb?32'h04c11db7:0);end end
 endfunction
 generate if(!ENABLE)begin:g_off
 assign s_awready=0;assign s_wready=0;assign s_arready=0;
 always @*begin s_bvalid=0;s_rvalid=0;s_rdata=0;m_awvalid=0;m_awaddr=0;m_awlen=0;end
 assign m_awsize=0;assign m_awburst=0;assign m_wvalid=0;assign m_wdata=0;assign m_wstrb=0;assign m_wlast=0;assign m_bready=0;assign irq=0;
 assign req_v=0;assign req_we=0;assign req_addr=0;assign req_wdata=0;assign req_wstrb=0;assign req_tag=0;assign rsp_rdy=0;
 end else begin:g_on
 localparam integer VB=$clog2(VOUT);
 initial if(CDC_AW<2 || VOUT<2 || (VOUT&(VOUT-1)) || VOUT>=(1<<TW) || BURST<1 || BURST>128 || MAXOUT<1 || MAXOUT>255)$fatal(1,"STORE geometry");
 reg[63:0] haddr;reg[31:0] daddr,nbytes,crc_exp,crc_got,vcrc_got,sectors,cycles;
 reg[3:0] status;reg busy,done,cmd_pending,mem_complete,axi_err;
 reg[31:0] nsec,aw_sec,w_sec;reg[63:0] aw_next;reg[8:0] w_left;
 reg[7:0] outstanding;
 wire wr=s_awvalid&&s_wvalid&&!s_bvalid;
 assign s_awready=wr;assign s_wready=wr;assign s_arready=s_arvalid&&!s_rvalid;
 wire start=wr&&s_awaddr[7:0]==0&&s_wdata[0]&&!busy;
 wire cmd_rdy,cv,crdy,dv,drdy,kv,krdy,cplv;
 wire[63:0] cd;wire[255:0] dd,kd;wire[67:0] cpld;
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
 haddr<=0;daddr<=0;nbytes<=0;crc_exp<=0;crc_got<='1;vcrc_got<=0;sectors<=0;cycles<=0;status<=0;busy<=0;done<=0;
 cmd_pending<=0;mem_complete<=0;axi_err<=0;nsec<=0;aw_sec<=0;w_sec<=0;aw_next<=0;w_left<=0;outstanding<=0;
 s_bvalid<=0;s_rvalid<=0;s_rdata<=0;m_awvalid<=0;m_awaddr<=0;m_awlen<=0;
 end else begin
 if(s_bvalid&&s_bready)s_bvalid<=0;
 if(wr)begin s_bvalid<=1;case(s_awaddr[7:0])
 'h04:if(s_wdata[8])done<=0;
 'h08:if(!busy)haddr[31:0]<=s_wdata;
 'h0c:if(!busy)haddr[63:32]<=s_wdata;
 'h10:if(!busy)daddr<=s_wdata;
 'h14:if(!busy)nbytes<=s_wdata;
 'h18:if(!busy)crc_exp<=s_wdata;
 default:;endcase end
 if(s_rvalid&&s_rready)s_rvalid<=0;
 if(s_arvalid&&s_arready)begin s_rvalid<=1;case(s_araddr[7:0])
 'h00:s_rdata<={31'b0,busy};'h04:s_rdata<={23'b0,done,4'b0,status};
 'h08:s_rdata<=haddr[31:0];'h0c:s_rdata<=haddr[63:32];'h10:s_rdata<=daddr;'h14:s_rdata<=nbytes;
 'h18:s_rdata<=crc_exp;'h1c:s_rdata<=crc_got;'h20:s_rdata<=vcrc_got;'h24:s_rdata<=sectors;'h28:s_rdata<=cycles;
 default:s_rdata<=0;endcase end
 if(start)begin
 done<=0;status<=0;crc_got<='1;vcrc_got<=0;sectors<=0;cycles<=0;mem_complete<=0;axi_err<=0;
 if(nbytes==0||nbytes[4:0]!=0||haddr[4:0]!=0||daddr[4:0]!=0||{1'b0,daddr}+{1'b0,nbytes}>33'h100000000||{1'b0,haddr}+{33'b0,nbytes}>65'h10000000000000000)begin done<=1;status<=3;end
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
 ot_gpu_cdc_fifo #(.ENABLE(1),.W(64),.AW(2)) u_cmd(.wclk(clk_host),.wrst_n(rst_host_n),.in_v(cmd_pending),.in_rdy(cmd_rdy),.in_d({nsec,daddr}),.rclk(clk_mem),.rrst_n(rst_mem_n),.out_v(cv),.out_rdy(crdy),.out_d(cd),.ovf_fault(overflow0));
 ot_gpu_cdc_fifo #(.ENABLE(1),.W(256),.AW(CDC_AW)) u_data(.wclk(clk_mem),.wrst_n(rst_mem_n),.in_v(kv),.in_rdy(krdy),.in_d(kd),.rclk(clk_host),.rrst_n(rst_host_n),.out_v(dv),.out_rdy(drdy),.out_d(dd),.ovf_fault(overflow1));
 // Ordered memory data and memory completion are separate held CDC records.
 reg completion_v;reg[67:0] completion_d;wire completion_rdy;
 ot_gpu_cdc_fifo #(.ENABLE(1),.W(68),.AW(2)) u_cpl(.wclk(clk_mem),.wrst_n(rst_mem_n),.in_v(completion_v),.in_rdy(completion_rdy),.in_d(completion_d),.rclk(clk_host),.rrst_n(rst_host_n),.out_v(cplv),.out_rdy(1'b1),.out_d(cpld),.ovf_fault(overflow2));
 reg active,fault;reg[31:0] base,total,issued,retired,mcrc;
 reg[VOUT-1:0] live,valid;reg[TW-1:0] tags[VOUT];reg[255:0] rob[VOUT];
 wire[VB-1:0] slot=issued[VB-1:0],head=retired[VB-1:0],rs=rsp_tag[VB-1:0];
 wire send=req_v&&req_rdy;
 assign req_v=active&&issued!=total&&!live[slot];assign req_we=0;assign req_addr=base+(issued<<5);
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
 if(cv&&crdy)begin active<=1;base<=cd[31:0];total<=cd[63:32];issued<=0;retired<=0;mcrc<='1;live<=0;valid<=0;end
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
