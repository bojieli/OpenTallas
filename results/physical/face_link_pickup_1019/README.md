# SYSFACE / D2D native result pickup, 2026-10-19

No job restarted; no source constraint changed; no REVIEW or submit. Frozen source manifests and source kit specs are copied under each kit directory. Parent source branches remain the source authority.

| Frozen gate | Result | TT/FF pin spread ps | Trial overflow / exit | Consequence |
|---|---|---|---|---|
| SF7 | WARN |65.1 /62.1|0 /2|GRT-0183 on _07404_ during repair_design; zero initial overflow is not route completion.|
| SF7w | WARN |66.3 /62.1|0 /0|Actual completed trial global route; prefer over SF7, subject to shared PG and production qualification.|
| SYSFACE bc3 | FAIL |48.3 /44.5|no table /1|grt.log truncates mid repair_timing; actual failure cause UNKNOWN.|
| SYSFACE bc3c | WARN |38.1 /38.1|0 /2|GRT-0183 boundary_101789/net14518 during repair_timing; not completed.|

SF7w TT placement-RC setup/hold +161.581/+35.743 ps are from pc.log, not routed signoff. Actual final GRT reports SS sensitivity setup +83.16 and FF hold +30.01 ps after hold repair. SF7w real 5_1_grt ODB SHA and all-driver census are in sf7w_native_summary.json. 61,091 instances, 32,278 unbound native PG pins: production adoption remains HOLD. Data fanout max32, no over32, no mixed data/clock cones. Data pin-to-pin L1 max365.686 um, none >405. This does not measure routing length.

SYSFACE bc3c real 4_1_cts ODB: 52,844 instances, 18,922 unbound native PG pins. All nonclock roots <=25 and pin-to-pin L1 max347.362 um; no over32/far405. This is post-CTS only; failed GRT output does not upgrade it. TT placement setup/hold +48.858/+35.288 ps. Partial failed GRT ended SS sensitivity setup -61.96 /FF hold +18.64 ps. Depth warning23 generic levels/705ps remains despite the earlier source-only19-level claim.

The first audit versions incorrectly classified some genuine open-output clock-load cells as data. Full immutable intermediate JSONs remain in original remote roots; compact v1/v2 records are retained here. Final audit follows BUF/INV/CKINVDC transparently, treats a real open-output BUF/INV as a physical load, and separates a clock cone only when every terminal is an actual sequential/macro clock pin or such an open-output clock load, with at least one real sequential/macro clock terminal. No instance-name waiver. CKINVDC is the native Liberty inverter function !A (INVBUF_RVT_TT_nldm_220122); clock-load Y has no net or a net with no consumer. No mixed cones remain. Complete per-driver JSONs remain remote, SHA-bound by the summary.

## Actual contact audit and checklist

SF7w actually binds ot_sram_1r1w_64x137_m1_r2c2_p192:229 signal/clock contacts on each W/E face, min center pitch192nm =>5.208/um. It does not bind the 64x512 SRAM3 family. SYSFACE binds 64x16 SRAM (32/31 contacts) AND4096x72 ROM (43/43 contacts); both have min96nm =>10.417/um FAIL. No blind SRAM-family substitution is appropriate.

1. Registered pins/reset: source wrappers explicitly register functional ports; gate raw reset max2, no newly added edges.
2. Reach: native terminal L1 as above, independent of full route closure.
3. Fanout: final all-driver native census as above, ties included. Clock is separately counted.
4. Depth: SF7w463.4ps PASS at source-lint scope; SYSFACE705.1ps/23levels warning remains and failed GRT does not qualify it.
5. Storage: four real64x137 SRAMs in SF7w, six real64x16 SRAMs plus three4096x72 ROMs SYSFACE; no new indexed arrays.
6. Geometry: personally viewed actual floorplan+density PNGs for SF7w and bc3c. SF7w four macros in one horizontal row on43.2um lattice, ample visible intervening channels, connected std-cell space around the row; outline388.8x172.8. Aspect2.25 exceeds nominal~2 guideline and needs explicit root disposition. Fill24.8% is the existing measured pin-bound exception, not 40–60% whole-outline utilization. SYSFACE9 macros on lattice, rows separated with visible channels; outline302.4x172.8; actual96nm local contacts FAIL. Layout PNG labels include filler/PG pin counts, distinct from3668/2788 functional ports in pin_geometry audit.
7. Clock: SF7w N-face centre clock beside boundary register rows, pin-flop spread66.3/62.1 <=80; insertion371.6/308.9ps is guidance only, parent landing/compensation still owed. SYSFACE clock near NW,38.1/38.1 but actual failed repair and contacts preclude adoption.
8. Schedule: no edges added by these existing source candidates. Full die boundary/schedule and physical token-rate qualification remain separate dependencies.

Root must personally review SHA-bound SF7w PNGs before any critical physical submission. Shared PG source owner must resolve birth-time native binding. No local PG fix, manual global_connect, clock relaxation, retry or new engine run was made here. LAND8 lane file was absent; only the future-dated LEAD2-QW statement claimed a started task; no actual new LAND8 process or source evidence was established.
