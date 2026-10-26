`timescale 1ns/1ps
// Bench: landing-FIFO model -> ot_hbm_host_packet_static -> REAL ot_hbm_host_static_ingress; endpoint
// face model returns one credit CRD edges after each flit (CRD=0: never -> credit exhaustion test).
// Checks: a full 256-b configuration frame + descriptor reach the ingress broadcast exactly; every
// write/read gets its byte-exact op81/op82 response packet (tid echoed); F30 status read; status packet
// opFF on irq/fault change; dynamic-loader op03 refused with protocol_fault; never more than TXC flits
// outstanding without credit; reserved flit header zero. MUT 1/2/3 must FAIL.
module tb_hbm_host_packet_static;
parameter integer MUT=0;
reg clk=0,rst_n=0; always #1 clk=~clk;
integer errors=0,checks=0;
task chk(input c,input [8*64-1:0] what); begin checks=checks+1; if(!c) begin errors=errors+1; $display("FAIL %0s t=%0t",what,$time); end end endtask
reg rx_valid=0; reg [511:0] rx_packet=0; wire rx_ready;
wire f_send; wire [544:0] f_flit; reg t_cr=0; reg irq=0,fault=0; wire pfault;
wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready; wire [11:0] s_awaddr,s_araddr; wire [31:0] s_wdata,s_rdata; wire [3:0] s_wstrb;
wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid; wire [1:0] s_bresp;
ot_hbm_host_packet_static #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.rx_valid(rx_valid),.rx_packet(rx_packet),.rx_ready(rx_ready),
 .f_send(f_send),.f_flit(f_flit),.t_cr(t_cr),
 .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_bvalid(s_bvalid),.s_bresp(s_bresp),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
 .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.irq(irq),.fault(fault),.protocol_fault(pfault));
wire cfg_v,desc_v,launch_v,ifault; wire [7:0] cfg_target; wire [11:0] cfg_addr,desc_base; wire [255:0] cfg_data; wire [12:0] desc_limit; wire [15:0] desc_loops;
ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<112)) ing(.clk(clk),.rst_n(rst_n),
 .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
 .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.block_ready(1'b0),.program_active(1'b0),.program_fault(1'b0),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
 .desc_loops(desc_loops),.launch_v(launch_v),.fault(ifault));
// ---------------- landing model: queue of packets, out_v held until out_ready, >=1 idle edge between
reg [511:0] q[0:63]; integer qh=0,qt=0;
always @(posedge clk) begin
 if(rx_valid && rx_ready) begin rx_valid<=0; qh<=qh+1; end
 else if(!rx_valid && qh!=qt) begin rx_valid<=1; rx_packet<=q[qh]; end
end
function [511:0] wr(input [15:0] id,input [11:0] a,input [31:0] d); wr={341'd0,1'b0,2'd0,8'h0f,32'd0,d,64'(a),id,8'd1,8'h01}; endfunction
function [511:0] rd(input [15:0] id,input [11:0] a); rd={341'd0,1'b0,2'd0,8'h00,64'd0,64'(a),id,8'd1,8'h02}; endfunction
task push(input [511:0] p); begin q[qt]=p; qt=qt+1; end endtask
// ---------------- face model: credits, flit log
integer CRD=10; integer outstanding=0,maxout=0,nflit=0; reg [544:0] fl[0:255]; integer cr_q[0:4095]; integer cyc=0,crh=0,crt=0;
always @(posedge clk) begin
 cyc<=cyc+1; t_cr<=0;
 if(f_send) begin fl[nflit]=f_flit; nflit=nflit+1; outstanding=outstanding+1; if(outstanding>maxout) maxout=outstanding; if(CRD>0) begin cr_q[crt]=cyc+CRD; crt=crt+1; end end
 if(crh!=crt && cr_q[crh]<=cyc) begin t_cr<=1; crh=crh+1; outstanding=outstanding-1; end
end
// ingress broadcast monitor
reg [255:0] got_data; reg [11:0] got_addr; reg [7:0] got_t; integer ncfg=0,ndesc=0;
always @(posedge clk) begin if(cfg_v) begin ncfg=ncfg+1; got_data=cfg_data; got_addr=cfg_addr; got_t=cfg_target; end if(desc_v) ndesc=ndesc+1; end
integer i,k,n0; reg [255:0] D; reg ok;
initial begin
 D=256'h0123_4567_89ab_cdef_fedc_ba98_7654_3210_dead_beef_cafe_f00d_1111_2222_3333_4444;
 repeat(5) @(posedge clk); rst_n=1; repeat(5) @(posedge clk);
 push(wr(16'h0101,12'hf20,{12'd0,12'd7,8'd112}));
 for(k=0;k<8;k=k+1) push(wr(16'h0200+k,12'hf24,D[k*32+:32]));
 push(wr(16'h0301,12'hf28,{7'd0,13'd9,12'd7})); push(wr(16'h0302,12'hf2c,32'd1));
 push(rd(16'h0401,12'hf30));
 wait(nflit==12); repeat(20) @(posedge clk);
 chk(ncfg==1 && got_data==D && got_addr==12 'd7 && got_t==8'd112,"frame reached ingress broadcast exactly");
 chk(ndesc==1,"descriptor reached ingress");
 ok=1; for(k=0;k<11;k=k+1) if(fl[k][7:0]!=8'h81 || fl[k][169:168]!=0 || fl[k][15:8]!=1 || fl[k][544:512]!=0) ok=0;
 chk(ok,"op81 OKAY responses with zero flit header");
 chk(fl[0][31:16]==16'h0101 && fl[1][31:16]==16'h0200 && fl[8][31:16]==16'h0207 && fl[10][31:16]==16'h0302,"tids echoed in order");
 chk(fl[11][7:0]==8'h82 && fl[11][31:16]==16'h0401 && fl[11][127:102]==26'h0 && fl[11][99:96]==4'h0,"op82 status read");
 // status packet on irq change
 irq=1; repeat(20) @(posedge clk);
 chk(nflit==13 && fl[12][7:0]==8'hff && fl[12][97:96]==2'b01,"status packet on irq");
 chk(!pfault,"no protocol fault yet");
 push({341'd0,1'b0,2'd0,8'h00,64'd0,64'h1000,16'h0444,8'd1,8'h03}); repeat(30) @(posedge clk);
 chk(pfault && nflit==13,"dynamic-loader op03 refused (protocol fault, no response)");
 // bad write (unbound target) -> SLVERR response + protocol_fault
 push(wr(16'h0501,12'hf20,{12'd0,12'd0,8'd9})); wait(nflit==14); repeat(4) @(posedge clk);
 chk(fl[13][7:0]==8'h81 && fl[13][169:168]==2'd2,"SLVERR response");
 // credit exhaustion: stop credits, 40 reads -> at most TXC flits outstanding
 CRD=0; n0=nflit; for(i=0;i<40;i=i+1) push(rd(16'h0600+i,12'hf30));
 repeat(1500) @(posedge clk);
 chk(nflit-n0<=32 && maxout<=32,"no more than 32 flits without credit");
 chk(nflit-n0==32,"exactly the credit window sent");
 if(errors==0) $display("PASS host packet static checks=%0d flits=%0d maxout=%0d",checks,nflit,maxout);
 else $display("FAIL errors=%0d checks=%0d",errors,checks);
 $finish;
end
initial begin #400000; $display("FAIL timeout"); $finish; end
endmodule
