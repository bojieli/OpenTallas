# HBM terminal pickup — 2026-10-19

Bounded read-only collection. No RTL, gate, route, submit, frozen worktree or prior failure was changed. TT setup and FF hold are binding; SS is sensitivity only. None of these records qualifies a release element or token.

## PAD exact-N — functional PASS, structural FAIL

Fleet `ot-epyc6:/tmp/codex-hbfd-pad-1019-0c3eecf04`, client1588066/unit `oth-ubuntu-4108740-1792424573`, exit0. Source and bench bytes exactly match committed0c3eecf04 (source_commit_binding.json). Verilator5.050 PASS72 shapes×7000 edges, four mechanism mutants detected,14 reset epochs, real SRAM deliberately poisoned before reset. This is the combined bench; individually nonzero mutant witness logs from latest366dc27e7 bench remain owed.

ALL sequential Q outputs in all five actual generic Yosys0.68 synth JSONs were counted by direction, including top output loads, not just top12 nets. See reproducible audit_pad.py, full per-Q load pins in pad/fanout_raw.json, input SHA and client receipt. This is generic synthesis, not technology mapping, placement or native timing.

| W×N | Q outputs | SRAM macros | max Q loads | Q outputs >32 |
|---|---:|---:|---:|---:|
|17×115|2003|0|115|17|
|1×3|9|0|3|0|
|34×73|89|1|8|0|
|274×14|588|2|7|0|
|136×28|302|1|7|0|

All macro masters are actual ot_sram_1r1w_128x256_m1_r2c2 blackbox cells, not technology-qualified physical banks. 17×115 is1955 bits, below the2048-bit threshold; intended NI=8 ingress_local copies alias to one FF per bit despite source keep. Same-edge distinct kept paramod/hierarchy copies and post-synthesis actual load proof are required. Do not replace the ring with a shift chain. Preserve exact N/II1/reset warmup and zero external extra edges. Whole production inventory remains315 pads/103608 bits with191 N>=3, seven >2048-bit shapes and nine modeled SRAM macros; these five synths are representative, not a census of all315 instances.

Next source owner: repair actual merged ingress, prove every Q<=32 plus all scalar/input/reset distribution, run latest individual fail witnesses and exact/poison bench, then technology synthesis area, bank pin access/native timing and model geometry. No gate authorized by this pickup.

## SFUk9 — terminal failure, no usable CTS

Preserved local gate_result.json is generated09:17:52 PT, exact source snapshot archive050e9333712b57305228281186fe5fb2209e3913ab64ec877719036d46b77752 from7ec780d03. Actual item count is1 FAIL/39 WARN, correcting earlier3/40 shorthand. Remote ep4 ref_gate/hbm_sfucore_k9-20261019-050354. cts.log fails: `OT_HYBRID: CTS source clk must reach only standard-cell clock pins`. pc.log subsequently errors because4_1_cts.odb does not exist; cross-clock STA did not complete. This is not measured clock closure or merely an SDC syntax error. GRT rc2, clock insertion/spread null despite legacy clock.verdict PASS. Preserve all failure files.

Current safety blockers include standard-clock root incorrectly reaching hard macro clocks;12224 flops over1594×1767um; reset fanouts6245/2991/2989/2989;19-level/~717ps logic; child face pin obstruction and2613 unclosed own-layer pockets. Need model-first source/regional architecture, real macro clock ownership and local landed crossings with priced fixed latency, safe reset/control copies and child-access correction. Do not rerun the same kit or relax hybrid guard.

## Top-k e86 — old coarse gate WARN, current safety FAIL

Exact old gate remote ot-agidock128 ref_gate/hcoll_v7_tkm_tile_e86-20261019-014037, start292bdef26. Submission refused stale REVIEW: current geometry339be3bd73fc3a3f4eba2fdefa186f7f298f66f1b787a0f6fd9eb3d1af1505f5 vs prior ecc1357139d7. No submit occurred. Gate source binding remains in e86/gate_result.json; no attempt to claim current source equals this historical snapshot.

| Safe requirement | Actual evidence / outstanding obligation |
|---|---|
| Registered pins/reset | Legacy lint no comb input-output; input depth3/output0. Source internal pin stage asserted by spec; full per-pin proof/clear startup remains owed, reset_ports empty. |
| Reach <=405um |259.2 square gives max corner Manhattan518.4; actual route endpoints needed. Legacy reach_worst=0 is not proof. |
| Critical FF fanout <=32 |FAIL: mapped textbook census q_conv_g groups1..7 each2064 loads, group0=1378. |
| Logic depth |461.8ps/11 levels old mapped lint; actual native budgets still owed. |
| Storage |12694 flops, no macros. Sorting state X64×86 is parallel compare/update state; audit finite delays and indexed arrays separately, do not claim SRAM compliance from zero macro count. |
| Floorplan/pins |259.2 square; synth27753um²/42.7%, placed27537.5um²/41.0%; no macros.1386 pins all track accessible/inside. Pins N/S/W only, E empty; full-face intent requires review. |
| Clock |Five real roots. Largest r3 pin spread28.1/26.7ps; rootclk47.7/42.1ps, r0 16.6/15.0, r1 leaf27.3/25.2, r2 leaf23.1/22.0. Parent pair matching/native launch/capture budgets remain owed. |
| Schedule |Prior PRE1 adds one stage, TLAT4 with SETTLE4NT+8; actual compiler/die bind and bench source hashes remain owed. |

GRT0, M2 usage55.07%; old cross-clock minimum hold63.4ps and minimum setup65.8ps under old budgets are evidence only, not current native-pin qualification. Geometric screenshots are original paths listed below; root should not approve current safety until source control distribution is repaired and actual mapped/native/reset/storage evidence exists. No refresh of REVIEW.json.

- /home/ubuntu/wt/hh4-e86/physical/ref_tile/hcoll_v7_tkm_tile_e86/gate_layout/floorplan.png
- /home/ubuntu/wt/hh4-e86/physical/ref_tile/hcoll_v7_tkm_tile_e86/gate_layout/density.png

Fresh source follow-up: preserve historical failed routes, model same-edge per-subgroup kept control copies; actual mapped all-Q load census, registered boundary/startup proof, storage/reach/native clocks, then distinct safe kit and exact/mutant witnesses before coordinator PNG decision. Do not shrink the already valid42.7% model fill just to satisfy stale45% warning.
