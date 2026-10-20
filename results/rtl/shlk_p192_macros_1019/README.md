# SHLK p192 dual-clock SRAM replacement analytical masters

The private replacement masters are generated from the repository SRAM compiler, not renamed LEFs. Public defaults and predecessor views remain unchanged. Source predecessor is 7e92217f5. Reproducible generator: tools/mem_compiler/build_shlk_p192_1019.py.

| master suffix | width um | height um | area um2 | actual W/E signal contacts | minimum local pitch |
|---|---:|---:|---:|---:|---:|
| 16x257_m1_p192 | 89.448 | 76.968 | 6884.633664 | 392/391 | .192 um |
| 16x289_m1_p192 | 99.144 | 86.136 | 8539.867584 | 440/439 | .192 um |

Actual decoded signal RECT centers are at .192 um spacing, giving 5.208333 contacts/um. These values are local contact spacing, not whole-perimeter averages. Width and height are 24 mod48nm; M4 signal centers are12mod48nm and retain that phase in R0/MX/MY/R180 at lattice-compatible origins. R90 is removed. The parent must place origins on its43.2um lattice and reserve actual face-access corridors; this packet does not grant a physical gate.

Both use unchanged16-word physical arrays, width257/289, mux1, one bank, no spares, independent wclk/rclk. Source/spec/core-array equality is checked against the exact predecessor. Every behavioral byte is equal after replacing only the master name, including masked writes, initialization and fault support. There is one registered read edge and one write edge, no added data cycle. IMPORTANT: simultaneous same-address read/write is FORBIDDEN for the dual-clock generator. Its independent always blocks do not guarantee deterministic old-data on coincident clocks. Any parent requiring that behavior needs a separate implementation/contract; this packet makes no old-read claim. The original zero-initialization simulation convention remains unchanged and is not a silicon initialization guarantee.

Core dimensions remain89.3168x15.351163260579265 and98.9936x15.351163260579265um and fit inside the expanded abstracts. There is no density enhancement claim: total macro area increases1.951917/1.955858x, adding3357.520128/4173.565824um2 per instance. The extra area is pin-access perimeter, not new memory capacity. Parent must use the new areas/actual heights for band sizing and floorplan model.

Conservative M4 longest terminal-to-core lead=macro_height-core_height is priced in allTT/SS/FF tables: .38RC wire delay plus max(calibrated inv4, output-driver)R*C; CQ/setup/slew and pin/clockcap increase; min-period adds twice the delay; read/write energy includes switched added cap. Hold remains unchanged conservatively. TT CQ273.303/280.151ps; SS355.256/362.930ps; FF222.346/228.740ps. Full corner comparison is in source_and_cost_comparison.json. All timing/area/energy numbers are calibrated analytical abstracts, not transistor layout, SPICE or silicon characterization. No GDS, IR adequacy, native OBS/PG/access closure or parent timing PASS is claimed.

Fleet generation+coordinate audit ran unpinned ot-run2GB/1thread on ot-epyc8 unitoth-ubuntu-294396-1792456777, actual terminal0, log included. Failed earlier stdin-transfer run was a transport failure before generation, preserved in transfer_failure.log. No local simulation/synthesis/OpenROAD and no native gate were run. Parent behavioral benches may bind these new names because exact behavior equality was checked; no duplicate simulation is necessary to verify an unchanged body. The parent still owns clock/calendar/first-use/reset and source-owned simultaneous-address exclusion proofs.
