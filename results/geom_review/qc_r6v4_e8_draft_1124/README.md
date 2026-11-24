# Exact QC R6V4 C1h E8 placement review

All eight images are from the 3_place ODB saved by the corresponding epyc8 private attempt. I viewed the digest-matched epyc2 geometry renders before deciding on any successor. The runs remained unmodified. This replay measured placement and estimated channel demand. GRT and STA were outside its scope.

| Exact placed attempt | Longest r2r (µm) | Captures over 405 µm | Peak vertical demand | Geometry finding |
|---|---:|---:|---:|---|
| [slw_fe_v1__cl95cd1d0c](slw_fe_v1__cl95cd1d0c.png) | 698.92 | 9 | None | Concentrated center strip. Worst path is core scd bit 0 to the southwest fault capture. East arm and arv pad starts also need reseating. |
| [slw_su_l1__clcc9d0155](slw_su_l1__clcc9d0155.png) | 410.05 | 27 | 2.65 | The eastern channel alongside the SRAM column carries the worst vertical demand and concentrates the 5,449-sink tap. |
| [sle_stm_v1__clbe630b9c](sle_stm_v1__clbe630b9c.png) | 1387.21 | 220 | 1.013 | Thin input-strip landings and upper-left macro corridor. Move the branch endpoints before timing the long path. |
| [sle_st_a_v1__cl989804f6__cl18eece69](sle_st_a_v1__cl989804f6__cl18eece69.png) | 1138.64 | 965 | 1.571 | Relay bands and pin taps crowd the middle/east macro corridor. Regroup relay taps in the narrow east and macro-crossing channels. |
| [sle_st_a_v2__pv30dda31f__pv88773f93](sle_st_a_v2__pv30dda31f__pv88773f93.png) | 896.75 | 1034 | 1.426 | The southern macro throat and eastern landing strip carry the dominant congestion. Ring/relay station and pin changes need a fresh place build. |
| [sle_st_a_v2__pv4242de79](sle_st_a_v2__pv4242de79.png) | 897.56 | 1038 | 1.432 | Similar macro throat, with its own bindings and stage paths. Keep it held independently pending measured row. |
| [slw_st_a_v1__clfc5867a6__pvdf8e5ca4](slw_st_a_v1__clfc5867a6__pvdf8e5ca4.png) | 742.39 | 847 | 2.629 | Largest right-side channel demand in the reviewed batch, with congested pin landings at the lower macro pair. |
| [slw_st_a_v2__cl9f076a5c](slw_st_a_v2__cl9f076a5c.png) | 896.89 | 1179 | 2.215 | Packed tap corridor at lower east macro edge, plus long detours from the upper macros. Requires changed station and clock-entry placements. |

Future route hold on all eight exact forms pending revised placement and independent review.

## Checkpoint identities

- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_fe_v1__cl95cd1d0c_1124052635/gen/slw_fe_v1__cl95cd1d0c` uses 3_place SHA-256 `7ad18789b2d1398a8d86efe42e411f951641dada99fa24a29d0374a37d589afa`.
- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_su_l1__clcc9d0155_1124052823/gen/slw_su_l1__clcc9d0155` uses 3_place SHA-256 `41be9659ae9a336a388ad7c136d96b4c9bbe9a3c43b00d1cbd528710b3e9b24c`.
- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_stm_v1__clbe630b9c_1124052559/gen/sle_stm_v1__clbe630b9c` uses 3_place SHA-256 `579488c24a18f9e8b385dae52bb05fda95c644b8a54946f800885817425cc282`.
- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_st_a_v1__cl989804f6__cl18eece69_1124052412/gen/sle_st_a_v1__cl989804f6__cl18eece69` uses 3_place SHA-256 `93d7b9fabae8ebe35f0828514ed434bc6a733ba1e8a640c728e1bd032c3f3420`.
- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_st_a_v2__pv30dda31f__pv88773f93_1124052447/gen/sle_st_a_v2__pv30dda31f__pv88773f93` uses 3_place SHA-256 `c2e8a3a1d695b74e8facd37cf2d7fce656551372fcc37003075e4846b368eb73`.
- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_st_a_v2__pv4242de79_1124052524/gen/sle_st_a_v2__pv4242de79` uses 3_place SHA-256 `ee2b93c0f4497dd3b325deb986b55fdf65e82462eb3a8ab333f5b99fec430de1`.
- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_st_a_v1__clfc5867a6__pvdf8e5ca4_1124052710/gen/slw_st_a_v1__clfc5867a6__pvdf8e5ca4` uses 3_place SHA-256 `66c6297519cf41f915babb25874f7c3dcea43c3d4d7a86df3d8fad4bdb1a1dd8`.
- `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_st_a_v2__cl9f076a5c_1124052745/gen/slw_st_a_v2__cl9f076a5c` uses 3_place SHA-256 `65f9d77b0fcea0b2527ef32ae88ad065edb72867dd92b4bbfd25109796b8eb01`.
