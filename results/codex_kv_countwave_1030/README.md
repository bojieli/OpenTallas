# Current native KV synthesis census, first four results

Actual complete native RTL synthesis/count only; no P&R/STA/LEC launched for these census runs. Stock SYNTHESIS and emitted actual wrapper/dependency closure; physical hard-core substitution/clock-mean contracts disabled only in count snapshots so digital hard children are genuinely mapped. The counted source is the current main75 canonical wrapper cohort, not the new SD R52 overlay.

| type | full native std | native FF | parent residual upper estimate std | physical limitation |
|---|---:|---:|---:|---|
| kv3_sys_SD | 56864 | 14104 | 56864 | excludes one explicit W522 SerDes macro |
| kv3_sys_SD_v1 | 57219 | 14079 | 57219 | excludes one explicit W521 SerDes macro |
| kv3_pc_v3 | 998239 | 240289 | 829328 | four actual KVPC children168911; UNSEALED prefix remainder, not capacity FAIL |
| kv3_hgi_v3 | 3040105 | 510149 | 420199 | sixteen actual head children2619906; UNSEALED prefix remainder, not capacity FAIL |

`type.cells` is the full hierarchical standard-cell census. Named hard-child cells are included exactly once; no analytical landing increment. These totals must not be used as parent soft FF/clock load or one physical-run size. PC and HGI parent residuals are UNSEALED upper estimates: anonymous global ABC logic may belong to hard children while escaping named prefixes. Their named child counts are lower bounds. These receipts do not prove a400k capacity failure or authorize physical work. No unknown/unmapped cells or opaque digital hard cores. Explicit SRAM/SerDes macro instances are excluded from std totals and listed separately.

Receipts include actual retained-AIG native metadata SHA and emitted source prefix ownership (unsealed across global ABC) (`u_` aliases validated against corresponding bound module declaration). Full mapped metadata/stat files remain in job roots. Baseline source branch75aa0966bb9; count snapshot clears physical substitutions only, not RTL data/control.

Job roots: intel1 `/srv/opentallas-scratch2/claude/codex-kv-1030/count_batch1/kits2/{kv3_sys_SD,kv3_sys_SD_v1}/TYPE`; intel2 `/srv/opentallas-scratch2/claude/codex-kv-countbatch-1030/kv3_pc_v3`; HGI original completed on epyc2 same countbatch root and metadata/stat copied intact to intel1 `.../count_batch1/kits3/kv3_hgi_v3/kv3_hgi_v3`.

Rejected attempts preserved: count GEN old pin base / absent signed clock mean; HGI extractor launched before metadata copy completed (JSON partial-read), corrected after copy terminal0; initial PC/HGI hierarchy attribution omitted actual emitted `u_` prefix, original incomplete residual records retained. No synthesis rerun for these parsing repairs.

Second batch completed additional current native census: HGIv4 3034887std/508239FF, v5 3046212/512513, v6 3070075/519064, v7 3064645/517263, v8 3094440/526995. All no macro/unknown cells. Source roots intel1 count_batch2/kits/TYPE/TYPE (v4..v6), intel2 codex-kv-countbatch-1030/TYPE (v7,v8). Full totals include16 actual hard children; their prefix-only lower bounds and parent upper estimates remain UNSEALED, without a capacity verdict.
