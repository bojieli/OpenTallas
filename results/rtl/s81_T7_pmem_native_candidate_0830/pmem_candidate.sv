// DISABLED standalone candidate only; never selected by production RTL/manifest.
module pmem_candidate(input wire clk,rst_n,input wire[8:0]pr,wa,input wire[1:0]pstep,input wire owner,p_v,p_ready_i,input wire[511:0]wd,wm,input integer mutant,
output wire p_ready,out_v,output wire[1023:0]out_w,slot0,slot1,output reg[1:0]sk_n,output reg wp,rp);
wire push=p_v&&p_ready,pop=out_v&&p_ready_i;
assign p_ready=(sk_n!=2);assign out_v=(sk_n!=0);
reg latest_slot;reg[2:0]format;reg[1023:0]older;reg push_d;
always@(posedge clk)push_d<=push;
wire[511:0]even_word,odd_word;wire[7:0]even_a=pr[8:1]+{7'd0,pr[0]},odd_a=pr[8:1];
genvar bank,slice;generate for(bank=0;bank<2;bank++)begin:b
 for(slice=0;slice<2;slice++)begin:s
  wire[7:0]a=(bank==0?even_a:odd_a)^((mutant==1&&bank==0)?8'd1:8'd0);
  wire[255:0]q;
  ot_sram_1r1w_256x256_m2_r2c2 ram(.clk(clk),.r_ce_in(mutant==2?push_d:push),.r_addr_in(a),.rd_out(q),
    .w_ce_in((wa[0]==bank)&&(|wm[256*slice+:256])),.w_addr_in(wa[8:1]),.wd_in(wd[256*slice+:256]),.w_mask_in(wm[256*slice+:256]),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
  if(bank==0)assign even_word[256*slice+:256]=q;else assign odd_word[256*slice+:256]=q;
 end
end endgenerate
wire odd_format=(format==2||format==4),tail_format=(format==3||format==4);
wire[1023:0]latest=(format==0)?1024'd0:{tail_format?{512{1'b1}}:(odd_format?even_word:odd_word),odd_format?odd_word:even_word};
wire[2:0]next_format=!owner?3'd0:(pstep==2?(pr[0]?3'd2:3'd1):(pr[0]?3'd4:3'd3));
assign slot0=latest_slot==0?latest:older;assign slot1=latest_slot==1?latest:older;
assign out_w=rp?slot1:slot0;
always@(posedge clk or negedge rst_n)begin
 if(!rst_n)begin sk_n<=0;wp<=0;rp<=0;end
 else begin sk_n<=sk_n+(push?2'd1:2'd0)-(pop?2'd1:2'd0);if(push)wp<=!wp;if(pop)rp<=!rp;end
end
// Like native payload captures: independent of the resettable control process.
always@(posedge clk)begin
 if(push)begin
  if(wp!=latest_slot)older<=latest;
  latest_slot<=wp;
 end
 if(mutant==3&&!rst_n)format<=0;
 else if(push)format<=next_format;
end
endmodule
