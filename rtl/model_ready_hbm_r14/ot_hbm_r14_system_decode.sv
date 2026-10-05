`timescale 1ps/1fs
// Optional flattenedSYSTEM sector namespace ONLY. Actual Qwen metadata already
// supplies die/stack/local and does not pass through this decoder. System
// contiguous bursts crossing4sector stripes require addressed perstack requests.
module ot_hbm_r14_system_decode(
 input wire [33:0] system_sector,output wire die,output wire [1:0] stack,
 output wire [30:0] local_sector,output wire legal,output wire [33:0] reconstructed);
 assign die=system_sector[33];assign stack=system_sector[3:2];
 assign local_sector={system_sector[32:4],system_sector[1:0]};
 assign reconstructed={die,local_sector[30:2],stack,local_sector[1:0]};
 assign legal=local_sector<31'd703125000;
endmodule
