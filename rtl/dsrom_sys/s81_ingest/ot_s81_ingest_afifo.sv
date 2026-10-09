`timescale 1ns/1ps
// Payload-protected additive asynchronousFIFO. StandardGray pointerflow and
// initialcredits are unchanged. SECDED failure masks unreadable head before
// consumers can capture it, then returns a sticky synchronized fault to writer.
// Original ot_link_afifo source remains byte-identical. Pointer/controlstate
// protection is a separate obligation, explicitly not supplied by this wrapper.
module ot_s81_ingest_afifo #(
 parameter integer W=64,AW=4,SYNC=2,
 parameter [72*((W+63)/64)-1:0] READ_INJECT=0
)(input wire wclk,wrst_n,wr,input wire[W-1:0] wdata,
 output wire wfull,output wire[AW:0] wfreed,output wire ovf,
 input wire rclk,rrst_n,rd,output wire rempty,output wire[W-1:0] rdata,output wire[AW:0] rcount);
 localparam integer N=(W+63)/64;
 wire[N*64-1:0] padded={{(N*64-W){1'b0}},wdata},decoded;
 wire[N*72-1:0] encoded,head;wire[N-1:0] ce,ue;
 wire full,empty,bovf;wire[AW:0] count;
 reg read_fault;reg[1:0] read_fault_w;
 genvar n;
 generate for(n=0;n<N;n=n+1)begin:g_codec
  ot_s81_secded_enc72 enc(padded[n*64+:64],encoded[n*72+:72]);
  ot_s81_secded_dec72 dec(head[n*72+:72]^READ_INJECT[n*72+:72],decoded[n*64+:64],ce[n],ue[n]);
 end endgenerate
 wire bad=!empty&&(|ue);
 ot_link_afifo #(.W(N*72),.AW(AW),.SYNC(SYNC)) fifo(.wclk(wclk),.wrst_n(wrst_n),.wr(wr&&!read_fault_w[1]),
  .wdata(encoded),.wfull(full),.wfreed(wfreed),.ovf(bovf),.rclk(rclk),.rrst_n(rrst_n),.rd(rd&&!bad&&!read_fault),
  .rempty(empty),.rdata(head),.rcount(count));
 always @(posedge rclk or negedge rrst_n)if(!rrst_n)read_fault<=0;else if(bad)read_fault<=1;
 always @(posedge wclk or negedge wrst_n)if(!wrst_n)read_fault_w<=0;else read_fault_w<={read_fault_w[0],read_fault};
 assign wfull=full|read_fault_w[1];assign ovf=bovf|read_fault_w[1];
 assign rempty=empty|bad|read_fault;assign rcount=read_fault?0:count;assign rdata=decoded[W-1:0];
endmodule
