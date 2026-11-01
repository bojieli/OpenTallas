`timescale 1ps/1fs
module tb_vq_metadata_lease;reg clk=0;always #416.5 clk=~clk;reg rn=0,mv=0,yv=0;reg[7:0]mi=128;reg[2:0]yi=0;reg[127:0]y=0;wire xv,xs,fault;wire[275:0]xd;reg[15:0]v[0:63];reg[1023:0]payload[0:159];reg[1103:0]word_=0;integer cyc=0,fr=0,nq=0,nb=0,tagbad=0,databad=0;
ot_s81sl_vq #(.AQ_XMEM(2))dut(.clk(clk),.rst_n(rn),.y_v(yv),.y_i(yi),.y(y),.u_v(1'b0),.u_i(3'd0),.u(256'd0),.sid(4'd0),.k(3'd0),.m_v(mv),.m_q(1'b1),.m_b(1'b1),.m_i(mi),.um_v(1'b0),.um_q(1'b0),.um_b(1'b0),.um_i(8'd0),.xf_v(xv),.xf_s(xs),.xf(xd),.fault(fault));
initial begin $readmemh("y64.memh",v);$readmemh("payloads.memh",payload);end
always @(negedge clk)begin rn=cyc>=64;mv=cyc==80||($test$plusargs("MUT_METADATA")&&cyc==200);mi=cyc==200?129:128;yv=cyc>=300&&cyc<308;yi=3'(cyc-300);for(integer j=0;j<8;j++)y[16*j+:16]=yv?v[8*(cyc-300)+j]:16'd0;end
always @(posedge clk)begin cyc++;#1;if(xv)begin if(xs)fr=0;word_[276*fr+:276]=xd;if(fr==3)begin if(word_[20:13]!=128)tagbad++;if(word_[3:1]==1)begin nq++;if(word_[21+:532]!==payload[0][531:0])databad++;end else if(word_[3:1]==2)begin nb++;if(word_[21+:1024]!==payload[1])databad++;end else databad++;end fr=(fr+1)%4;end
if(cyc==500)begin $display("VQ_METADATA_LEASE Q%0d BF%0d tagbad%0d databad%0d fault%0d",nq,nb,tagbad,databad,fault);if(nq==1&&nb==1&&tagbad==0&&databad==0&&!fault)$display("VQ_METADATA_LEASE_PASS");else $fatal(1,"VQ_METADATA_LEASE_FAIL");$finish;end end
endmodule
