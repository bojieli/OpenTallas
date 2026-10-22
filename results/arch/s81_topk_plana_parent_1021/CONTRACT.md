# S81 TOPK Plan A source candidate

This is a default-off, source-validated successor. It is not an adopted parent view or a physical closure. ROOT owns any main merge.

## Source and actual quarter identity

The source foundation is current main `ccf68cf584d0aaef60454936a5cd7d06998baf70`. `closed_source_inventory.json` pins the exact selected quarter source from `f9753ee142a0ce191b0a60b4f885f404712ac35a`. Required opt-in HQ/FIFO_SRAM/P192/SUCC/FAN32/ACC32/HARD_CHILDREN/HQ_INPUT_RAW dispatch and dependencies are restored at their real canonical paths. The existing full-shape indexed13 bench compiles those sources, including the actual SRAM models.

The quarter view is the CLOSED hk2l record `0d4ba50ed516c8dce8e70a03bee57cab1d1a6d17`, published at **`physical/ref_tile/s81dvbk_sq_hq3/views/dsdv_bksel_q`**. That old path is intentional and remains byte-identical. Its reported TT +37.37 / FF +5.16 ps, DRC 0, and SS sensitivity −309.48 ps are quarter evidence only.

`dsdv_bk_sel_pa` is a wires-only connected regional description. The standard `tools/landed_parent/lp.py` generates the actual `dsdv_bk_sel_pa_lp`: four real quarter instances, actual glue and rung masters, a new control, and every commanded/data/credit crossing. No token fixture replaces the quarter's computation. Pure station modules describe region boundaries; all added state exists in the generated landing rings and readers.

`dsdv_bksel_c_pa` keeps the original arithmetic, comparison, reduction, and merge order. It fixes SEARCH_PIPE=1, DM=4, PACE=2, MRG_PIPE=1, RQPIPE=1, SLAT=4, **XDX=15**, hence XD=17 and XR=34. The old control fixes XDX=1, XD=3, XR=6. Search step-A metadata must be delayed by the actual quarter round trip; adding parent landings against the unchanged old control is invalid. The CLOSED `selc2` view is never assigned to this changed control.

## Timing and state charged to the model

Each quarter path has seven D=2/K=1 landings, two edges apiece:

| Path | Added edges |
|---|---:|
| Glue lane to quarter | 14 |
| Control command to quarter | 14 |
| Quarter status to control | 14 |
| Quarter selected data to control | 14 |
| Control credit to quarter | 14 |
| Command/status or credit/data round trip | 28 |
| Rung face to glue | 14 |
| Glue to rung output face | 14 |
| Rung forwarding through the parent | 28 |
| Local control VD relay to glue | 1 |

The actual generated record audits PASS: 39 related clock roots, 224 landed seams, 12-bit kept chunks, and bounded regional reset copies. Its declared storage inventory is 238,532 landing FFs plus 509 reset FFs. The local VD relay adds 514 data FFs. This inventory is not mapped area. DM4 remains unchanged; the longer credit round trip can stall selected output after four credits. No unchanged sustained-throughput claim is made.

The old calendar is preserved as a failure. New CLRW is 103 instead of 47; the old header at edge100 reached the source before the boot DONE at159. The old drain also missed the late final DONE. The fixed booking shifts first input by64 and drain input by192, with another28 forwarding edges reflected in expected output. This is an **external tail of796 edges instead of640**. Dates are fixed before execution; nothing waits for DONE.

The unchanged existing topk-final fixture contains 512 candidates per quarter, K=512. With first input164, last input487, and output window1283..1358, the real generated-source bench passes all73 expected beats with zero mismatch and no fault. This qualifies that component and booking, not a whole-token replay or a 131,072-score sustained-throughput run. `timing_ledger.json` carries exact source, unit, and calendar fields.

## Physical candidates and immutable failures

The original east-corridor geometry passes 7,244 published-quarter-pin and planned segment checks, max388.8µm. It is nevertheless rejected: every legal43.2µm translation tested has off-track mirrored signal pins (MX354, MY1447, R1801801; R0zero). `mirror_lattice.json` and `failures/mirrored_kitgen/` preserve the actual refusal. No LEF edits, origin rewrites, or track exceptions are applied.

The successor kit `s81dvbk_selpaw` keeps every quarter R0 at x216, y43.2/864/1771.2/2548.8. The last quarter moves down43.2 to leave an86.4µm top corridor. It retains the approved907.2×3283.2 parent outline; the new control reserves388.8×172.8 at(216,1555.2), and CLOSED g2 occupies216×172.8 at(648,1555.2). The continuous west corridor is216µm wide. This kit generates cleanly with the existing two-level cluster contract: child PG M7, parent PG M8, signals M2–M7. Generation is not a cell-placement or routing proof.

The new control **fails mandatory native admission before floorplan initialization**: 237 violating roots, max4,280 dynamic loads, 121,764 roots examined, zero role errors. Its mapped source is233,093 cells /28,299 FF /26,030.19888µm² (8,626.4028µm² sequential), netlist SHA256 `4f1c88b666810f173bcbc6e1d2c518fab2df84d50d1ce2fd58037c4c3f2db759`. Actual dominant roots are `rst_s[1]`4,280, search result `res_b[1]`1,820 /`res_b[0]`1,260 and timestamp `ts_r[1]`1,440 /`ts_r[0]`722, alongside combinational cones. The original gate report also records missing downstream textbook-verdict execution after this prerequisite failure; it is preserved without re-gating or treating it as a pass. The small `s81dvbk_selcpa` gate stopped at admission; no parent gate, CTS, trial route, or physical adoption occurred. This is a real structural-control debt; changing XDX alone does not qualify a control view. The CLOSED c2 remains immutable.

`west_paths.json` and `verify_west_paths.py` now check7,204 individual quarter signal paths, using literal public quarter/glue pins and seven equal routed-length seam segments through free corridors. After54nm/270nm site/row snapping, the maximum routed-hop bound is398.863286µm (q3 lane514), local pin-to-bank distance21.642µm. Every sampled stage anchor avoids macro bodies. Control coordinates explicitly use old-c2 pins as a **proxy**, never as a new c_pa view or adoption. VD proxy reach with its one priced relay is216.594µm. This is path feasibility only: it does not place real cells, route simultaneous wires, qualify new-control pins, or establish region fences/CTS.

The 86.4µm top band has5,390 raw preferred-direction horizontal tracks; the two-bank N bundle plus chunk12 valid uses at least3,140 modeled wires (58.26%). Restricting to the2.16µm core inset gives5,255.25 tracks and59.75%. The old43.2µm band would require116.51% raw capacity, so moving q3down43.2 is necessary in this model. No routing occupancy allowance or layer grant is inferred. `landing_region_inventory.json` estimates218,820 functional landing FFs before mapping, excluding unused assertion epochs; it does not replace the declared238,532 FF inventory or prove body area. Actual simultaneous routing, station/body allocation, fences, new-control native localization, mapped timing, clock/PG phase, rung per-bit physical paths, and parent context remain open.

## Reproduction and evidence

- Generate/audit: `python3 tools/landed_parent/lp.py gen tools/landed_parent/specs/dsdv_bk_sel_pa.json` and `audit` with that spec.
- Source test: `tools/s81_dv/topk_plana_parent_1021/run_generated.sh`; its actual compile defines match the selected hk2l source plus ILD/FRPR. `bench_booked` contains fixed stimulus, golden beats, metadata, and actual logs. Compile objects are retained on fleet.
- Exact source run: EPYC7 `/srv/opentallas-scratch/claude/codex-s81-topk-plana-parent-1021/src_gen_r2`; build `bench_gen_r2`; separately booked input/output `booking_r2/bench_booked`.
- Positive unit `oth-ubuntu-2390844-1792605990`, terminal0: 73/73, zero mismatch/fault.
- Identity negative `oth-ubuntu-2480126-1792606373`, terminal1 as expected: one metadata mismatch, 69/69 beats.
- Final-output-landing causal mutant `oth-ubuntu-1014402-1792607467`, terminal1 as expected: exact landing210 bypass only, same fixed booking, 76 mismatches /73 beats /no fault. Source and mutant SHA256 plus checker/logs are under `mutants/output_landing`.
- Native admission: ep9 `/srv/opentallas-scratch/claude/ref_gate/s81dvbk_selcpa-20261021-112637`, flowRC1 after580s; local gateRC1. `native/summary.json` contains all237 root identities/load counts, loaded-Liberty and netlist hashes, mapped cost. `native/native_census.json.gz` preserves the complete19,130,339-byte census; `native/gate.*` and synthesis statistics are retained.
- Old generated calendar `oth-ubuntu-2283067-1792605520`, terminal1: four booking mismatches, preserved.
- Earlier hand-expanded prototype `oth-ubuntu-1802430-1792604521`, terminal1: six old-calendar mismatches, preserved. It is historical source only and is not the physical candidate.
- Initial generated dependency attempt `oth-ubuntu-2704375-1792605288`, terminal2 before simulation: missing reset-copy source, preserved and corrected in the actual runner.

Source and source-qualification files are opt-in. Existing default parent and CLOSED control/quarter views remain the baseline.
