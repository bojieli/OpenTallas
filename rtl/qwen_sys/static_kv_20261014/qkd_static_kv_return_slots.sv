`timescale 1ns/1ps
// New static return master. Both ring addresses advance on compiler slots,
// including failed slots. Publication/consumption are fault checks only.
// compiled_hbm_put must come from the real controller read calendar, including
// RL/ECC/return stages; it must NEVER be derived from controller_co[0].
// This candidate is not native-qualified until its source calendar/phase and
// physical homes are joined. Historical qkd_static_kv_return_cdc is unchanged.
module qkd_static_kv_return_slots #(parameter integer DEPTH=8)(
 input wire pll_hbm,hrst,ck,rsi,
 input wire [293:0] controller_co,input wire [15:0] controller_epoch,
 input wire compiled_hbm_put,
 input wire expected_put,input wire [9:0] expected_sector,
 input wire [15:0] expected_epoch,input wire [5:0] expected_layer,
 output reg actual_valid,output reg [9:0] actual_sector,
 output reg [15:0] actual_epoch,output reg [5:0] actual_layer,
 output reg [255:0] actual_data,output reg fault_hbm,output reg fault_core
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
 reg [287:0] data[0:DEPTH-1];
 reg [DEPTH-1:0] published,consumed,observed_valid;
 (* async_reg="true" *)reg [DEPTH-1:0] pub_sync1,pub_sync2,done_sync1,done_sync2;
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
    data[wa]<=hd;published[wa]<=~wp[AW];observed_valid[wa]<=observed;
    wp<=wp+1'b1;
    if(done_sync2[wa] !== wp[AW])fault_hbm<=1;
   end
  end
 always @(posedge ck or negedge rs)
  if(!rs)begin rp<=0;consumed<=0;pub_sync1<=0;pub_sync2<=0;actual_valid<=0;fault_core<=0;end
  else begin
   pub_sync1<=published;pub_sync2<=pub_sync1;
   actual_valid<=slot;
   if(slot)begin
    actual_data<=data[ra][255:0];actual_sector<=data[ra][265:256];
    actual_layer<=data[ra][271:266];actual_epoch<=data[ra][287:272];
    consumed[ra]<=~rp[AW];rp<=rp+1'b1;
    if(pub_sync2[ra] !== ~rp[AW] || observed_valid[ra] !== 1'b1 || data[ra][287:256] !== meta)fault_core<=1;
   end
  end
endmodule
