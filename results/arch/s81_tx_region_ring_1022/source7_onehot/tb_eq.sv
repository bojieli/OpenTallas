`timescale 1ns/1ps
module tb_eq;
parameter integer D=4,K=2;
reg sck=0,dck=0,srn=0,drn=0; reg[15:0]d=0; wire[15:0]qa,qb; integer n=0,cyc=0;
old_slice #(.W(16),.D(D),.K(K)) a(.src_ck(sck),.dst_ck(dck),.src_rn(srn),.dst_rn(drn),.d(d),.q(qa));
dsdv_tx_ring_slice #(.W(16),.D(D),.K(K)) b(.src_ck(sck),.dst_ck(dck),.src_rn(srn),.dst_rn(drn),.d(d),.q(qb));
always #5 sck=~sck;
always #(3+($urandom%5)) dck=~dck;
always @(negedge sck) begin d<=$urandom; if(($urandom%300)==0) srn<=0; else srn<=1; end
always @(negedge dck) begin if(($urandom%300)==0) drn<=0; else drn<=1; end
always @(posedge dck) begin #0.01; cyc=cyc+1; if(qa!==qb) begin $display("EQ_FAIL D=%0d K=%0d cyc=%0d %h %h",D,K,cyc,qa,qb); $fatal(1); end if(qa!=0) n=n+1; end
initial begin #400000; if(n<1000) $fatal(1,"vacuous %0d",n); $display("EQ_PASS D=%0d K=%0d dst_cycles=%0d nonzero=%0d",D,K,cyc,n); $finish; end
endmodule
