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
 assert(oq==dq);assert(oq==eq);
 assert(oc==dc);assert(oc==ec);assert(oa==da);assert(oa==ea);
 assert(o_sel==d_sel);assert(o_sel==e_sel);assert(os==ds);assert(os==es);
 assert(om==dm);assert(om==em);
end
always @* if (!$initstate) begin
 if (o_sel2[0]) begin assert(og[0+:256]==eg[0+:256]);assert(og[0+:256]==dg[0+:256]);end
 if (o_sel2[0] && !(os && o_sel[0])) assert(og[0+:256]==rom_rd[0+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[1]) begin assert(og[256+:256]==eg[256+:256]);assert(og[256+:256]==dg[256+:256]);end
 if (o_sel2[1] && !(os && o_sel[1])) assert(og[256+:256]==rom_rd[266+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[2]) begin assert(og[512+:256]==eg[512+:256]);assert(og[512+:256]==dg[512+:256]);end
 if (o_sel2[2] && !(os && o_sel[2])) assert(og[512+:256]==rom_rd[532+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[3]) begin assert(og[768+:256]==eg[768+:256]);assert(og[768+:256]==dg[768+:256]);end
 if (o_sel2[3] && !(os && o_sel[3])) assert(og[768+:256]==rom_rd[798+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[4]) begin assert(og[1024+:256]==eg[1024+:256]);assert(og[1024+:256]==dg[1024+:256]);end
 if (o_sel2[4] && !(os && o_sel[4])) assert(og[1024+:256]==rom_rd[1064+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[0]) begin assert(og[1280+:256]==eg[1280+:256]);assert(og[1280+:256]==dg[1280+:256]);end
 if (o_sel2[0] && !(os && o_sel[0])) assert(og[1280+:256]==rom_rd[1330+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[1]) begin assert(og[1536+:256]==eg[1536+:256]);assert(og[1536+:256]==dg[1536+:256]);end
 if (o_sel2[1] && !(os && o_sel[1])) assert(og[1536+:256]==rom_rd[1596+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[2]) begin assert(og[1792+:256]==eg[1792+:256]);assert(og[1792+:256]==dg[1792+:256]);end
 if (o_sel2[2] && !(os && o_sel[2])) assert(og[1792+:256]==rom_rd[1862+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[3]) begin assert(og[2048+:256]==eg[2048+:256]);assert(og[2048+:256]==dg[2048+:256]);end
 if (o_sel2[3] && !(os && o_sel[3])) assert(og[2048+:256]==rom_rd[2128+:256]);
end
always @* if (!$initstate) begin
 if (o_sel2[4]) begin assert(og[2304+:256]==eg[2304+:256]);assert(og[2304+:256]==dg[2304+:256]);end
 if (o_sel2[4] && !(os && o_sel[4])) assert(og[2304+:256]==rom_rd[2394+:256]);
end
endmodule
