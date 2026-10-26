`timescale 1ns/1ps
// TOKj-KV 10-23: bench copy of the die's ANALOG PLL model (hub_C u_pll; the as-built qkd_pll_analog_model is itself a
// behavioural model of an analog macro, not RTL).  Same ports and the same lock law (locked LOCK_REF_EDGES refclk edges
// after por_n); the free-running pll_* clock outputs are driven 0 here because the bound top takes every functional clock
// from its top clock ports (bind.py clock_roles; the pll_* outputs of u_pll have no reader in the bound hub_C), which lets
// the partition be verilated as a hierarchical block without timing delays.
module qkd_pll_analog_model #(
 parameter real CORE_HALF=0.416667,HBM_HALF=0.512,
 parameter real HOST_HALF=0.500,ING_HALF=0.833334,PHY_HALF=0.521500,
 parameter integer LOCK_REF_EDGES=8
)(input wire refclk,por_n,
 output wire pll_WS,pll_WN,pll_ES,pll_EN,pll_c,pll_fwd,
 output wire pll_hbm_WS,pll_hbm_WN,pll_hbm_ES,pll_hbm_EN,
 output wire pll_host,pll_ingest,pll_phy,output reg locked);
 integer refs;
 always @(posedge refclk or negedge por_n)
  if(!por_n)begin refs<=0;locked<=0;end
  else if(!locked)begin if(refs==LOCK_REF_EDGES-1)locked<=1;else refs<=refs+1;end
 assign {pll_WS,pll_WN,pll_ES,pll_EN,pll_c,pll_fwd,pll_hbm_WS,pll_hbm_WN,pll_hbm_ES,pll_hbm_EN,pll_host,pll_ingest,pll_phy}=13'd0;
endmodule
