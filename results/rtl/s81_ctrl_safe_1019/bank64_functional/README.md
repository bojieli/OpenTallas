# Controller bank64 functional receipt

Source: `5df89681c` on `codex/s81-ctrl-bank64-1019`; default-off `S81CTRL_SRAM_BANK64` uses the real compiler-native `ot_sram_1r1w2c_32x64_m1` from `e26d92503`. Verilator 5.050 ran through unpinned ot-run on ot-epyc6, unit `oth-ubuntu-89524-1792427485`. Every shipped source file matches the local source hash inventory.

Six positive FIFO cases cover request W340/AF1 and response W277/AF2 at relative phases 0, 180 and 720 ps. Each passes 11,547 comparisons and 5,540 reads, including reset, empty/full, wrap and stalls. CURRENT-head mutant fails with 3,314 mismatches; EMPTYREAD mutant triggers an actual address collision at 9 ns. Each directory preserves build and process return codes; negative abort codes are expected.

The actual two-PC comparison passes 2,798 stream and 2,274 PHY checks: 192 accepted requests, 152 refusals, 323 reads and 206 write-done pulses. Real KRDY retry-drop, response packing and request packing mutants fail at 20.993, 21.217 and 16.897 ns. No extra FIFO read edge is added.

Two PCs require 22 banks (six request and five response banks per PC). Physical capacity is 45,056 bits for 9,872 logical bits; unused rows and bank tails are paid capacity. Raw macro area is 12,178.970496 um². This receipt does not establish a physical slot, standard-cell band fill, clock/CDC qualification, PG access, signal escape, route DRC or native timing. The existing 546-bit option and default all-flop RTL remain unchanged.
