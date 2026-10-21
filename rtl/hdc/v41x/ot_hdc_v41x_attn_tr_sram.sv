`timescale 1ns/1ps
// Opt-in actual masked transpose. Constant-address SRAM, explicit write-through.
// Source-only until selected parent native/clock/physical proofs close.
module ot_hdc_v41x_attn_tr_sram #(
 parameter integer TD=32,DPT=8,NL=4,XOFF=0,MUT=0,RESET_SPLIT=0
)(input wire clk,rst_n,w_en_i,w_half_i,input wire[7:0]w_cnt_i,
 input wire[NL-1:0]w_pad_i,input wire[NL*265-1:0]w_g,
 input wire r_half_i,input wire[7:0]r_c_i,input wire sel_i,
 input wire[63:0]reset_leaf_i=64'd0,
 input wire[TD*18-1:0]qk_ib,output wire[TD*18-1:0]col,eib);
 localparam integer NR=2*TD, NS=2*DPT, W=NR*18, NB=(W+127)/128, RG=(NR+15)/16;
 function automatic[17:0]elem(input[264:0]gw,input integer x,input pad);
  if(gw[264])elem={pad,1'b1,4'd0,gw[4*x+:4],gw[128+8*(x/16)+:8]};
  else elem={pad,1'b0,gw[8*x+:8],gw[263:256]};
 endfunction
 reg[NL-1:0]fp_t;always@(posedge clk)fp_t<=w_pad_i;
 wire[NS-1:0]rsel_c;
 for(genvar s=0;s<NS;s=s+1)begin:g_rs
  assign rsel_c[s]=(r_half_i==(s/DPT))&&(r_c_i==(s%DPT));
 end
 wire[17:0]cell_data[0:DPT-1][0:NR-1];
 for(genvar x=0;x<DPT;x=x+1)begin:g_dim
  wire[NB*128-1:0]wd,wm,rd;
  reg[NL*18-1:0]forward_data;
  for(genvar lane=0;lane<NL;lane=lane+1)begin:g_lane
   always@(posedge clk)forward_data[18*lane+:18]<=elem(w_g[lane*265+:265],XOFF+((MUT==2)?((x+1)%DPT):x),fp_t[lane]);
  end
  for(genvar row=0;row<NR;row=row+1)begin:g_row
   wire we,forward_en;
   wire row_select=w_en_i&&((MUT==3)?(w_half_i!=(row/TD)):(w_half_i==(row/TD)))&&(w_cnt_i==((row%TD)/NL));
   wire row_reset=RESET_SPLIT?reset_leaf_i[(x*RG+row/16)%64]:rst_n;
   ot_hdc_v41x_kreg #(.W(1),.R(1))u_we(.clk(clk),.rst_n(row_reset),.d(row_select),.q(we));
   ot_hdc_v41x_kreg #(.W(1),.R(1))u_fe(.clk(clk),.rst_n(row_reset),.d(we),.q(forward_en));
   assign wd[18*row+:18]=elem(w_g[(row%NL)*265+:265],XOFF+((MUT==2)?((x+1)%DPT):x),fp_t[row%NL]);
   assign wm[18*row+:18]={18{we}};
   assign cell_data[x][row]=((MUT!=1)&&forward_en)?forward_data[18*(row%NL)+:18]:rd[18*row+:18];
  end
  if(NB*128>W)begin:g_pad
   assign wd[W+:NB*128-W]='0;assign wm[W+:NB*128-W]='0;
  end
  for(genvar b=0;b<NB;b=b+1)begin:g_bank
   ot_sram_1r1w_32x128_m1 u_mem(.clk(clk),.r_ce_in(1'b1),.r_addr_in(5'd0),.rd_out(rd[128*b+:128]),
    .w_ce_in(1'b1),.w_addr_in(5'd0),.wd_in(wd[128*b+:128]),.w_mask_in(wm[128*b+:128]));
  end
 end
 for(genvar row=0;row<TD;row=row+1)begin:g_c
  wire[NS-1:0]oh;wire sel;
  ot_hdc_v41x_kreg #(.W(NS),.R(0))u_rs(.clk(clk),.rst_n(rst_n),.d(rsel_c),.q(oh));
  ot_hdc_v41x_kreg #(.W(1),.R(1))u_sl(.clk(clk),.rst_n(RESET_SPLIT?reset_leaf_i[(DPT*RG+row/32)%64]:rst_n),.d(sel_i),.q(sel));
  reg[17:0]value;
  always@*begin value=0;for(integer k=0;k<NS;k=k+1)value=value|({18{oh[k]}}&cell_data[k%DPT][(k/DPT)*TD+row]);end
  assign col[18*row+:18]=value;
  reg[17:0]e;always@(posedge clk)e<=sel?value:qk_ib[18*row+:18];
  assign eib[18*row+:18]=e;
 end
 initial if(RESET_SPLIT && DPT*RG+(TD+31)/32>64)$error("reset-leaf geometry exceeds64");
 initial if(TD%NL!=0||DPT<1||XOFF+DPT>32)$error("unsupported transpose source shape");
endmodule
