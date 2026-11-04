`timescale 1ns/1ps
// Controller PROFILE0 reservation pin -> raw PHY and corrected-return pins.
// Source 3221e4f5e: two reservation captures (parent, scheduler), scheduler
// column output register, physical PO register; licensed raw HBM RL23;
// physical PI capture, pcport KV capture, landing ECC P0/P1/correct = five.
// Fixed slots advance even when the actual PHY or ECC result is missing.
// Epoch metadata belongs to the reservation, never to the later current CMD.
// Physical route stages/clock phase are separate compiler inputs. This module
// does not schedule the RD reservation, refresh or source command producer.
module qkd_static_kv_return_calendar #(
 parameter integer CORE_CLOCK=0,
 parameter integer PHYSICAL_CMD_EDGES=4, HBM_RL=CORE_CLOCK ? ((23*1024+832)/833) : 23, CORRECTED_EDGES=5
)(
 input wire pll_hbm,hrst,
 input wire reserved_rd,reserved_static_read,
 input wire [15:0] reservation_epoch,
 output wire expected_raw_valid,compiled_hbm_put,
 output wire [15:0] expected_return_epoch
);
 localparam integer RAW=PHYSICAL_CMD_EDGES+HBM_RL;
 localparam integer CORRECTED=RAW+CORRECTED_EDGES;
 initial if(RAW<1 || CORRECTED<=RAW)$error("invalid physical return calendar");
 reg [CORRECTED-1:0] slots;
 reg [RAW-1:0] raw_slots;
 reg [15:0] epochs[0:CORRECTED-1];
 integer i;
 always @(posedge pll_hbm or negedge hrst)
  if(!hrst)begin slots<=0;raw_slots<=0;end
  else begin
   slots<={slots[CORRECTED-2:0],reserved_rd};
   raw_slots<={raw_slots[RAW-2:0],reserved_rd|reserved_static_read};
  end
 always @(posedge pll_hbm)begin
  epochs[0]<=reservation_epoch;
  for(i=1;i<CORRECTED;i=i+1)epochs[i]<=epochs[i-1];
 end
 assign expected_raw_valid=raw_slots[RAW-1];
 assign compiled_hbm_put=slots[CORRECTED-1];
 assign expected_return_epoch=epochs[CORRECTED-1];
endmodule
