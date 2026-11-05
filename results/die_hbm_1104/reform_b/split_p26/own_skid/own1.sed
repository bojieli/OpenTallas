s/wire \[1023:0\] i_kr_data;$/&/
s/reg \[3:0\] i_kr_rdy;wire \[67:0\] i_kr_tag;/wire [3:0] i_kr_rdy;wire [67:0] i_kr_tag;/
s/^ reg \[3:0\] response_accepted;$/ reg [3:0] response_accepted;wire [3:0] dec_ok,dec_fire;wire [LB-1:0] dec_bank[0:3];wire [10:0] dec_ordinal[0:3];wire [15:0] dec_epoch[0:3];wire [1023:0] sk_data;/
s/\.response_take(response_accepted\[pc\])/.response_take(dec_fire[pc])/
s/\.response_ok(response_ok\[pc\]),\.response_ordinal(response_ordinal\[pc\])/.response_ok(dec_ok[pc]),.response_ordinal(dec_ordinal[pc])/
s/\.response_epoch(response_epoch\[pc\]),\.response_bank(response_bank\[pc\])/.response_epoch(dec_epoch[pc]),.response_bank(dec_bank[pc])/
/^   \.i_v(i_kr_v\[pc\]),\.i_rdy(i_kr_rdy\[pc\])/a\
  reg [256+11+16+LB-1:0] sk_m[0:1];reg sk_wp,sk_rp;reg [1:0] sk_n;\
  assign dec_fire[pc]=dec_ok[pc]&&sk_n!=(MUT==5?2'd3:2'd2);assign i_kr_rdy[pc]=dec_fire[pc];\
  assign response_ok[pc]=sk_n!=0&&!hbm_fault;\
  assign {sk_data[256*pc+:256],response_ordinal[pc],response_epoch[pc],response_bank[pc]}=sk_m[sk_rp];\
  always @(posedge hbm_pc_clk[pc])if(dec_fire[pc])sk_m[sk_wp]<={i_kr_data[256*pc+:256],dec_ordinal[pc],dec_epoch[pc],dec_bank[pc]};\
  always @(posedge hbm_pc_clk[pc] or negedge hrst)begin\
   if(!hrst)begin sk_wp<=0;sk_rp<=0;sk_n<=0;end\
   else begin if(dec_fire[pc])sk_wp<=~sk_wp;if(response_accepted[pc])sk_rp<=~sk_rp;sk_n<=sk_n+2'(dec_fire[pc])-2'(response_accepted[pc]);end\
  end
s/^  i_kr_rdy=0;bk_in_v=0;response_accepted=0;/  bk_in_v=0;response_accepted=0;/
s/^     i_kr_rdy\[p\]=1;bk_in_v\[l\]=1;/     bk_in_v[l]=1;/
s/response_epoch\[p\],i_kr_data\[256\*p+:256\]};/response_epoch[p],sk_data[256*p+:256]};/
