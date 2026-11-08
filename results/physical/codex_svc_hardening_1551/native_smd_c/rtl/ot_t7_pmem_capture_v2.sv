// MEM v2 (S81 svc fit 2026-11-03): ot_t7_pmem_capture_candidate with 4 x ot_sram_1r1w_256x256_m1_r0c0 (no mux, no repair).
// DISABLED isolated T7 data-cut projection. Original control stays in its bound parent.
// Algorithm source gate09032d7ab; this integration projection has not been elaborated.
module ot_t7_pmem_capture_v2(input wire clk,input wire[8:0]pr,wa,input wire[1:0]pstep,input wire owner,push,wp,input wire[511:0]wd,wm,output wire[1023:0]slot0,slot1);
reg latest_slot;reg[2:0]format;reg[1023:0]older;
wire[511:0]even_word,odd_word;wire[7:0]even_a=pr[8:1]+{7'd0,pr[0]},odd_a=pr[8:1];
genvar bank,slice;generate for(bank=0;bank<2;bank++)begin:b
 for(slice=0;slice<2;slice++)begin:s
  wire[255:0]q;
  ot_sram_1r1w_256x256_m1_r0c0 ram(.clk(clk),.r_ce_in(push),.r_addr_in(bank==0?even_a:odd_a),.rd_out(q),
   .w_ce_in((wa[0]==bank)&&(|wm[256*slice+:256])),.w_addr_in(wa[8:1]),.wd_in(wd[256*slice+:256]),.w_mask_in(wm[256*slice+:256]));
  if(bank==0)assign even_word[256*slice+:256]=q;else assign odd_word[256*slice+:256]=q;
 end
end endgenerate
wire odd_format=(format==2||format==4),tail_format=(format==3||format==4);
wire[1023:0]latest=(format==0)?1024'd0:{tail_format?{512{1'b1}}:(odd_format?even_word:odd_word),odd_format?odd_word:even_word};
wire[2:0]next_format=!owner?3'd0:(pstep==2?(pr[0]?3'd2:3'd1):(pr[0]?3'd4:3'd3));
assign slot0=latest_slot==0?latest:older;assign slot1=latest_slot==1?latest:older;
// These are reset-free like both removed native payload captures.
always@(posedge clk)if(push)begin
 if(wp!=latest_slot)older<=latest;
 latest_slot<=wp;format<=next_format;
end
endmodule
