`default_nettype none
// Fixed compiler-issued5/5/6bit radix schedule, Q4xW16 production shape. No ready,
// replay, queue, credit or variable-length scan. Owns 12 real 256x256 SRAMs.
// Opcodes: 0idle,1clear frame,2ingest,3hist clear,4hist scan,5choose bin,
// 6compact scan,7flush partial,8emit line. Every phase includes its fixed
// memory drain edges. Bins scanned31..0,31..0,63..0 for passes0..2. Ingest fuses pass0 histogram.
module ot_hbm_idx_selector_static #(parameter integer MUT=0)(
 input wire clk_ctl,input wire [3:0] clk_q,input wire [11:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [2367:0] in_line,
 output reg [3:0] out_v,output reg [2367:0] out_line,
 output wire [15:0] threshold_observe,
 output reg [3:0] selected_v,output reg [2367:0] selected_line,
 output wire [55:0] selected_observe,
 output reg fault
);
 localparam integer EW=37,W=16,LW=592;
 function automatic [15:0] orderkey(input [15:0] x);
  orderkey=x[15]?~x:(x^16'h8000);
 endfunction
 reg [15:0] threshold;
 reg [13:0] rank_left;
 reg found;
 reg [13:0] hist[0:3][0:63];
 reg [13:0] ties[0:3];
 wire [13:0] ntie[0:3];
 reg [13:0] selected[0:3];
 reg [3:0] qfault;
 assign threshold_observe=threshold;
 wire [15:0] prior_mask=(pass==0)?16'd0:((pass==1)?16'hf800:16'hffc0);
 wire [3:0] shift=(pass==0)?4'd11:((pass==1)?4'd6:4'd0);
 wire [15:0] binmask=(pass==2)?16'd63:16'd31;
 integer allcount,remain;
 always @(posedge clk_ctl or negedge rst_n)begin
  if(!rst_n)begin threshold<=0;rank_left<=0;found<=0;fault<=0;for(integer q=0;q<4;q=q+1)ties[q]<=0;end
  else begin
   if(|qfault)fault<=1;
   if(op==1)begin threshold<=0;rank_left<={4'b0,k};found<=0;if(k>512||k==0)fault<=1;end
   if(op==3)found<=0;
   if(op==5&&!found)begin
    allcount=0;for(integer q=0;q<4;q=q+1)allcount=allcount+int'(hist[q][addr[5:0]]);
    if(int'(rank_left)>allcount)rank_left<=rank_left-14'(allcount);
    else begin
     threshold <= (threshold & prior_mask) | (16'(addr[5:0]) << shift);found<=1;
     if(pass==2)begin
      remain=int'(rank_left);
      for(integer q=0;q<4;q=q+1)begin
       ties[q]<=14'((remain>int'(hist[q][addr[5:0]]))?int'(hist[q][addr[5:0]]):remain);
       remain=remain-int'(hist[q][addr[5:0]]);if(remain<0)remain=0;
      end
     end
    end
   end
  end
 end
 for(genvar q=0;q<4;q=q+1)begin:gq
  reg rv;reg[3:0]rop;reg[1:0]rpass;reg[7:0]raddr;
  wire re=op==4||op==6||op==8;
  wire [767:0] raw;
  reg [1183:0] buf_q;
  reg [4:0] fill;
  reg [5:0] wp;
  reg [13:0] tie_rem;
  reg comp_started;
  reg [1183:0] packed_next;
  reg [5:0] fill_next;
  reg [13:0] ties_next;
  reg [13:0] chosen_next;
  reg [15:0] mask_choose;
  reg [19:0] last_id;
  integer count;
  reg [15:0] ky;
  reg choose;
  wire compact=rv&&rop==6;
  wire emit=rv&&rop==8;
  wire pack_write=compact&&fill_next>=16;
  wire flush=op==7&&fill!=0;
  wire we=op==2||pack_write||flush;
  wire [7:0]wa=(op==2)?addr:{2'd0,wp};
  wire [591:0] wd=(op==2)?in_line[q*LW+:LW]:(pack_write?packed_next[591:0]:buf_q[591:0]);
  wire [767:0]wide_wd={176'd0,wd};
  assign selected_observe[q*14+:14]=selected[q];
  for(genvar m=0;m<3;m=m+1)begin:gm
   ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk_mem[q*3+m]),.r_ce_in(re),.r_addr_in(addr),.rd_out(raw[m*256+:256]),
    .w_ce_in(we),.w_addr_in(wa),.wd_in(wide_wd[m*256+:256]),.w_mask_in({256{1'b1}}),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
  end
  always @*begin
   packed_next=buf_q;fill_next={1'b0,fill};ties_next=comp_started?tie_rem:ties[q];chosen_next=0;mask_choose=0;
   for(integer l=0;l<W;l=l+1)begin
    ky=orderkey(raw[l*EW+1+:16]);
    choose=raw[l*EW]&&(ky>threshold||(ky==threshold&&ties_next!=0));
    if(MUT==1)choose=raw[l*EW]&&(ky>=threshold);
    if(compact&&choose)begin
     packed_next[fill_next*EW+:EW]=raw[l*EW+:EW];fill_next=fill_next+1;chosen_next=chosen_next+1;mask_choose[l]=1;
     if(ky==threshold&&ties_next!=0)ties_next=ties_next-1;
    end
   end
  end
  always @(posedge clk_q[q] or negedge rst_n)begin
   if(!rst_n)begin
    rv<=0;buf_q<=0;fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;qfault[q]<=0;out_v[q]<=0;selected_v[q]<=0;last_id<=0;
    for(integer b=0;b<64;b=b+1)hist[q][b]<=0;
   end else begin
    rv<=re;rop<=op;rpass<=pass;raddr<=addr;out_v[q]<=emit;selected_v[q]<=compact;
    for(integer l=0;l<W;l=l+1)begin selected_line[q*LW+l*EW+:EW]<=raw[l*EW+:EW];selected_line[q*LW+l*EW]<=compact&&mask_choose[l];end
    if(op==1)begin buf_q<=0;fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;last_id<=0;end
    if(op==3)for(integer b=0;b<64;b=b+1)hist[q][b]<=0;
    if((rv&&rop==4)||op==2)begin
     for(integer b=0;b<64;b=b+1)begin
      count=0;
      for(integer l=0;l<W;l=l+1)begin
       if(op==2)begin
        if(in_line[q*LW+l*EW]&&(orderkey(in_line[q*LW+l*EW+1+:16])>>11)==16'(b))count=count+1;
       end else if(raw[l*EW]&&((orderkey(raw[l*EW+1+:16])&prior_mask)==(threshold&prior_mask))&&
         ((orderkey(raw[l*EW+1+:16]) >> shift)&binmask)==16'(b))count=count+1;
      end
      hist[q][b]<=hist[q][b]+14'(count);
     end
    end
    if(compact)begin
     comp_started<=1;tie_rem<=ties_next;selected[q]<=selected[q]+chosen_next;
     if(pack_write)begin buf_q<=packed_next>>LW;fill<=5'(fill_next-16);wp<=wp+1;end
     else begin buf_q<=packed_next;fill<=5'(fill_next);end
     if(selected[q]+chosen_next>512)qfault[q]<=1;
     if(pack_write&&wa>raddr)qfault[q]<=1; // never overwrite an unread source line
     for(integer l=0;l<W;l=l+1)if(raw[l*EW])begin
      if((raddr!=0||l!=0)&&raw[l*EW+17+:20]<=last_id)qfault[q]<=1;
      last_id<=raw[l*EW+17+:20];
     end
    end
    if(flush)begin wp<=wp+1;buf_q<=0;fill<=0;end
    if(emit)begin
     for(integer l=0;l<W;l=l+1)begin
      out_line[q*LW+l*EW+:EW]<=raw[l*EW+:EW];
      out_line[q*LW+l*EW]<=((int'(raddr)*16+l)<int'(selected[q]));
      if(MUT==2&&raddr==0&&l==0)out_line[q*LW+l*EW+17+:20]<=raw[l*EW+17+:20]^20'd1;
     end
    end
    if((op==2&&(compact||flush))||(op==3&&rv&&rop==4))qfault[q]<=1;
   end
  end
 end
endmodule
`default_nettype wire
