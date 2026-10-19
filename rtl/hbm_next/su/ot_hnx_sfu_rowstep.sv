`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_sfu_rowstep (HBM-NEXT-UNITS-SUDMA2 2026-10-19): SFU CHAIN ROW STEP of the next HBM die (HGI-1R ROWX, P = 4),
// between the d4g SFU programme store (ot_hgi_sfu_programme_store_r10, CRITICAL, unchanged) and the stream SFU core
// (ot_hgi_sfu_core_split3, unchanged). Control only: no datapath, no queue, no ready/credit.
// Why: an N-row SFU chain record (SwiGLU / softplus / norm-style chains on the stream SFU) runs the SAME IO calendar
// once a row: the store already repeats [base, limit) start_loops times with no bubble at the wrap (program stripe
// pc <= base), but every loop fetched / drained the same VM sectors. Unrolled, the IO image grows N x (2,048 rows a
// stripe at PAGE_AW 1). Here the IO image holds row 0's words and this stage adds the row offset to the VM fields of
// io_word (the 471-b SFU IO ABI of ot_hgi_sfu_core_split2):
//   prefetch_sector[b] (io[16 + 16 b +: 16], b = 0..7) += row x s_rd   when prefetch_v[b]   (operand and scalar loads)
//   drain_vm_sector[j] (io[436 + 16 j +: 16], j = 0..1) += row x s_wr  when drain_v[j]      (row results)
// Local store / scalar / lane fields (prefetch_local_addr, scalar_addr, drain_addr, prefetch_word/group) and the
// arithmetic programme (compiler_control, started once a row by the IO word's arith-start bit, d4g) are unchanged.
// Row index: from the store's io_ordinal: ordinal 0 = row 0 (a new launch);
// ordinal = next wrap (k x P, P = the record's IO period in words) = the next row. Incremental (one adder a stride, no
// multiplier, no divider). Broadcast operands go in a prologue launch of P0 <= P words before the row-body launch
// (ordinal restarts at 0, so the prologue stays on row 0 = unstepped).
// Strides are record-static (CP: rs_k in sectors; s[2:0] must be 0 so a sector keeps its bank / port id).
// Checks (sticky FAULT): a stepped sector carries out of 16 b; a stepped sector with s[2:0] != 0 (row > 0).
// OLAG 1 (MEASURED, tb_hnx_sfu_rows first run, bundle 1ec36302d): the r10 store's io_ordinal LEADS its io_word by one
// edge (with OLAG 0 exactly the last word of every row took the next row's offset: N mismatches a record), so the stage
// delays the ordinal one edge (ord_q) to align it with io_word.
// REG 1: io_word and compiler_control registered together (+1 edge both; the core's pin registers are unchanged).
// MUT (bench only, must FAIL): 1 drain stride dropped; 2 prefetch stride dropped; 3 wrap one word early;
// 4 row not cleared at ordinal 0 (a second record keeps the first record's row).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_sfu_rowstep #(parameter integer REG=1,OLAG=1,MUT=0)(
 input wire clk,rst_n,
 input wire [470:0] io_in,
 input wire [1741:0] ctl_in,
 input wire [31:0] ordinal,
 input wire [11:0] period,                    // P: IO words a row (record-static, 0 = not a row record)
 input wire [15:0] s_rd,s_wr,                 // sector strides a row (record-static)
 output reg [470:0] io_out,
 output reg [1741:0] ctl_out,
 output reg [15:0] row_out,
 output reg fault
);
 reg [15:0] row; reg [31:0] nxt; reg [15:0] off_r,off_w;
 reg [31:0] ord_q; always @(posedge clk)ord_q<=ordinal;
 wire [31:0] ord=(OLAG!=0)?ord_q:ordinal;
 wire zero=(ord==32'd0)&&(MUT!=4);
 wire wrap=(ord!=32'd0)&&(ord==((MUT==3)?nxt-32'd1:nxt))&&(period!=12'd0);
 wire [15:0] row_c=zero?16'd0:(wrap?row+16'd1:row);
 wire [16:0] or_c=zero?17'd0:(wrap?{1'b0,off_r}+{1'b0,s_rd}:{1'b0,off_r});
 wire [16:0] ow_c=zero?17'd0:(wrap?{1'b0,off_w}+{1'b0,s_wr}:{1'b0,off_w});
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin row<=0; nxt<=0; off_r<=0; off_w<=0; end
  else if(zero)begin row<=0; nxt<={20'd0,period}; off_r<=0; off_w<=0; end
  else if(wrap)begin row<=row_c; nxt<=nxt+{20'd0,period}; off_r<=or_c[15:0]; off_w<=ow_c[15:0]; end
 reg [470:0] y; reg bad; integer b; reg [16:0] sx;
 always @*begin
  y=io_in; bad=1'b0;
  if((or_c[16]||ow_c[16])&&(|io_in[7:0]||(|io_in[405:404])))bad=1'b1;
  for(b=0;b<8;b=b+1)if(io_in[b])begin
   sx={1'b0,io_in[16+16*b+:16]}+((MUT==2)?17'd0:{1'b0,or_c[15:0]});
   if(sx[16]||(row_c!=0&&s_rd[2:0]!=3'd0))bad=1'b1;
   y[16+16*b+:16]=sx[15:0];
  end
  for(b=0;b<2;b=b+1)if(io_in[404+b])begin
   sx={1'b0,io_in[436+16*b+:16]}+((MUT==1)?17'd0:{1'b0,ow_c[15:0]});
   if(sx[16]||(row_c!=0&&s_wr[2:0]!=3'd0))bad=1'b1;
   y[436+16*b+:16]=sx[15:0];
  end
 end
 if(REG!=0)begin:g_reg
  always @(posedge clk)begin io_out<=y; ctl_out<=ctl_in; row_out<=row_c; end
 end else begin:g_comb
  always @*begin io_out=y; ctl_out=ctl_in; row_out=row_c; end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=1'b0; else if(bad)fault<=1'b1;
endmodule
`default_nettype wire
