`timescale 1ns/1ps
// Finite packet CDC for the native two-credit x3 / four-credit ar hub ports.
// Cold reset only. Epoch fences never reset transport counters or FIFO pointers.
module ot_qwen_kvc_hub_cdc #(
 parameter integer ENABLE=0, parameter [1:0] DEST=0
)(
 input wire rst_n, input wire local_clk, input wire hub_clk, input wire native_hub_fault,
 input wire tx_v, input wire [509:0] tx_packet, output wire tx_ready,
 output wire rx_v, output wire [509:0] rx_packet,
 output wire [10:0] rx_tag, output wire [1:0] rx_source,
 input wire rx_take, output wire local_quiet, output wire fault,
 output wire x3_v, output wire [511:0] x3_d, output wire [10:0] x3_tag,
 input wire x3_cr, input wire ar_v, input wire [511:0] ar_d,
 input wire [10:0] ar_tag, input wire [1:0] ar_source, output reg ar_cr
);
 wire tr, tv, rr, rv; wire [509:0] td; wire [522:0] rd;
 wire tx_over, tx_under, rx_over, rx_under;
 reg [1:0] credits;
 reg hub_fault;
 reg [3:0] returns, returns_gray;
 (* async_reg="true" *) reg [3:0] rg1,rg2;
 reg [3:0] returned;
 function automatic [3:0] ungray(input [3:0] g);
  begin ungray[3]=g[3]; ungray[2]=g[3]^g[2]; ungray[1]=g[3]^g[2]^g[1]; ungray[0]=^g; end
 endfunction
 wire send=ENABLE && tv && credits!=0 && !hub_fault;
 wire pop=ENABLE && rv && rx_take;
 wire [3:0] pending=ungray(rg2)-returned;
 reg [3:0] ar_owned;
 wire [4:0] owned_next={1'b0,ar_owned}+ar_v-ar_cr;
 (* async_reg="true" *) reg fault1,fault2, quiet1,quiet2;
 wire hub_quiet=!tv && credits==2 && !ar_v && !ar_cr && ar_owned==0 && pending==0;
 ot_async_fifo #(.WIDTH(510),.DEPTH(16)) txq(
  .wr_clk(local_clk),.wr_rst_n(rst_n),.wr_valid(ENABLE&&tx_v),.wr_ready(tr),.wr_data(tx_packet),.wr_overflow(tx_over),
  .rd_clk(hub_clk),.rd_rst_n(rst_n),.rd_valid(tv),.rd_ready(send),.rd_data(td),.rd_underflow(tx_under));
 ot_async_fifo #(.WIDTH(523),.DEPTH(8)) rxq(
  .wr_clk(hub_clk),.wr_rst_n(rst_n),.wr_valid(ENABLE&&ar_v),.wr_ready(rr),.wr_data({ar_source,ar_tag,ar_d[511:2]}),.wr_overflow(rx_over),
  .rd_clk(local_clk),.rd_rst_n(rst_n),.rd_valid(rv),.rd_ready(pop),.rd_data(rd),.rd_underflow(rx_under));
 assign tx_ready=ENABLE&&tr;
 assign rx_v=ENABLE&&rv;
 assign {rx_source,rx_tag,rx_packet}=rd;
 assign x3_v=send;
 assign x3_d={DEST,td};
 assign x3_tag=td[481:471]; // seq[10:0]
 assign fault=fault2;
 assign local_quiet=quiet2&&!rv&&!tx_v;
 always @(posedge local_clk or negedge rst_n) begin
  if(!rst_n) begin returns<=0;returns_gray<=0;fault1<=0;fault2<=0;quiet1<=0;quiet2<=0;end
  else begin
   fault1<=hub_fault;fault2<=fault1;quiet1<=hub_quiet;quiet2<=quiet1;
   if(pop) begin returns<=returns+1'b1;returns_gray<=((returns+1'b1)>>1)^(returns+1'b1);end
  end
 end
 always @(posedge hub_clk or negedge rst_n) begin
  if(!rst_n) begin credits<=2;hub_fault<=0;rg1<=0;rg2<=0;returned<=0;ar_cr<=0;ar_owned<=0;end
  else begin
   rg1<=returns_gray;rg2<=rg1;ar_cr<=0;
   if(ENABLE) begin
    if(native_hub_fault)hub_fault<=1;
    case({x3_cr,send})
     2'b10:if(credits<2)credits<=credits+1'b1;else hub_fault<=1;
     2'b01:credits<=credits-1'b1;
    endcase
    if(ar_v&&!rr)hub_fault<=1;
    if(owned_next>4)hub_fault<=1; else ar_owned<=owned_next[3:0];
    if(pending>4)hub_fault<=1;
    else if(pending!=0)begin ar_cr<=1;returned<=returned+1'b1;end
   end
  end
 end
endmodule
