# CB cb_rw10is

HBM-ELEM13/HC 10-21 SRAM-island clock spine (tools/hbm_hc_clock_1021/hc_island_spine.tcl): roots whose real sinks straddle an SRAM column (E2 replay 3b4b14119 d2 130.2; B0 w1 795 west/240 east 147729d92, east late 70 ps from extra trunk path repeaters) get one local subtree per island, equal buffer depth, fork at the x-midpoint between islands outside every macro. MAIN: all glue roots rebuilt; fork outside macros at island x-midpoint (equal trunks). Same outline/children/pins/roots/RTL/edges; no SDC/RC/Lib change; 0 cycles.

SAFE8: 1 pins unchanged; 2 reach unchanged (path repeaters every 150 um); 3 fanout native32 (gate census); 4 depth unchanged; 5 storage SRAM columns on lattice unchanged; 6 floorplan unchanged outline; 7 clock: local subtree per SRAM-separated island, equal depth, equal-length trunks, per-root spread target <=80 TT+FF; 8 reset unchanged landed.
