# KV 21:00 source cut and outer-hub physical follow-up

The live KV plan remains `4c5a163e9a21`, with adopted strict bind `1126113657`. The prepared zero-cycle cut is `5bee15cebae2`, source seal `121aa2c4217f`. It carries 40 field changes across 37 types for landing-pin clock clearance, Hroot and SYS_SD forwarded-clock stages, SYS_C local writer and abort paths, and IO reset-entry rows. Whole strict bind was clean across 93 types. As-built LATCHECK passed all 2,746 lanes. G0 and whole PRE passed with zero findings. Exact PHYv1 plan form `891850e4` was viewed and received GOOD for dry generation. The formal publication gate passed in commit `0c075894e2a`.

The source, sealed bind and referenced post-bind RTL are staged on epyc8, intel2, epyc7 and intel1. The ordinary four-host source guard `eff91d3fdf6f` passed. Use the strict carrier at `intel2:/srv/opentallas-scratch2/claude/kv-int-r2/c2100/codex/d/candidate.with_holds.json` at the intended cut. It retains existing holds and adds explicit Wi place and Eo/Wi/Wo route holds for the unchanged physical defects. No live switch or source-cut physical run has started.

The alternative `c9037cde0bff` passed whole PRE, strict bind, LATCHECK and G0. L2114 adds one cycle to 1,056 payload, valid, epoch and status bits into VPORT ES2 side 0. The effective external round trip rises from 80 to 81 cycles while side 1 stays at 52. Existing hard parameters and boot parameter bytes match. The additional cycle has approval for candidate work. This alternative remains private pending measured slot and side parity evidence.

## Hub source follow-up

The exact current Hub Eo detailed placement `00a749e64092` was reviewed independently and marked BAD. The lower and right ASTK macro passages are narrow. The placed census contains 40 groups needing stations and seven physical path families, with 2,102 legs over 405 µm. Retained R6 Eo reproduces the census. Wo is the direct sibling and shows all seven families. Both retained type definitions match the current plan byte-for-byte.

| Path family | Eo groups needing stations | Eo over 405 µm | Wo over 405 µm |
| --- | ---: | ---: | ---: |
| pDRAM write | 3 | 494 | 540 |
| XS traffic | 4 | 512 | 258 |
| Fan data and status | 6 | 363 | 398 |
| AM and calendar LPAD | 5 | 137 | 162 |
| Receiver rings and seams | 8 | 51 | 136 |
| Reset and fault | 14 | 18 | 28 |
| FT transport | 0 | 527 | 356 |

The reviewed partial same-cycle packet is on epyc7 at `/srv/opentallas-scratch2/claude/kv-int-r2/hub/eo-class-1126/eo_wo_reach_combo.ops.json`, SHA `9f8fffb3f6c8`. It moves existing Eo ft29/30/31 and Wo ft1/3 registers, eliminating 515 and 353 modeled long legs through macro-clear paths. The pDRAM fit reuses five existing ranks per hub and tops out at 389.610 and 368.982 µm after excluding those FT seats. Wo WS AM reuses six ranks and tops out at 349.569 µm. Seven other AM/calendar packed ranks are infeasible as single straight rows against their fixed endpoints and need bit-group placement. The packet checks against current and cut-D reserve geometry. No cycle change, reset-source reassignment, new route or adoption is implied.

The inherited Eo CTS-only run remains isolated. The native clock assignment reports t20 at 1,578 and t53 at 1,788 against a cap of 1,200. The native TT report has emitted worst setup slack −1,702.54 ps. FF remains open. Preserve the geometry and clock holds while closing phase, remaining FT face legs, XS/fan/receiver/reset paths and macro access.

The Hroot collector correction and exact SEQ relay-seat identity repair `f29ff9ed5063` passed scoped strict bind. Whole comparator lane ages, pads, clock and selected reset match. Independent plan review `a7587e2f` is GOOD for place-only. Its E7 stock controller is `kv-hroot-seq-seat-place-1126`. CTS and route remain held.
