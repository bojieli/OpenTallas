# KV D28 ASTK output hubs, placement review 2026-11-23 09:29 PST

Source form is the equal-depth ASTK reset plan 240c9e69c3f1, strict-bound on runtime 65f367a55943. Both actual `3_place.odb` geometry images were opened. Root below is on epyc8.

`/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D28/private/FAM-KV-HUBWO-S1`

- **kv3_hub_Eo, FAIL.** `kv3_hub_Eo_1122231125/geom/auto_geom.png`. A dense vertical stripe on the center-east macro side runs from the lower macro to the upper macro. The separated west pin islands and sparse interior create long diagonals. R2R max 1319.60 µm, 1183 events over the set bound. The worst assigned sink reaches 2760.05 µm and t34 drives 10,196. Named 128-bit paths from sequence XS output to separate fan banks reach 858 µm. Correct both the logical locality and the clock assignment before considering the next placement.
- **kv3_hub_Wo, FAIL.** `kv3_hub_Wo_1122231146/geom/auto_geom.png`. Dense southwest launch/receive flow crowds the macro corner and is separated from the small southeastern processing islands. R2R max 1458.16 µm, 1206 events over the bound. The worst assigned sink reaches 2765.95 µm and t37 has 23,456 sinks. A 128-bit sequence XS ring-to-bin hop reaches 1222 µm. Correct the receiver band and the two endpoint regions along with tap assignment.

The inherited Eo run is at GRT and Wo at CTS, both started before this review. Keep their results for diagnosis. These exact placements have no visual clearance for a new route or STA.
