Claude takeover — collective endpoint, 2026-10-09

Worktree: `/home/ubuntu/wt/codex-hgi-collective-endpoint`
Branch: `codex/hgi-collective-endpoint-20261009` (pushed; clean).

`7d856b31d` is an **unverified** shift/mask payload-guard draft. No bench, build, or route was launched for it. Its prebuild model is `results/uarch/hgi_collective_endpoint_20261009/guard_shift_prebuild.json`. Use `3208d76a3` as the last functional source baseline: it changes declaration ordering only from the proven `916a3915a` implementation. Evidence is pinned by `8c78c1318`.

Completed functional evidence:

- The earlier `57814c941` campaign passed 970 positive runs, including 192 real TP96 owner cycle-lockstep runs and ten DS/gather legacy runs. Its overall FAIL from four pad-mutant timeouts remains preserved.
- The `158cff53c` remaining-mechanisms campaign passed four genuine `PAD_PROGRESS` mutants, rejection of raw codes 4–14 and oversized group-1 payloads, and a genuine mode-guard mutant. EPYC3 driver `1133011` is terminal, rc 0.
- Multicast child branch `codex/hgi-coll-global-mcast-bench-20261009` at `f8bef7f44`: 1,728 positives, 12 DS lockstep runs, and 36 consuming mutants passed against source `916a3915a`.
- Rearm child branch `codex/hgi-coll-rearm-bench-20261009` at `135ad1db3`: 45 commands without reset, 13,928 exact delivered flits, and 50,318 actual credit-stall cycles passed, including descriptor capture, duplicate fault, and premature-done mutant checks.
- These SUM/gather proofs do not establish the ARGMAX_MERGE conformance row. Mutable-payload ECC is also still being integrated by the separate SRAM owner.

Preserve this live synthesis job:

- Host `ot-epyc4`; driver `2122801`; container `d3d730c04ef9`; container init `2122867`; Yosys `2125395`; ABC `2158573`.
- Remote root: `/srv/opentallas-scratch2/scratch/codex/hgi-psg-synth-eec9f9778`.
- Source: endpoint `3208d76a3`, inventory script `eec9f9778`, halo correction `c103cfee4`; all source files are present in `158cff53c`.
- Current phase: top-level ABC. Measured container peak: 4,443,156,480 bytes, against an 8 GiB declaration.
- This is full-shape, real-SRAM synthesis characterization only. The script stops after actual mapped `1_2_yosys.v` normalization, before floorplanning. Collect `out/receipt.json`, mapped cell/macro/area/pin inventory, logs, and the final resource receipt. Failed attempts a1 and a2 remain preserved.

Physical blockers: there is no qualified installed `ot_hcoll_port` view. Fanout-8 candidate `c4be41d70` ended NEEDS_RTL: TT −118.65 ps / FF −48.23 ps, slew 292 and fanout 512 failures. LVT candidate `bbe601a79` remains with `hbm_system/link_retry`. Eight 480×540 µm slices occupy 2.0736 mm² before the core, exceeding the old 1400×1404 µm collector slot. A grown-slot model and real exported port views are needed for the two hierarchical routes. No Liberty, closed baseline, or flat 8,680-pin physical vehicle was fabricated.

Real 96-rank SUM: child `sum96` owns a parallel final tree at `4660d5131`, bench `a8f0309ae`, branch `codex/hgi-sum96-20261009`. It adds 176 LAT-7 FP32 adders for the 12→6→3→2→1 tree, taking raw FP32 subtree vectors, without intermediate BF16 rounding. Twelve parallel protected banks cost 36 actual SRAM macros. Producer integration, protected bank binding, grown-slot fit, and normative odd-carry golden confirmation remain pending. The sequential prototype `5da48f2e9` is rejected latency history, not an adoption candidate. The child will publish its exact final HEAD and live handles.

All children have been told to stop new RTL, builds, and routes under the owner takeover. Existing progressing compute is preserved. Claude owns review and merges.
