`timescale 1ns/1ps
module tb_qfd_io_xfifo;
 reg rst_n=0;
 reg ck_local=0,ck_seq=0;
 always #1.0 ck_local=~ck_local;
 always #1.7 ck_seq=~ck_seq;
 wire [21:0] fault;
 wire [9:0] done,failed;
 wire up_wck,up_rck,up_i_v,up_i_cr,up_o_v,up_o_cr; wire [545:0] up_i_d,up_o_d;
 xf_stream_check #(.W(546),.IBUF(32),.ID(1),.HW(1.0),.HR(1.3)) chk_up
 (.rst_n(rst_n),.wck(up_wck),.rck(up_rck),.i_v(up_i_v),.i_d(up_i_d),.i_cr(up_i_cr),
 .o_v(up_o_v),.o_d(up_o_d),.o_cr(up_o_cr),.done(done[0]),.failed(failed[0]));
 wire dp_wck,dp_rck,dp_i_v,dp_i_cr,dp_o_v,dp_o_cr; wire [545:0] dp_i_d,dp_o_d;
 xf_stream_check #(.W(546),.IBUF(4),.ID(2),.HW(1.021),.HR(1.317)) chk_dp
 (.rst_n(rst_n),.wck(dp_wck),.rck(dp_rck),.i_v(dp_i_v),.i_d(dp_i_d),.i_cr(dp_i_cr),
 .o_v(dp_o_v),.o_d(dp_o_d),.o_cr(dp_o_cr),.done(done[1]),.failed(failed[1]));
 wire ur_wck,ur_rck,ur_i_v,ur_i_cr,ur_o_v,ur_o_cr; wire [513:0] ur_i_d,ur_o_d;
 xf_stream_check #(.W(514),.IBUF(32),.ID(3),.HW(1.042),.HR(1.334)) chk_ur
 (.rst_n(rst_n),.wck(ur_wck),.rck(ur_rck),.i_v(ur_i_v),.i_d(ur_i_d),.i_cr(ur_i_cr),
 .o_v(ur_o_v),.o_d(ur_o_d),.o_cr(ur_o_cr),.done(done[2]),.failed(failed[2]));
 wire dr_wck,dr_rck,dr_i_v,dr_i_cr,dr_o_v,dr_o_cr; wire [513:0] dr_i_d,dr_o_d;
 xf_stream_check #(.W(514),.IBUF(4),.ID(4),.HW(1.063),.HR(1.351)) chk_dr
 (.rst_n(rst_n),.wck(dr_wck),.rck(dr_rck),.i_v(dr_i_v),.i_d(dr_i_d),.i_cr(dr_i_cr),
 .o_v(dr_o_v),.o_d(dr_o_d),.o_cr(dr_o_cr),.done(done[3]),.failed(failed[3]));
 wire sx0_wck,sx0_rck,sx0_i_v,sx0_i_cr,sx0_o_v,sx0_o_cr; wire [545:0] sx0_i_d,sx0_o_d;
 xf_stream_check #(.W(546),.IBUF(64),.ID(5),.HW(1.084),.HR(1.368)) chk_sx0
 (.rst_n(rst_n),.wck(sx0_wck),.rck(sx0_rck),.i_v(sx0_i_v),.i_d(sx0_i_d),.i_cr(sx0_i_cr),
 .o_v(sx0_o_v),.o_d(sx0_o_d),.o_cr(sx0_o_cr),.done(done[4]),.failed(failed[4]));
 wire sx1_wck,sx1_rck,sx1_i_v,sx1_i_cr,sx1_o_v,sx1_o_cr; wire [545:0] sx1_i_d,sx1_o_d;
 xf_stream_check #(.W(546),.IBUF(64),.ID(6),.HW(1.105),.HR(1.385)) chk_sx1
 (.rst_n(rst_n),.wck(sx1_wck),.rck(sx1_rck),.i_v(sx1_i_v),.i_d(sx1_i_d),.i_cr(sx1_i_cr),
 .o_v(sx1_o_v),.o_d(sx1_o_d),.o_cr(sx1_o_cr),.done(done[5]),.failed(failed[5]));
 wire sx2_wck,sx2_rck,sx2_i_v,sx2_i_cr,sx2_o_v,sx2_o_cr; wire [545:0] sx2_i_d,sx2_o_d;
 xf_stream_check #(.W(546),.IBUF(64),.ID(7),.HW(1.126),.HR(1.4020000000000001)) chk_sx2
 (.rst_n(rst_n),.wck(sx2_wck),.rck(sx2_rck),.i_v(sx2_i_v),.i_d(sx2_i_d),.i_cr(sx2_i_cr),
 .o_v(sx2_o_v),.o_d(sx2_o_d),.o_cr(sx2_o_cr),.done(done[6]),.failed(failed[6]));
 wire sr0_wck,sr0_rck,sr0_i_v,sr0_i_cr,sr0_o_v,sr0_o_cr; wire [545:0] sr0_i_d,sr0_o_d;
 xf_stream_check #(.W(546),.IBUF(4),.ID(8),.HW(1.147),.HR(1.419)) chk_sr0
 (.rst_n(rst_n),.wck(sr0_wck),.rck(sr0_rck),.i_v(sr0_i_v),.i_d(sr0_i_d),.i_cr(sr0_i_cr),
 .o_v(sr0_o_v),.o_d(sr0_o_d),.o_cr(sr0_o_cr),.done(done[7]),.failed(failed[7]));
 wire sr1_wck,sr1_rck,sr1_i_v,sr1_i_cr,sr1_o_v,sr1_o_cr; wire [545:0] sr1_i_d,sr1_o_d;
 xf_stream_check #(.W(546),.IBUF(4),.ID(9),.HW(1.168),.HR(1.436)) chk_sr1
 (.rst_n(rst_n),.wck(sr1_wck),.rck(sr1_rck),.i_v(sr1_i_v),.i_d(sr1_i_d),.i_cr(sr1_i_cr),
 .o_v(sr1_o_v),.o_d(sr1_o_d),.o_cr(sr1_o_cr),.done(done[8]),.failed(failed[8]));
 wire sr2_wck,sr2_rck,sr2_i_v,sr2_i_cr,sr2_o_v,sr2_o_cr; wire [545:0] sr2_i_d,sr2_o_d;
 xf_stream_check #(.W(546),.IBUF(4),.ID(10),.HW(1.189),.HR(1.453)) chk_sr2
 (.rst_n(rst_n),.wck(sr2_wck),.rck(sr2_rck),.i_v(sr2_i_v),.i_d(sr2_i_d),.i_cr(sr2_i_cr),
 .o_v(sr2_o_v),.o_d(sr2_o_d),.o_cr(sr2_o_cr),.done(done[9]),.failed(failed[9]));
 qfd_io_xfifo dut (
 .rst_n(rst_n),
 .ck_local(ck_local),
 .ck_seq(ck_seq),
 .fault(fault),
 .i_seq_coll_v(1'b0),
 .i_seq_coll(546'b0),
 .i_seq_coll_cr(),
 .o_seq_coll_v(),
 .o_seq_coll(),
 .o_seq_coll_cr(1'b0),
 .i_coll_seq_v(1'b0),
 .i_coll_seq(517'b0),
 .o_coll_seq_v(),
 .o_coll_seq(),
 .up_wck(up_wck),
 .up_rck(up_rck),
 .up_i_v(up_i_v),
 .up_i_d(up_i_d),
 .up_i_cr(up_i_cr),
 .up_o_v(up_o_v),
 .up_o_d(up_o_d),
 .up_o_cr(up_o_cr),
 .dp_wck(dp_wck),
 .dp_rck(dp_rck),
 .dp_i_v(dp_i_v),
 .dp_i_d(dp_i_d),
 .dp_i_cr(dp_i_cr),
 .dp_o_v(dp_o_v),
 .dp_o_d(dp_o_d),
 .dp_o_cr(dp_o_cr),
 .ur_wck(ur_wck),
 .ur_rck(ur_rck),
 .ur_i_v(ur_i_v),
 .ur_i_d(ur_i_d),
 .ur_i_cr(ur_i_cr),
 .ur_o_v(ur_o_v),
 .ur_o_d(ur_o_d),
 .ur_o_cr(ur_o_cr),
 .dr_wck(dr_wck),
 .dr_rck(dr_rck),
 .dr_i_v(dr_i_v),
 .dr_i_d(dr_i_d),
 .dr_i_cr(dr_i_cr),
 .dr_o_v(dr_o_v),
 .dr_o_d(dr_o_d),
 .dr_o_cr(dr_o_cr),
 .sx0_wck(sx0_wck),
 .sx0_rck(sx0_rck),
 .sx0_i_v(sx0_i_v),
 .sx0_i_d(sx0_i_d),
 .sx0_i_cr(sx0_i_cr),
 .sx0_o_v(sx0_o_v),
 .sx0_o_d(sx0_o_d),
 .sx0_o_cr(sx0_o_cr),
 .sx1_wck(sx1_wck),
 .sx1_rck(sx1_rck),
 .sx1_i_v(sx1_i_v),
 .sx1_i_d(sx1_i_d),
 .sx1_i_cr(sx1_i_cr),
 .sx1_o_v(sx1_o_v),
 .sx1_o_d(sx1_o_d),
 .sx1_o_cr(sx1_o_cr),
 .sx2_wck(sx2_wck),
 .sx2_rck(sx2_rck),
 .sx2_i_v(sx2_i_v),
 .sx2_i_d(sx2_i_d),
 .sx2_i_cr(sx2_i_cr),
 .sx2_o_v(sx2_o_v),
 .sx2_o_d(sx2_o_d),
 .sx2_o_cr(sx2_o_cr),
 .sr0_wck(sr0_wck),
 .sr0_rck(sr0_rck),
 .sr0_i_v(sr0_i_v),
 .sr0_i_d(sr0_i_d),
 .sr0_i_cr(sr0_i_cr),
 .sr0_o_v(sr0_o_v),
 .sr0_o_d(sr0_o_d),
 .sr0_o_cr(sr0_o_cr),
 .sr1_wck(sr1_wck),
 .sr1_rck(sr1_rck),
 .sr1_i_v(sr1_i_v),
 .sr1_i_d(sr1_i_d),
 .sr1_i_cr(sr1_i_cr),
 .sr1_o_v(sr1_o_v),
 .sr1_o_d(sr1_o_d),
 .sr1_o_cr(sr1_o_cr),
 .sr2_wck(sr2_wck),
 .sr2_rck(sr2_rck),
 .sr2_i_v(sr2_i_v),
 .sr2_i_d(sr2_i_d),
 .sr2_i_cr(sr2_i_cr),
 .sr2_o_v(sr2_o_v),
 .sr2_o_d(sr2_o_d),
 .sr2_o_cr(sr2_o_cr));
 initial begin
 #40 rst_n=1;
 wait (&done); #10;
 if (failed==0 && fault==0) $display("PASS qfd_io_xfifo 10 concurrent native channels, 512 words per channel, unrelated boundary clocks, delayed credits");
 else $display("FAIL qfd_io_xfifo failed=%h fault=%h",failed,fault);
 $finish;
 end
 initial begin #200000; $display("FAIL qfd_io_xfifo timeout done=%h fault=%h",done,fault); $finish; end
endmodule
module xf_stream_check #(parameter W=546,IBUF=4,ID=1,N=512,parameter real HW=1.0,HR=1.3)
 (input rst_n,output reg wck,rck,i_v,output reg [W-1:0] i_d,input i_cr,o_v,input [W-1:0] o_d,output reg o_cr,done,failed);
 initial begin wck=0;rck=0;i_v=0;i_d=0;o_cr=0;done=0;failed=0;end
 always #HW wck=~wck; always #HR rck=~rck;
 reg [W-1:0] expected[0:N-1];
 integer ns=0,nr=0,credits=IBUF,cycle=0,owe=0,k;
 reg [3:0] cp=0;
 always @(posedge wck) if(rst_n) begin
 cycle=cycle+1;
 if(i_v) begin expected[ns]=i_d;ns=ns+1;end
 cp<={cp[2:0],i_cr}; credits=credits+cp[2];
 i_v<=0;
 if(cycle>24 && ns<N && credits>0 && cycle%7!=ID%7) begin
 i_v<=1; credits=credits-1;
 for(k=0;k<W;k=k+1) i_d[k]<=((ns*23+ID*119+k*43)>>(k%11))&1;
 end
 end
 always @(posedge rck) if(rst_n) begin
 if(o_v) begin
 if(nr>=ns || o_d!==expected[nr]) failed<=1;
 nr=nr+1;owe=owe+1;
 end
 o_cr<=0;
 if(owe>0 && (nr+cycle)%4==0) begin o_cr<=1;owe=owe-1;end
 if(nr==N) done<=1;
 end
endmodule
