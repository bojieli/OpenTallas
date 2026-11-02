# Current native SW / RD source seam

The exact current selected t48PG s_0S_L0 leaf, actual SRAM model and native595-bit input packet are copied unchanged from the norm lane closure. Two consecutive256-bit SW row pairs at320/322 produce four actual bank-write events and literal RDOUT n2 returns all512 bits exactly at native and public outputs, with zero faults and ready1. Flipping one real input payload bit127 makes the numerical checker fail. No arithmetic or source RTL is replaced.

Registered leafdn SW→its actual SRAM write is2 edges per pair. External595 packet→registered leafdn is3 edges. RDOUT registered leafdn CV→nativeLO is5/6, publicLO6/7 for two pairs. These named event bases are component measurements, not global packet issue dates. Bound-lane age calculations may already include the3-edge crossing; never add it twice. Source capture publication, all80 leaf profiles, actual routes, port calendars and leases remain open.

The closed source inventory is source.json; the actual test body is tools/s81_dv/final_ffn_source_1131/tb_native_rd.sv. Fleet run directory contains source.f,defines.f,source/,stage.json,closure_retry.json,run.sh and immutable positive/mutant outputs. The gate uses Verilator5.050 --binary --timing --build-jobs2 -O1, split5000/cfunc500 and C++O0, at833ps. No physical timing/G5/full-token claim.
