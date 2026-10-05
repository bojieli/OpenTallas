`timescale 1ns/1ps
// Eight finite position lists. Each independently masked 64-bit entry stores a
// SECDED35 word: block14 plus the FULL slot/entry address14. No ROM exemption.
// Aligned 1R1W macros; macro clkQ -> local capture -> 4:1 partial -> final select
// -> syndrome -> correction/identity check. Read latency SIX edges to consumer.
module ot_dsrom_reindex_list_macro (
 input wire clk, rst_n,
 input wire w_v, input wire [2:0] w_slot, input wire [10:0] w_addr,
 input wire [13:0] w_block,
 input wire active, input wire [2:0] active_slot,
 input wire r_re, input wire [2:0] r_slot, input wire [9:0] r_pair,
 input wire [1:0] r_mask,
 output reg [13:0] r_even, r_odd,
 output reg r_valid, output reg [1:0] corrected,
 output reg fault,
 output wire [11:0] active_count,
 output wire writer_pending
);
 function automatic [34:0] encode(input [27:0] data);
  reg [34:0] word; integer p,k,j; reg parity;
  begin
   word=0;j=0;
   for(p=1;p<=34;p=p+1) if((p&(p-1))!=0)begin word[p-1]=data[j];j=j+1;end
   for(k=0;k<6;k=k+1)begin
    parity=0;for(p=1;p<=34;p=p+1) if((p&(1<<k))!=0)parity=parity^word[p-1];
    word[(1<<k)-1]=parity;
   end
   word[34]=^word[33:0];encode=word;
  end
 endfunction
 function automatic [5:0] syndrome(input [34:0] word);
  reg [5:0] s;integer p,k;
  begin
   s=0;for(k=0;k<6;k=k+1)for(p=1;p<=34;p=p+1)if((p&(1<<k))!=0)s[k]=s[k]^word[p-1];
   syndrome=s;
  end
 endfunction
 function automatic [27:0] unpack_word(input [34:0] word);
  reg [27:0] d;integer p,j;
  begin d=0;j=0;for(p=1;p<=34;p=p+1)if((p&(p-1))!=0)begin d[j]=word[p-1];j=j+1;end unpack_word=d;end
 endfunction
 // Protected prefix counts distinguish unwritten storage from valid entries.
 // 'seen' counts accepted writes, 'committed' advances ONLY on actual macro write.
 reg [11:0] seen[0:7], seen_n[0:7], committed[0:7], committed_n[0:7];
 reg wr,wr_n;reg [2:0] ws;reg [10:0] wa;reg [34:0] wd;
 wire prefix_ok=(seen[w_slot]==~seen_n[w_slot])&&(committed[w_slot]==~committed_n[w_slot]);
 wire w_ok=prefix_ok&&!(active&&w_slot==active_slot)&&
           ((w_addr==0)||(12'(w_addr)==seen[w_slot]));
 assign active_count=committed[active_slot];
 assign writer_pending=wr||!wr_n;
 wire [3:0] rb={r_slot,r_pair[9]};
 wire [3:0] wb={ws,wa[10]};
 wire [127:0] macro_q[0:15];
 wire [127:0] write_word=wa[0]?{29'd0,wd,64'd0}:{64'd0,29'd0,wd};
 wire [127:0] write_mask=wa[0]?{64'hffffffffffffffff,64'd0}:{64'd0,64'hffffffffffffffff};
 wire rp_good=(committed[r_slot]==~committed_n[r_slot])&&
              (!r_mask[0]||({1'b0,r_pair,1'b0}<committed[r_slot]))&&
              (!r_mask[1]||({1'b0,r_pair,1'b1}<committed[r_slot]));
 genvar b;
 generate for(b=0;b<16;b=b+1)begin:g_b
  ot_sram_1r1w_512x128_m4_r2c2 u_macro(
   .clk(clk),.r_ce_in(r_re&&rp_good&&!fault&&(rb==b)),.r_addr_in(r_pair[8:0]),.rd_out(macro_q[b]),
   .w_ce_in(wr&&!wr_n&&!fault&&(wb==b)),.w_addr_in(wa[9:1]),.wd_in(write_word),.w_mask_in(write_mask),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
 end endgenerate
 reg [69:0] capture[0:15],partial[0:3],joined,checked_word;
 reg [5:0] se,so;reg pe,po;
 reg [4:0] valid_pipe,valid_n;
 reg [3:0] bank_pipe[0:2],bank_n[0:2];
 reg [13:0] echo[0:4],echo_n[0:4];
 reg [1:0] masks[0:4],masks_n[0:4];
 integer i;
 reg [34:0] fe,fo;reg [27:0] de,doo;reg ue,uo,good;
 always @* begin
  ue=((se!=0)&&!pe)||(pe&&(se>34));uo=((so!=0)&&!po)||(po&&(so>34));
  fe=checked_word[34:0];fo=checked_word[69:35];
  if(pe&&!ue)begin if(se==0)fe[34]=~fe[34];else fe[se-1]=~fe[se-1];end
  if(po&&!uo)begin if(so==0)fo[34]=~fo[34];else fo[so-1]=~fo[so-1];end
  de=unpack_word(fe);doo=unpack_word(fo);
  good=(echo[4]==~echo_n[4])&&(masks[4]==~masks_n[4])&&
       (!masks[4][0]||(!ue&&de[27:14]==echo[4]))&&
       (!masks[4][1]||(!uo&&doo[27:14]==(echo[4]|14'd1)));
 end
 always @(posedge clk)begin
  if(!rst_n)begin
   wr<=0;wr_n<=1;fault<=0;valid_pipe<=0;valid_n<=5'b11111;r_valid<=0;corrected<=0;
   for(i=0;i<8;i=i+1)begin seen[i]<=0;seen_n[i]<=12'hfff;committed[i]<=0;committed_n[i]<=12'hfff;end
  end else begin
   wr<=w_v&&w_ok&&!fault;wr_n<=!(w_v&&w_ok&&!fault);
   if(wr==wr_n||valid_pipe!=~valid_n)fault<=1;
   if(w_v&&!w_ok)fault<=1;
   if(w_v&&w_ok&&!fault)begin
    ws<=w_slot;wa<=w_addr;wd<=encode({w_slot,w_addr,w_block});
    seen[w_slot]<=12'(w_addr)+1'b1;seen_n[w_slot]<=~(12'(w_addr)+1'b1);
   end
   if(wr&&!fault)begin committed[ws]<=12'(wa)+1'b1;committed_n[ws]<=~(12'(wa)+1'b1);end
   if(r_re&&!rp_good)fault<=1;
   valid_pipe<={valid_pipe[3:0],r_re&&rp_good&&!fault};
   valid_n<={valid_n[3:0],!(r_re&&rp_good&&!fault)};
   echo[0]<={r_slot,r_pair,1'b0};echo_n[0]<=~{r_slot,r_pair,1'b0};
   masks[0]<=r_mask;masks_n[0]<=~r_mask;
   bank_pipe[0]<=rb;bank_n[0]<=~rb;
   for(i=1;i<5;i=i+1)begin
    echo[i]<=echo[i-1];echo_n[i]<=echo_n[i-1];masks[i]<=masks[i-1];masks_n[i]<=masks_n[i-1];
   end
   for(i=1;i<3;i=i+1)begin bank_pipe[i]<=bank_pipe[i-1];bank_n[i]<=bank_n[i-1];end
   for(i=0;i<16;i=i+1)capture[i]<={macro_q[i][98:64],macro_q[i][34:0]};
   for(i=0;i<4;i=i+1)partial[i]<=capture[4*i+bank_pipe[1][1:0]];
   joined<=partial[bank_pipe[2][3:2]];
   checked_word<=joined;se<=syndrome(joined[34:0]);so<=syndrome(joined[69:35]);pe<=^joined[34:0];po<=^joined[69:35];
   r_valid<=valid_pipe[4]&&(valid_pipe==~valid_n)&&good&&!fault;
   corrected<=valid_pipe[4]&&good&&!fault?{po&&masks[4][1],pe&&masks[4][0]}:2'd0;
   if(valid_pipe[4]&&!good)fault<=1;
   if((valid_pipe[1]&&(bank_pipe[1]!=~bank_n[1]))||(valid_pipe[2]&&(bank_pipe[2]!=~bank_n[2])))fault<=1;
   if(valid_pipe[4]&&good&&!fault)begin r_even<=de[13:0];r_odd<=doo[13:0];end
  end
 end
endmodule
