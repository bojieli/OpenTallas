`timescale 1ns/1ps
// Allowed hard PLL analog model, not a digital reset controller. Periods match
// the real native HOST family fixture (host_owner.hpp) and HBM controller gate.
// Host-owned reset sequencing consumes locked and actual link/boot receipts.
module qkd_pll_analog_model #(
 parameter real CORE_HALF=0.416667,HBM_HALF=0.512,
 parameter real HOST_HALF=0.500,ING_HALF=0.833334,PHY_HALF=0.521500,
 parameter integer LOCK_REF_EDGES=8
)(input wire refclk,por_n,
 output wire pll_WS,pll_WN,pll_ES,pll_EN,pll_c,pll_fwd,
 output wire pll_hbm_WS,pll_hbm_WN,pll_hbm_ES,pll_hbm_EN,
 output wire pll_host,pll_ingest,pll_phy,output reg locked);
 reg core=0,hbm=0,host=0,ingest=0,phy=0;integer refs=0;
 initial locked=0;
 always @(posedge refclk or negedge por_n)
  if(!por_n)begin refs<=0;locked<=0;end
  else if(!locked)begin if(refs==LOCK_REF_EDGES-1)locked<=1;else refs<=refs+1;end
 always #(CORE_HALF)core=por_n?~core:1'b0;
 always #(HBM_HALF)hbm=por_n?~hbm:1'b0;
 always #(HOST_HALF)host=por_n?~host:1'b0;
 always #(ING_HALF)ingest=por_n?~ingest:1'b0;
 always #(PHY_HALF)phy=por_n?~phy:1'b0;
 assign pll_WS=core,pll_WN=core,pll_ES=core,pll_EN=core,pll_c=core,pll_fwd=core;
 assign pll_hbm_WS=hbm,pll_hbm_WN=hbm,pll_hbm_ES=hbm,pll_hbm_EN=hbm;
 assign pll_host=host,pll_ingest=ingest,pll_phy=phy;
endmodule
