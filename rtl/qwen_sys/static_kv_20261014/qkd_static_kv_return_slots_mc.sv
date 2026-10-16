// Explicit multi-root successor. Original module remains unchanged.
`timescale 1ns/1ps
// New static return master. Both ring addresses advance on compiler slots,
// including failed slots. Publication/consumption are fault checks only.
// compiled_hbm_put must come from the real controller read calendar, including
// RL/ECC/return stages; it must NEVER be derived from controller_co[0].
// This candidate is not native-qualified until its source calendar/phase and
// physical homes are joined. Historical qkd_static_kv_return_cdc is unchanged.
module qkd_static_kv_return_slots_mc #(parameter integer DEPTH=8)(
 input wire pll_hbm,hrst,ck,rsi,
 input wire [3:0] pll_hbm_data,
 input wire [293:0] controller_co,input wire [15:0] controller_epoch,
 input wire compiled_hbm_put,
 input wire expected_put,input wire [9:0] expected_sector,
 input wire [15:0] expected_epoch,input wire [5:0] expected_layer,
 output reg actual_valid,output reg [9:0] actual_sector,
 output reg [15:0] actual_epoch,output reg [5:0] actual_layer,
 output reg [255:0] actual_data,output reg fault_hbm,output reg fault_core,
 output reg idle_hbm,output reg idle_core
);
 localparam integer AW=$clog2(DEPTH);
 initial if(DEPTH<4 || (DEPTH&(DEPTH-1))!=0)$error("static return depth must be power of two >=4");
 (* keep *)reg hr,rs;
 always @(posedge pll_hbm)hr<=hrst;
 always @(posedge ck)rs<=rsi;
 (* keep *)reg observed,write_slot;
 (* keep *)reg [287:0] hd;
 always @(posedge pll_hbm)hd<={controller_epoch,controller_co[17:12],controller_co[11:9],controller_co[7:1],controller_co[281:26]};
 always @(posedge pll_hbm or negedge hr)
  if(!hr)begin observed<=0;write_slot<=0;end
  else begin observed<=controller_co[0];write_slot<=compiled_hbm_put;end
 (* keep *)reg slot;
 (* keep *)reg [31:0] meta;
 always @(posedge ck)meta<={expected_epoch,expected_layer,expected_sector};
 always @(posedge ck or negedge rs)if(!rs)slot<=0;else slot<=expected_put;
 wire [287:0] read_data;
 reg [DEPTH-1:0] published,consumed,observed_valid;
 (* async_reg="true" *)reg [DEPTH-1:0] pub_sync1,pub_sync2,done_sync1,done_sync2;
 // Local-domain drain observations, not a ready or scheduling interface.
 // Both exports plus upstream controller/front quiet are required at the parent.
 // Core publication synchronizers can lag a new HBM write; idle_core alone
 // therefore cannot establish whole-ring or whole-KV drained.
 // mc_r3b (Q-ELEM 10-16): idle_hbm no longer looks at the raw controller_co[0] / compiled_hbm_put pins (the r3
 // route failed CTS hold/setup on that pin -> compare -> idle_hbm cone: setup -527 ps / hold -90 ps); registered pin
 // captures only (drain observation only; no schedule uses it).
 // mc_r3c (Q-ELEM-RING 10-16): the r3b form (P && !observed && !write_slot && !obs_d && !ws_d) used the CURRENT
 // occupancy term with the pin terms of the two previous edges, so it missed the put arriving at the pin on the edge
 // itself (one-cycle early assertion vs the reference; tb_static_return_idle_mc caught it). Now exactly the original
 // observation one pll_hbm edge later: idle_hbm_pre holds edge e's registered terms, edge e+1 ANDs in observed /
 // write_slot, which then hold the pin values of edge e.
 (* keep *)reg idle_hbm_pre;
 always @(posedge pll_hbm or negedge hr)
  if(!hr)begin idle_hbm<=0;idle_hbm_pre<=0;end
  else begin
   idle_hbm_pre<=(published==done_sync2) && !observed && !write_slot;
   idle_hbm<=idle_hbm_pre && !observed && !write_slot;
  end
 // mc_r3c (Q-ELEM-RING 10-16): idle_core no longer looks at the raw expected_put pin. mc3b-d4c0e5fee native audit:
 // capture 259.3 ps on expected_put (budget 190), measured cone expected_put -> INV -> AND5 -> AND4 -> idle_core flop
 // ~330 um away at the N face (250 ps of logic+wire), while the slot capture flop sits at the pin. Now expected_put
 // drives the slot flop only. idle_core = the original observation one ck edge later, never earlier: idle_core_pre
 // holds the registered terms of edge e (pub_sync2==consumed, slot, actual_valid) and edge e+1 ANDs in slot, which
 // then holds the expected_put pin value of edge e. Drain observation only; no schedule uses it (+1 ck edge).
 (* keep *)reg idle_core_pre;
 always @(posedge ck or negedge rs)
  if(!rs)begin idle_core<=0;idle_core_pre<=0;end
  else begin
   idle_core_pre<=(pub_sync2==consumed) && !slot && !actual_valid;
   idle_core<=idle_core_pre && !slot;
  end
 reg [AW:0] wp,rp;
 wire [AW-1:0] wa=wp[AW-1:0];
`ifdef OT_KV_RETURN_MUT_READ_ADDR
 wire [AW-1:0] ra=rp[AW-1:0]+1'b1;
`else
 wire [AW-1:0] ra=rp[AW-1:0];
`endif
 always @(posedge pll_hbm or negedge hr)
  if(!hr)begin wp<=0;published<=0;observed_valid<=0;done_sync1<=0;done_sync2<=0;fault_hbm<=0;end
  else begin
   done_sync1<=consumed;done_sync2<=done_sync1;
   if(observed !== write_slot)fault_hbm<=1;
   if(write_slot)begin
    published[wa]<=~wp[AW];observed_valid[wa]<=observed;
    wp<=wp+1'b1;
    if(done_sync2[wa] !== wp[AW])fault_hbm<=1;
   end
  end
 // Storage roots are independent die clock entries with exactly the same
 // frequency/phase as pll_hbm. Every fixed 72-bit slice has <= DEPTH*72 sinks.
 genvar bank;
 generate for(bank=0;bank<4;bank=bank+1)begin:g_storage
  reg [71:0] bank_data[0:DEPTH-1];
  // mc_r3b: the 64:1 read mux select is a per-18-bit pointer copy (4 per bank, 16 total), not the one rp
  // (mc3b gate: rp[1] drove 18,407 mux loads). Each copy advances on slot exactly as rp (keep_hierarchy).
  genvar q;
  for(q=0;q<4;q=q+1)begin:g_rq
   wire [AW-1:0] rq;
   (* keep_hierarchy *) qkd_ksr_mc_rp #(.AW(AW),
`ifdef OT_KV_RETURN_MUT_READ_ADDR
    .INIT(1)
`else
    .INIT(0)
`endif
   ) u_rq(.clk(ck),.rst_n(rs),.adv(slot),.q(rq));
   assign read_data[bank*72+q*18+:18]=bank_data[rq][q*18+:18];
  end
  always @(posedge pll_hbm_data[bank])
   if(hr && write_slot)bank_data[wa]<=hd[bank*72+:72];
 end endgenerate
 always @(posedge ck or negedge rs)
  if(!rs)begin rp<=0;consumed<=0;pub_sync1<=0;pub_sync2<=0;actual_valid<=0;fault_core<=0;end
  else begin
   pub_sync1<=published;pub_sync2<=pub_sync1;
   actual_valid<=slot;
   if(slot)begin
    actual_data<=read_data[255:0];actual_sector<=read_data[265:256];
    actual_layer<=read_data[271:266];actual_epoch<=read_data[287:272];
    consumed[ra]<=~rp[AW];rp<=rp+1'b1;
    if(pub_sync2[ra] !== ~rp[AW] || observed_valid[ra] !== 1'b1 || read_data[287:256] !== meta)fault_core<=1;
   end
  end
endmodule

// read-pointer copy of the static return ring: advances on slot exactly as the ring's rp (keep_hierarchy: never merged)
module qkd_ksr_mc_rp #(parameter integer AW=6, parameter integer INIT=0)(input wire clk,input wire rst_n,input wire adv,
                                                                       output reg [AW-1:0] q);
 localparam [AW-1:0] C_INIT=INIT;
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=C_INIT;else if(adv)q<=q+1'b1;
endmodule
