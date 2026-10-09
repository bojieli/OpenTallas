`timescale 1ns/1ps
// One injector's actual four-edge SRAM return ownership. Hub samples this
// packet on edge5. Metadata parity and duplicate validity fail closed before
// that capture; this leaf is independently placeable with the actual table.
module ot_hbm_collective_indexed_capture #(parameter W=512)(
 input wire clk,rst_n,request_valid,input wire[15:0] ordinal,index,
 input wire response_valid,response_fault,input wire[W-1:0] response_data,
 output wire capture_valid,output wire[W+31:0] capture_packet,
 output wire pending,output wire fault
);
 reg[4:0] valid_pipe,valid_check;
 reg[31:0] metadata[0:4];reg parity[0:4];reg bad;
 wire mismatch=response_valid!=valid_pipe[4] || valid_pipe!=valid_check ||
 (valid_pipe[4] && (^metadata[4])!=parity[4]);
 assign pending=|valid_pipe;
 assign fault=bad || mismatch || response_fault;
 assign capture_valid=response_valid && !fault;
 assign capture_packet={metadata[4],response_data};
 always@(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
 valid_pipe<=0;valid_check<=0;bad<=0;
 for(integer t=0;t<5;t=t+1)begin metadata[t]<=0;parity[t]<=0;end
 end else begin
 if(mismatch || response_fault)bad<=1;
 valid_pipe<={valid_pipe[3:0],request_valid};
 valid_check<={valid_check[3:0],request_valid};
 metadata[0]<={ordinal,index};parity[0]<=^{ordinal,index};
 for(integer t=1;t<5;t=t+1)begin metadata[t]<=metadata[t-1];parity[t]<=parity[t-1];end
 end end
endmodule
