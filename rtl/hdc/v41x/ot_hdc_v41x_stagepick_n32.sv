`timescale 1ns/1ps
// Two existing selector edges; dense consumed-bit leaves, <=8bits per final selector.
module ot_hdc_v41x_stagepick_n32 #(parameter integer W=1060,parameter[W-1:0]LIVE={W{1'b1}})(
 input wire clk,input wire source_select,legacy_select,input wire[W-1:0]bank0,bank1,output wire[W-1:0]word_out);
 function automatic integer rank(input integer stop);
  integer k;begin rank=0;for(k=0;k<stop;k=k+1)if(LIVE[k])rank=rank+1;end
 endfunction
 localparam integer N=(rank(W)+7)/8,C=(N+31)/32;
 wire[C-1:0]early;wire[N-1:0]late;
 for(genvar c=0;c<C;c=c+1)begin:g_cohort
  ot_hdc_v41x_kreg #(.W(1),.R(0))u_first(.clk(clk),.rst_n(1'b1),.d(source_select),.q(early[c]));
 end
 for(genvar s=0;s<N;s=s+1)begin:g_leaf
  ot_hdc_v41x_kreg #(.W(1),.R(0))u_second(.clk(clk),.rst_n(1'b1),.d(early[s/32]),.q(late[s]));
 end
 for(genvar b=0;b<W;b=b+1)begin:g_bit
  if(LIVE[b])assign word_out[b]=late[rank(b)/8]?bank1[b]:bank0[b];
  else assign word_out[b]=legacy_select?bank1[b]:bank0[b];
 end
 initial if(rank(W)<1)$error("stagepick requires live bits");
endmodule
