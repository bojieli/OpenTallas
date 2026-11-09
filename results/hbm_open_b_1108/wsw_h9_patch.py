import sys
f=sys.argv[1]
t=open(f).read()
old="""     if(ordinal+s<total[fill_bank])begin
      if(!wc_l[33*s+32]||wc_l[33*s+:32]!=(base[fill_bank]+ordinal+s))stream_sticky<=1;
     end else if(wc_l[33*s+32])stream_sticky<=1;"""
new="""     if(ordinal+s<total[fill_bank])begin
      if(!wc_l[33*s+32]||(fill_bank?wc_bad1[s]:wc_bad0[s]))stream_sticky<=1;
     end else if(wc_l[33*s+32])stream_sticky<=1;"""
assert t.count(old)==1
t=t.replace(old,new)
anchor=" reg fill_done,done_v,done_bank;reg [15:0] done_epoch;reg [11:0] done_sectors;\n integer s;\n"
assert t.count(anchor)==1
add=(" // HBM-OPEN-B 11-08 H9 (H8+ECO routed TT -7.19/1 at stream_sticky: fill_bank -> base[] mux -> 32-bit add -> compare): the two per-bank\n"
     " // expected addresses are compared before the fill_bank select, so the bank mux is a late 2:1 on one bit. Same function, combinational.\n"
     " wire [7:0] wc_bad0,wc_bad1;genvar gws;\n"
     " generate for(gws=0;gws<8;gws=gws+1)begin:g_wc_cmp\n"
     "  assign wc_bad0[gws]=wc_l[33*gws+:32]!=(base[0]+ordinal+gws);\n"
     "  assign wc_bad1[gws]=wc_l[33*gws+:32]!=(base[1]+ordinal+gws);\n"
     " end endgenerate\n")
open(f,'w').write(t.replace(anchor,add+anchor))
