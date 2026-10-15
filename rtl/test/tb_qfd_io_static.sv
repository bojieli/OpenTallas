`timescale 1ns/1ps
module tb_qfd_io_static;
 parameter MUT=0;
 reg rst_n=0;
 wire [11:0] done,failed;
wire up_wck,up_rck,up_w_slot,up_r_slot,up_w_version,up_r_version,up_i_valid,up_o_valid,up_w_fault,up_r_fault;
wire [5:0] up_w_addr,up_r_addr;
wire [545:0] up_i_data,up_o_data;
 io_static_stream #(.W(546),.ID(1),.MUT(0==3?MUT:0)) c_up (.rst_n(rst_n), .done(done[0]), .failed(failed[0]), .wck(up_wck), .rck(up_rck), .w_slot(up_w_slot), .r_slot(up_r_slot), .w_version(up_w_version), .r_version(up_r_version), .i_valid(up_i_valid), .o_valid(up_o_valid), .w_fault(up_w_fault), .r_fault(up_r_fault), .w_addr(up_w_addr), .r_addr(up_r_addr), .i_data(up_i_data), .o_data(up_o_data));
wire dp_wck,dp_rck,dp_w_slot,dp_r_slot,dp_w_version,dp_r_version,dp_i_valid,dp_o_valid,dp_w_fault,dp_r_fault;
wire [5:0] dp_w_addr,dp_r_addr;
wire [545:0] dp_i_data,dp_o_data;
 io_static_stream #(.W(546),.ID(2),.MUT(1==3?MUT:0)) c_dp (.rst_n(rst_n), .done(done[1]), .failed(failed[1]), .wck(dp_wck), .rck(dp_rck), .w_slot(dp_w_slot), .r_slot(dp_r_slot), .w_version(dp_w_version), .r_version(dp_r_version), .i_valid(dp_i_valid), .o_valid(dp_o_valid), .w_fault(dp_w_fault), .r_fault(dp_r_fault), .w_addr(dp_w_addr), .r_addr(dp_r_addr), .i_data(dp_i_data), .o_data(dp_o_data));
wire ur_wck,ur_rck,ur_w_slot,ur_r_slot,ur_w_version,ur_r_version,ur_i_valid,ur_o_valid,ur_w_fault,ur_r_fault;
wire [5:0] ur_w_addr,ur_r_addr;
wire [513:0] ur_i_data,ur_o_data;
 io_static_stream #(.W(514),.ID(3),.MUT(2==3?MUT:0)) c_ur (.rst_n(rst_n), .done(done[2]), .failed(failed[2]), .wck(ur_wck), .rck(ur_rck), .w_slot(ur_w_slot), .r_slot(ur_r_slot), .w_version(ur_w_version), .r_version(ur_r_version), .i_valid(ur_i_valid), .o_valid(ur_o_valid), .w_fault(ur_w_fault), .r_fault(ur_r_fault), .w_addr(ur_w_addr), .r_addr(ur_r_addr), .i_data(ur_i_data), .o_data(ur_o_data));
wire dr_wck,dr_rck,dr_w_slot,dr_r_slot,dr_w_version,dr_r_version,dr_i_valid,dr_o_valid,dr_w_fault,dr_r_fault;
wire [5:0] dr_w_addr,dr_r_addr;
wire [513:0] dr_i_data,dr_o_data;
 io_static_stream #(.W(514),.ID(4),.MUT(3==3?MUT:0)) c_dr (.rst_n(rst_n), .done(done[3]), .failed(failed[3]), .wck(dr_wck), .rck(dr_rck), .w_slot(dr_w_slot), .r_slot(dr_r_slot), .w_version(dr_w_version), .r_version(dr_r_version), .i_valid(dr_i_valid), .o_valid(dr_o_valid), .w_fault(dr_w_fault), .r_fault(dr_r_fault), .w_addr(dr_w_addr), .r_addr(dr_r_addr), .i_data(dr_i_data), .o_data(dr_o_data));
wire sx0_wck,sx0_rck,sx0_w_slot,sx0_r_slot,sx0_w_version,sx0_r_version,sx0_i_valid,sx0_o_valid,sx0_w_fault,sx0_r_fault;
wire [5:0] sx0_w_addr,sx0_r_addr;
wire [545:0] sx0_i_data,sx0_o_data;
 io_static_stream #(.W(546),.ID(5),.MUT(4==3?MUT:0)) c_sx0 (.rst_n(rst_n), .done(done[4]), .failed(failed[4]), .wck(sx0_wck), .rck(sx0_rck), .w_slot(sx0_w_slot), .r_slot(sx0_r_slot), .w_version(sx0_w_version), .r_version(sx0_r_version), .i_valid(sx0_i_valid), .o_valid(sx0_o_valid), .w_fault(sx0_w_fault), .r_fault(sx0_r_fault), .w_addr(sx0_w_addr), .r_addr(sx0_r_addr), .i_data(sx0_i_data), .o_data(sx0_o_data));
wire sx1_wck,sx1_rck,sx1_w_slot,sx1_r_slot,sx1_w_version,sx1_r_version,sx1_i_valid,sx1_o_valid,sx1_w_fault,sx1_r_fault;
wire [5:0] sx1_w_addr,sx1_r_addr;
wire [545:0] sx1_i_data,sx1_o_data;
 io_static_stream #(.W(546),.ID(6),.MUT(5==3?MUT:0)) c_sx1 (.rst_n(rst_n), .done(done[5]), .failed(failed[5]), .wck(sx1_wck), .rck(sx1_rck), .w_slot(sx1_w_slot), .r_slot(sx1_r_slot), .w_version(sx1_w_version), .r_version(sx1_r_version), .i_valid(sx1_i_valid), .o_valid(sx1_o_valid), .w_fault(sx1_w_fault), .r_fault(sx1_r_fault), .w_addr(sx1_w_addr), .r_addr(sx1_r_addr), .i_data(sx1_i_data), .o_data(sx1_o_data));
wire sx2_wck,sx2_rck,sx2_w_slot,sx2_r_slot,sx2_w_version,sx2_r_version,sx2_i_valid,sx2_o_valid,sx2_w_fault,sx2_r_fault;
wire [5:0] sx2_w_addr,sx2_r_addr;
wire [545:0] sx2_i_data,sx2_o_data;
 io_static_stream #(.W(546),.ID(7),.MUT(6==3?MUT:0)) c_sx2 (.rst_n(rst_n), .done(done[6]), .failed(failed[6]), .wck(sx2_wck), .rck(sx2_rck), .w_slot(sx2_w_slot), .r_slot(sx2_r_slot), .w_version(sx2_w_version), .r_version(sx2_r_version), .i_valid(sx2_i_valid), .o_valid(sx2_o_valid), .w_fault(sx2_w_fault), .r_fault(sx2_r_fault), .w_addr(sx2_w_addr), .r_addr(sx2_r_addr), .i_data(sx2_i_data), .o_data(sx2_o_data));
wire sr0_wck,sr0_rck,sr0_w_slot,sr0_r_slot,sr0_w_version,sr0_r_version,sr0_i_valid,sr0_o_valid,sr0_w_fault,sr0_r_fault;
wire [5:0] sr0_w_addr,sr0_r_addr;
wire [545:0] sr0_i_data,sr0_o_data;
 io_static_stream #(.W(546),.ID(8),.MUT(7==3?MUT:0)) c_sr0 (.rst_n(rst_n), .done(done[7]), .failed(failed[7]), .wck(sr0_wck), .rck(sr0_rck), .w_slot(sr0_w_slot), .r_slot(sr0_r_slot), .w_version(sr0_w_version), .r_version(sr0_r_version), .i_valid(sr0_i_valid), .o_valid(sr0_o_valid), .w_fault(sr0_w_fault), .r_fault(sr0_r_fault), .w_addr(sr0_w_addr), .r_addr(sr0_r_addr), .i_data(sr0_i_data), .o_data(sr0_o_data));
wire sr1_wck,sr1_rck,sr1_w_slot,sr1_r_slot,sr1_w_version,sr1_r_version,sr1_i_valid,sr1_o_valid,sr1_w_fault,sr1_r_fault;
wire [5:0] sr1_w_addr,sr1_r_addr;
wire [545:0] sr1_i_data,sr1_o_data;
 io_static_stream #(.W(546),.ID(9),.MUT(8==3?MUT:0)) c_sr1 (.rst_n(rst_n), .done(done[8]), .failed(failed[8]), .wck(sr1_wck), .rck(sr1_rck), .w_slot(sr1_w_slot), .r_slot(sr1_r_slot), .w_version(sr1_w_version), .r_version(sr1_r_version), .i_valid(sr1_i_valid), .o_valid(sr1_o_valid), .w_fault(sr1_w_fault), .r_fault(sr1_r_fault), .w_addr(sr1_w_addr), .r_addr(sr1_r_addr), .i_data(sr1_i_data), .o_data(sr1_o_data));
wire sr2_wck,sr2_rck,sr2_w_slot,sr2_r_slot,sr2_w_version,sr2_r_version,sr2_i_valid,sr2_o_valid,sr2_w_fault,sr2_r_fault;
wire [5:0] sr2_w_addr,sr2_r_addr;
wire [545:0] sr2_i_data,sr2_o_data;
 io_static_stream #(.W(546),.ID(10),.MUT(9==3?MUT:0)) c_sr2 (.rst_n(rst_n), .done(done[9]), .failed(failed[9]), .wck(sr2_wck), .rck(sr2_rck), .w_slot(sr2_w_slot), .r_slot(sr2_r_slot), .w_version(sr2_w_version), .r_version(sr2_r_version), .i_valid(sr2_i_valid), .o_valid(sr2_o_valid), .w_fault(sr2_w_fault), .r_fault(sr2_r_fault), .w_addr(sr2_w_addr), .r_addr(sr2_r_addr), .i_data(sr2_i_data), .o_data(sr2_o_data));
wire seq_wck,seq_rck,seq_w_slot,seq_r_slot,seq_w_version,seq_r_version,seq_i_valid,seq_o_valid,seq_w_fault,seq_r_fault;
wire [5:0] seq_w_addr,seq_r_addr;
wire [545:0] seq_i_data,seq_o_data;
 io_static_stream #(.W(546),.ID(11),.MUT(10==3?MUT:0)) c_seq (.rst_n(rst_n), .done(done[10]), .failed(failed[10]), .wck(seq_wck), .rck(seq_rck), .w_slot(seq_w_slot), .r_slot(seq_r_slot), .w_version(seq_w_version), .r_version(seq_r_version), .i_valid(seq_i_valid), .o_valid(seq_o_valid), .w_fault(seq_w_fault), .r_fault(seq_r_fault), .w_addr(seq_w_addr), .r_addr(seq_r_addr), .i_data(seq_i_data), .o_data(seq_o_data));
wire cq_wck,cq_rck,cq_w_slot,cq_r_slot,cq_w_version,cq_r_version,cq_i_valid,cq_o_valid,cq_w_fault,cq_r_fault;
wire [5:0] cq_w_addr,cq_r_addr;
wire [516:0] cq_i_data,cq_o_data;
 io_static_stream #(.W(517),.ID(12),.MUT(11==3?MUT:0)) c_cq (.rst_n(rst_n), .done(done[11]), .failed(failed[11]), .wck(cq_wck), .rck(cq_rck), .w_slot(cq_w_slot), .r_slot(cq_r_slot), .w_version(cq_w_version), .r_version(cq_r_version), .i_valid(cq_i_valid), .o_valid(cq_o_valid), .w_fault(cq_w_fault), .r_fault(cq_r_fault), .w_addr(cq_w_addr), .r_addr(cq_r_addr), .i_data(cq_i_data), .o_data(cq_o_data));
qfd_io_xfifo_static dut (.rst_n(rst_n),
.up_wck(up_wck),
.up_rck(up_rck),
.up_w_slot(up_w_slot),
.up_r_slot(up_r_slot),
.up_w_version(up_w_version),
.up_r_version(up_r_version),
.up_i_valid(up_i_valid),
.up_o_valid(up_o_valid),
.up_w_fault(up_w_fault),
.up_r_fault(up_r_fault),
.up_w_addr(up_w_addr),
.up_r_addr(up_r_addr),
.up_i_data(up_i_data),
.up_o_data(up_o_data),
.dp_wck(dp_wck),
.dp_rck(dp_rck),
.dp_w_slot(dp_w_slot),
.dp_r_slot(dp_r_slot),
.dp_w_version(dp_w_version),
.dp_r_version(dp_r_version),
.dp_i_valid(dp_i_valid),
.dp_o_valid(dp_o_valid),
.dp_w_fault(dp_w_fault),
.dp_r_fault(dp_r_fault),
.dp_w_addr(dp_w_addr),
.dp_r_addr(dp_r_addr),
.dp_i_data(dp_i_data),
.dp_o_data(dp_o_data),
.ur_wck(ur_wck),
.ur_rck(ur_rck),
.ur_w_slot(ur_w_slot),
.ur_r_slot(ur_r_slot),
.ur_w_version(ur_w_version),
.ur_r_version(ur_r_version),
.ur_i_valid(ur_i_valid),
.ur_o_valid(ur_o_valid),
.ur_w_fault(ur_w_fault),
.ur_r_fault(ur_r_fault),
.ur_w_addr(ur_w_addr),
.ur_r_addr(ur_r_addr),
.ur_i_data(ur_i_data),
.ur_o_data(ur_o_data),
.dr_wck(dr_wck),
.dr_rck(dr_rck),
.dr_w_slot(dr_w_slot),
.dr_r_slot(dr_r_slot),
.dr_w_version(dr_w_version),
.dr_r_version(dr_r_version),
.dr_i_valid(dr_i_valid),
.dr_o_valid(dr_o_valid),
.dr_w_fault(dr_w_fault),
.dr_r_fault(dr_r_fault),
.dr_w_addr(dr_w_addr),
.dr_r_addr(dr_r_addr),
.dr_i_data(dr_i_data),
.dr_o_data(dr_o_data),
.sx0_wck(sx0_wck),
.sx0_rck(sx0_rck),
.sx0_w_slot(sx0_w_slot),
.sx0_r_slot(sx0_r_slot),
.sx0_w_version(sx0_w_version),
.sx0_r_version(sx0_r_version),
.sx0_i_valid(sx0_i_valid),
.sx0_o_valid(sx0_o_valid),
.sx0_w_fault(sx0_w_fault),
.sx0_r_fault(sx0_r_fault),
.sx0_w_addr(sx0_w_addr),
.sx0_r_addr(sx0_r_addr),
.sx0_i_data(sx0_i_data),
.sx0_o_data(sx0_o_data),
.sx1_wck(sx1_wck),
.sx1_rck(sx1_rck),
.sx1_w_slot(sx1_w_slot),
.sx1_r_slot(sx1_r_slot),
.sx1_w_version(sx1_w_version),
.sx1_r_version(sx1_r_version),
.sx1_i_valid(sx1_i_valid),
.sx1_o_valid(sx1_o_valid),
.sx1_w_fault(sx1_w_fault),
.sx1_r_fault(sx1_r_fault),
.sx1_w_addr(sx1_w_addr),
.sx1_r_addr(sx1_r_addr),
.sx1_i_data(sx1_i_data),
.sx1_o_data(sx1_o_data),
.sx2_wck(sx2_wck),
.sx2_rck(sx2_rck),
.sx2_w_slot(sx2_w_slot),
.sx2_r_slot(sx2_r_slot),
.sx2_w_version(sx2_w_version),
.sx2_r_version(sx2_r_version),
.sx2_i_valid(sx2_i_valid),
.sx2_o_valid(sx2_o_valid),
.sx2_w_fault(sx2_w_fault),
.sx2_r_fault(sx2_r_fault),
.sx2_w_addr(sx2_w_addr),
.sx2_r_addr(sx2_r_addr),
.sx2_i_data(sx2_i_data),
.sx2_o_data(sx2_o_data),
.sr0_wck(sr0_wck),
.sr0_rck(sr0_rck),
.sr0_w_slot(sr0_w_slot),
.sr0_r_slot(sr0_r_slot),
.sr0_w_version(sr0_w_version),
.sr0_r_version(sr0_r_version),
.sr0_i_valid(sr0_i_valid),
.sr0_o_valid(sr0_o_valid),
.sr0_w_fault(sr0_w_fault),
.sr0_r_fault(sr0_r_fault),
.sr0_w_addr(sr0_w_addr),
.sr0_r_addr(sr0_r_addr),
.sr0_i_data(sr0_i_data),
.sr0_o_data(sr0_o_data),
.sr1_wck(sr1_wck),
.sr1_rck(sr1_rck),
.sr1_w_slot(sr1_w_slot),
.sr1_r_slot(sr1_r_slot),
.sr1_w_version(sr1_w_version),
.sr1_r_version(sr1_r_version),
.sr1_i_valid(sr1_i_valid),
.sr1_o_valid(sr1_o_valid),
.sr1_w_fault(sr1_w_fault),
.sr1_r_fault(sr1_r_fault),
.sr1_w_addr(sr1_w_addr),
.sr1_r_addr(sr1_r_addr),
.sr1_i_data(sr1_i_data),
.sr1_o_data(sr1_o_data),
.sr2_wck(sr2_wck),
.sr2_rck(sr2_rck),
.sr2_w_slot(sr2_w_slot),
.sr2_r_slot(sr2_r_slot),
.sr2_w_version(sr2_w_version),
.sr2_r_version(sr2_r_version),
.sr2_i_valid(sr2_i_valid),
.sr2_o_valid(sr2_o_valid),
.sr2_w_fault(sr2_w_fault),
.sr2_r_fault(sr2_r_fault),
.sr2_w_addr(sr2_w_addr),
.sr2_r_addr(sr2_r_addr),
.sr2_i_data(sr2_i_data),
.sr2_o_data(sr2_o_data),
.seq_wck(seq_wck),
.seq_rck(seq_rck),
.seq_w_slot(seq_w_slot),
.seq_r_slot(seq_r_slot),
.seq_w_version(seq_w_version),
.seq_r_version(seq_r_version),
.seq_i_valid(seq_i_valid),
.seq_o_valid(seq_o_valid),
.seq_w_fault(seq_w_fault),
.seq_r_fault(seq_r_fault),
.seq_w_addr(seq_w_addr),
.seq_r_addr(seq_r_addr),
.seq_i_data(seq_i_data),
.seq_o_data(seq_o_data),
.cq_wck(cq_wck),
.cq_rck(cq_rck),
.cq_w_slot(cq_w_slot),
.cq_r_slot(cq_r_slot),
.cq_w_version(cq_w_version),
.cq_r_version(cq_r_version),
.cq_i_valid(cq_i_valid),
.cq_o_valid(cq_o_valid),
.cq_w_fault(cq_w_fault),
.cq_r_fault(cq_r_fault),
.cq_w_addr(cq_w_addr),
.cq_r_addr(cq_r_addr),
.cq_i_data(cq_i_data),
.cq_o_data(cq_o_data));
initial begin #20 rst_n=1;wait(&done);#20;
 if(failed==0)$display("PASS static_io channels=12 words=6144 exact_read_latency=3rck no_runtime_credit_or_backpressure");
 else $display("FAIL static_io channels_bad=%h",failed);$finish;end
 initial begin #10000;$display("FAIL static_io timeout done=%h",done);$finish;end
endmodule
module io_static_stream #(parameter W=546,ID=1,N=512,MUT=0)(
 input rst_n,output reg wck,rck,
 output reg w_slot,r_slot,w_version,r_version,i_valid,
 output reg [5:0] w_addr,r_addr,output reg [W-1:0] i_data,
 input o_valid,w_fault,r_fault,input [W-1:0] o_data,
 output reg done,failed);
 initial begin wck=0;rck=0;w_slot=0;r_slot=0;w_version=0;r_version=0;i_valid=0;w_addr=0;r_addr=0;i_data=0;done=0;failed=0;end
 initial begin #(ID*0.05);forever #1 wck=~wck;end
 initial begin #(ID*0.05);forever #2 rck=~rck;end
 integer wc=0,rc=0,wi=0,ri=0,got=0,k;integer ix[0:3];reg [3:0] ev=0;
 function [W-1:0] payload(input integer i);
 integer b;begin for(b=0;b<W;b=b+1) payload[b]=((i*17+ID*79+b*63)>>(b%13))&1;end endfunction
 always @(negedge wck) if(rst_n) begin
 wc=wc+1;w_slot=0;i_valid=0;
 if(wc>=16 && (wc-16)%2==0 && wi<N) begin
 w_slot=1;w_addr=wi%64;w_version=!((wi/64)%2);i_valid=(MUT && wi==123)?(MUT==2?1'bx:1'b0):1'b1;i_data=payload(wi);wi=wi+1;end
 end
 always @(negedge rck) if(rst_n) begin
 rc=rc+1;r_slot=0;
 if(rc>=17 && ri<N) begin r_slot=1;r_addr=ri%64;r_version=!((ri/64)%2);ri=ri+1;end
 end
 always @(posedge rck) if(rst_n) begin
 for(k=3;k>0;k=k-1)ix[k]=ix[k-1];ix[0]=ri-1;ev={ev[2:0],r_slot};#0.1;
 if(o_valid!==ev[3] || w_fault!==1'b0 || r_fault!==1'b0) failed=1;
 if(o_valid)begin if(o_data!==payload(ix[3]))failed=1;got=got+1;end
 if(got==N)done=1;
 end
endmodule
