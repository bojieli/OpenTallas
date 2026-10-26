WR_HALF_CYCLE exploratory candidate, opt-in default OFF (root approved exploration 2026-10-25).
Keeps each existing rising write staging register and inserts a falling-edge landing register directly before SRAM write data/address/enable.
The falling register samples the rising stage after its update; the SRAM consumes it on the SAME next rising edge as baseline.
Adds0 production/boot/write-consumption cycles. +1056 falling FF BTAB/+950 PROG, in addition to ROW_WRITE_RELAY+24/+27 rising FF.
Reads/fault/reset semantics unchanged. tb_half.sv checks outputs/fault plus SRAM consumed WE/WA/WD at each actual rising edge.
20000 cycles with reset bursts and directed write/read collisions:0 mismatches; rising-edge-instead-of-falling mutant caught consumed-enable atcycle17.
Current physical blocker: existing mscts_band root-net discovery rejects clockinverters; negative-edge mapped flops need explicit regional clock inversion after each tap and phase-aware timing reports.
No phase physical adoption or closure claim, no CTS/route started. Standard833 TTsetup/FFhold60/25 remains; both416.5ps halfcycles must close without exceptions.
