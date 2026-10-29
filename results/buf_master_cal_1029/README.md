# BTAB clock buffer calibration

Adds measured `spice_cell` factors for BUFx10, BUFx12, BUFx12f and BUFx16f to the shared clock model. BUFx8 comes from the previously measured HEAD START row on main. These five masters had prevented BTAB F3b/F3r from using their required calibration mode.

Each new master has a 20-stage extracted-cell chain at 2 um and 60 um of 1x clock-layer RC per stage, with taps at stages 5 and 20. The same netlist and RC ladder run in OpenSTA and ngspice, at TT and FF, for rising and falling source edges. Per-master late factors round the largest measured spice/STA-late ratio upward; early factors round the smallest spice/STA-early ratio downward. This follows the existing MODEL-REFIT-2 method. These are bounds on the measured reference cases; the current routed BTAB timing still decides its band and sign-off.

The extracted CDL BUFx16f header orders its ports `A VSS VDD Y`; the other buffer headers use `VSS VDD A Y`. The deck generator now preserves that per-master order. Named Verilog pins remain the same. A focused test catches a reverted supply/input ordering. The generator produces all 84 files of the 12 previous reference cases byte for byte unchanged.

Run: `intel2:/srv/opentallas-scratch2/claude/codex-buf-cal-intel-0827`, ot-run unit `oth-ubuntu-2001498-1793287678`, script `run.sh`. Source decks and waveforms remain there. `raw.json` contains the measured arrivals; the golden stores deck hashes and the resulting ratios. Initial EPYC runs failed with an illegal instruction in the inherited OSDI library and were retained under `epyc2:/srv/opentallas-scratch2/claude/codex-buf-cal-0827`; the successful run uses the existing Intel OSDI library on an Intel host.

Results: 16 TT/FF simulation pairs completed with exit 0; 64 new arrival rows. All 272 golden rows satisfy measured late >= spice >= measured early after the bounding calibration, with zero bound violations; every previous mode/row ratio remains exactly unchanged. The focused cell calibration and model correlation suites pass 39 tests. No RTL, clock period, uncertainty, or default calibration mode changes.
