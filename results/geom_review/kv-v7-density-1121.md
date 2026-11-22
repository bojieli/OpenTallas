# KV v7 split measured tap review, Nov 21

I looked at both halves of the exact private v7 split, source cca34940374057153d27e9b09384ab73aed4f67b927d130a6d5c210c56c62b64, after the measured-density updates. The retained D25e3 a3 placement has 168,513 registers and no unresolved clock roots. The absolute x1080 cut before 10.8 µm binning retains 60,110 west and 95,967 east grid sinks and excludes 12,436 non-grid roots.

| Type | Pin count | Estimated max load | Farthest nearest tap | References | Longest referenced tap move |
|---|---:|---:|---:|---:|---:|
| kv3_pv_v7 | 143 | 903 | 206.784 µm | 116 | 201.984 µm |
| kv3_pv_v7e | 252 | 917 | 273.184 µm | 74 | 154.368 µm |

Both halves meet the 1,000-sink and 340 µm targets on the retained-placement load projection. West adds the snapped clk_t142 site at (9.12, 1010.912). East adds zero manual sites. Twelve east south landing reservation bands and their collector replicas move 0.27 µm north. The east ft32_i reservation and its collector replica move 0.648 µm west, from [1054.08, 265.545, 1062.72, 291.465] to [1053.432, 265.545, 1062.072, 291.465]. The latter clearance admits native tap tracks at (1070.752, 274.848) and (1070.752, 286.176). All rectangles retain their dimensions and preserve the collector status pins. The changed footprints have no new overlaps. I looked at the two rendered macro, tap and measured-load layouts.

Every referenced clock tap has a distinct successor within the 340 µm tolerance. The pending KV work is reset re-selection, native binding and latency checks in the exact adopted carrier. No route was armed.

Intel2 evidence is under `/srv/opentallas-scratch2/claude/tap-grid-r4/v7_split/` in `out/v7_adoption.json`, `candidate_v7_measured.json`, `v7_density_review.png` and the two measured files in `bins/`.
