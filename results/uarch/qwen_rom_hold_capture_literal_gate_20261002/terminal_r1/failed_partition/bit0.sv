module qwen_hold_capture_formal(input clk,rst_n,wrom_re,input [23:0] wrom_addr,input [2659:0] payload);
reg [2659:0] rom_rd;
wire [511:0] oq,dq,eq;
wire [4:0] oc,dc,ec,o_sel,o_sel2,d_sel,d_sel2,e_sel,e_sel2;
wire [11:0] oa,da,ea;
wire os,ds,es;
wire [79:0] om,dm,em;
wire [2559:0] og,dg,eg;
qwen_current_capture_logic o(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(oq),.rom_ce(oc),.rom_addr(oa),.f_q(o_sel),.f_q2(o_sel2),.f_s(os),.f_mask(om),.f_cap(og));
qwen_optin_capture_logic d(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(dq),.rom_ce(dc),.rom_addr(da),.f_q(d_sel),.f_q2(d_sel2),.f_s(ds),.f_mask(dm),.f_cap(dg));
qwen_optin_capture_logic #(.ROM_HOLD_DIRECT_CAPTURE(1)) e(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(eq),.rom_ce(ec),.rom_addr(ea),.f_q(e_sel),.f_q2(e_sel2),.f_s(es),.f_mask(em),.f_cap(eg));
always @* if ($initstate) assume(!rst_n);
integer p,b;
always @(posedge clk) for(p=0;p<2;p=p+1) for(b=0;b<5;b=b+1)
  if(oc[b]) rom_rd[(p*5+b)*266 +:266] <= payload[(p*5+b)*266 +:266];
always @* if (!$initstate) begin
 assert(oq[0]==dq[0]);assert(oq[32]==dq[32]);assert(oq[64]==dq[64]);assert(oq[96]==dq[96]);assert(oq[128]==dq[128]);assert(oq[160]==dq[160]);assert(oq[192]==dq[192]);assert(oq[224]==dq[224]);assert(oq[256]==dq[256]);assert(oq[288]==dq[288]);assert(oq[320]==dq[320]);assert(oq[352]==dq[352]);assert(oq[384]==dq[384]);assert(oq[416]==dq[416]);assert(oq[448]==dq[448]);assert(oq[480]==dq[480]);assert(oq[0]==eq[0]);assert(oq[32]==eq[32]);assert(oq[64]==eq[64]);assert(oq[96]==eq[96]);assert(oq[128]==eq[128]);assert(oq[160]==eq[160]);assert(oq[192]==eq[192]);assert(oq[224]==eq[224]);assert(oq[256]==eq[256]);assert(oq[288]==eq[288]);assert(oq[320]==eq[320]);assert(oq[352]==eq[352]);assert(oq[384]==eq[384]);assert(oq[416]==eq[416]);assert(oq[448]==eq[448]);assert(oq[480]==eq[480]);
 assert(oc==dc);assert(oc==ec);assert(oa==da);assert(oa==ea);
 assert(o_sel==d_sel);assert(o_sel==e_sel);assert(os==ds);assert(os==es);
 assert(om==dm);assert(om==em);
end
always @* if (!$initstate) begin
 if (o_sel2[0]) begin assert(og[0]==eg[0]);assert(og[32]==eg[32]);assert(og[64]==eg[64]);assert(og[96]==eg[96]);assert(og[128]==eg[128]);assert(og[160]==eg[160]);assert(og[192]==eg[192]);assert(og[224]==eg[224]);assert(og[0]==dg[0]);assert(og[32]==dg[32]);assert(og[64]==dg[64]);assert(og[96]==dg[96]);assert(og[128]==dg[128]);assert(og[160]==dg[160]);assert(og[192]==dg[192]);assert(og[224]==dg[224]);end
 if (o_sel2[0] && !(os && o_sel[0])) assert(og[0]==rom_rd[0]);assert(og[32]==rom_rd[32]);assert(og[64]==rom_rd[64]);assert(og[96]==rom_rd[96]);assert(og[128]==rom_rd[128]);assert(og[160]==rom_rd[160]);assert(og[192]==rom_rd[192]);assert(og[224]==rom_rd[224]);
end
always @* if (!$initstate) begin
 if (o_sel2[1]) begin assert(og[256]==eg[256]);assert(og[288]==eg[288]);assert(og[320]==eg[320]);assert(og[352]==eg[352]);assert(og[384]==eg[384]);assert(og[416]==eg[416]);assert(og[448]==eg[448]);assert(og[480]==eg[480]);assert(og[256]==dg[256]);assert(og[288]==dg[288]);assert(og[320]==dg[320]);assert(og[352]==dg[352]);assert(og[384]==dg[384]);assert(og[416]==dg[416]);assert(og[448]==dg[448]);assert(og[480]==dg[480]);end
 if (o_sel2[1] && !(os && o_sel[1])) assert(og[256]==rom_rd[266]);assert(og[288]==rom_rd[298]);assert(og[320]==rom_rd[330]);assert(og[352]==rom_rd[362]);assert(og[384]==rom_rd[394]);assert(og[416]==rom_rd[426]);assert(og[448]==rom_rd[458]);assert(og[480]==rom_rd[490]);
end
always @* if (!$initstate) begin
 if (o_sel2[2]) begin assert(og[512]==eg[512]);assert(og[544]==eg[544]);assert(og[576]==eg[576]);assert(og[608]==eg[608]);assert(og[640]==eg[640]);assert(og[672]==eg[672]);assert(og[704]==eg[704]);assert(og[736]==eg[736]);assert(og[512]==dg[512]);assert(og[544]==dg[544]);assert(og[576]==dg[576]);assert(og[608]==dg[608]);assert(og[640]==dg[640]);assert(og[672]==dg[672]);assert(og[704]==dg[704]);assert(og[736]==dg[736]);end
 if (o_sel2[2] && !(os && o_sel[2])) assert(og[512]==rom_rd[532]);assert(og[544]==rom_rd[564]);assert(og[576]==rom_rd[596]);assert(og[608]==rom_rd[628]);assert(og[640]==rom_rd[660]);assert(og[672]==rom_rd[692]);assert(og[704]==rom_rd[724]);assert(og[736]==rom_rd[756]);
end
always @* if (!$initstate) begin
 if (o_sel2[3]) begin assert(og[768]==eg[768]);assert(og[800]==eg[800]);assert(og[832]==eg[832]);assert(og[864]==eg[864]);assert(og[896]==eg[896]);assert(og[928]==eg[928]);assert(og[960]==eg[960]);assert(og[992]==eg[992]);assert(og[768]==dg[768]);assert(og[800]==dg[800]);assert(og[832]==dg[832]);assert(og[864]==dg[864]);assert(og[896]==dg[896]);assert(og[928]==dg[928]);assert(og[960]==dg[960]);assert(og[992]==dg[992]);end
 if (o_sel2[3] && !(os && o_sel[3])) assert(og[768]==rom_rd[798]);assert(og[800]==rom_rd[830]);assert(og[832]==rom_rd[862]);assert(og[864]==rom_rd[894]);assert(og[896]==rom_rd[926]);assert(og[928]==rom_rd[958]);assert(og[960]==rom_rd[990]);assert(og[992]==rom_rd[1022]);
end
always @* if (!$initstate) begin
 if (o_sel2[4]) begin assert(og[1024]==eg[1024]);assert(og[1056]==eg[1056]);assert(og[1088]==eg[1088]);assert(og[1120]==eg[1120]);assert(og[1152]==eg[1152]);assert(og[1184]==eg[1184]);assert(og[1216]==eg[1216]);assert(og[1248]==eg[1248]);assert(og[1024]==dg[1024]);assert(og[1056]==dg[1056]);assert(og[1088]==dg[1088]);assert(og[1120]==dg[1120]);assert(og[1152]==dg[1152]);assert(og[1184]==dg[1184]);assert(og[1216]==dg[1216]);assert(og[1248]==dg[1248]);end
 if (o_sel2[4] && !(os && o_sel[4])) assert(og[1024]==rom_rd[1064]);assert(og[1056]==rom_rd[1096]);assert(og[1088]==rom_rd[1128]);assert(og[1120]==rom_rd[1160]);assert(og[1152]==rom_rd[1192]);assert(og[1184]==rom_rd[1224]);assert(og[1216]==rom_rd[1256]);assert(og[1248]==rom_rd[1288]);
end
always @* if (!$initstate) begin
 if (o_sel2[0]) begin assert(og[1280]==eg[1280]);assert(og[1312]==eg[1312]);assert(og[1344]==eg[1344]);assert(og[1376]==eg[1376]);assert(og[1408]==eg[1408]);assert(og[1440]==eg[1440]);assert(og[1472]==eg[1472]);assert(og[1504]==eg[1504]);assert(og[1280]==dg[1280]);assert(og[1312]==dg[1312]);assert(og[1344]==dg[1344]);assert(og[1376]==dg[1376]);assert(og[1408]==dg[1408]);assert(og[1440]==dg[1440]);assert(og[1472]==dg[1472]);assert(og[1504]==dg[1504]);end
 if (o_sel2[0] && !(os && o_sel[0])) assert(og[1280]==rom_rd[1330]);assert(og[1312]==rom_rd[1362]);assert(og[1344]==rom_rd[1394]);assert(og[1376]==rom_rd[1426]);assert(og[1408]==rom_rd[1458]);assert(og[1440]==rom_rd[1490]);assert(og[1472]==rom_rd[1522]);assert(og[1504]==rom_rd[1554]);
end
always @* if (!$initstate) begin
 if (o_sel2[1]) begin assert(og[1536]==eg[1536]);assert(og[1568]==eg[1568]);assert(og[1600]==eg[1600]);assert(og[1632]==eg[1632]);assert(og[1664]==eg[1664]);assert(og[1696]==eg[1696]);assert(og[1728]==eg[1728]);assert(og[1760]==eg[1760]);assert(og[1536]==dg[1536]);assert(og[1568]==dg[1568]);assert(og[1600]==dg[1600]);assert(og[1632]==dg[1632]);assert(og[1664]==dg[1664]);assert(og[1696]==dg[1696]);assert(og[1728]==dg[1728]);assert(og[1760]==dg[1760]);end
 if (o_sel2[1] && !(os && o_sel[1])) assert(og[1536]==rom_rd[1596]);assert(og[1568]==rom_rd[1628]);assert(og[1600]==rom_rd[1660]);assert(og[1632]==rom_rd[1692]);assert(og[1664]==rom_rd[1724]);assert(og[1696]==rom_rd[1756]);assert(og[1728]==rom_rd[1788]);assert(og[1760]==rom_rd[1820]);
end
always @* if (!$initstate) begin
 if (o_sel2[2]) begin assert(og[1792]==eg[1792]);assert(og[1824]==eg[1824]);assert(og[1856]==eg[1856]);assert(og[1888]==eg[1888]);assert(og[1920]==eg[1920]);assert(og[1952]==eg[1952]);assert(og[1984]==eg[1984]);assert(og[2016]==eg[2016]);assert(og[1792]==dg[1792]);assert(og[1824]==dg[1824]);assert(og[1856]==dg[1856]);assert(og[1888]==dg[1888]);assert(og[1920]==dg[1920]);assert(og[1952]==dg[1952]);assert(og[1984]==dg[1984]);assert(og[2016]==dg[2016]);end
 if (o_sel2[2] && !(os && o_sel[2])) assert(og[1792]==rom_rd[1862]);assert(og[1824]==rom_rd[1894]);assert(og[1856]==rom_rd[1926]);assert(og[1888]==rom_rd[1958]);assert(og[1920]==rom_rd[1990]);assert(og[1952]==rom_rd[2022]);assert(og[1984]==rom_rd[2054]);assert(og[2016]==rom_rd[2086]);
end
always @* if (!$initstate) begin
 if (o_sel2[3]) begin assert(og[2048]==eg[2048]);assert(og[2080]==eg[2080]);assert(og[2112]==eg[2112]);assert(og[2144]==eg[2144]);assert(og[2176]==eg[2176]);assert(og[2208]==eg[2208]);assert(og[2240]==eg[2240]);assert(og[2272]==eg[2272]);assert(og[2048]==dg[2048]);assert(og[2080]==dg[2080]);assert(og[2112]==dg[2112]);assert(og[2144]==dg[2144]);assert(og[2176]==dg[2176]);assert(og[2208]==dg[2208]);assert(og[2240]==dg[2240]);assert(og[2272]==dg[2272]);end
 if (o_sel2[3] && !(os && o_sel[3])) assert(og[2048]==rom_rd[2128]);assert(og[2080]==rom_rd[2160]);assert(og[2112]==rom_rd[2192]);assert(og[2144]==rom_rd[2224]);assert(og[2176]==rom_rd[2256]);assert(og[2208]==rom_rd[2288]);assert(og[2240]==rom_rd[2320]);assert(og[2272]==rom_rd[2352]);
end
always @* if (!$initstate) begin
 if (o_sel2[4]) begin assert(og[2304]==eg[2304]);assert(og[2336]==eg[2336]);assert(og[2368]==eg[2368]);assert(og[2400]==eg[2400]);assert(og[2432]==eg[2432]);assert(og[2464]==eg[2464]);assert(og[2496]==eg[2496]);assert(og[2528]==eg[2528]);assert(og[2304]==dg[2304]);assert(og[2336]==dg[2336]);assert(og[2368]==dg[2368]);assert(og[2400]==dg[2400]);assert(og[2432]==dg[2432]);assert(og[2464]==dg[2464]);assert(og[2496]==dg[2496]);assert(og[2528]==dg[2528]);end
 if (o_sel2[4] && !(os && o_sel[4])) assert(og[2304]==rom_rd[2394]);assert(og[2336]==rom_rd[2426]);assert(og[2368]==rom_rd[2458]);assert(og[2400]==rom_rd[2490]);assert(og[2432]==rom_rd[2522]);assert(og[2464]==rom_rd[2554]);assert(og[2496]==rom_rd[2586]);assert(og[2528]==rom_rd[2618]);
end
endmodule
