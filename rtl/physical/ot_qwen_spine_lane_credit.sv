`timescale 1ns/1ps
// Opt-in transaction shell. Upstream starts with32 credits, downstream with2.
// Returning in_cr releases one complete transaction reservation. Credits and
// payloads cross registered pins only. Reset flushes both peers' credit state.
module ot_qwen_spine_lane_credit (
 input wire clk,rst_n,
 input wire in_v,
 input wire [1535:0] in_data,
 input wire [3:0] in_split,
 input wire [31:0] in_tag,
 output reg in_cr,
 output reg out_v,
 output reg [1535:0] out_data,
 output reg [31:0] out_tag,
 input wire out_cr,
 output reg fault
);
 localparam integer DEPTH=32, TL=8, PIPE=41;
 reg iv,cr;
 reg [1535:0] idata;
 reg [3:0] isp;
 reg [31:0] itag;
 reg [PIPE-1:0] valid_pipe;
 reg [3:0] split_pipe[0:PIPE-1];
 reg [31:0] tag_pipe[0:PIPE-1];
 wire [13:0] sel,tv;
 wire [1535:0] tree_y;
 wire tree_fault;
 wire [3:0] safe_split=(isp>=7 && isp<=13)?isp:4'd7;
 integer i;
 always @(posedge clk) begin idata<=in_data;isp<=in_split;itag<=in_tag; end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin iv<=0;cr<=0;valid_pipe<=0; end
  else begin iv<=in_v;cr<=out_cr;valid_pipe<={valid_pipe[PIPE-2:0],iv}; end
 always @(posedge clk) begin
  split_pipe[0]<=safe_split;tag_pipe[0]<=itag;
  for(i=1;i<PIPE;i=i+1) begin split_pipe[i]<=split_pipe[i-1];tag_pipe[i]<=tag_pipe[i-1];end
 end
 assign sel[7:0]=0;assign tv[7:0]=0;assign sel[13]=0;assign tv[13]=0;
 genvar lv;
 generate for(lv=8;lv<=12;lv=lv+1) begin: g_ctl
  localparam integer D=(lv-8)*TL;
  if(D==0) assign tv[lv]=iv && safe_split>=lv;
  else assign tv[lv]=valid_pipe[D-1] && split_pipe[D-1]>=lv;
  assign sel[lv]=split_pipe[D+6]>=lv;
 end endgenerate
 ot_qwen_spine_lane u_tree(clk,rst_n,idata,sel,tv,tree_y,tree_fault);
 reg [1535:0] data_fifo[0:DEPTH-1];
 reg [31:0] tag_fifo[0:DEPTH-1];
 reg [4:0] wp,rp;
 reg [5:0] used,pending;
 reg [1:0] credits;
 wire push=valid_pipe[PIPE-1];
 wire pop=(used!=0)&&(credits!=0);
 reg [1535:0] bank_rd[0:7],group_rd[0:1];
 reg [2:0] bank_sel;
 reg group_sel;
 reg [31:0] tag_rd,tag_rd2;
 reg v1,v2;
 integer b;
 // Every read mux has <=4 inputs, with kept registered intermediate stages.
 always @(posedge clk) begin
  if(push) begin data_fifo[wp]<=tree_y;tag_fifo[wp]<=tag_pipe[PIPE-1];end
  if(pop) begin
   for(b=0;b<8;b=b+1) bank_rd[b]<=data_fifo[b*4+rp[1:0]];
   bank_sel<=rp[4:2];tag_rd<=tag_fifo[rp];
  end
  if(v1) begin
   group_rd[0]<=bank_rd[{1'b0,bank_sel[1:0]}];
   group_rd[1]<=bank_rd[{1'b1,bank_sel[1:0]}];
   group_sel<=bank_sel[2];tag_rd2<=tag_rd;
  end
  if(v2) begin out_data<=group_rd[group_sel];out_tag<=tag_rd2;end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wp<=0;rp<=0;used<=0;pending<=0;credits<=2;v1<=0;v2<=0;out_v<=0;in_cr<=0;fault<=0;end
  else begin
   v1<=pop;v2<=v1;out_v<=v2;in_cr<=v2;
   if(push) wp<=wp+1'b1;
   if(pop) rp<=rp+1'b1;
   case({push,pop}) 2'b10:used<=used+1'b1;2'b01:used<=used-1'b1;default:;endcase
   case({in_v,v2}) 2'b10:pending<=pending+1'b1;2'b01:pending<=pending-1'b1;default:;endcase
   case({cr,pop}) 2'b10:credits<=credits+1'b1;2'b01:credits<=credits-1'b1;default:;endcase
   if(tree_fault || (in_v && pending==DEPTH && !v2) ||
      (push && used==DEPTH && !pop) || (cr && credits==2 && !pop) ||
      (iv && (isp<7 || isp>13))) fault<=1;
  end
 end
endmodule
