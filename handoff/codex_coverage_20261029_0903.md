# Codex coverage handoff — 2026-10-29 09:03 PDT

Explicit Claude reset received. Coverage and both children parked; no new engineering, routes or merges after reset. Live jobs were left untouched. Detailed per-step evidence is in CODEX-LOG under the 09:03 coverage and support/review handoff sections.

## Branches and completed work

- `codex/hbm-direct-station-0822@147de74dd` is clean and pushed. Worktree `/srv/opentallas-scratch/claude/wt/codex-hbm-direct-station-0822`. Source lineage 062db0f0a, 094958910, 53cbd53ad, 4cecd4c6c, 9696e6ad6, 147de74dd. Root had 4ce/969 picks on its private root branch, not main at reset: avoid duplicate picks. Latest complete implementation is 147de74dd.
- Optional `tools/hbm_b2/direct_stations.py` materializes exact directed source/sink bit slices, common logical clock, control-only caller reset, and resetless data. Default disabled preserves source bytes including CRLF. Serial_k2 and requested runtime adoption are rejected.
- Latest combined source: `intel1:/srv/opentallas-scratch2/claude/codex-hbm-direct-station-0822/top_vms128_dma16_geometry.sv`; `combined144_contract.json` and `combined144_receipt.json` alongside. 128 actual North VMS links plus all 16 actual North DMA links; 201,458 FF bits including 3,254 control FFs. Exactly 144 paths rewrite 102 sink ports; all 379 native instances/masters/parameters and unselected bits remain unchanged. No South paths or epoch signals fabricated. Parent clocks/reset/calendar/physical qualification remain open.
- All 16 DMA routes reconstructed by support: `codex/dma-station-0848@bd3092274`, push in progress at child report. Results `results/hbm_dma_native_stations_1029/{native_station_recipes.json,native_dma_stations.png}`. Exact 2,192 pins, no missing/surplus pin bits, max per-bit hop 362.88 <=364.5 um, no station centre inside 159 cores plus 4.32-um halos. Requests/returns each use stages `[17,20,15,16,5,8,3,6]`, including two endpoint stages. Per-bit FF body packing remains open; no physical adoption.
- Source miters: five focused tests PASS (3.92 s), including 4,096-cycle 257-bit stream, actual masks/widths, 17/285-bit paths through 31 stages, warm resets and 27 seeded mutants caught. One bounded station-only Yosys synthesis retained exact VMS128 state: 173,724 resetless +3,074 synchronous-control FF bits. All own synthesis jobs terminal; no full native core elaboration or physical qualification.
- `codex/number-qc31-0822@53bb5b582` and `codex/vmword-import-0822@1cf5ada39` were reported merged by root. QC vK pair calculations confirmed; VM diagnostic test collection fixed by package-qualified import.
- Support also retired an exact legacy QC prog cache entry with 108 unconnected buffers/216 open PG terms, transferred surviving routed DB to QC owner, and produced HBM placed-stage calibration source `codex/support-0822@4dfbcaca2` plus QC prog geometry failure record 6391e0ec4. Root owns integration/repair; no old invalid sign-off restored.
- Review branch `codex/geom-0822@b380c28cb` is clean/pushed. Independent reviews delivered to owners for HEAD pure FT/hk6 crop, modeled KV PHY, QC prog GRT-only, ASTK GRT-only, and HNX residual data ECO. Current HEAD hk5 is not subject to the old explicit-mesh risk.
- Selector source `codex/hbm-selector-reset-0855@42f0d6913` is clean/pushed, default off, +2 deterministic boot cycles; no adoption/P&R. Actual original/default-off/enabled miter PASS 567 comparisons/24 valid cycles; mutant caught 516. Width lint PASS. Formal attempt exited because Yosys SAT cannot model the generated `$check` assertion cell; no RTL counterexample, mutant formal NOT RUN. HBM parent owns adoption/reset contract.

## Live jobs — preserve and collect

Only support's S81 source/gen wave is live from this subtree:

- Host intel2, root `/srv/opentallas-scratch2/claude/codex-support-s81-0840`, source worktree `codex-support-s81-0840@3ad9fd700ad`.
- Launcher clients 2392623..2392626; ot-run units `oth-ubuntu-2395928-1793288382`, `oth-ubuntu-2395975-1793288382`, `oth-ubuntu-2395980-1793288382`, `oth-ubuntu-2395971-1793288382`.
- Check: `ssh intel2 'tail -8 /srv/opentallas-scratch2/claude/codex-support-s81-0840/wave0.otrun.log'` and wave1..3 equivalents. Preserve live runs; do not duplicate them.
- Last collection: 22/61 source exports PASS, 15 kit generation PASS, 7 SerDes generation FAIL due to reserved u_phy lacking actual LEF. IQF/seqhost plus five stations preflight PASS; none placed. S81 lead owns actual PHY source/shape repair.

Terminal jobs: DMA solver epyc2 unit3553301-1793289381, `/srv/opentallas-scratch2/claude/codex-dma-station-0848/geometry4/summary.json`; selector units3559790/3584905 under epyc2 `/srv/opentallas-scratch2/claude/codex-selector-reset-0855`; direct station synthesis intel1 `codex-hbm-direct-station-0822/station_scope.{log,json}`. No own live geometry/STA/route jobs.

## Open failures and next steps

1. DMA RR_RT80 is explicitly **NEEDS_PADDING on all eight banks**: deficits `[39,33,43,41,63,57,67,61]`. Intrinsic bank latency is 7 launch-to-launch cycles; consumer capture is one edge later. Request padding costs 6,868 FF bits but changes memory read sample dates and needs compiler write/version agreement. Response padding costs 103,828 bits, each bank above 2 kb and needing a priced SRAM solution. Neither padding location is selected. Current actual calendar has no qualified immutable-read window.
2. HBM bind should rebuild native flat/core/station mapping once against the combined source event, after calendar/padding/physical choices. Baseline flat is unchanged. `top_station3.sv` is superseded (old entirely resetless prep); old six-path NW4 depth3 is superseded by full DMA geometry depth5. Do not double-insert NE7 paths already contained in VMS128.
3. Missing South128 VMS geometry, per-bit station body packing, actual source clock/reset delivery, parent compiler dates and physical gates stay assigned to HBM/TOK. No die/token/sign-off claim.
4. Collect the remaining S81 source/gen waves and repair the real SerDes PHY view/lot issue before placement; preserve failures.
5. Selector formal infrastructure needs an assertion representation SAT supports; no equivalence verdict was fabricated. Review/source packets are handed to HBM owners.

OWNER? None. No blocking dialog was opened. All remaining items above are assigned engineering dependencies.
