# SYS_SD secondary PHY clock: structural candidate, not a physical result

This candidate keeps the existing outline, PG region and external clock pins. It moves the RX capture/FIFO and TX FIFO/output groups beside the PHY's actual E-face RX/TX pins. No RTL or functional cycle changes are proposed. SD's RX output is also on E; there is no extra RX-to-S hop or proposed two-cycle charge.

Proposed full-cone group regions use the existing free E strip x=1883.52..1896.48 µm: TX about y=17.28..418 and RX y=480.06..966. The initial 190-µm-high sequential-only packing was rejected when the mapped anonymous mux logic was counted. Actual complete cone area is RX 3492.829 µm² and TX 2880.716 µm²; 1027 planned BUFx24 clock drivers add 449.210 µm². The combined geometric area budget is near 60% utilization, before row/PG/legal-site qualification; it is not a floorplan PASS.

Actual DFF widths are 1.08/1.134 µm (control FFs 1.404), height .27, site .054. PHY-clock bit FFs use x=1883.574+slot*1.188, TX y=17.28+.27*(2*bit+floor(5*bit/6)), and RX y=480.06+.27*(3*bit+floor(4*bit/9)); logic and primary-clock FIFO members need the whole mapped-cone regions above. Primary-clock FIFO placement/capacity also needs review. This is not permission to move only the PHY-clock capture flops.

The clock topology uses eight-level TX/RX FF trees, a shared E-rim root, shortest Manhattan edges with the minimum repeaters to keep segments <=150 µm, and a separate actual 50 fF macro-clock leaf. The planner considers existing ancestors for that leaf and selects by joint TT/FF endpoint error. It adds no delay pads or wire meanders. Clock-driver x positions are inside the free strip with actual BUFx24 width 1.62; Y legalization and occupied-site checks have not run. Earlier exploratory variants that put drivers at every wire bend were rejected: a wire bend does not require a clock driver.

`data_local_clock_estimate.json` is the current candidate and covers all 5,260 selected-root sinks and all 40,340 structural related pairs, with no missing identities. Raw pair skew is 20.18 ps TT / 16.46 ps FF; the canonical spice-scaled, last-common-node AOCV estimate is 47.06 ps TT / 42.02 ps FF, with zero pairs over 80 ps. Slew is 67.91 / 67.60 ps. AOCV uses the approved g=.21%/mm table, actual modeled non-common cell/net delays, and same-CORE-PDN shared clock droop. These are **unchecked plan estimates**, not sign-off numbers.

Physical status is **NOT RUN**: actual row-origin legalization, full PG/occupied-site geometry, actual TX landing-to-FIFO reach, primary-clock capacity/CTS, G1 review and routed TT/FF timing remain required. The shared root-scoped flow changes are separately guarded; this analysis does not authorize installing an incomplete root census or routing this candidate.

Inputs and analysis are pinned here; bulk ASAP7 libraries are not copied into the repository. To reproduce, provide the same ASAP7 RVT INVBUF gzipped and SEQ uncompressed TT/FF NLDM files:

```
python3 results/flow_secondary_phy_1030/estimate_candidate.py --choice 3 \
  --library-dir /path/to/ASAP7/NLDM --out /new/path/estimate.json
```

The script refuses to overwrite an existing estimate. Original geometry came from the prior SD census; the logical pair export and exact macro pin positions came from SDPG3_4. Proposed FF coordinates replace the original positions. The mixed source contexts are deliberately not presented as a current placed-netlist gate.

The opt-in shared API uses one selected `core_tree.clock_port` and a complete `clock_entries` table. Its `core_tree.root_scope` contains `ordinary_roots`, explicit `ordinary_cts_roots` (a subset, excluding forwarded clock pass-throughs), and optional `clock_editor_roots: {script_basename: [ordinary_root_pins]}`. Declaring an editor does not exempt it from checking: before/after rooted graphs must preserve every root outside that editor's list. CTS may grow the selected root only below its declared open leaves, and every pre-existing register clock pin must retain its root. Ordinary requested CTS targets are preserved. Missing roots, overlapping cones, undeclared editor scope and cross-root rewiring fail closed. Existing single-root/default hooks are byte-identical.

The runtime guard was also read-only probed on the actual SDPG `3_4_place_resized.odb` (no placement/STA/route run). It found nine disjoint roots and a stable selected-root cone with 5,260 sinks. A deliberately wrong-root FF clock rewiring by an editor declared for `clk` was rejected as `OT_CORE_SCOPE_EDITOR_CHANGED`. `guard_probe/probe.log` records the native OpenDB result. The diagnostic mounted the original kit read-only and wrote no ODB; `wrong_root_editor.tcl` is a fault-control input, not a production clock script.

The earlier `seq_only_clock_estimate.json` and `estimate_seq_only.py` retain the phase-only compact-region result as history. Its sequential-only area accounting was insufficient; it must not be built. The full-cone candidate is the current analysis.

Current structural data-flow check: the 39,293 in-root FF-to-FF pairs have maximum proposed Manhattan separation 380.54 µm (zero over 405). All 522 exact RX bit-pin-to-capture pairs are <=303.80 µm; the 522 TX output-to-bit-pin pairs are <=182.41 µm. Ten shared control FFs were centered on their actual peer bounding boxes to remove 500+ µm control legs, without changing RTL or adding cycles. These are endpoint estimates; 4,186 cross-root pairs, scalar PHY control pins, TX landing-ring bit geometry and real combinational placement/route detours remain open.

`clock_candidate.json.gz` exports 1,027 named planned drivers, 513 leaves, all 5,260 exact clock sink identities, proposed sink positions and per-leaf TT/FF input-clock intervals. It intentionally sets `build_allowed=false` and `electrical_latency_qualified=false`: an owner must legalize the full cell/PG plan, refresh the model and complete clock-entry/editor metadata before installation. It is an analysis payload rather than a directly installable master slice.

`candidate_clock_estimate.json`, `estimate_clock_only.py`, and `clock_only_candidate.json.gz` retain the earlier full-area clock-only hypothesis as history; its shared-control placement exceeded data reach and is superseded by the data-local candidate. The earlier sequential-only artifacts also remain rejected. None of these history files is a physical gate result.
