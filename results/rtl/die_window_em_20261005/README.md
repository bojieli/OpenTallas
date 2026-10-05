# Actual die-window PSM EM (2026-10-05)

OpenROAD PSM `analyze_power_grid -enable_em -em_outfile` completed on VDD and VSS for four S81 layer-die windows and three Qwen windows:14 successful rail solves. Existing completed peak-power IR Tcl/DEF/LEF/source-location/manifest inputs were copied byte-for-byte; only the EM arguments were added. No allocator, full-die route, PDN change, power regeneration, RTL change or local heavy job occurred.

**EM acceptance is not established.** Every window exceeds the repository's existing assumed1mA/um screening level. ASAP7's actual technology LEF has no DC/AC current-density EM rules, so foundry violation counts remain null. Both donor and new raster terminal checks emit PSM-0025; solver shape connectivity and successful current export are recorded separately. None of these facts is a zero-EM or tape-out signoff claim.

| Original window | Peak W | VDD M8 mA/um | VDD M9 mA/um | VSS M8 mA/um | VSS M9 mA/um |
|---|---:|---:|---:|---:|---:|
| qwen-shoreline_w-r1 | 9.8848 | 2.802 | 2.181 | 3.392 | 3.090 |
| qwen-spine_hub-r1 | 5.5073 | 1.652 | 2.083 | 2.890 | 3.554 |
| qwen-tile_field-r1 | 6.7725 | 1.797 | 1.544 | 2.890 | 3.554 |
| s81-c5-band_s-r1 | 10.5461 | 4.708 | 3.185 | 4.058 | 3.833 |
| s81-c5-field-r2 | 25.1966 | 4.192 | 3.527 | 4.460 | 5.333 |
| s81-c5-field_bf-r1 | 18.8354 | 4.079 | 3.446 | 4.602 | 4.773 |
| s81-c5-spine-r1 | 9.2335 | 4.017 | 3.463 | 4.544 | 5.848 |

Densities use the actual original0.48um strap width, not the reduced-block signoff tool's0.8um default. Maxima cover the entire cut window, including its edges; exact resistor endpoint locations, segment counts, wire currents and via currents appear in each summary. No via-density rule or interior-only EM exemption is invented. The rule gap and any PDN widening are escalated to Claude; widening requires Maxwell/Ampere to revalidate their die GRT.

## Source and power authority

S81 manifests exactly match the committed main21fcf6469 feasibility cases c5_field,c5_field_bf,c5_spine,c5_band_s. Their raster peak power authority retains the original measured-scaled pair power plus explicit assumed BF/config/slab classes. These are the pre-recovery4706-node die and r5 placement (r7 changed VM pins), not current recovery or strict5090-node qualification.

Qwen uses the actual completed b3r13c_ir_tile_field/spine_hub/shoreline_w inputs that the source STATUS says feed the PDNr5/IR evidence inherited by the closed b3r16B40 route at f1df64409. This does not qualify Ampere's current split-face/grown-slab recipe. The precise original instance loads and supply sources are SHA256-pinned in input.json; no rail current is guessed.

Authority.json records the model/route scope, technology hash, no-hardware/cycle delta and measured admission basis. All work ran on EPYC2 through existing admit.sh32GiB with8OpenROAD threads; no process-size/wall-time cap. Initial checks showed1065-1093GiB available,81-91percent idle CPU and637-717GiB free disk. Donor PSM peak RSS reached13.4GiB;32GiB was an admission reservation for solve/export overhead, not a process limit. New resources.txt measures the Python/docker wrapper only, not container OpenROAD peak RSS.

## Evidence and failure preservation

summary.json selects the actual per-case results. input.json pins every source/prepared input; command.json pins the exact image/argv; run.log retains the actual OpenROAD reports/errors. Bulk DEFs and all raw EM CSVs remain at `ot-epyc2:/srv/opentallas-scratch/codex/die-em-item8-20261005/<case>/`, with CSV SHA256 in the actual summaries. Small committed records retain source Tcl, original manifests, logs and current maxima; large compute outputs are not copied to localhost.

launcher_PATH_FAIL_r1 preserves the first launcher127 failure before OpenROAD execution. Executed source snapshots785738c4c andc409925e0 are retained. The first S81 postprocessor required terminal-checkPASS and therefore marked result.json false/launcher.exit1 despite OpenROAD exit.txt0 and exported currents. Those original files are preserved. Additive actual_psm_summary.json separates the successful solve/export from the unchanged terminal-checkFAIL, using pinned postprocessor05b5b3fe89f424109c97eed030b739d0446bc324; no PSM rerun. The Qwen runs used that corrected source and recorded both facts directly.

All seven analysis jobs are terminal; raw inputs/outputs stay available to Maxwell/Ampere/Claude. Confucius owns serialized tapeout inventory updates; Kepler owns scoreboard/register coordination. No shared inventory/scoreboard/UPF/meso files are edited here. The next physical action requires an authoritative EM limit and/or Claude's PDN recipe with die-GRT revalidation, rather than an unapproved sweep.
