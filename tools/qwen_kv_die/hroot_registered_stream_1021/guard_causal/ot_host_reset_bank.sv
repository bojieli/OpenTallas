module ot_host_reset_bank #(parameter integer N=2)(input wire clk,async_rst_n,output wire[N-1:0]sync_rst_n);
 (* async_reg="true",keep="true",dont_touch="true" *) reg first;
 (* async_reg="true",keep="true",dont_touch="true" *) reg[N-1:0] last;
 always @(posedge clk or negedge async_rst_n)
 if(!async_rst_n)begin first<=0;last<=0;end else begin first<=1;last<={N{first}};end
 assign sync_rst_n=last;
endmodule
