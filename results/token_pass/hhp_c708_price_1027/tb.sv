// Directed boundary price bench: exact own/m_fault/steering logic of qkd_static_kv_pc_es_merge_b (origin/main)
// GOLD = main (own <= !ebr), DUT = c708 transform (own_pin <= !ebr; own <= own_pin). u_emb sees raw ebr in both -> identical, omitted.
module face #(parameter DUT=0) (input ck, rs_q, ebr, wes0, hes0, emb0, er0, cv, output reg own, output reg m_fault, output er_e0, output reg her0, output reg hcv);
  reg own_pin, hq0;
  always @(posedge ck or negedge rs_q) if(!rs_q) own_pin<=1; else own_pin<=!ebr;
  always @(posedge ck or negedge rs_q) if(!rs_q) own<=1; else own<= DUT ? own_pin : !ebr;
  always @(posedge ck or negedge rs_q) if(!rs_q) hq0<=0; else hq0<=hes0;
  assign er_e0 = own ? 1'b0 : er0;
  always @(posedge ck or negedge rs_q) if(!rs_q) begin m_fault<=0; her0<=0; hcv<=0; end else begin
    if (wes0 && emb0) m_fault<=1; if (hq0 && (wes0||emb0)) m_fault<=1; if (hq0 && !own) m_fault<=1; if (wes0 && own) m_fault<=1;
    her0 <= own && er0; hcv <= own && cv; end
endmodule
module tb; reg ck=0; always #5 ck=~ck; reg rs=0, ebr=0, wes=0, hes=0, emb=0, er=0, cv=0;
  wire go,gf,ge,gh,gc, do_,df,de,dh,dc;
  face #(0) g(ck,rs,ebr,wes,hes,emb,er,cv,go,gf,ge,gh,gc); face #(1) d(ck,rs,ebr,wes,hes,emb,er,cv,do_,df,de,dh,dc);
  integer dir, ev, off, t, gfault, dfault, glost, dlost;
  initial begin
    for(dir=0;dir<2;dir=dir+1) for(ev=0;ev<4;ev=ev+1) for(off=0;off<4;off=off+1) begin
      rs=0; ebr=dir?1:0; wes=0;hes=0;emb=0;er=0;cv=0; repeat(3) @(negedge ck); rs=1; repeat(4) @(negedge ck);
      ebr = dir?0:1;            // transition driven at negedge T0; first posedge seeing it = edge 0
      gfault=0;dfault=0;glost=0;dlost=0;
      for(t=0;t<8;t=t+1) begin
        wes=(ev==0&&t==off); hes=(ev==1&&t==off); er=(ev==2&&t==off); cv=(ev==3&&t==off);
        #1; if(ev==2 && t==off) begin glost = ge; dlost = de; end  // endpoint samples er_e at the coming posedge
        @(posedge ck); #1;
        if(gc) gfault=gfault+1; if(dc) dfault=dfault+1; if(gh) glost=glost+2; if(dh) dlost=dlost+2;
        @(negedge ck);
      end
      $display("%s ev=%0d off=%0d GOLD fault=%0d DUT fault=%0d | er: gold ep=%0d slice=%0d dut ep=%0d slice=%0d | cpl->slice gold=%0d dut=%0d",
        dir?"FALL":"RISE", ev, off, gf, df, glost%2, glost/2, dlost%2, dlost/2, gfault, dfault);
    end
    $finish; end
  // capture hcv pulses
  reg gseen=0,dseen=0;
endmodule
